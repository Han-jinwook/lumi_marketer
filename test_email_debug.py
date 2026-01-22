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
                ]
            )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
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
                logger.info(f"Phase 1: Found {len(list_items)} list items. Extracting basic info...")
                
                shops_to_process = []
                
                for li in list_items:
                    try:
                        # Prioritize the Title Link which usually has class 'place_bluelink'
                        link_node = li.locator("a.place_bluelink[href*='/place/']")
                        if await link_node.count() == 0: link_node = li.locator("a[href*='/place/']")
                        link_node = link_node.first
                        if await link_node.count() == 0: continue
                        
                        raw_name = await link_node.text_content()
                        # Debug Target
                        if "프롬미" in raw_name or len(shops_to_process) == 0: 
                             href = await link_node.get_attribute("href")
                             match = re.search(r'/place/(\d+)', href)
                             if match:
                                 place_id = match.group(1)
                                 detail_url = f"https://m.place.naver.com/place/{place_id}/home"
                                 shops_to_process.append({"name": raw_name.strip(), "detail_url": detail_url})
                                 logger.info(f"Targeting for Debug: {raw_name.strip()}")
                                 break 
                    except: pass
                
                if not shops_to_process:
                    logger.warning("No shops found for debug.")
                    continue

                logger.info(f"Phase 1 Debug Complete. Processing {shops_to_process[0]['name']}...")
                
                # Phase 2: Detail Extraction (Debug Mode)
                shop = shops_to_process[0]
                await page.goto(shop['detail_url'], wait_until="networkidle")
                await asyncio.sleep(4)
                
                # Try clicking '사업자정보' with forceful wait
                logger.info("Attempting to find 'Business Info' button...")
                try:
                     biz_btn = page.locator("a:has-text('사업자정보'), div[role='button']:has-text('사업자정보')").first
                     if await biz_btn.count() > 0:
                         logger.info("Found 'Business Info' button. Clicking...")
                         await biz_btn.click(force=True)
                         await asyncio.sleep(2)
                     else:
                         logger.warning("'Business Info' button NOT found.")
                except Exception as e:
                    logger.error(f"Click Error: {e}")
                
                content = await page.content()
                with open("debug_email_page.html", "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info("Dumped page HTML to debug_email_page.html")
                
                # Check for @ matches manually in log
                import re
                emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
                logger.info(f"ALL Raw Email Matches in HTML: {emails}")

            except Exception as e:
                 logger.error(f"Error processing keyword {keyword}: {e}")

        await browser.close()
        logger.info(f"✅ All Done. Total saved: {total_saved}")

if __name__ == "__main__":
    asyncio.run(run_crawler())
