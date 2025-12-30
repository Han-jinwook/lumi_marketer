import logging
import os
from supabase import create_client, Client
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
        self.supabase: Optional[Client] = None
        self.init_supabase()
        
    def init_supabase(self):
        """Initialize Supabase client."""
        url = config.SUPABASE_URL
        key = config.SUPABASE_KEY
        
        if not url or not key or url == "your_supabase_url_here":
            logger.warning("Supabase credentials not found or invalid in .env. DB features will be disabled.")
            return

        try:
            self.supabase = create_client(url, key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.warning(f"Supabase wrapper init failed: {e}. Using direct requests fallback.")
            self.supabase = None # Will use requests fallback in methods
            
    def insert_lead(self, data: Dict) -> bool:
        """
        Insert a lead into Supabase.
        Expected data format:
        {
            "blog_url": "...",
            "title": "...",
            "email": "..."
        }
        """
        if not self.supabase:
            return False
            
        try:
            if self.supabase:
                response = self.supabase.table(config.SUPABASE_TABLE).upsert(
                    data, 
                    on_conflict="blog_url"
                ).execute()
            else:
                # Direct requests fallback
                url = f"{config.SUPABASE_URL}/rest/v1/{config.SUPABASE_TABLE}?on_conflict=blog_url"
                headers = {
                    "apikey": config.SUPABASE_KEY,
                    "Authorization": f"Bearer {config.SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates"
                }
                resp = requests.post(url, headers=headers, json=data)
                resp.raise_for_status()
            
            logger.info(f"Successfully saved lead: {data.get('blog_url')}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to Supabase: {e}")
            return False

    def insert_shop(self, data: Dict) -> bool:
        """
        Insert a shop into the unified leads table.
        """
        if not self.supabase:
            return self.insert_lead(data) # Fallback to requests in insert_lead
            
        try:
            # Handle different client interfaces
            if hasattr(self.supabase, 'table'):
                query = self.supabase.table(config.SUPABASE_TABLE)
            else:
                query = self.supabase.from_(config.SUPABASE_TABLE)
                
            # Upsert based on detail_url or blog_url
            conflict_key = "detail_url" if "detail_url" in data else "blog_url"
            response = query.upsert(
                data, 
                on_conflict=conflict_key
            ).execute()
            
            logger.info(f"Successfully saved entry to {config.SUPABASE_TABLE}: {data.get('name') or data.get('blog_url')}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to Supabase table {config.SUPABASE_TABLE}: {e}")
            return False
            
    def fetch_existing_urls(self) -> List[str]:
        """Fetch all existing blog URLs to avoid re-crawling."""
        if not self.supabase:
            return []
            
        try:
            if self.supabase:
                response = self.supabase.table(config.SUPABASE_TABLE).select("blog_url").execute()
                urls = [item['blog_url'] for item in response.data]
            else:
                # Direct requests fallback
                url = f"{config.SUPABASE_URL}/rest/v1/{config.SUPABASE_TABLE}?select=blog_url"
                headers = {
                    "apikey": config.SUPABASE_KEY,
                    "Authorization": f"Bearer {config.SUPABASE_KEY}"
                }
                resp = requests.get(url, headers=headers)
                resp.raise_for_status()
                urls = [item['blog_url'] for item in resp.json()]

            logger.info(f"Fetched {len(urls)} existing URLs from DB")
            return urls
        except Exception as e:
            logger.error(f"Error fetching existing URLs: {e}")
            return []
