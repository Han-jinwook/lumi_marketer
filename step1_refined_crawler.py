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
from playwright_stealth import Stealth
import config
from crawler.db_handler import DBHandler
import time

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
TABLE_NAME = "t_crawled_shops"

def save_to_db(shop_data):
    """
    Saves a single shop dict to Firebase via DBHandler.
    Falls back to local JSON if Firebase fails.
    """
    try:
        db = DBHandler()
        if db.insert_shop_fs(shop_data):
            logger.info(f"✅ Firebase Saved: {shop_data.get('name')}")
            return True
        else:
            logger.error(f"❌ Firebase Save Failed: {shop_data.get('name')}")
            return False
    except Exception as e:
        logger.warning(f"⚠️ Firebase connection error: {e}")
        # Fallback: Save to local JSON
        try:
            local_file = "crawled_shops_emergency.json"
            data_list = []
            if os.path.exists(local_file):
                with open(local_file, "r", encoding="utf-8") as f:
                    try:
                        data_list = json.load(f)
                    except: pass
            
            data_list.append(shop_data)
            
            with open(local_file, "w", encoding="utf-8") as f:
                json.dump(data_list, f, ensure_ascii=False, indent=2)
                
            logger.info(f"💾 Saved to local file instead: {shop_data.get('name')}")
            return True
        except Exception as local_e:
            logger.error(f"❌ Local save also failed: {local_e}")
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
    except Exception as e:
        logger.warning(f"Failed to extract details for {shop_data.get('name')}: {e}")
        return False

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

