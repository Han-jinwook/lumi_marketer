import asyncio
import random
import logging
import requests
import json
import csv
import sys
import os
import re
from playwright.async_api import async_playwright
import config
from crawler.db_handler import DBHandler

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
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

async def extract_detail_info(page, shop_data):
    """
    Visits the detail page and extracts rich information using Apollo State and DOM fallback.
    """
    try:
        url = shop_data['detail_url']
        logger.info(f"🔍 Visiting detail page: {shop_data['name']}")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(random.uniform(3, 5))
        
        # 1. Extract via Apollo State (Most Accurate)
        state = await page.evaluate("window.__APOLLO_STATE__")
        if state:
            for key, val in state.items():
                if not isinstance(val, dict): continue
                
                # PlaceDetailBase contains the core info
                if "PlaceDetailBase" in key:
                    # Clean Name
                    if "name" in val and val["name"]:
                        raw_name = val["name"].strip()
                        shop_data["name"] = raw_name.replace("알림받기", "").strip()
                    
                    # Full Address
                    if "roadAddress" in val and val["roadAddress"]:
                        shop_data["address"] = val["roadAddress"]
                    elif "address" in val and val["address"]:
                        shop_data["address"] = val["address"]
                    
                    # Coordinates
                    if "coordinate" in val:
                        coord = val["coordinate"]
                        shop_data["longitude"] = float(coord.get("x", 0.0))
                        shop_data["latitude"] = float(coord.get("y", 0.0))
                    
                    # TalkTalk
                    if "talktalkUrl" in val and val["talktalkUrl"]:
                        shop_data["talk_url"] = val["talktalkUrl"].strip()
                
                # Extract SNS Links from homepages section
                if "homepages" in val and val["homepages"]:
                    for hp in val["homepages"]:
                        if not isinstance(hp, dict): continue
                        hp_url = hp.get("url", "")
                        if "instagram.com" in hp_url:
                            # Normalize Instagram URL
                            insta_handle = hp_url.strip("/").split("/")[-1].split("?")[0]
                            if insta_handle and insta_handle not in ['p', 'reels', 'stories', 'explore']:
                                shop_data["instagram_handle"] = f"https://www.instagram.com/{insta_handle}"
                        elif "blog.naver.com" in hp_url:
                            shop_data["naver_blog_id"] = hp_url.strip()
                            # Fallback email from blog ID
                            if not shop_data.get("email"):
                                handle = hp_url.strip("/").split("/")[-1].split("?")[0]
                                if handle:
                                    shop_data["email"] = f"{handle}@naver.com"

        # 2. DOM Fallback & Advanced Extraction (Email from description)
        content = await page.content()
        
        # [NEW] Explicit mailto link check (Strong signal)
        if not shop_data.get("email"):
             try:
                mailto_link = page.locator("a[href^='mailto:']").first
                if await mailto_link.count() > 0:
                    href = await mailto_link.get_attribute("href")
                    if href:
                        shop_data["email"] = href.replace("mailto:", "").strip()
                        logger.info(f"📧 Found email via mailto: {shop_data['email']}")
             except: pass

        # Email Extraction from Description if not found yet
        if not shop_data.get("email"):
            emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', content)
            if emails:
                # Filter out image-like extensions in emails
                filtered_emails = [e for e in emails if not any(ext in e.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp'])]
                if filtered_emails:
                    shop_data["email"] = filtered_emails[0]
                    logger.info(f"📧 Found email in page content: {shop_data['email']}")

        # Owner Name (Representative)
        if not shop_data.get("owner_name"):
            owner_match = re.search(r'대표자\s*[:]\s*([가-힣]+)', content)
            if owner_match:
                shop_data["owner_name"] = owner_match.group(1)

        # 3. DOM Link Fallback (If Apollo failed)
        if not shop_data.get("instagram_handle") or not shop_data.get("naver_blog_id") or not shop_data.get("talk_url"):
            
            # Instagram Logic Improvement
            if not shop_data.get("instagram_handle"):
                # Strategy A: Regex search in full content (Fast)
                insta_match = re.search(r'href="(https://www\.instagram\.com/[^"]+)"', content)
                if insta_match:
                    candidate = insta_match.group(1).split("?")[0]
                    if not any(x in candidate for x in ['/p/', '/reels/', '/explore/', '/stories/']):
                         shop_data["instagram_handle"] = candidate
                
                # Strategy B: DOM Traversal (More robust for dynamic elements)
                if not shop_data.get("instagram_handle"):
                    try:
                        insta_links = await page.locator("a[href*='instagram.com']").all()
                        for link in insta_links:
                            href = await link.get_attribute("href")
                            if href:
                                clean_href = href.split("?")[0].strip()
                                if not any(x in clean_href for x in ['/p/', '/reels/', '/explore/', '/stories/']):
                                    shop_data["instagram_handle"] = clean_href
                                    break
                    except: pass
            
            # Naver Blog
            if not shop_data.get("naver_blog_id"):
                blog_match = re.search(r'href="(https://blog\.naver\.com/[^"]+)"', content)
                if blog_match:
                    shop_data["naver_blog_id"] = blog_match.group(1).split("?")[0]
                    # Also try to extract email from blog url
                    if not shop_data.get("email"):
                        handle = shop_data["naver_blog_id"].strip("/").split("/")[-1]
                        if handle: shop_data["email"] = f"{handle}@naver.com"

            # TalkTalk
            if not shop_data.get("talk_url"):
                talk_match = re.search(r'href="(https://talk\.naver\.com/[^"]+)"', content)
                if talk_match:
                    shop_data["talk_url"] = talk_match.group(1)

        return True
async def install_playwright_browsers():
    """
    Attempts to install playwright browsers if they are missing.
    Useful for Streamlit Cloud environments.
    """
    import subprocess
    try:
        logger.info("📦 Checking Playwright browsers...")
        # Check if chromium is already available via playwright
        # We try a simple command to see if it works
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], capture_output=True, check=True)
        logger.info("✅ Playwright browsers are ready.")
    except Exception as e:
        logger.warning(f"⚠️ Playwright install failed or already handled: {e}")

