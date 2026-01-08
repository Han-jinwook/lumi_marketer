import asyncio
import json
import os
from playwright.async_api import async_playwright
import requests
import sys

# Add parent dir to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
import config

async def diagnose_shop(url):
    print(f"[*] Diagnosing: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 390, "height": 844}
        )
        page = await context.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)
            
            state = await page.evaluate("() => window.__APOLLO_STATE__")
            if state:
                with open("debug_apollo_state.json", "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                print("[+] Saved Apollo State to debug_apollo_state.json")
                
                insta = ""
                talk = ""
                blog = ""
                email = ""
                
                # Check Apollo State
                for key, val in state.items():
                    # Instagram
                    if "homepages" in val and val["homepages"]:
                        for hp in val["homepages"]:
                            hp_url = hp.get("url", "")
                            if "instagram.com" in hp_url:
                                insta = hp_url.split("/")[-1].split("?")[0]
                                if not insta and len(hp_url.split("/")) > 1:
                                    insta = hp_url.split("/")[-2]
                            if "blog.naver.com" in hp_url:
                                blog = hp_url.split("/")[-1].split("?")[0]
                    
                    # TalkTalk
                    if "talktalkUrl" in val and val["talktalkUrl"]:
                        talk = val["talktalkUrl"]
                
                print(f"[Results from Apollo State]")
                print(f"  Instagram: {insta}")
                print(f"  TalkTalk: {talk}")
                print(f"  Blog ID: {blog}")
                
                # Try DOM
                print(f"[Checking DOM...]")
                insta_node = page.locator("a[href*='instagram.com']").first
                if await insta_node.count() > 0:
                    insta_dom = await insta_node.get_attribute("href")
                    print(f"  DOM Instagram: {insta_dom}")
                
                talk_node = page.locator("a[href*='talk.naver.com']").first
                if await talk_node.count() > 0:
                    talk_dom = await talk_node.get_attribute("href")
                    print(f"  DOM TalkTalk: {talk_dom}")
                
                blog_node = page.locator("a[href*='blog.naver.com']").first
                if await blog_node.count() > 0:
                    blog_dom = await blog_node.get_attribute("href")
                    print(f"  DOM Blog: {blog_dom}")
                    
                # E-mail is harder, usually in 'description' or needs specific searching
                desc_node = page.locator("div.C_m_a, ._1Y_N8, .place_section_content").first
                if await desc_node.count() > 0:
                    desc_text = await desc_node.text_content()
                    emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', desc_text)
                    if emails:
                        email = emails[0]
                        print(f"  Found Email in Desc: {email}")

            else:
                print("[-] Apollo State not found.")
                await page.screenshot(path="debug_diagnose_fail.png")

        except Exception as e:
            print(f"[-] Error during diagnosis: {e}")
        finally:
            await browser.close()

import re
if __name__ == "__main__":
    test_url = sys.argv[1] if len(sys.argv) > 1 else ""
    if not test_url:
        # Try to get one from DB
        import requests
        url = config.SUPABASE_URL
        key = config.SUPABASE_KEY
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        resp = requests.get(f"{url}/rest/v1/t_crawled_shops?address=ilike.*부평동*&select=source_link&limit=1", headers=headers)
        if resp.status_code == 200 and resp.json():
            test_url = resp.json()[0]['source_link']
            print(f"[*] Fetched test URL from DB: {test_url}")
        else:
            print("[-] No URL found in DB and no URL provided.")
            sys.exit(1)
            
    asyncio.run(diagnose_shop(test_url))
