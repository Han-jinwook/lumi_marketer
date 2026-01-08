import requests
import json
import os
import sys

# Add parent dir to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    import config
except ImportError:
    import config

def list_tables():
    headers = {
        "apikey": config.SUPABASE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_KEY}"
    }
    
    # Supabase REST API documentation endpoint often provides the schema
    url = f"{config.SUPABASE_URL}/rest/v1/"
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            print("Accessible Tables/Views:")
            if 'paths' in data:
                for path in data['paths']:
                    if path.startswith('/'):
                        print(f"- {path[1:]}")
            else:
                print(json.dumps(data, indent=2))
        else:
            print(f"Failed to fetch schema: {resp.status_code}")
            print(resp.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_tables()
