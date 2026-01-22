import requests
import json
import os
import sys

# Add parent dir to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
import config

def inspect_columns():
    url = f"{config.SUPABASE_URL}/rest/v1/t_crawled_shops?limit=1"
    headers = {
        "apikey": config.SUPABASE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_KEY}",
        "Prefer": "return=minimal"
    }
    
    # Alternatively, get the OpenAPI spec
    spec_url = f"{config.SUPABASE_URL}/rest/v1/"
    spec_headers = {
        "apikey": config.SUPABASE_KEY,
    }
    
    try:
        # Try getting one record to see keys
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                print(f"Columns in t_crawled_shops: {list(data[0].keys())}")
            else:
                print("Table is empty. Cannot determine columns via GET.")
        else:
            print(f"GET failed: {resp.status_code} {resp.text}")
            
        # Try getting OpenAPI spec
        resp = requests.get(spec_url, headers=spec_headers)
        if resp.status_code == 200:
            spec = resp.json()
            table_info = spec.get("definitions", {}).get("t_crawled_shops", {})
            properties = table_info.get("properties", {})
            if properties:
                print(f"Columns in t_crawled_shops (from spec): {list(properties.keys())}")
            else:
                print("Could not find definition for t_crawled_shops in spec.")
        else:
            print(f"Spec GET failed: {resp.status_code}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_columns()
