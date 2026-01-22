
import os
import time
import json
import logging
import asyncio
from typing import List, Dict, Any
from apify_client import ApifyClient
from config import APIFY_TOKEN
from crawler.db_handler import DBHandler
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Actor ID for Naver Map Scraper
# Using a reliable actor. 'crawlers-collection/naver-map-scraper' or 'compass/naver-map-scraper' are common.
# 'curious_coder/naver-place-scraper' was in the previous code.
# Let's use 'compass/naver-map-scraper' which is often the most robust 'official-like' one.
ACTOR_ID = "compass/naver-map-scraper"

def run_apify_crawler(keywords: List[str] = None, max_items_per_query: int = 50):
    """
    Run Apify crawler for a list of keywords and save to Firebase/DB.
    """
    if not APIFY_TOKEN:
        logger.error("❌ APIFY_TOKEN is missing in .env or config.py")
        return

    client = ApifyClient(APIFY_TOKEN)
    db = DBHandler()
    
    if keywords is None:
        keywords = ["서울 강남구 피부관리샵"] # Default for testing

    total_saved = 0

    for keyword in keywords:
        logger.info(f"🚀 Starting crawl for keyword: {keyword}")
        
        # Prepare the Actor input
        # Note: Input parameters vary by Actor. This is for compass/naver-map-scraper.
        run_input = {
            "searchStrings": [keyword],
            "maxCrawledPlacesPerSearch": max_items_per_query,
            "language": "ko",
            "zoom": 13,
            "includeReviewCount": True,
            "includeImageCount": True,
            # Some actors allow specifying what to scrape
        }

        try:
            # Run the Actor and wait for it to finish
            logger.info("⏳ Waiting for Apify Actor to finish...")
            run = client.actor(ACTOR_ID).call(run_input=run_input)
            
            if not run:
                logger.error("❌ Apify run failed to start or returned None.")
                continue

            # Fetch and print Actor results from the run's dataset
            logger.info(f"✅ Crawl finished for {keyword}. Fetching results...")
            
            count = 0
            dataset_id = run["defaultDatasetId"]
            
            # Fetch in batches if needed, but client.dataset().iterate_items() handles pagination
            for item in client.dataset(dataset_id).iterate_items():
                # Process item to match our desired schema
                shop_data = process_apify_item(item, keyword)
                
                # Save to DB
                if shop_data:
                    # Enrich with minimal valid checks
                    if shop_data.get("name") and (shop_data.get("address") or shop_data.get("phone")):
                         if db.insert_shop_fs(shop_data):
                             logger.info(f"✅ Saved: {shop_data['name']}")
                             count += 1
                    else:
                        logger.debug(f"⚠️ Skipped invalid item: {shop_data.get('name')}")

            logger.info(f"📦 Retrieved and processed {count} items for {keyword}")
            total_saved += count
            
        except Exception as e:
            logger.error(f"❌ Error scraping {keyword}: {e}")

    logger.info(f"🎉 Crawling completed. Total items saved: {total_saved}")
    return total_saved

def process_apify_item(item: Dict[str, Any], keyword: str) -> Dict[str, Any]:
    """
    Map Apify result field names to our project's schema.
    """
    # Schema Mapping for 'compass/naver-map-scraper' (common keys)
    # Adjust keys based on actual output if needed.
    
    # Try to extract common fields
    name = item.get("name") or item.get("title")
    address = item.get("address") or item.get("roadAddress")
    phone = item.get("phone") or item.get("phoneNumber")
    
    # Coordinates
    lat = item.get("lat") or item.get("latitude") or item.get("y")
    lng = item.get("lng") or item.get("longitude") or item.get("x")
    
    # URLs
    detail_url = item.get("url") or item.get("placeUrl")
    if not detail_url and item.get("id"):
        detail_url = f"https://m.place.naver.com/place/{item.get('id')}/home"

    # Socials - often in 'additionalInfo' or 'socialLinks' depending on actor
    instagram = None
    blog = None
    
    # Heuristic for social links if available in item top-level or sub-objects
    # (Implementation depends on specific actor output, this is a generic robust attempt)
    
    return {
        "name": name,
        "address": address,
        "phone": phone,
        "detail_url": detail_url,
        "description": item.get("description", ""),
        "latitude": float(lat) if lat else 0.0,
        "longitude": float(lng) if lng else 0.0,
        "keyword": keyword,
        "source": "apify",
        # Fields that might be missing in simple crawl
        "instagram_handle": instagram, 
        "naver_blog_id": blog,
        "email": "", # Usually not available in map lists
        "crawled_at": datetime.now().isoformat()
    }

if __name__ == "__main__":
    # Test run with a simple keyword
    # Use a small number to save credits/time
    run_apify_crawler(["서울 강남구 피부관리샵"], max_items_per_query=5)
