import asyncio
import logging
from playwright.async_api import async_playwright
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run():
    url = "https://m.place.naver.com/place/1669894270/home" # From.Me Gangnam
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page()
        
        logger.info(f"Going to {url}")
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(3)
        
        # Click Biz Info
        try:
             biz_btn = page.locator("a:has-text('사업자정보'), div[role='button']:has-text('사업자정보')").first
             if await biz_btn.count() > 0:
                 logger.info("Clicking Biz Info...")
                 await biz_btn.click(force=True)
                 await asyncio.sleep(2)
             else:
                 logger.warning("Biz Info button missing.")
        except Exception as e:
            logger.error(f"Click invalid: {e}")
            
        content = await page.content()
        with open("debug_simple.html", "w", encoding="utf-8") as f:
            f.write(content)
            
        # Email Check
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
        logger.info(f"Emails found: {emails}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
