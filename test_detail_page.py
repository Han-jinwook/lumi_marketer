import asyncio
import random
import re
import json
from playwright.async_api import async_playwright
import logging

# Logger setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_detail_test():
    # Example Target: A specific shop ID known to exist or just one from a list.
    # Let's use a generic search and pick the first one to simulate the flow.
    keyword = "서울 강남구 피부관리샵"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="msedge", 
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled", 
                "--no-sandbox", 
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # 1. First, search and get a Detail URL
        logger.info(f"🔍 Searching list to get a target...")
        await page.goto(f"https://m.place.naver.com/place/list?query={keyword}", wait_until="networkidle")
        await asyncio.sleep(2)
        
        try:
            # Find first link
            link = page.locator("a[href*='/place/']").first
            href = await link.get_attribute("href")
            # href might be /place/12345?entry=...
            place_id = re.search(r'/place/(\d+)', href).group(1)
            detail_url = f"https://m.place.naver.com/place/{place_id}/home"
            logger.info(f"🎯 Found Target ID: {place_id}, URL: {detail_url}")
            
            # 2. Go to Detail Page
            logger.info(f"🚀 Navigating to Detail Page: {detail_url}")
            await page.goto(detail_url, wait_until="networkidle")
            await asyncio.sleep(3)
            
            # 3. Extract Info
            # Dump HTML for analysis
            content = await page.content()
            with open("debug_detail_page.html", "w", encoding="utf-8") as f:
                f.write(content)
            
            # Try to find specific fields
            
            # A. Owner Name / Business Info
            # Usually hidden behind "펼쳐보기" (Expand) in the footer or info tab
            # We might need to click "정보" (Info) tab if we are on "home" tab and it's not there.
            # Usually m.place.naver.com/place/{id}/home has basic info.
            
            # Check for Instagram / Website
            # There is often a link with icon
            insta = ""
            try:
                # Look for links containing instagram
                insta_link = page.locator("a[href*='instagram.com']")
                if await insta_link.count() > 0:
                     insta = await insta_link.first.get_attribute("href")
                     logger.info(f"📸 Found Instagram: {insta}")
            except: pass
            
            # Check for Blog
            blog = ""
            try:
                blog_link = page.locator("a[href*='blog.naver.com']")
                if await blog_link.count() > 0:
                    blog = await blog_link.first.get_attribute("href")
                    logger.info(f"📝 Found Blog: {blog}")
            except: pass

            # Email
            # Often in the "Detail" tab or extracted from JSON
            
            # JS State Extraction (The Holy Grail)
            # window.__APOLLO_STATE__ contains everything usually
            data = await page.evaluate("window.__APOLLO_STATE__")
            if data:
                with open("debug_detail_state.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info("✅ Extracted __APOLLO_STATE__ from Detail Page!")
                
                # Basic parsing attempt of JSON
                # Look for 'root' or 'Place:{id}'
                # We can do offline analysis of the JSON file
            else:
                logger.warning("❌ No __APOLLO_STATE__ found.")

            # 4. Extract Coordinates from JSON (if valid)
            lat, lng = 0.0, 0.0
            if data:
                try:
                    # Find any PlaceDetailBase object
                    for key, val in data.items():
                        if "PlaceDetailBase" in key and "coordinate" in val:
                            coord = val["coordinate"]
                            lng = coord["x"] # Naver X is Longitude
                            lat = coord["y"] # Naver Y is Latitude
                            logger.info(f"📍 Coordinates Found: {lat}, {lng}")
                            break
                except Exception as e:
                    logger.error(f"Error parsing coordinates: {e}")

            # 5. Extract Detailed Business Info (Owner, Email) via DOM interaction
            # "사업자정보" is often a button we need to click
            try:
                biz_btn = page.locator("a:has-text('사업자정보')")
                if await biz_btn.count() > 0:
                     await biz_btn.click()
                     await asyncio.sleep(1)
                     # Now scrape the expanded info
                     biz_info_text = await page.locator(".biz_info_area").text_content() # Hypothetical class
                     # Or just dump the new text
                     full_text = await page.content()
                     if "대표" in full_text:
                         logger.info("found Representative keyword in page.")
                         # RegEx for Representative Name
                         match = re.search(r'대표자\s*[:]\s*([가-힣]+)', full_text)
                         if match:
                             logger.info(f"👤 Owner Name Candidate: {match.group(1)}")
                         
                     # Phone/Email
                     email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', full_text)
                     if email_match:
                         logger.info(f"📧 Email Found: {email_match.group(0)}")
            except: pass

            # 6. Test "Nearby Search"
            if lat and lng:
                logger.info("🔄 Testing Nearby Search using extracted coordinates...")
                # Naver Place List with specific location center
                nearby_url = f"https://m.place.naver.com/place/list?query={keyword}&x={lng}&y={lat}&radius=2000" # 2km radius
                await page.goto(nearby_url, wait_until="networkidle")
                await asyncio.sleep(3)
                
                # Check if we get results
                items = await page.locator("li").count()
                logger.info(f"🏘️ Found {items} nearby items for coordinate search.")
                
        except Exception as e:
            logger.error(f"Error: {e}")
            await page.screenshot(path="debug_detail_error.png")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_detail_test())
