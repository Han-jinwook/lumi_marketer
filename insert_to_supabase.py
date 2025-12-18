import csv
import logging
import requests
import json
import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INPUT_FILE = "raw_shops_with_coords.csv"

def insert_data():
    url = config.SUPABASE_URL
    key = config.SUPABASE_KEY
    
    if not url or not key:
        logger.error("Missing credentials.")
        return

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates" # Upsert behavior
    }
    endpoint = f"{url}/rest/v1/t_crawled_shops"

    success_count = 0
    fail_count = 0
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Basic Cleaning
                name = row.get('Name', '').strip()
                name = name.split('\n')[0]
                
                lat = row.get('Latitude', '0')
                lon = row.get('Longitude', '0')
                try:
                    lat = float(lat)
                    lon = float(lon)
                except:
                    lat = 0.0
                    lon = 0.0
                
                payload = {
                    "name": name,
                    "address": row.get('Address', ''),
                    "dong": row.get('Dong', ''),
                    "phone": row.get('Phone', ''),
                    "detail_url": row.get('Detail_Url', ''),
                    "owner_name": row.get('Owner_Name', ''),
                    "latitude": lat,
                    "longitude": lon,
                    "source_link": row.get('Link', '')
                }
                
                # Direct Request
                # Using on_conflict=detail_url via headers or query param?
                # Postgrest upsert: Prefer: resolution=merge-duplicates (requires unique key in payload matches)
                # Or ?on_conflict=detail_url
                
                query_url = f"{endpoint}?on_conflict=detail_url"
                
                resp = requests.post(query_url, headers=headers, json=payload)
                
                if resp.status_code in [200, 201, 204]:
                    success_count += 1
                    logger.info(f"Saved: {name}")
                else:
                    fail_count += 1
                    logger.error(f"Failed {name}: {resp.status_code} {resp.text}")
                    
            except Exception as e:
                logger.error(f"Row error: {e}")
                fail_count += 1
                
    logger.info(f"Direct Insertion Complete. Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    insert_data()
