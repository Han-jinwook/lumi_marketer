import requests
import config
import json

def check():
    url = config.SUPABASE_URL
    key = config.SUPABASE_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    # Select rows where address is NOT NULL or empty
    resp = requests.get(f"{url}/rest/v1/t_crawled_shops?select=name,address,phone&limit=5&order=updated_at.desc", headers=headers)
    data = resp.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    check()
