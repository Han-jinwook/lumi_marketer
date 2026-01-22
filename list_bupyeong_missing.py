import requests
import config
import json

url = config.SUPABASE_URL
key = config.SUPABASE_KEY
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}"
}

def get_shops():
    query_url = f"{url}/rest/v1/t_crawled_shops?address=ilike.*부평동*&select=id,name,source_link,instagram_handle,talk_url,naver_blog_id,email"
    resp = requests.get(query_url, headers=headers)
    if resp.status_code == 200:
        all_shops = resp.json()
        print(f"Total shops in Bupyeong: {len(all_shops)}")
        print(json.dumps(all_shops, indent=2, ensure_ascii=False))
    else:
        print(f"Error: {resp.status_code}")

if __name__ == "__main__":
    get_shops()
