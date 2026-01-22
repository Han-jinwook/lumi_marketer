import logging
import os
import sys
import pandas as pd
import requests

# Add current dir to path to import config
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import config
from crawler.db_handler import DBHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate():
    logger.info("Starting migration from Supabase to Firebase...")
    db = DBHandler()
    
    if not db.db_fs:
        logger.error("Firebase not initialized. Check firebase_key.json.")
        return

    # 1. Fetch from Supabase
    url = f"{config.SUPABASE_URL}/rest/v1/{config.SUPABASE_TABLE}?select=*"
    headers = {"apikey": config.SUPABASE_KEY, "Authorization": f"Bearer {config.SUPABASE_KEY}"}
    
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Fetched {len(data)} records from Supabase.")
    except Exception as e:
        logger.error(f"Failed to fetch from Supabase: {e}")
        return

    # 2. Upload to Firebase
    success_count = 0
    for item in data:
        # We use the document-safe version of links or names as IDs
        if db.insert_shop_fs(item):
            success_count += 1
            if success_count % 10 == 0:
                logger.info(f"Progress: {success_count}/{len(data)}")

    logger.info(f"Migration complete! Successful: {success_count}/{len(data)}")

if __name__ == "__main__":
    migrate()
