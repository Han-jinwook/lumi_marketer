import requests
import config

def check_bad_talk_urls():
    url = config.SUPABASE_URL
    key = config.SUPABASE_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}"
    }
    
    # 1. 톡톡 URL이 'https://talk.naver.com/ch'인 레코드 조회
    query_url = f"{url}/rest/v1/t_crawled_shops?talk_url=eq.https://talk.naver.com/ch&select=id,name,talk_url"
    resp = requests.get(query_url, headers=headers)
    
    if resp.status_code == 200:
        bad_shops = resp.json()
        print(f"[*] Found {len(bad_shops)} shops with generic TalkTalk URL.")
        for s in bad_shops:
            print(f"    - {s['name']} ({s['id']})")
    else:
        print(f"[-] Error: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    check_bad_talk_urls()
