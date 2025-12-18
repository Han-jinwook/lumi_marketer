import asyncio
import random
import logging
import requests
import json
import re
from playwright.async_api import async_playwright
import config

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Supabase Config
SUPABASE_URL = config.SUPABASE_URL
SUPABASE_KEY = config.SUPABASE_KEY
TABLE_NAME = "t_crawled_shops"

def save_to_db(shop_data):
    """
    Saves a single shop dict to Supabase directly via HTTP.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase credentials missing.")
        return False
        
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    
    endpoint = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?on_conflict=detail_url"
    
    try:
        resp = requests.post(endpoint, headers=headers, json=shop_data)
        if resp.status_code in [200, 201, 204]:
            logger.info(f"✅ DB Saved: {shop_data.get('name')}")
            return True
        elif resp.status_code == 409:
            logger.info(f"⚠️ DB Duplicate: {shop_data.get('name')}")
            return True
        else:
            logger.error(f"❌ DB Save Failed: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.error(f"❌ DB Request Error: {e}")
        return False

async def run_crawler():
    # Target Keywords
    keywords = ["서울 강남구 피부관리샵"] 
    target_count = 10
    total_saved = 0
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                channel="msedge", 
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled", 
                    "--no-sandbox", 
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ]
            )
        except:
             logger.warning("Edge channel failed, trying chrome.")
             browser = await p.chromium.launch(
                channel="chrome",
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled", 
                    "--no-sandbox", 
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ]
            )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            # viewport={"width": 412, "height": 915} # Let it auto-size
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
                
                # Scroll to load at least some
                for _ in range(2):
                     await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                     await asyncio.sleep(random.uniform(1, 2))
                
                
                # Check for items
                list_items = await page.locator("li").all()
                logger.info(f"Found {len(list_items)} list items (potential shops).")

                logger.info(f"Found {len(list_items)} list items (potential shops).")
                
                if len(list_items) == 0:
                    logger.warning("Found 0 items. Dumping page...")
                    await page.screenshot(path="debug_screenshot.png")
                    with open("debug_page.html", "w", encoding="utf-8") as f:
                         f.write(await page.content())

                
                for li in list_items:
                    if total_saved >= target_count:
                        logger.info(f"🎯 Target count {target_count} reached. Stopping.")
                        break

                    try:
                        # Prioritize the Title Link which usually has class 'place_bluelink'
                        # This avoids picking up the thumbnail link which might come first
                        link_node = li.locator("a.place_bluelink[href*='/place/']")
                        if await link_node.count() == 0:
                            # Fallback to any place link
                             link_node = li.locator("a[href*='/place/']")
                        
                        link_node = link_node.first
                        
                        if await link_node.count() > 0:
                            href = await link_node.get_attribute("href")
                            
                            # ID Extraction
                            match = re.search(r'/place/(\d+)', href)
                            if not match: continue
                            place_id = match.group(1)
                            detail_url = f"https://m.place.naver.com/place/{place_id}"
                            
                            # Name Extraction
                            # Get text from the link, which is usually the shop name in the list title
                            # Sometimes there are spans inside, use text_content()
                            raw_name = await link_node.text_content()
                            
                            # Address Extraction
                            text_content = await li.text_content()
                            # Match generic Korean address pattern
                            addr_match = re.search(r'((?:서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)[가-힣]*\s+[가-힣]+(?:시|군|구)?\s+[가-힣]+(?:동|읍|면|가|로))', text_content)
                            address = addr_match.group(1) if addr_match else ""
                            
                            # Phone Extraction (Look for tel: link)
                            phone = ""
                            try:
                                tel_link = li.locator("a[href^='tel:']").first
                                if await tel_link.count() > 0:
                                    tel_href = await tel_link.get_attribute("href")
                                    phone = tel_href.replace("tel:", "")
                            except: pass

                            # Refined Name Extraction
                            # The name is often the first span with substantial text inside the link container
                            # or specifically styled.
                            # We will try to find the 'title' element.
                            # Usually the structure is: <div> <span class="name">Name</span> <span class="category">Cat</span> </div>
                            
                            try:
                                # DEBUG: Dump outerHTML to find the real name element
                                html = await link_node.evaluate("el => el.outerHTML")
                                if total_saved == 0:
                                    # logger.info(f"DEBUG HTML STRUCTURE: {html}")
                                    with open("debug_node_structure.html", "w", encoding="utf-8") as f:
                                        f.write(html)

                                    
                                # ... existing logic ...
                                title_elem = link_node.locator(".place_bluelink").first
                                if await title_elem.count() > 0:
                                    # Use JS to strictly get the first span's text to avoid any Playwright text merging issues
                                    candidate_name = await title_elem.evaluate("""el => {
                                        const span = el.querySelector('span');
                                        return span ? span.textContent : el.textContent;
                                    }""")
                                    
                                    candidate_name = candidate_name.strip()
                                
                                # If still empty, iterate spans as backup but be careful
                                if not candidate_name:
                                    spans = await link_node.locator("span").all()
                                    for span in spans:
                                        t = await span.text_content()
                                        t = t.strip()
                                        if not t: continue
                                        
                                        # Skip irrelevant
                                        if t in ["알림받기", "예약", "주문", "쿠폰", "N배달", "영수증리뷰", "블로그리뷰", "방문자리뷰", "이미지수", "새로오픈"]: continue
                                        if t.isdigit(): continue
                                        if "리뷰" in t: continue
                                        
                                        cls = await span.get_attribute("class") or ""
                                        if "blind" in cls: continue
                                        if "place_thumb_count" in cls: continue
                                        
                                        logger.info(f"CANDIDATE: {t} (class={cls})")
                                        candidate_name = t
                                        break
                                name = candidate_name
                            except:
                                name = await link_node.text_content()
                            
                            name = name.strip() if name else ""
                            name = name.replace("알림받기", "").strip()

                            # Remove common suffix if present in name (naive cleanup)
                            if "," in name: # "Name, Category" sometimes happens
                                name = name.split(",")[0].strip()

                            # If address is empty, it might be an ad or irrelevant item
                            if not address:
                                continue
                            
                            logger.info(f"Processing: {name} | {address} | {phone}")

                            shop_data = {
                                "name": name,
                                "address": address, 
                                "phone": phone,
                                "detail_url": detail_url,
                                "owner_name": "", 
                                "latitude": 0.0,
                                "longitude": 0.0,
                                "source_link": detail_url,
                            }
                            
                            # Attempt DB Save
                            if save_to_db(shop_data):
                                total_saved += 1
                                logger.info(f"Progress: {total_saved}/{target_count}")
                            
                            await asyncio.sleep(0.5) # Slight delay
                            
                    except Exception as e:
                        logger.warning(f"Item parse error: {e}")
                        pass
                
            except Exception as e:
                 logger.error(f"Error processing keyword {keyword}: {e}")

        await browser.close()
        logger.info(f"✅ Finished. Total saved: {total_saved}")

if __name__ == "__main__":
    asyncio.run(run_crawler())
