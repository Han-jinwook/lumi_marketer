import asyncio
import random
import logging
import requests
import json
import re
from playwright.async_api import async_playwright
import sys
import os

# Add parent dir to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
import config
from crawler.db_handler import DBHandler

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Supabase Config
SUPABASE_URL = config.SUPABASE_URL
SUPABASE_KEY = config.SUPABASE_KEY
TABLE_NAME = "t_crawled_shops"

def save_to_db(shop_data):
    """
    Saves a single shop dict to Firebase via DBHandler.
    """
    db = DBHandler()
    if db.insert_shop_fs(shop_data):
        logger.info(f"✅ Firebase Saved: {shop_data.get('name')}")
        return True
    else:
        logger.error(f"❌ Firebase Save Failed: {shop_data.get('name')}")
        return False

async def run_target_crawl():
    keyword = "부평동 피부관리샵"
    target_count = 50
    total_saved = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Changed back to True for server env
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            viewport={"width": 412, "height": 915}
        )
        page = await context.new_page()
        
        logger.info(f"🔍 Searching: {keyword}")
        url = f"https://m.place.naver.com/place/list?query={keyword}"
        
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(20) # 목록 로드를 위해 충분한 대기 시간 부여
        
        # 목록이 로딩 중인지 확인 (스피너 등)
        try:
             # Wait for spinner to disappear if exists
             await page.wait_for_selector(".loading_spinner, .spinner, ._2LxpA", state="hidden", timeout=10000)
        except: pass
        
        # 목록이 바로 안 뜰 경우 스크롤 살짝 해보기
        await page.mouse.wheel(0, 500)
        await asyncio.sleep(5)
        
        # Ensure we are in list view (Wait for the list items)
        try:
            # Check for multiple possible item containers
            await page.wait_for_selector("li.VLTHu, li.item_root, li", timeout=30000)
            logger.info("Base list items detected.")
            
            # Explicitly wait for the specific shop list items
            try:
                # 여러 종류의 선택자 시도
                selectors = ["li.VLTHu", "li.item_root", "li[data-id]"]
                for sel in selectors:
                    try:
                        await page.wait_for_selector(sel, timeout=10000)
                        logger.info(f"List items detected with selector: {sel}")
                        break
                    except: continue
            except:
                logger.info("Specific list items not immediately visible. Checking '목록보기' (View List) button...")
                list_view_btn = page.locator("a:has-text('목록보기'), button:has-text('목록보기'), a._1_H8q").first
                if await list_view_btn.count() > 0:
                    await list_view_btn.click()
                    await asyncio.sleep(5)
        except Exception as e:
            logger.info(f"List items wait failed: {e}. Capturing debug screenshot...")
            await page.screenshot(path="debug_crawler_not_found.png")

        while total_saved < target_count:
            list_items = await page.locator("li.VLTHu").all()
            logger.info(f"Found {len(list_items)} items. Processing...")
            
            if not list_items:
                logger.warning("No items found with li.VLTHu. Trying generic li...")
                list_items = await page.locator("li").all()

            for li in list_items:
                if total_saved >= target_count: break
                
                try:
                    # Robust Selectors from research
                    # Name
                    name_node = li.locator("a.place_bluelink span").first
                    if await name_node.count() == 0: continue
                    name = (await name_node.text_content()).strip()
                    
                    # Link
                    link_node = li.locator("a.place_bluelink").first
                    href = await link_node.get_attribute("href")
                    place_id_match = re.search(r'/place/(\d+)', href)
                    if not place_id_match: continue
                    place_id = place_id_match.group(1)
                    detail_url = f"https://m.place.naver.com/place/{place_id}/home"
                    
                    instagram = ""
                    talk_url = ""
                    blog_id = ""
                    email = ""

                    # --- Step 1: Get Full Jibon Address 및 SNS/Email 정보 추출 ---
                    # 상세 페이지를 한 번만 방문하도록 통합
                    logger.info(f"Visiting detail page for {name} to get info...")
                    detail_page = await context.new_page()
                    await detail_page.goto(detail_url, wait_until="domcontentloaded")
                    await asyncio.sleep(random.uniform(2, 4))
                    
                    instagram = ""
                    talk_url = ""
                    blog_id = ""
                    email = ""

                    try:
                        # 1. Apollo State 추출 (가장 정확한 데이터 소스)
                        state = await detail_page.evaluate("() => window.__APOLLO_STATE__")
                        if state:
                            for key, val in state.items():
                                if not isinstance(val, dict): continue
                                # Instagram & Blog in homepages
                                if "homepages" in val and val["homepages"]:
                                    for hp in val["homepages"]:
                                        if not isinstance(hp, dict): continue
                                        hp_url = hp.get("url", "")
                                        if "instagram.com" in hp_url:
                                            insta_handle = hp_url.strip("/").split("/")[-1].split("?")[0]
                                            if insta_handle:
                                                instagram = f"https://www.instagram.com/{insta_handle}"
                                        elif "blog.naver.com" in hp_url:
                                            blog_handle = hp_url.strip("/").split("/")[-1].split("?")[0]
                                            if blog_handle:
                                                blog_id = f"https://blog.naver.com/{blog_handle}"
                                
                                # TalkTalk URL
                                if "talktalkUrl" in val and val["talktalkUrl"]:
                                    talk_url = val["talktalkUrl"].strip()
                        
                        # 2. DOM Fallback (Apollo State에 없을 경우)
                        content = await detail_page.content()
                        if not instagram:
                            match = re.search(r'instagram\.com/([a-zA-Z0-9._-]+)', content)
                            if match and match.group(1) not in ['p', 'reels', 'stories', 'explore']:
                                instagram = f"https://www.instagram.com/{match.group(1)}"
                        
                        if not talk_url:
                            match = re.search(r'talk\.naver\.com/([a-zA-Z0-9-]+)', content)
                            if match: 
                                tmp_talk = match.group(0) if match.group(0).startswith('http') else f"https://{match.group(0)}"
                                if not tmp_talk.endswith("/ch"):
                                    talk_url = tmp_talk

                        if not blog_id:
                            match = re.search(r'blog\.naver\.com/([a-zA-Z0-9-]+)', content)
                            if match: blog_id = f"https://blog.naver.com/{match.group(1)}"

                        # 3. Email Extraction from Description
                        desc_node = detail_page.locator("div.v_GvP, div.C_m_a, ._1Y_N8, .place_section_content").first
                        if await desc_node.count() > 0:
                            desc_text = await desc_node.text_content()
                            emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', desc_text)
                            if emails:
                                email = emails[0]

                        # Fallback for Email using Blog ID
                        if not email and blog_id and "blog.naver.com" in blog_id:
                            # Extract handle from https://blog.naver.com/handle
                            handle = blog_id.strip("/").split("/")[-1].split("?")[0]
                            if handle:
                                email = f"{handle}@naver.com"
                                logger.info(f"Generated fallback email from blog: {email}")
                    except Exception as e:
                        logger.error(f"Error extracting SNS/Email: {e}")
                    
                    full_address = ""
                    # Selector for address expansion
                    addr_anchor = detail_page.locator("a.PkgBl, a.uFxr1").first
                    if await addr_anchor.count() > 0:
                        await addr_anchor.click()
                        # Wait longer for the expansion/DOM update
                        await asyncio.sleep(3)
                        
                        # Debug: Capture screenshot of the expanded address area
                        await detail_page.screenshot(path="debug_address_expansion.png")
                        
                        # After click, find the section containing the Jibon address
                        # Based on screenshot, it's often inside a container with '지번' label and a '복사' (Copy) button
                        jibon_label = detail_page.locator("span:has-text('지번'), em:has-text('지번')").first
                        if await jibon_label.count() > 0:
                            # Get the parent or following text that contains the actual address
                            # In modern mobile view, it's often in the same line or a sibling div
                            actual_addr_node = detail_page.locator("div:has(> span:has-text('지번')), div:has(> em:has-text('지번'))").first
                            if await actual_addr_node.count() > 0:
                                raw_text = await actual_addr_node.text_content()
                                # Clean up formatting (e.g., remove labels and '복사' button text)
                                clean_addr = raw_text.replace("지번", "").replace("복사", "").strip()
                                full_address = clean_addr
                                logger.info(f"Extracted Jibon address via text matching: {full_address}")
                            else:
                                # Fallback to specific span siblings
                                jibon_span = detail_page.locator("span:has-text('지번') + span, em:has-text('지번') + span").first
                                if await jibon_span.count() > 0:
                                    full_address = (await jibon_span.text_content()).replace("복사", "").strip()
                                    logger.info(f"Extracted Jibon address via sibling: {full_address}")
                        
                        if not full_address:
                            # Try searching for text containing numbers (often lot numbers) in the address container
                            addr_container = detail_page.locator("div.v_GvP, div.PkgBl").first
                            if await addr_container.count() > 0:
                                container_text = await addr_container.text_content()
                                logger.warning(f"Jibon tag not found. Full container text: {container_text}")
                            
                            # Fallback to search list address if detail fails
                            addr_node = li.locator("a.uFxr1 span").first
                            if await addr_node.count() > 0:
                                full_address = (await addr_node.text_content()).strip()
                                logger.info(f"Using fallback address: {full_address}")
                    
                    await detail_page.close()

                    # Phone
                    phone = ""
                    tel_link = li.locator("a._T0lO[href^='tel:']").first
                    if await tel_link.count() > 0:
                        phone = (await tel_link.get_attribute("href")).replace("tel:", "")

                    shop_data = {
                        "name": name,
                        "address": full_address or "주소 확인 불가",
                        "phone": phone,
                        "owner_name": "",
                        "latitude": 0.0,
                        "longitude": 0.0,
                        "source_link": detail_url,
                        "email": email,
                        "instagram_handle": instagram,
                        "naver_blog_id": blog_id,
                        "talk_url": talk_url
                    }
                    
                    if save_to_db(shop_data):
                        total_saved += 1
                        logger.info(f"Progress: {total_saved}/{target_count}")
                        
                except Exception as e:
                    continue
            
            if total_saved < target_count:
                # Scroll more if needed
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                # Check if we still have the same number of items after scroll
                new_items = await page.locator("li").all()
                if len(new_items) <= len(list_items):
                    logger.info("No more items found.")
                    break
        
        await browser.close()
        logger.info(f"Target crawl finished. Total saved: {total_saved}")

if __name__ == "__main__":
    asyncio.run(run_target_crawl())
