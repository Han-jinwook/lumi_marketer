import requests
import json
import re
import logging
import config

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = config.SUPABASE_URL
SUPABASE_KEY = config.SUPABASE_KEY
TABLE_NAME = "t_crawled_shops"

def save_to_db(shop_data):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    endpoint = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?on_conflict=detail_url"
    try:
        resp = requests.post(endpoint, headers=headers, json=shop_data)
        if resp.status_code in [200, 201, 204]:
            logger.info(f"✅ DB Saved: {shop_data.get('name')}")
            return True
        elif resp.status_code == 409:
            logger.info(f"⚠️ DB Duplicate: {shop_data.get('name')}")
            return True
        else:
            logger.error(f"❌ DB Save Failed: {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ DB Request Error: {e}")
        return False

def run_test():
    keyword = "서울 강남구 피부관리샵"
    url = f"https://m.place.naver.com/place/list?query={keyword}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://m.place.naver.com/"
    }
    
    logger.info(f"Fetching {url}...")
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        logger.info(f"Status Code: {resp.status_code}")
        
        if "서비스 이용이 제한되었습니다" in resp.text:
            logger.error("🚫 Blocked by Naver (IP Block/Captcha).")
            return

        html = resp.text
        
        # Extract __APOLLO_STATE__
        match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.*?});', html, re.DOTALL)
        if not match:
            # Try finding via index if regex fails (sometimes structure varies)
             start = html.find('window.__APOLLO_STATE__ = {')
             if start != -1:
                 end = html.find('</script>', start)
                 json_str = html[start + 26 : end].strip()
                 if json_str.endswith(';'): json_str = json_str[:-1]
                 try:
                     state = json.loads(json_str)
                 except: 
                     state = None
             else:
                 state = None
        else:
            try:
                state = json.loads(match.group(1))
            except:
                state = None
                
        if not state:
            logger.error("❌ Could not extract state from HTML.")
            # write debug
            with open("debug_requests_fail.html", "w", encoding="utf-8") as f:
                f.write(html)
            return
            
        logger.info("✅ Extracted State! Parsing items...")
        
        # Parse items from state
        # The structure is flattened in Apollo client cache usually
        # We look for keys that look like shops
        
        items_saved = 0
        target = 10
        
        for key, value in state.items():
            if items_saved >= target: break
            
            # Simple heuristic: object must have 'name', 'phone', 'roadAddress' (or similar)
            # And typename usually 'Place' or similar, but keys are random IDs
            
            # Key format often: "Place:12345678"
            if key.startswith("Place:") or (isinstance(value, dict) and "name" in value and "id" in value):
                # Ensure it's a shop data node
                if "name" not in value or "x" not in value: continue
                
                name = value.get("name")
                _id = value.get("id")
                
                # Check category if possible, but keyword search usually filters
                
                address = value.get("roadAddress") or value.get("abbrAddress") or ""
                phone = value.get("phone") or value.get("virtualPhone") or ""
                
                lat = value.get("y") # Naver uses x, y but check format
                lon = value.get("x")
                
                detail_url = f"https://m.place.naver.com/place/{_id}"
                
                logger.info(f"Found: {name} | {address}")
                
                shop_data = {
                    "name": name,
                    "address": address,
                    "phone": phone,
                    "detail_url": detail_url,
                    "owner_name": "", 
                    "latitude": float(lat) if lat else 0.0,
                    "longitude": float(lon) if lon else 0.0,
                    "source_link": detail_url
                }
                
                if save_to_db(shop_data):
                    items_saved += 1
        
        logger.info(f"Done. Saved {items_saved} items.")
        
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    run_test()
