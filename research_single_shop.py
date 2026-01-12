import asyncio
import requests
import json
import re
import os
import sys
import random
from playwright.async_api import async_playwright

# Add current dir to path to import config
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import config

async def research_shop(shop_id):
    url = config.SUPABASE_URL
    key = config.SUPABASE_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    # 1. Fetch shop info
    query_url = f"{url}/rest/v1/t_crawled_shops?id=eq.{shop_id}&select=id,name,source_link"
    resp = requests.get(query_url, headers=headers)
    
    if resp.status_code != 200 or not resp.json():
        print(f"[-] Failed to fetch shop info or shop not found: {resp.status_code}")
        return
    
    shop = resp.json()[0]
    name = shop['name']
    link = shop['source_link']
    
    if not link:
        print(f"[-] No source_link for {name}. Cannot re-search.")
        return
    
    print(f"[*] Re-searching [{name}]...")
    
    async with async_playwright() as p:
        # Using headless=True for background execution
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        try:
            # Visit Home Page
            await page.goto(link, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5)
            
            # Extract SNS and Email (similar logic to fill_missing_links.py)
            content = await page.content()
            
            insta, talk, blog, email = "", "", "", ""
            
            # Try Apollo State first
            try:
                state = await page.evaluate("() => window.__APOLLO_STATE__")
                if state:
                    for k, val in state.items():
                        if not isinstance(val, dict): continue
                        if "homepages" in val and val["homepages"]:
                            for hp in val["homepages"]:
                                if not isinstance(hp, dict): continue
                                hp_url = hp.get("url", "")
                                if "instagram.com" in hp_url:
                                    insta_handle = hp_url.strip("/").split("/")[-1].split("?")[0]
                                    if insta_handle: insta = f"https://www.instagram.com/{insta_handle}"
                                elif "blog.naver.com" in hp_url:
                                    blog_handle = hp_url.strip("/").split("/")[-1].split("?")[0]
                                    if blog_handle: blog = f"https://blog.naver.com/{blog_handle}"
                        if "talktalkUrl" in val and val["talktalkUrl"]:
                            talk = val["talktalkUrl"]
            except: pass

            # Regex Fallbacks
            if not insta:
                match = re.search(r'instagram\.com/([a-zA-Z0-9._-]+)', content)
                if match and match.group(1) not in ['p', 'reels', 'stories', 'explore']:
                    insta = f"https://www.instagram.com/{match.group(1)}"
            if not talk:
                match = re.search(r'talk\.naver\.com/([a-zA-Z0-9-]+)', content)
                if match:
                    talk = match.group(0)
                    if not talk.startswith('http'): talk = f"https://{talk}"
            if not blog:
                match = re.search(r'blog\.naver\.com/([a-zA-Z0-9-]+)', content)
                if match: blog = f"https://blog.naver.com/{match.group(1)}"

            # Email Extraction
            desc_text = await page.evaluate("() => document.body.innerText")
            emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', desc_text)
            if emails: email = emails[0]

            # Update DB
            update_data = {}
            if insta: update_data["instagram_handle"] = insta
            if talk: update_data["talk_url"] = talk
            if blog: update_data["naver_blog_id"] = blog
            if email: update_data["email"] = email
            
            if update_data:
                print(f"    [+] Found: {update_data}")
                upd_url = f"{url}/rest/v1/t_crawled_shops?id=eq.{shop_id}"
                upd_resp = requests.patch(upd_url, headers=headers, json=update_data)
                if upd_resp.status_code in [200, 204]:
                    print("    [+] DB Updated successfully.")
                else:
                    print(f"    [-] DB Update Failed: {upd_resp.status_code}")
            else:
                print("    [-] No new information found.")
                
        except Exception as e:
            print(f"    [-] Error during research: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python research_single_shop.py <shop_id>")
    else:
        asyncio.run(research_shop(sys.argv[1]))
