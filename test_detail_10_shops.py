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
    
    # Updated Conflict Key: source_link
    endpoint = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?on_conflict=source_link"
    
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

import sys

async def run_crawler():
    # Target Keywords (from CLI or default)
    if len(sys.argv) > 1:
        # Join all args in case of spaces, e.g. "Seoul Gangnam"
        raw_keyword = " ".join(sys.argv[1:])
        # Ensure it has "피부관리샵" suffix if not present? 
        # Or just trust user input. user said "Select Region", so I'll construct the keyword in app.py.
        keywords = [f"{raw_keyword} 피부관리샵"]
        logger.info(f"🚀 CLI Triggered: Searching for '{keywords[0]}'")
    else:
        keywords = ["인천 부평구 부평동 피부관리샵"] 
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
                    if len(shops_to_process) >= target_count: break
                    
                    try:
                        # Prioritize the Title Link which usually has class 'place_bluelink'
                        link_node = li.locator("a.place_bluelink[href*='/place/']")
                        if await link_node.count() == 0:
                             link_node = li.locator("a[href*='/place/']")
                        link_node = link_node.first
                        
                        if await link_node.count() == 0: continue
                        
                        href = await link_node.get_attribute("href")
                        match = re.search(r'/place/(\d+)', href)
                        if not match: continue
                        place_id = match.group(1)
                        detail_url = f"https://m.place.naver.com/place/{place_id}/home"
                        
                        # Name Extraction (JS logic)
                        title_elem = link_node
                        candidate_name = await title_elem.evaluate("""el => {
                            const span = el.querySelector('span');
                            return span ? span.textContent : el.textContent;
                        }""")
                        name = candidate_name.strip()
                        name = name.replace("알림받기", "").strip()
                        if name.endswith("피부"): name = name[:-2] 
                        
                        # Address & Phone (Phase 1 Basic)
                        text_content = await li.text_content()
                        addr_match = re.search(r'((?:서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)[가-힣]*\s+[가-힣]+(?:시|군|구)?\s+[가-힣]+(?:동|읍|면|가|로))', text_content)
                        address = addr_match.group(1) if addr_match else ""
                        
                        phone = ""
                        try:
                            tel_link = li.locator("a[href^='tel:']").first
                            if await tel_link.count() > 0:
                                phone = (await tel_link.get_attribute("href")).replace("tel:", "")
                        except: pass

                        if not name: continue
                        
                        shop_data = {
                            "name": name,
                            "address": address, 
                            "phone": phone,
                            "detail_url": detail_url,
                            "id": place_id,
                            "source_link": detail_url
                        }
                        shops_to_process.append(shop_data)
                        logger.info(f"Captured List Item: {name}")
                        
                    except Exception as e:
                        logger.debug(f"List item error: {e}")
                        pass
                
                logger.info(f"Phase 1 Complete. Collected {len(shops_to_process)} shops. Starting Phase 2 (Details)...")
                
                # Phase 2: Detail Extraction
                for idx, shop in enumerate(shops_to_process):
                    logger.info(f"[{idx+1}/{len(shops_to_process)}] Processing Detail: {shop['name']}")
                    try:
                        await page.goto(shop['detail_url'], wait_until="networkidle")
                        await asyncio.sleep(random.uniform(2, 4))
                        
                        # A. Coordinates & Full Address from JSON
                        try:
                            data = await page.evaluate("window.__APOLLO_STATE__")
                            if data:
                                lat, lng = 0.0, 0.0
                                full_address = shop["address"] # default fallback
                                found_coords = False

                                for key, val in data.items():
                                    if "PlaceDetailBase" in key:
                                        # Extract Coords
                                        if "coordinate" in val:
                                            coord = val["coordinate"]
                                            lng = coord["x"]
                                            lat = coord["y"]
                                            found_coords = True
                                        
                                        # Extract Full Address
                                        if "roadAddress" in val and val["roadAddress"]:
                                            full_address = val["roadAddress"]
                                        elif "jibunAddress" in val and val["jibunAddress"]:
                                            full_address = val["jibunAddress"]
                                        
                                        if found_coords: break
                                
                                shop["latitude"] = float(lat)
                                shop["longitude"] = float(lng)
                                shop["address"] = full_address # Overwrite with Detailed Address
                                logger.info(f"   -> Coords: {lat}, {lng} | Addr: {full_address}")
                        except Exception as e:
                            logger.error(f"   -> JSON Error: {e}")
                            shop["latitude"] = 0.0
                            shop["longitude"] = 0.0

                        # B. Owner / Email / Insta from DOM
                        try:
                             # Try clicking '사업자정보' (often fails but worth trying)
                             biz_btn = page.locator("a:has-text('사업자정보')")
                             if await biz_btn.count() > 0:
                                 await biz_btn.click()
                                 await asyncio.sleep(1)
                             
                             full_text = await page.content()
                             
                             # Owner
                             owner_match = re.search(r'대표자\s*[:]\s*([가-힣]+)', full_text)
                             if owner_match:
                                 shop["owner_name"] = owner_match.group(1)
                                 logger.info(f"   -> Owner: {shop['owner_name']}")
                             else:
                                 shop["owner_name"] = ""
                             
                             # Email - Refined Regex to exclude image filenames
                             email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?!png|jpg|gif|svg|webp)[a-zA-Z]{2,}', full_text)
                             if email_match:
                                 email_candidate = email_match.group(0)
                                 # strict check
                                 if not any(ext in email_candidate for ext in ['.png', '.jpg', '.gif', '.svg', '.webp']):
                                     shop["email"] = email_candidate
                                     logger.info(f"   -> Email: {shop['email']}")

                             # Instagram
                             insta_link = page.locator("a[href*='instagram.com']").first
                             if await insta_link.count() > 0:
                                 shop["instagram_handle"] = await insta_link.get_attribute("href")
                                 logger.info(f"   -> Insta: {shop['instagram_handle']}")
                             
                             # Naver TalkTalk
                             talk_link = page.locator("a[href*='talk.naver.com']").first
                             if await talk_link.count() > 0:
                                 shop["talk_url"] = await talk_link.get_attribute("href")
                                 logger.info(f"   -> TalkTalk: {shop['talk_url']}")

                             # Naver Blog & Derived Email
                             blog_link = page.locator("a[href*='blog.naver.com']").first
                             if await blog_link.count() > 0:
                                 blog_url = await blog_link.get_attribute("href")
                                 try:
                                     # Extract ID: blog.naver.com/ID
                                     match = re.search(r'blog\.naver\.com/([a-zA-Z0-9_-]+)', blog_url)
                                     if match:
                                         blog_id = match.group(1)
                                         shop["naver_blog_id"] = blog_id
                                         
                                         # Fallback email
                                         if "email" not in shop or not shop["email"]:
                                             shop["email"] = f"{blog_id}@naver.com"
                                             logger.info(f"   -> Email (from Blog): {shop['email']}")
                                 except Exception as e:
                                     logger.debug(f"Blog parse error: {e}")

                        except Exception as e:
                             logger.debug(f"   -> DOM Error: {e}")

                        # Save Full Data to JSON for verification
                        with open("crawled_shops_full.json", "a", encoding="utf-8") as f:
                             json.dump(shop, f, ensure_ascii=False)
                             f.write("\n")

                        # Prepare DB Payload 
                        db_payload = shop.copy()
                        # Cleanup Schema Mismatch (removed keys)
                        for key in ["id", "dong", "detail_url", "near_500m_count"]:
                            if key in db_payload: del db_payload[key]
                        
                        if save_to_db(db_payload):
                            total_saved += 1
                        
                    except Exception as e:
                        logger.error(f"Failed Detail Page for {shop['name']}: {e}")
                    
                    await asyncio.sleep(2)
                
                logger.info(f"✅ Finished. Total with details saved: {final_count if 'final_count' in locals() else total_saved}")
                
            except Exception as e:
                 logger.error(f"Error processing keyword {keyword}: {e}")

        await browser.close()
        logger.info(f"✅ All Done. Total saved: {total_saved}")

if __name__ == "__main__":
    asyncio.run(run_crawler())
