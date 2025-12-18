import asyncio
from playwright.async_api import async_playwright
import json

from playwright_stealth import stealth_async

URL = "https://m.place.naver.com/place/1503740004"

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        )
        page = await context.new_page()
        await stealth_async(page)
        
        print(f"Visiting {URL}")
        await page.goto(URL, wait_until="networkidle")
        await asyncio.sleep(2)
        
        # 1. HTML
        html = await page.content()
        with open("debug_shop.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        # 2. JSON LD
        json_ld = await page.evaluate("""() => {
            const scripts = document.querySelectorAll('script[type="application/ld+json"]');
            return Array.from(scripts).map(s => s.innerText);
        }""")
        
        print(f"JSON LD found: {len(json_ld)}")
        for i, j in enumerate(json_ld):
            print(f"--- JSON {i} ---")
            print(j[:500])
            with open(f"debug_json_{i}.json", "w", encoding="utf-8") as f:
                f.write(j)
            
        # 3. DOM Checks
        title = await page.title()
        print(f"Title: {title}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
