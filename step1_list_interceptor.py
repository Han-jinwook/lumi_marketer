import asyncio
import json
from playwright.async_api import async_playwright

URL = "https://m.place.naver.com/place/list?query=청라동 피부관리샵"

async def intercept():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
            viewport={"width": 390, "height": 844}
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        
        # Capture Responses
        async def handle_response(response):
            if "json" in response.headers.get("content-type", ""):
                try:
                    url = response.url
                    if "place" in url or "graphql" in url or "search" in url:
                        print(f"Captured API: {url}")
                        text = await response.text()
                        if len(text) > 1000:
                            fname = f"debug_api_{url.split('?')[-1][:20].replace('/','_')}.json"
                            # sanitize filename
                            fname = "".join(c for c in fname if c.isalnum() or c in "._-")
                            with open(fname, "w", encoding="utf-8") as f:
                                f.write(text)
                except: pass
                
        page.on("response", handle_response)
        
        print(f"Visiting {URL}")
        await page.goto(URL, wait_until="networkidle")
        
        # Scroll a bit to trigger more data
        print("Scrolling...")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(intercept())