async def run_crawler(target_area=None, target_count=10):
    # Proactively try to install browsers in Cloud environments
    if os.environ.get("STREAMLIT_RUNTIME_ENV") or "/home/appuser" in os.getcwd():
        await install_playwright_browsers()

    # Target Keywords
    if target_area:
        keywords = [f"{target_area} 피부관리샵"]
    else:
        keywords = ["서울 강남구 피부관리샵"] 
    
    total_saved = 0
    
    async with async_playwright() as p:
        # Cloud-Compatible Browser Launch Logic
        browser = None
        launch_args = [
            "--disable-blink-features=AutomationControlled", 
            "--no-sandbox", 
            "--disable-setuid-sandbox", 
            "--disable-dev-shm-usage",
            "--disable-gpu"
        ]
        
        # Strategy 1: Try system chromium (for Streamlit Cloud / Linux)
        if os.path.exists("/usr/bin/chromium"):
            try:
                logger.info("🌐 Using system chromium at /usr/bin/chromium")
                browser = await p.chromium.launch(
                    executable_path="/usr/bin/chromium",
                    headless=True,
                    args=launch_args
                )
            except Exception as e:
                logger.warning(f"System chromium failed: {e}")
        
        # Strategy 2: Fallback to Playwright's bundled browser
        if not browser:
            try:
                logger.info("🌐 Using Playwright bundled browser")
                browser = await p.chromium.launch(
                    headless=True,
                    args=launch_args
                )
            except Exception as e:
                logger.error(f"Failed to launch browser: {e}")
                raise
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 412, "height": 915},
            locale="ko-KR",
            timezone_id="Asia/Seoul"
        )
        
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        
        for keyword in keywords:
            if total_saved >= target_count: break
            
            logger.info(f"🔍 Searching: {keyword}")
            url = f"https://m.place.naver.com/place/list?query={keyword}"
            
            try:
                await page.goto(url, wait_until="networkidle")
                await asyncio.sleep(random.uniform(2, 4))
                
                # Check for Map View and switch to list if necessary
                list_view_btn = page.locator("a:has-text('목록보기'), button:has-text('목록보기')")
                if await list_view_btn.count() > 0:
                    logger.info("🗺️ Map view detected. Switching to list view...")
                    await list_view_btn.first.click()
                    await asyncio.sleep(random.uniform(2, 4))

                # Scroll to load more
                for _ in range(3):
                     if total_saved >= target_count: break
                     await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                     await asyncio.sleep(random.uniform(1, 2))
                
                # Wait for items
                selectors = ["li.VLTHu", "li[data-id]", "li.item_root"]
                list_items = []
                for sel in selectors:
                    items = await page.locator(sel).all()
                    if len(items) > 0:
                        list_items = items
                        break
                
                if not list_items:
                    list_items = await page.locator("li").all()

                logger.info(f"Found {len(list_items)} list items. Extracting basic info...")
                
                shops_to_visit = []
                for li in list_items:
                    if len(shops_to_visit) >= (target_count - total_saved): break
                    
                    try:
                        link_node = li.locator("a[href*='/place/']").first
                        if await link_node.count() > 0:
                            href = await link_node.get_attribute("href")
                            
                            match = re.search(r'/place/(\d+)', href)
                            if not match: continue
                            place_id = match.group(1)
                            detail_url = f"https://m.place.naver.com/place/{place_id}/home"
                            
                            raw_name = await link_node.text_content()
                            name = raw_name.replace("알림받기", "").strip()
                            
                            phone = ""
                            try:
                                tel_link = li.locator("a[href^='tel:']").first
                                if await tel_link.count() > 0:
                                    tel_href = await tel_link.get_attribute("href")
                                    phone = tel_href.replace("tel:", "")
                            except: pass
                            
                            shops_to_visit.append({
                                "name": name,
                                "phone": phone,
                                "detail_url": detail_url,
                                "source_link": detail_url,
                                "keyword": keyword
                            })
                    except: continue

                # Visit each shop's detail page
                for shop_data in shops_to_visit:
                    if total_saved >= target_count: break
                    
                    shop_data.update({
                        "owner_name": "",
                        "address": "",
                        "latitude": 0.0,
                        "longitude": 0.0,
                        "email": "",
                        "instagram_handle": "",
                        "naver_blog_id": "",
                        "talk_url": ""
                    })

                    if await extract_detail_info(page, shop_data):
                        if shop_data.get("name") and shop_data.get("address"):
                            if save_to_db(shop_data):
                                total_saved += 1
                                logger.info(f"Progress: {total_saved}/{target_count}")
                        else:
                            logger.warning(f"⏩ Skipping shop {shop_data.get('name')} due to missing critical info (Address).")
                    
                    await asyncio.sleep(random.uniform(15, 20))

            except Exception as e:
                 logger.error(f"Error processing keyword {keyword}: {e}")

        await browser.close()
        logger.info(f"✅ Finished. Total saved: {total_saved}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    asyncio.run(run_crawler(target, count))
