import logging
import os
import requests
from supabase import create_client, Client
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, List, Optional

try:
    from .. import config
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config

logger = logging.getLogger(__name__)

class DBHandler:
    def __init__(self):
        self.db_fs = None # Firestore Client
        self.init_firebase()
        
    def init_firebase(self):
        """Initialize Firebase Admin SDK."""
        try:
            if not firebase_admin._apps:
                # config.FIREBASE_SERVICE_ACCOUNT can be a dict (from secrets) or a string (file path)
                cred_info = config.FIREBASE_SERVICE_ACCOUNT
                
                # If it's a dict, use it directly. If it's a string, treat it as a path.
                if isinstance(cred_info, str):
                    if not os.path.exists(cred_info):
                        logger.warning(f"Firebase key file not found at {cred_info}. Skipping initialization.")
                        return
                    cred = credentials.Certificate(cred_info)
                else:
                    cred = credentials.Certificate(cred_info)
                
                firebase_admin.initialize_app(cred)
            self.db_fs = firestore.client()
            logger.info("Firebase Firestore initialized successfully")
        except Exception as e:
            logger.error(f"Firebase initialization failed: {e}")
            self.db_fs = None
            
    def insert_shop(self, data: Dict) -> bool:
        """Insert or update shop in Firebase Firestore."""
        if not self.db_fs:
            return False
        try:
            # Unified key for shops
            key = data.get("detail_url") or data.get("source_link") or data.get("blog_url") or data.get("플레이스링크")
            if not key: return False
            doc_id = key.replace("/", "_").replace(":", "_")
            
            self.db_fs.collection(config.FIREBASE_COLLECTION).document(doc_id).set(data, merge=True)
            logger.info(f"Successfully saved shop to Firebase: {data.get('name') or data.get('상호명')}")
            return True
        except Exception as e:
            logger.error(f"Error saving shop to Firebase: {e}")
            return False

    def insert_shop_fs(self, data: Dict) -> bool:
        """Alias for backward compatibility."""
        return self.insert_shop(data)

    def insert_lead(self, data: Dict) -> bool:
        """Alias for lead insertion."""
        return self.insert_shop(data)

    def insert_lead_fs(self, data: Dict) -> bool:
        """Alias for lead insertion."""
        return self.insert_shop(data)

    def fetch_existing_urls(self) -> List[str]:
        """Fetch existing shop URLs from Firebase."""
        if not self.db_fs:
                return []
        try:
            docs = self.db_fs.collection(config.FIREBASE_COLLECTION).stream()
            urls = []
            for doc in docs:
                d = doc.to_dict()
                url = d.get("detail_url") or d.get("source_link") or d.get("blog_url") or d.get("플레이스링크")
                if url: urls.append(url)
            return urls
        except Exception as e:
            logger.error(f"Error fetching URLs: {e}")
            return []

    def save_session(self, platform: str, session_data: str) -> bool:
        """Save browser session data to Firebase."""
        if not self.db_fs:
            return False
        try:
            data = {
                "platform": platform,
                "session_json": session_data,
                "updated_at": firestore.SERVER_TIMESTAMP
            }
            self.db_fs.collection(config.FIREBASE_SESSION_COLLECTION).document(platform).set(data)
            logger.info(f"Saved session for {platform} to Firebase")
            return True
        except Exception as e:
            logger.error(f"Error saving session to Firebase: {e}")
            return False

    def save_session_fs(self, platform: str, session_data: str) -> bool:
        return self.save_session(platform, session_data)

    def load_session(self, platform: str) -> Optional[str]:
        """Load browser session data from Firebase."""
        if not self.db_fs:
            return None
        try:
            doc = self.db_fs.collection(config.FIREBASE_SESSION_COLLECTION).document(platform).get()
            if doc.exists:
                return doc.to_dict().get('session_json')
            return None
        except Exception as e:
            logger.error(f"Error loading session: {e}")
            return None
