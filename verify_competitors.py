import requests
import json
import config

def verify():
    url = config.SUPABASE_URL
    key = config.SUPABASE_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    
    # Fetch one shop to check the competitors field
    query_url = f"{url}/rest/v1/t_crawled_shops?select=name,address,top_9_competitors&limit=1&order=updated_at.desc"
    resp = requests.get(query_url, headers=headers)
    
    if resp.status_code == 200:
        data = resp.json()[0]
        print(f"Target Shop: {data['name']}")
        print(f"Address: {data['address']}")
        print("Top 9 Competitors:")
        
        competitors = json.loads(data['top_9_competitors'])
        for idx, comp in enumerate(competitors, 1):
            print(f"  {idx}. {comp['name']} ({comp['distance_m']}m) - {comp['address']}")
            
if __name__ == "__main__":
    verify()
