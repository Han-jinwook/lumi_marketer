import requests
import config

def check_old_table():
    headers = {
        "apikey": config.SUPABASE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_KEY}",
        "Prefer": "count=exact"
    }
    
    try:
        url = f"{config.SUPABASE_URL}/rest/v1/skin_shop_leads?select=*"
        resp = requests.head(url, headers=headers)
        if resp.status_code == 200:
            total = resp.headers.get("Content-Range").split("/")[1]
            print(f"Total rows in skin_shop_leads: {total}")
        else:
            print(f"Table skin_shop_leads might not exist or empty (Status: {resp.status_code})")

    except Exception as e:
        print(f"Error checking skin_shop_leads: {e}")

if __name__ == "__main__":
    check_old_table()
