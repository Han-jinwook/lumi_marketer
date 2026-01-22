import asyncio
import csv
import os
import random
import json
from playwright.async_api import async_playwright
import config

INPUT_FILE = "intermediate_links.csv"
OUTPUT_FILE = config.RAW_DATA_FILE

async def extract_details():
    print("[*] Starting Detail Extractor...")
    
    # 1. Load URLs to process
    urls_to_process = [] # list of (url, keyword)
    if os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 1:
                    urls_to_process.append((row[0], row[1] if len(row) > 1 else ""))
    else:
        print(f"[-] {INPUT_FILE} not found. Run step1_crawler.py first.")
        return

    print(f"[*] Loaded {len(urls_to_process)} URLs.")

    # 2. Check processed
    processed_urls = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Detail_Url'):
                    # Check if it has valid name, if not maybe retry? 
                    # For now assume if in file, it's done.
                    processed_urls.add(row['Detail_Url'])
    else:
        with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'Address', 'Dong', 'Phone', 'Link', 'Owner_Name', 'Latitude', 'Longitude', 'Detail_Url', 'Keyword'])
    
    remaining = [u for u in urls_to_process if u[0] not in processed_urls]
    print(f"[*] Remaining: {len(remaining)} shops.")
    
    # 3. Process in Batches
    BATCH_SIZE = 5
    for i in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[i:i+BATCH_SIZE]
        print(f"\n[batch] Processing {i+1}-{i+len(batch)} / {len(remaining)}")
        
        # New Browser for every batch
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False, # Must be False
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
                    viewport={"width": 390, "height": 844},
                    device_scale_factor=3,
                    is_mobile=True,
                    has_touch=True
                )
                await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                page = await context.new_page()
                
                for url, keyword in batch:
                    try:
                        print(f"    Processing: {url}")
                        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(random.uniform(2.0, 3.0))
                        
                        shop_data = {
                            'Name': '', 'Address': '', 'Dong': '', 'Phone': '', 
                            'Link': '', 'Owner_Name': '', 'Latitude': 0, 'Longitude': 0,
                            'Detail_Url': url, 'Keyword': keyword
                        }
                        
                        # Method 1: JSON-LD
                        try:
                            json_data = await page.evaluate("""() => {
                                const el = document.querySelector('script[type="application/ld+json"]');
                                return el ? el.innerText : null;
                            }""")
                            if json_data:
                                d = json.loads(json_data)
                                if isinstance(d, list): d = d[0]
                                shop_data['Name'] = d.get('name', '')
                                shop_data['Phone'] = d.get('telephone', '')
                                addr = d.get('address', {})
                                if isinstance(addr, dict):
                                    shop_data['Address'] = addr.get('streetAddress', '')
                                else:
                                    shop_data['Address'] = str(addr)
                                if 'geo' in d:
                                    shop_data['Latitude'] = d['geo'].get('latitude')
                                    shop_data['Longitude'] = d['geo'].get('longitude')
                        except: pass
                        
                        # Method 2: Apollo State (Redundant fallback)
                        # ...
                        
                        # Method 3: DOM Fallback (If Name missing)
                        if not shop_data['Name']:
                             try:
                                 # Title often has name
                                 t = await page.title()
                                 shop_data['Name'] = t.replace(' : 네이버 플레이스', '')
                             except: pass
                             
                        # Dong Extraction
                        if shop_data['Address']:
                             for part in shop_data['Address'].split():
                                 if part.endswith('동') or part.endswith('가'):
                                     shop_data['Dong'] = part
                                     break
                                     
                        # Save if we got Name which is minimum
                        if shop_data['Name']:
                            with open(OUTPUT_FILE, 'a', encoding='utf-8', newline='') as f:
                                writer = csv.DictWriter(f, fieldnames=shop_data.keys())
                                writer.writerow(shop_data)
                            print(f"      [Success] {shop_data['Name']}")
                        else:
                            print(f"      [Failed] Could not extract name.")
                            # Dump HTML for debugging this specific failure
                            with open(f"failed_extract_{random.randint(1000,9999)}.html", "w", encoding="utf-8") as f:
                                f.write(await page.content())
                                
                    except Exception as e:
                        print(f"      [Error] {e}")
                        
                await browser.close()
                await asyncio.sleep(1) # Cool down
                
        except Exception as e:
            print(f"[CRITICAL] Browser/Batch Error: {e}")
            await asyncio.sleep(5)
            # Continue to next batch

if __name__ == "__main__":
    asyncio.run(extract_details())
