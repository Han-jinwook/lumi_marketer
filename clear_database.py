import logging
import time
from crawler.db_handler import DBHandler
import config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_all_shops():
    """
    Deletes ALL documents in the Firebase collection.
    USE WITH CAUTION!
    """
    logger.warning("⚠️ CRITICAL ACTION: Preparing to delete ALL shops from Firebase...")
    
    # Simple double confirmation for safety (when run directly)
    confirm = input("⚠️ Are you sure you want to delete EVERYTHING? (y/n): ")
    if confirm.lower() != 'y':
        logger.info("❌ Operation cancelled.")
        return

    db = DBHandler()
    if not db.db_fs:
        logger.error("❌ Firebase fails to initialize.")
        return

    collection_ref = db.db_fs.collection(config.FIREBASE_COLLECTION)
    
    # Batch delete logic for efficiency
    try:
        docs = list(collection_ref.limit(500).stream())
        deleted_count = 0
        
        while docs:
            batch = db.db_fs.batch()
            for doc in docs:
                batch.delete(doc.reference)
                deleted_count += 1
            
            batch.commit()
            logger.info(f"🧹 Deleted {deleted_count} documents so far...")
            
            # Get next batch
            docs = list(collection_ref.limit(500).stream())
            time.sleep(0.5) # Slight pause to avoid rate limiting
            
        logger.info(f"🎉 SUCCESS: Database cleared! Total {deleted_count} references removed.")
        
    except Exception as e:
        logger.error(f"❌ Error during deletion: {e}")

if __name__ == "__main__":
    clear_all_shops()
