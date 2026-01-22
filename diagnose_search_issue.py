import asyncio
import random
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def diagnose_search():
    keyword = "서울 피부관리샵"
    url = f"https://m.place.naver.com/place/list?query={keyword}"
    
    async with async_playwright() as p:
        logger.info("🚀 Launching Chrome...")
        try:
            browser = await p.chromium.launch(headless=True, timeout=10000)
            logger.info("✅ Chrome launched successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to launch browser: {e}")
            return

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 412, "height": 915}
        )
        page = await context.new_page()
        
        logger.info(f"🔍 Navigating to: {url}")
        try:
            # Change wait_until to domcontentloaded to avoid hanging on background network requests
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            logger.info("✅ Page navigation started (domcontentloaded).")
        except Exception as e:
            logger.error(f"❌ Navigation failed or timed out: {e}")
            await browser.close()
            return

        logger.info("⏳ Waiting 3 seconds for initial render...")
        await asyncio.sleep(3)
        
        try:
            await page.screenshot(path="debug_search_results.png")
            logger.info("📸 Saved debug_search_results.png")
        except Exception as e:
             logger.error(f"❌ Screenshot failed: {e}")
        
        # Check for Map View
        try:
            list_view_btn = page.locator("a:has-text('목록보기'), button:has-text('목록보기')").first
            if await list_view_btn.count() > 0:
                logger.info("🗺️ Map view detected. Clicking list view...")
                await list_view_btn.click(timeout=3000)
                await asyncio.sleep(3)
                await page.screenshot(path="debug_list_view.png")
                logger.info("📸 Saved debug_list_view.png")
        except Exception as e:
            logger.warning(f"⚠️ Map view check warning: {e}")

        # Test various selectors
        selectors = ["li.VLTHu", "li[data-id]", "li.item_root", "li.UE77Y", "li.u7tT8", "div.lp_list_place > ul > li"]
        found_any = False
        for sel in selectors:
            try:
                count = await page.locator(sel).count()
                if count > 0:
                    logger.info(f"✅ Selector '{sel}' found {count} items.")
                    found_any = True
                else:
                    logger.info(f"❌ Selector '{sel}' found 0 items.")
            except Exception as e:
                logger.error(f"⚠️ Error checking selector {sel}: {e}")
            
        content = await page.content()
        with open("debug_search_page.html", "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("📄 Saved debug_search_page.html")
        
        await browser.close()
        logger.info("🏁 Diagnosis finished.")

if __name__ == "__main__":
    asyncio.run(diagnose_search())
