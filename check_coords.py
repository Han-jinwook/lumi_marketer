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
    # Select rows with name, latitude, longitude
    resp = requests.get(f"{url}/rest/v1/t_crawled_shops?select=name,latitude,longitude&limit=10&order=updated_at.desc", headers=headers)
    data = resp.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    check()
