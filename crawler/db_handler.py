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
        except TypeError:
            try:
                # Direct Postgrest usage to bypass wrapper issues
                from postgrest import PostgrestClient
                self.supabase = PostgrestClient(f"{url}/rest/v1")
                self.supabase.auth(key)
                logger.info("Initialized PostgrestClient directly")
            except Exception as e2:
                logger.error(f"Postgrest fallback failed: {e2}")
                self.supabase = None
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.supabase = None
            
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
            # Upsert based on blog_url (assuming it's a unique constraint or primary key)
            # If your table uses a different unique key, adjust 'on_conflict' accordingly
            response = self.supabase.table(config.SUPABASE_TABLE).upsert(
                data, 
                on_conflict="blog_url"
            ).execute()
            
            logger.info(f"Successfully saved lead: {data.get('blog_url')}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to Supabase: {e}")
            return False

    def insert_shop(self, data: Dict) -> bool:
        """
        Insert a shop into t_crawled_shops.
        """
        if not self.supabase:
            return False
            
        try:
            # Handle different client interfaces (Supabase wrapper vs raw Postgrest)
            if hasattr(self.supabase, 'table'):
                query = self.supabase.table("t_crawled_shops")
            else:
                # Raw PostgrestClient uses from_
                query = self.supabase.from_("t_crawled_shops")
                
            # Upsert based on detail_url
            response = query.upsert(
                data, 
                on_conflict="detail_url"
            ).execute()
            
            logger.info(f"Successfully saved shop: {data.get('name')}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving shop to Supabase: {e}")
            return False
            
    def fetch_existing_urls(self) -> List[str]:
        """Fetch all existing blog URLs to avoid re-crawling."""
        if not self.supabase:
            return []
            
        try:
            response = self.supabase.table(config.SUPABASE_TABLE).select("blog_url").execute()
            urls = [item['blog_url'] for item in response.data]
            logger.info(f"Fetched {len(urls)} existing URLs from DB")
            return urls
        except Exception as e:
            logger.error(f"Error fetching existing URLs: {e}")
            return []
