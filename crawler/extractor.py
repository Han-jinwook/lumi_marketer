import re
from bs4 import BeautifulSoup
from typing import Dict, Optional
import logging

try:
    from .safe_crawler import SafeCrawler
except ImportError:
    from safe_crawler import SafeCrawler

logger = logging.getLogger(__name__)

class Extractor:
    def __init__(self, crawler: SafeCrawler):
        self.crawler = crawler
        # Simple email regex
        self.email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

    def extract_email(self, text: str) -> Optional[str]:
        """Find the first email address in text."""
        match = self.email_regex.search(text)
        if match:
            return match.group(0)
        return None

    def extract_blog_data(self, url: str) -> Optional[Dict[str, str]]:
        """
        Visit the blog URL and extract title and email.
        Handles Naver's iframe structure.
        """
        logger.info(f"Extracting data from: {url}")
        
        # Special handling for Naver blogs due to iframes
        if "blog.naver.com" in url:
            return self._extract_naver_blog(url)
        else:
            return self._extract_generic_blog(url)

    def _extract_naver_blog(self, url: str) -> Optional[Dict[str, str]]:
        # Naver blogs often use frames. The real content is in the iframe src.
        # But for 'blog.naver.com/ID/PostID', we can usually get the ID/PostID
        # and construct the mobile version URL or main frame URL.
        
        # Strategy: Fetch the main page, look for 'mainFrame' or retrieve ID/logNo.
        # A simpler way for text extraction is requesting the mobile version: m.blog.naver.com/...
        mobile_url = url.replace("blog.naver.com", "m.blog.naver.com")
        
        response = self.crawler.get_with_retry(mobile_url)
        if not response:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Title
        # Mobile Naver: usually in <div class="se-module se-module-text ..."> or <h3 class="tit_h3">
        title_tag = soup.select_one("div.se-module-text p") or soup.select_one("h3.tit_h3") or soup.select_one("title")
        title = title_tag.get_text(strip=True) if title_tag else "No Title"
        
        # Email: Scan the whole text
        # Profile area is also good to check
        text_content = soup.get_text(" ", strip=True)
        email = self.extract_email(text_content)
        
        if email:
            return {
                "blog_url": url,
                "title": title,
                "email": email
            }
        else:
            logger.info(f"No email found in {url}")
            return None

    def _extract_generic_blog(self, url: str) -> Optional[Dict[str, str]]:
        response = self.crawler.get_with_retry(url)
        if not response:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_tag = soup.select_one("title")
        title = title_tag.get_text(strip=True) if title_tag else "No Title"
        
        text_content = soup.get_text(" ", strip=True)
        email = self.extract_email(text_content)
        
        if email:
            return {
                "blog_url": url,
                "title": title,
                "email": email
            }
        
        logger.info(f"No email found in {url}")
        return None
