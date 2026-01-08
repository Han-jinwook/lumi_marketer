import requests
import sys
import os

# Add current dir to path to import config
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import config

def fix_emails_with_blog():
    url = config.SUPABASE_URL
    key = config.SUPABASE_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    # 1. Fetch shops in Bupyeong-dong where email is missing but blog exists
    query_url = f"{url}/rest/v1/t_crawled_shops?address=ilike.*부평동*&select=id,name,naver_blog_id,email"
    resp = requests.get(query_url, headers=headers)
    
    if resp.status_code != 200:
        print(f"[-] Failed to fetch shops: {resp.status_code}")
        return
    
    shops = resp.json()
    total_updated = 0
    
    print(f"[*] Checking {len(shops)} shops in Bupyeong-dong for missing emails...")

    for shop in shops:
        email = shop.get('email')
        blog = shop.get('naver_blog_id')
        
        # If email is missing (None or empty string) AND blog exists
        if not email and blog and "blog.naver.com" in blog:
            # Extract handle from https://blog.naver.com/handle
            handle = blog.strip("/").split("/")[-1].split("?")[0]
            if handle:
                generated_email = f"{handle}@naver.com"
                print(f"[*] Updating [{shop['name']}]: Missing email -> {generated_email} (from blog {handle})")
                
                upd_data = {"email": generated_email}
                upd_url = f"{url}/rest/v1/t_crawled_shops?id=eq.{shop['id']}"
                upd_resp = requests.patch(upd_url, headers=headers, json=upd_data)
                
                if upd_resp.status_code in [200, 204]:
                    total_updated += 1
                else:
                    print(f"    [-] Update failed for {shop['name']}: {upd_resp.status_code}")
                    
    print(f"[*] Finished. Total {total_updated} shops' emails updated.")

if __name__ == "__main__":
    fix_emails_with_blog()
