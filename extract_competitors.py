import logging
import math
import json
import time
from typing import Dict, List
from crawler.db_handler import DBHandler
import config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    if not all([lat1, lon1, lat2, lon2]):
        return 999999
    
    # Convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula 
    dlat = lat2 - lat1 
    dlon = lon2 - lon1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers
    return c * r * 1000 # Distance in meters

def run_competitor_extraction(target_ids: List[str] = None):
    """
    Fetches all shops from Firebase, calculates the top 9 closest competitors for each,
    and updates the Firebase records.
    :param target_ids: Optional list of document IDs to process. If None, processes ALL shops.
    """
    logger.info(f"🚀 Starting Competitor Extraction (Target subset: {len(target_ids) if target_ids else 'ALL'})...")
    db = DBHandler()
    if not db.db_fs:
        logger.error("❌ Firebase fails to initialize. Aborting.")
        return

    # 1. Fetch all shops (for reference)
    try:
        docs = db.db_fs.collection(config.FIREBASE_COLLECTION).stream()
        all_shops = []
        for doc in docs:
            data = doc.to_dict()
            data['_fs_id'] = doc.id 
            all_shops.append(data)
    except Exception as e:
        logger.error(f"❌ Failed to fetch shops from Firebase: {e}")
        return

    logger.info(f"📊 Total reference shops loaded: {len(all_shops)}")
    
    # Filter shops with valid coordinates
    valid_shops = [s for s in all_shops if s.get('latitude') and s.get('longitude') and s.get('latitude') != 0]
    
    # 2. Identify target shops to update
    if target_ids:
        shops_to_update = [s for s in valid_shops if s['_fs_id'] in target_ids]
        if not shops_to_update:
            logger.warning("⚠️ None of the target IDs found with valid coordinates.")
            return
    else:
        shops_to_update = valid_shops

    if len(valid_shops) < 2:
        logger.warning("⚠️ Not enough shops with coordinates to calculate competitors.")
        return

    # 3. Process each shop
    updated_count = 0
    for target in shops_to_update:
        target_name = target.get('name') or target.get('상호명', 'Unknown')
        t_lat = target.get('latitude')
        t_lng = target.get('longitude')
        
        distances = []
        for other in valid_shops:
            if other.get('_fs_id') == target.get('_fs_id'):
                continue
            
            dist = haversine(t_lat, t_lng, other.get('latitude'), other.get('longitude'))
            
            # Use original field names or mapped ones consistently
            comp_data = {
                "name": other.get('name') or other.get('상호명'),
                "address": other.get('address') or other.get('주소'),
                "phone": other.get('phone') or other.get('번호'),
                "detail_url": other.get('detail_url') or other.get('플레이스링크'),
                "distance_m": round(dist)
            }
            distances.append(comp_data)
        
        # Sort by proximity
        distances.sort(key=lambda x: x['distance_m'])
        
        # Take best 9
        top_9 = distances[:9]
        
        # 4. Update Firebase
        try:
            db.db_fs.collection(config.FIREBASE_COLLECTION).document(target['_fs_id']).update({
                "top_9_competitors": top_9,
                "competitors_updated_at": time.strftime('%Y-%m-%d %H:%M:%S')
            })
            updated_count += 1
            if updated_count % 10 == 0:
                logger.info(f"✅ Processed {updated_count}/{len(shops_to_update)} shops...")
        except Exception as e:
            logger.error(f"❌ Failed to update {target_name}: {e}")

    logger.info(f"🎉 Competitor extraction finished. Total {updated_count} shops updated.")

if __name__ == "__main__":
    import sys
    # Example: python extract_competitors.py id1 id2 id3
    ids = sys.argv[1:] if len(sys.argv) > 1 else None
    run_competitor_extraction(ids)
