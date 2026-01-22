import asyncio
import requests
import json
import re
from playwright.async_api import async_playwright
import config

async def extract_missing_links():
    url = config.SUPABASE_URL
    key = config.SUPABASE_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    # 1. Fetch shops in Bupyeong-dong that are missing links
    query_url = f"{url}/rest/v1/t_crawled_shops?address=ilike.*부평동*&or=(instagram_handle.eq.'',talk_url.eq.'')&select=id,name,source_link"
    resp = requests.get(query_url, headers=headers)
    
    if resp.status_code != 200:
        print(f"[-] Failed to fetch shops: {resp.status_code}")
        return
    
    shops = resp.json()
    print(f"[*] Found {len(shops)} shops to check for missing links.")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 390, "height": 844}
        )
        
        for shop in shops:
            shop_id = shop['id']
            name = shop['name']
            link = shop['source_link']
            
            if not link: continue
            
            print(f"[*] Checking [{name}]: {link}")
            page = await context.new_page()
            
            try:
                await page.goto(link, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
                
                # Method 1: Apollo State
                insta = ""
                talk = ""
                
                state = await page.evaluate("() => window.__APOLLO_STATE__")
                if state:
                    for key, val in state.items():
                        # Instagram in homepages or similar
                        if "homepages" in val and val["homepages"]:
                            for hp in val["homepages"]:
                                hp_url = hp.get("url", "")
                                if "instagram.com" in hp_url:
                                    insta = hp_url.split("/")[-1].split("?")[0]
                        # TalkTalk
                        if "talktalkUrl" in val and val["talktalkUrl"]:
                            talk = val["talktalkUrl"]
                
                # Method 2: DOM Fallback
                if not insta:
                    insta_node = page.locator("a[href*='instagram.com']").first
                    if await insta_node.count() > 0:
                        insta_url = await insta_node.get_attribute("href")
                        insta = insta_url.split("/")[-1].split("?")[0]
                
                if not talk:
                    talk_node = page.locator("a[href*='talk.naver.com']").first
                    if await talk_node.count() > 0:
                        talk = await talk_node.get_attribute("href")

                if insta or talk:
                    print(f"    [+] Found: Insta={insta}, Talk={talk}")
                    # Update DB
                    update_data = {}
                    if insta: update_data["instagram_handle"] = insta
                    if talk: update_data["talk_url"] = talk
                    
                    upd_url = f"{url}/rest/v1/t_crawled_shops?id=eq.{shop_id}"
                    upd_resp = requests.patch(upd_url, headers=headers, json=update_data)
                    if upd_resp.status_code in [200, 204]:
                        print("    [+] DB Updated.")
                    else:
                        print(f"    [-] DB Update Failed: {upd_resp.status_code}")
                else:
                    print("    [-] No links found on page.")
                    
            except Exception as e:
                print(f"    [-] Error: {e}")
            finally:
                await page.close()
                await asyncio.sleep(1)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(extract_missing_links())
