import asyncio
import requests
import json
import re
from playwright.async_api import async_playwright
import config

async def enrich_coords():
    url = config.SUPABASE_URL
    key = config.SUPABASE_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    # 1. Fetch shops that need coordinate enrichment (Bupyeong-dong or identical center coords)
    # The center coords were 37.4906976, 126.723817
    center_lat = 37.4906976
    center_lng = 126.723817
    
    # query_url = f"{url}/rest/v1/t_crawled_shops?address=ilike.*부평동*&select=id,name,source_link,latitude,longitude"
    # Actually just grab anything with (0,0) or center_lat/lng
    query_url = f"{url}/rest/v1/t_crawled_shops?or=(latitude.eq.0,latitude.eq.{center_lat})&select=id,name,source_link"
    
    resp = requests.get(query_url, headers=headers)
    if resp.status_code != 200:
        print(f"[-] Failed to fetch shops: {resp.status_code}")
        return
    
    shops = resp.json()
    print(f"[*] Found {len(shops)} shops to enrich.")
    
    if not shops:
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        for shop in shops:
            shop_id = shop['id']
            name = shop['name']
            link = shop['source_link']
            
            if not link or "naver.com" not in link:
                continue
                
            print(f"[*] Processing [{name}]: {link}")
            
            page = await context.new_page()
            try:
                await page.goto(link, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
                
                # Method 1: Apollo State via window variable
                data_found = False
                try:
                    state = await page.evaluate("() => window.__APOLLO_STATE__")
                    if state:
                        # Find the PlaceDetailBase key
                        for key, val in state.items():
                            if key.startswith("PlaceDetailBase:") and "coordinate" in val:
                                coord = val["coordinate"]
                                lat = float(coord.get("y", 0))
                                lng = float(coord.get("x", 0))
                                if lat != 0:
                                    data_found = True
                                    break
                except Exception as e:
                    print(f"    [!] Apollo evaluate error: {e}")

                # Method 2: Navigation Links (Fallback)
                if not data_found:
                    content = await page.content()
                    # Look for longitude^126.xxx;latitude^37.xxx
                    nav_match = re.search(r'longitude\^([\d\.]+);latitude\^([\d\.]+)', content)
                    if nav_match:
                        lng = float(nav_match.group(1))
                        lat = float(nav_match.group(2))
                        data_found = True
                    else:
                        # Try another common pattern in scripts: "x":"126.xxx","y":"37.xxx"
                        # or "latitude":37.xxx,"longitude":126.xxx
                        lat_match = re.search(r'"y":\s*"([\d\.]+)"|"latitude":\s*([\d\.]+)', content)
                        lng_match = re.search(r'"x":\s*"([\d\.]+)"|"longitude":\s*([\d\.]+)', content)
                        if lat_match and lng_match:
                            lat = float(lat_match.group(1) or lat_match.group(2))
                            lng = float(lng_match.group(1) or lng_match.group(2))
                            data_found = True

                if data_found and lat != 0:
                    print(f"    [+] Found Coords: {lat}, {lng}")
                    # Update DB
                    update_data = {"latitude": lat, "longitude": lng}
                    update_url = f"{url}/rest/v1/t_crawled_shops?id=eq.{shop_id}"
                    upd_resp = requests.patch(update_url, headers=headers, json=update_data)
                    if upd_resp.status_code in [200, 204]:
                        print("    [+] DB Updated.")
                    else:
                        print(f"    [-] DB Update Failed: {upd_resp.status_code}")
                else:
                    print("    [-] Could not find coordinates in page.")
                    
            except Exception as e:
                print(f"    [-] Error processing {name}: {e}")
            finally:
                await page.close()
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(enrich_coords())
