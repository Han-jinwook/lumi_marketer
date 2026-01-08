import requests
import re
import config
import time

def enrich_fast():
    url = config.SUPABASE_URL
    key = config.SUPABASE_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    # Fetch shops needing coordinates
    center_lat = 37.4906976
    query_url = f"{url}/rest/v1/t_crawled_shops?or=(latitude.eq.0,latitude.eq.{center_lat})&select=id,name,source_link"
    
    resp = requests.get(query_url, headers=headers)
    if resp.status_code != 200:
        print(f"[-] Failed to fetch shops: {resp.status_code}")
        return
    
    shops = resp.json()
    print(f"[*] Found {len(shops)} shops to enrich.")
    
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    })
    
    for shop in shops:
        shop_id = shop['id']
        name = shop['name']
        link = shop['source_link']
        
        if not link: continue
        
        print(f"[*] Processing [{name}]: {link}")
        
        try:
            resp = s.get(link, timeout=10)
            html = resp.text
            
            lat, lng = 0.0, 0.0
            
            # Pattern 1: x and y in Apollo State (often "x":"126.7248666","y":"37.4904402")
            # We look for the coordinate block specific to Naver Place
            coord_match = re.search(r'"coordinate":\{"__typename":"Coordinate","x":"([\d\.]+)","y":"([\d\.]+)"', html)
            if coord_match:
                lng = float(coord_match.group(1))
                lat = float(coord_match.group(2))
            else:
                # Pattern 2: x and y as individual keys
                x_match = re.search(r'"x":"(12[\d\.]+)"', html)
                y_match = re.search(r'"y":"(3[\d\.]+)"', html)
                if x_match and y_match:
                    lng = float(x_match.group(1))
                    lat = float(y_match.group(1))
            
            if lat != 0:
                print(f"    [+] Found: {lat}, {lng}")
                # Update DB
                upd_url = f"{url}/rest/v1/t_crawled_shops?id=eq.{shop_id}"
                upd_resp = requests.patch(upd_url, headers=headers, json={"latitude": lat, "longitude": lng})
                if upd_resp.status_code in [200, 204]:
                    print("    [+] DB Updated.")
                else:
                    print(f"    [-] DB Update Failed: {upd_resp.status_code}")
            else:
                print("    [-] Coords not found in HTML.")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"    [-] Error: {e}")

if __name__ == "__main__":
    enrich_fast()
