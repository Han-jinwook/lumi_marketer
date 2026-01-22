import asyncio
import json
import random
from playwright.async_api import async_playwright

async def dump_state():
    search_keyword = "강남구 정앤정피부관리실"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print(f"🔍 Searching and visiting: {search_keyword}")
        await page.goto(f"https://m.place.naver.com/place/list?query={search_keyword}", wait_until="networkidle")
        await asyncio.sleep(2)
        
        # Click first item
        await page.locator("li a[href*='/place/']").first.click()
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        
        # Dump State
        state = await page.evaluate("window.__APOLLO_STATE__")
        if state:
            with open("debug_gangnam_apollo.json", "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            print("✅ Saved state to debug_gangnam_apollo.json")
        else:
            print("❌ No Apollo State found")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(dump_state())