async def run_crawler(target_area=None, target_count=10, resume=False):
    # Proactively try to install browsers in Cloud environments
    is_cloud = os.environ.get("STREAMLIT_RUNTIME_ENV") or "/home/appuser" in os.getcwd() or os.environ.get("STREAMLIT_SERVER_BASE_URL")
    if is_cloud:
        logger.info("☁️ Cloud environment detected. Ensuring Playwright browsers...")
        await install_playwright_browsers()
    
    # Target Keywords (Deep Scan Support)
    if target_area in config.CITY_MAP:
        logger.info(f"🔍 Deep Scan Mode: Expanding '{target_area}' to Dong-level keywords...")
        keywords = config.get_deep_keywords(target_area)
        logger.info(f"📂 Total sub-keywords to crawl: {len(keywords)}")
    elif target_area:
        keywords = [f"{target_area} 피부관리샵"]
    else:
        keywords = ["서울 강남구 피부관리샵"] 

    checkpoint_file = os.path.join(os.getcwd(), "crawler_checkpoint.json")
    start_index = 0
    
    if resume and os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                checkpoint_data = json.load(f)
                last_keyword = checkpoint_data.get("last_keyword")
                if last_keyword in keywords:
                    start_index = keywords.index(last_keyword) + 1
                    logger.info(f"⏭️ Resuming from index {start_index} (Last: {last_keyword})")
                else:
                    logger.info("ℹ️ Checkpoint keyword not found in current set. Starting from scratch.")
        except Exception as e:
            logger.error(f"⚠️ Error loading checkpoint: {e}")

    total_saved = 0
    keywords_to_run = keywords[start_index:]
    
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
                    headless=False,
                    args=launch_args
                )
            except Exception as e:
                logger.warning(f"System chromium failed: {e}")
        
        # Strategy 2: Fallback to Playwright's bundled browser
        if not browser:
            try:
                logger.info("🌐 Using Playwright bundled browser")
                browser = await p.chromium.launch(
                    headless=False,
                    args=launch_args
                )
            except Exception as e:
                logger.error(f"Failed to launch browser: {e}")
                raise
        
        # User-Agent Rotation
        user_agent = random.choice(config.USER_AGENTS)
        logger.info(f"🎭 Using User-Agent: {user_agent}")
        
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={"width": random.randint(375, 414), "height": random.randint(667, 915)},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            permissions=["geolocation"]
        )
        
        # Disable webdriver flag proactively
        # await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        
        # 🕵️ ACTIVATE STEALTH MODE
        logger.info("🕵️ Activating Playwright Stealth Mode...")
        await Stealth().apply_stealth_async(page)

        
        for keyword in keywords_to_run:
            if total_saved >= target_count: break
            
            logger.info(f"🔍 Searching: {keyword}")
            url = f"https://m.place.naver.com/place/list?query={keyword}"
            
            try:
                await page.goto(url, wait_until="networkidle")
                await asyncio.sleep(random.uniform(5, 8))
                
                # Block Detection
                content = await page.content()
                if "서비스 이용이 제한되었습니다" in content or "과도한 접근 요청" in content:
                    logger.error("🛑 IP Blocked by Naver. Stopping crawler to prevent further damage.")
                    print("🛑 CRITICAL: IP BLOCK DETECTED. PLEASE STOP AND WAIT.", flush=True)
                    await browser.close()
                    return
                
                # Check for Map View and switch to list if necessary (Stronger detection)
                # Naver often shows map first on mobile
                list_view_selectors = [
                    "a:has-text('목록보기')", "button:has-text('목록보기')",
                    "a:has-text('목록')", "button:has-text('목록')",
                    "._list_view_button", "[data-nclicks-code='listview']"
                ]
                
                for lv_sel in list_view_selectors:
                    btn = page.locator(lv_sel).first
                    if await btn.count() > 0 and await btn.is_visible():
                        logger.info(f"🗺️ Map view detected via '{lv_sel}'. Switching to list view...")
                        await btn.click()
                        await asyncio.sleep(random.uniform(3, 5))
                        break

                # Scroll to load more (Deep crawling)
                logger.info("🖱️ Scrolling to load all items...")
                last_height = 0
                for i in range(40): 
                     await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                     await asyncio.sleep(random.uniform(1.2, 1.8))
                     
                     new_height = await page.evaluate("document.body.scrollHeight")
                     if new_height == last_height: 
                         # Try one more time with a longer wait
                         await asyncio.sleep(2)
                         await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                         new_height = await page.evaluate("document.body.scrollHeight")
                         if new_height == last_height: break
                     last_height = new_height
                     if i % 10 == 0: logger.info(f"  .. scrolled {i} times")
                
                # Wait for items (Expanded list of potential selectors)
                selectors = [
                    "li.VLTHu", "li[data-id]", "li.item_root", "li.UE77Y", 
                    "div.UE77Y", "li.rY_pS", "div.rY_pS", "ul > li"
                ]
                list_items = []
                for sel in selectors:
                    items = await page.locator(sel).all()
                    # Filter for items that actually look like results (have links)
                    valid_items = []
                    for it in items:
                        if await it.locator("a[href*='/place/']").count() > 0:
                            valid_items.append(it)
                    
                    if len(valid_items) > 1: # Found a list
                        list_items = valid_items
                        logger.info(f"✅ Found list using selector: {sel}")
                        break
                
                if not list_items:
                    # Final fallback: any anchor with /place/ inside a list-like structure
                    list_items = await page.locator("a[href*='/place/']").all()

                logger.info(f"🔍 Found {len(list_items)} potential shops. Starting detail extraction...")
                
                shops_to_visit = []
                for li in list_items:
                    if len(shops_to_visit) >= (target_count - total_saved): break
                    
                    try:
                        # 1. Detect if li is the link itself or a container
                        link_node = None
                        tag_name = await li.evaluate("el => el.tagName.toLowerCase()")
                        href = await li.get_attribute("href")
                        
                        if tag_name == "a" and href and "/place/" in href:
                            link_node = li
                        else:
                            # Search for the primary place link inside container
                            potential_links = li.locator("a[href*='/place/']")
                            if await potential_links.count() > 0:
                                link_node = potential_links.first

                        if link_node:
                            href = await link_node.get_attribute("href")
                            match = re.search(r'/place/(\d+)', href)
                            if not match: continue
                            place_id = match.group(1)
                            detail_url = f"https://m.place.naver.com/place/{place_id}/home"
                            
                            # Clean Name extraction
                            raw_name = await link_node.text_content()
                            if not raw_name or len(raw_name.strip()) < 2:
                                # Try to find name in a span or div if link text is empty/icon
                                name_node = li.locator("span.TYpUv, span.name, .title").first
                                if await name_node.count() > 0:
                                    raw_name = await name_node.text_content()
                            
                            name = raw_name.replace("알림받기", "").replace("N예약", "").strip()
                            
                            phone = ""
                            try:
                                tel_link = li.locator("a[href^='tel:']").first
                                if await tel_link.count() > 0:
                                    tel_href = await tel_link.get_attribute("href")
                                    phone = tel_href.replace("tel:", "").strip()
                            except: pass
                            
                            # Deduplicate in the current batch
                            if not any(s['detail_url'] == detail_url for s in shops_to_visit):
                                shops_to_visit.append({
                                    "name": name if name else f"Shop_{place_id}",
                                    "phone": phone,
                                    "detail_url": detail_url,
                                    "source_link": detail_url,
                                    "keyword": keyword
                                })
                    except Exception as e: 
                        logger.debug(f"Error parsing list item: {e}")
                        continue

                logger.info(f"📍 Scheduled {len(shops_to_visit)} shops for detail extraction.")

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
                                # Standardized progress output for dashboard
                                print(f"Progress: {total_saved}/{target_count}", flush=True)
                                logger.info(f"✅ Saved ({total_saved}/{target_count}): {shop_data.get('name')}")
                        else:
                            logger.warning(f"⏩ Skipping shop {shop_data.get('name')} due to missing critical info (Address).")
                    
                    # Random delay between detail pages to avoid detection
                    # Increased delay with more variance
                    sleep_time = random.uniform(20, 70)
                    logger.info(f"⏳ Waiting {sleep_time:.1f}s before next shop...")
                    await asyncio.sleep(sleep_time)

                # ✅ Save checkpoint after each successful keyword (Dong)
                with open(checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump({"last_keyword": keyword, "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')}, f, ensure_ascii=False)
                logger.info(f"💾 Checkpoint saved: {keyword}")

            except Exception as e:
                 logger.error(f"Error processing keyword {keyword}: {e}")

        await browser.close()
        logger.info(f"✅ Finished. Total saved: {total_saved}")
        
        # Save final checkpoint as finished
        if keywords_to_run:
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump({"last_keyword": keywords_to_run[-1], "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')}, f, ensure_ascii=False)

if __name__ == "__main__":
    # Move immediate progress signaling to the ABSOLUTE START of execution
    # Argument parsing
    target = sys.argv[1] if len(sys.argv) > 1 else None
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    resume_mode = "--resume" in sys.argv
    
    # Clean up '--resume' from sys.argv[1] or [2] if it accidentally slipped in (common via CLI)
    if target == "--resume": target = None
    
    # 📢 THIS IS THE MOST CRITICAL LINE FOR DASHBOARD FEEDBACK
    print(f"Progress: 0/{count}", flush=True)
    
    # Check Environment
    is_cloud = os.environ.get("STREAMLIT_RUNTIME_ENV") or "/home/appuser" in os.getcwd() or os.environ.get("STREAMLIT_SERVER_BASE_URL")
    if is_cloud:
        print(f"DEBUG: Running on Cloud Environment. Python: {sys.executable}", flush=True)
    
    try:
        asyncio.run(run_crawler(target, count, resume=resume_mode))
        
        # 🎯 AUTOMATIC COMPETITOR EXTRACTION AFTER CRAWLING
        print("Progress: Finalizing...", flush=True)
        logger.info("🎯 Crawling complete. Starting automatic competitor extraction...")
        try:
            from extract_competitors import run_competitor_extraction
            run_competitor_extraction()
            logger.info("✅ All tasks (Crawl + Competitor Analysis) finished successfully!")
        except Exception as ce:
            logger.error(f"⚠️ Competitor extraction failed: {ce}")
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}", flush=True)
        logger.error(f"Engine crashed: {e}")
        sys.exit(1)
