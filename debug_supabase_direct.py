import os
import requests
import json
import config

def debug_insert():
    url = config.SUPABASE_URL
    key = config.SUPABASE_KEY
    
    print(f"URL: {url}")
    print(f"Key length: {len(key) if key else 0}")
    
    if not url or not key:
        print("Missing credentials.")
        return

    # Use raw requests to eliminate library ambiguity
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    endpoint = f"{url}/rest/v1/t_crawled_shops"
    
    payload = {
        "name": "TEST_SHOP_DEBUG_01",
        "detail_url": "https://m.place.naver.com/place/TEST01",
        "address": "Test Address",
        "latitude": 37.5,
        "longitude": 127.0
    }
    
    print(f"Sending POST to {endpoint}")
    print(f"Payload: {json.dumps(payload)}")
    
    try:
        resp = requests.post(endpoint, headers=headers, json=payload)
        print(f"Status Code: {resp.status_code}")
        print(f"Response Text: {resp.text}")
    except Exception as e:
        print(f"Request failed: {e}")

    # Verify via GET
    print("\n--- Verifying Data via GET ---")
    try:
        get_headers = headers.copy()
        del get_headers["Prefer"] # Remove for list
        
        resp = requests.get(f"{url}/rest/v1/t_crawled_shops?select=*", headers=get_headers)
        print(f"GET Status: {resp.status_code}")
        data = resp.json()
        print(f"Total Rows: {len(data)}")
        if len(data) > 0:
            print(f"First Row Name: {data[0].get('name')}")
    except Exception as e:
        print(f"GET failed: {e}")

if __name__ == "__main__":
    debug_insert()
