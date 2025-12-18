import time
import random
import requests
import logging
from typing import Optional, Dict

# Try to import config relative to the package, or fall back to absolute import if needed
try:
    from .. import config
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config

logger = logging.getLogger(__name__)

class SafeCrawler:
    def __init__(self):
        self.session = requests.Session()
        
    def random_delay(self):
        """Sleep for a random amount of time between MIN_DELAY and MAX_DELAY."""
        delay = random.uniform(config.MIN_DELAY, config.MAX_DELAY)
        logger.info(f"Waiting for {delay:.2f} seconds...")
        time.sleep(delay)
        
    def get_random_user_agent(self) -> str:
        """Return a random user agent string."""
        return random.choice(config.USER_AGENTS)
        
    def get_with_retry(self, url: str, params: Optional[Dict] = None) -> Optional[requests.Response]:
        """
        Perform a GET request with retry logic and safe delays.
        """
        headers = {
            "User-Agent": self.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        for attempt in range(config.MAX_RETRIES):
            try:
                self.random_delay() # Always delay before request
                
                logger.info(f"Requesting URL: {url} (Attempt {attempt + 1}/{config.MAX_RETRIES})")
                response = self.session.get(
                    url, 
                    headers=headers, 
                    params=params, 
                    timeout=config.REQUEST_TIMEOUT
                )
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    logger.warning("Rate limited (429). Waiting longer...")
                    time.sleep(30) # Wait longer if rate limited
                else:
                    logger.warning(f"Request failed with status code: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error requesting {url}: {e}")
                
            # Wait a bit before retry if it wasn't the last attempt
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(5)
                
        logger.error(f"Failed to fetch {url} after {config.MAX_RETRIES} attempts")
        return None
