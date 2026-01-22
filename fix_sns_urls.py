import requests
import config

url = config.SUPABASE_URL
key = config.SUPABASE_KEY
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

def fix_sns_urls():
    # 1. Fetch all shops in Bupyeong-dong
    query_url = f"{url}/rest/v1/t_crawled_shops?address=ilike.*부평동*&select=id,name,instagram_handle,naver_blog_id"
    resp = requests.get(query_url, headers=headers)
    
    if resp.status_code != 200:
        print(f"[-] Failed to fetch shops: {resp.status_code}")
        return
    
    shops = resp.json()
    total_updated = 0
    
    for shop in shops:
        update_data = {}
        
        # Instagram Fix
        insta = shop.get('instagram_handle')
        if insta and not insta.startswith('http'):
            update_data["instagram_handle"] = f"https://www.instagram.com/{insta}"
            
        # Blog Fix
        blog = shop.get('naver_blog_id')
        if blog and not blog.startswith('http'):
            update_data["naver_blog_id"] = f"https://blog.naver.com/{blog}"
            
        if update_data:
            print(f"[*] Updating [{shop['name']}]: {update_data}")
            upd_url = f"{url}/rest/v1/t_crawled_shops?id=eq.{shop['id']}"
            upd_resp = requests.patch(upd_url, headers=headers, json=update_data)
            
            if upd_resp.status_code in [200, 204]:
                total_updated += 1
            else:
                print(f"    [-] Update failed for {shop['name']}: {upd_resp.status_code}")
                
    print(f"[*] Total {total_updated} shops updated to full SNS URLs.")

if __name__ == "__main__":
    fix_sns_urls()
