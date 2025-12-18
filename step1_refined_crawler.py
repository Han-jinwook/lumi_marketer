import asyncio
import random
import logging
import requests
import json
import csv
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
    # Target Keywords - using specific dong to keep list small and relevant
    keywords = ["서울 강남구 피부관리샵"] 
    
    async with async_playwright() as p:
        try:
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
        except:
             logger.warning("Chrome channel failed, trying default.")
             browser = await p.chromium.launch(
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
            viewport={"width": 412, "height": 915}
        )
        
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        
        for keyword in keywords:
            logger.info(f"🔍 Searching: {keyword}")
            url = f"https://m.place.naver.com/place/list?query={keyword}"
            
            try:
                await page.goto(url, wait_until="networkidle")
                await asyncio.sleep(random.uniform(2, 4))
                
                # Scroll to load more
                for _ in range(3):
                     await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                     await asyncio.sleep(random.uniform(1, 2))
                
                # Extract List Items directly
                # Naver Place List Item Container usually has role="list" or similar.
                # Items are 'li'
                
                # Wait for items
                # Try specific selector based on observation or generic
                list_items = await page.locator("li").all()
                logger.info(f"Found {len(list_items)} list items (potential shops).")
                
                count = 0
                for li in list_items:
                    # Check if it's a shop item (has a link to /place/)
                    try:
                        link_node = li.locator("a[href*='/place/']").first
                        if await link_node.count() > 0:
                            href = await link_node.get_attribute("href")
                            
                            # ID Extraction
                            import re
                            match = re.search(r'/place/(\d+)', href)
                            if not match: continue
                            place_id = match.group(1)
                            detail_url = f"https://m.place.naver.com/place/{place_id}"
                            
                            # HEURISTIC EXTRACTION
                            text_content = await li.text_content()
                            
                            # Address Extraction using Regex
                            # Matches "Region District Dong" pattern commonly found in Korea addresses
                            import re
                            # Match generic Korean address pattern: City/Prov District Dong/Road
                            addr_match = re.search(r'((?:서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)[가-힣]*\s+[가-힣]+(?:시|군|구)?\s+[가-힣]+(?:동|읍|면|가|로))', text_content)
                            address = addr_match.group(1) if addr_match else ""
                            
                            # Phone Extraction (Look for tel: link)
                            phone = ""
                            try:
                                tel_link = li.locator("a[href^='tel:']").first
                                if await tel_link.count() > 0:
                                    tel_href = await tel_link.get_attribute("href")
                                    # href="tel:0507-1234-5678"
                                    phone = tel_href.replace("tel:", "")
                            except: pass

                            # Name Cleaning
                            # Try to extract just the name span if possible
                            # Usually the first non-empty span in the title block
                            # Or just split raw_name by known categories
                            name = raw_name.replace("알림받기", "").strip()
                            if name.endswith("피부,체형관리"):
                                name = name.replace("피부,체형관리", "").strip()
                                
                            if not name or "네이버 플레이스" in name:
                                if count < 5: logger.info(f"Skipping: Name {name}")
                                continue
                            
                            if count < 3:
                                logger.info(f"debug item: {name}, {address}, {phone}")

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
                                count += 1
                            
                    except Exception as e:
                        logger.warning(f"Item parse error: {e}")
                        pass
                
                logger.info(f"Processed {count} items for {keyword}")

            except Exception as e:
                 logger.error(f"Error processing keyword {keyword}: {e}")

        await browser.close()

# Remove the extract_detail function as we are doing list-only for now to stabilize
async def extract_detail(page, url):
    return {}

if __name__ == "__main__":
    asyncio.run(run_crawler())
