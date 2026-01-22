import requests
import json
import math
import config
import time

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula 
    dlat = lat2 - lat1 
    dlon = lon2 - lon1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 6371000 for meters.
    return c * r * 1000 # Distance in meters

def extract_competitors():
    url = config.SUPABASE_URL
    key = config.SUPABASE_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    # 1. Fetch all shops with valid coordinates
    # For now, we focus on shops that have non-zero coordinates
    query_url = f"{url}/rest/v1/t_crawled_shops?latitude=neq.0&select=id,name,address,latitude,longitude"
    resp = requests.get(query_url, headers=headers)
    
    if resp.status_code != 200:
        print(f"[-] Failed to fetch shops: {resp.status_code} {resp.text}")
        return
    
    all_shops = resp.json()
    print(f"[*] Loaded {len(all_shops)} shops with coordinates.")
    
    if not all_shops:
        print("[-] No shops found with valid coordinates.")
        return

    # 2. Iterate through each shop to find its competitors
    for target in all_shops:
        target_id = target['id']
        target_name = target['name']
        t_lat = target['latitude']
        t_lng = target['longitude']
        
        print(f"[*] Calculating competitors for: {target_name}")
        
        distances = []
        for other in all_shops:
            if other['id'] == target_id:
                continue # Don't compare with self
            
            dist = haversine(t_lat, t_lng, other['latitude'], other['longitude'])
            distances.append({
                "name": other['name'],
                "address": other['address'],
                "distance_m": round(dist)
            })
        
        # Sort by distance
        distances.sort(key=lambda x: x['distance_m'])
        
        # Take top 9
        top_9 = distances[:9]
        
        # Convert to string for DB storage
        top_9_json = json.dumps(top_9, ensure_ascii=False)
        
        # Update DB
        update_url = f"{url}/rest/v1/t_crawled_shops?id=eq.{target_id}"
        upd_resp = requests.patch(update_url, headers=headers, json={"top_9_competitors": top_9_json})
        
        if upd_resp.status_code in [200, 204]:
            print(f"    [+] Updated top 9 competitors for {target_name} ({len(top_9)} found)")
        else:
            print(f"    [-] Failed to update {target_name}: {upd_resp.status_code}")
        
        # Small sleep to be nice to the API
        time.sleep(0.1)

if __name__ == "__main__":
    extract_competitors()
