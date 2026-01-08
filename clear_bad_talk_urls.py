import requests
import config

def clear_bad_talk_urls():
    url = config.SUPABASE_URL
    key = config.SUPABASE_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    # 1. 'https://talk.naver.com/ch'를 톡톡 URL로 가진 레코드 조회
    query_url = f"{url}/rest/v1/t_crawled_shops?talk_url=eq.https://talk.naver.com/ch&select=id,name"
    resp = requests.get(query_url, headers=headers)
    
    if resp.status_code != 200:
        print(f"[-] Failed to fetch shops: {resp.status_code}")
        return
    
    shops = resp.json()
    total_cleared = 0
    
    print(f"[*] Found {len(shops)} shops with bad TalkTalk URL to clear.")

    for shop in shops:
        print(f"[*] Clearing TalkTalk URL for [{shop['name']}]...")
        
        # talk_url을 None(null)으로 업데이트
        upd_data = {"talk_url": None}
        upd_url = f"{url}/rest/v1/t_crawled_shops?id=eq.{shop['id']}"
        upd_resp = requests.patch(upd_url, headers=headers, json=upd_data)
        
        if upd_resp.status_code in [200, 204]:
            total_cleared += 1
        else:
            print(f"    [-] Failed to clear for {shop['name']}: {upd_resp.status_code}")
                    
    print(f"[*] Finished. Total {total_cleared} shops' TalkTalk URLs cleared.")

if __name__ == "__main__":
    clear_bad_talk_urls()
