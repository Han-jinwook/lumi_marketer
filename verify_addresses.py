import requests
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
import config

def verify_addresses():
    url = f"{config.SUPABASE_URL}/rest/v1/t_crawled_shops?select=name,address&limit=10"
    headers = {
        "apikey": config.SUPABASE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_KEY}"
    }
    
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            print("--- Verification: Recent Shop Addresses ---")
            for item in data:
                print(f"Shop: {item['name']}")
                print(f"Addr: {item['address']}")
                print("-" * 20)
        else:
            print(f"Failed: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_addresses()
