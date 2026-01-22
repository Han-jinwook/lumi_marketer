import urllib.parse
from bs4 import BeautifulSoup
from typing import List, Set
import logging

try:
    from .safe_crawler import SafeCrawler
except ImportError:
    from safe_crawler import SafeCrawler

logger = logging.getLogger(__name__)

class Searcher:
    def __init__(self, crawler: SafeCrawler):
        self.crawler = crawler

    def search_naver_blogs(self, keyword: str, limit: int = 20) -> List[str]:
        """
        Search for Naver blogs.
        Since we don't have API access, we'll try to scrape the search result page carefully.
        Targeting 'VIEW' tab or Blog tab.
        """
        logger.info(f"Searching Naver blogs for: {keyword}")
        blog_urls = []
        
        # Searching Naver View/Blog tab
        base_url = "https://search.naver.com/search.naver"
        
        # We might need to iterate pages if we want many results
        # For now, let's grab the first page (usually ~30 results)
        params = {
            "where": "blog",
            "query": keyword,
            "sm": "tab_opt" 
        }
        
        response = self.crawler.get_with_retry(base_url, params=params)
        if not response:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Select blog links
        # Naver structure changes often, so we'll look for any link containing blog.naver.com
        links = soup.select("a")
        
        for link in links:
            url = link.get('href')
            if url and "blog.naver.com" in url:
                # Filter out some generic nav links if needed, but for now take them
                # Naver often redirects, the link might be like https://blog.naver.com/ID/LogNo
                if "PostView" in url or "/MyBlog" not in url: # basic filtering to avoid profile links if possible
                    blog_urls.append(url)
                    if len(blog_urls) >= limit:
                        break
                    
        logger.info(f"Found {len(blog_urls)} Naver blogs for '{keyword}'")
        return blog_urls

    def search_tistory_blogs(self, keyword: str, limit: int = 20) -> List[str]:
        """
        Search for Tistory blogs using Google or Daum search.
        Here we use a simulated Daum search or Google to find tistory sites.
        """
        logger.info(f"Searching Tistory blogs for: {keyword}")
        blog_urls = []
        
        # Using Daum search (Daum is Tistory's parent)
        base_url = "https://search.daum.net/search"
        params = {
            "w": "blog",
            "q": f"site:tistory.com {keyword}", # Limit to tistory
            "DA": "PGD",
            "spacing": "0"
        }
        
        response = self.crawler.get_with_retry(base_url, params=params)
        if not response:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Inspect Daum structure
        # Usually links are in 'a.f_link_b'
        links = soup.select("a.f_link_b")
        
        for link in links:
            url = link.get('href')
            if url and "tistory.com" in url:
                blog_urls.append(url)
                if len(blog_urls) >= limit:
                    break
                    
        logger.info(f"Found {len(blog_urls)} Tistory blogs for '{keyword}'")
        return blog_urls
        
    def search_all(self, keywords: List[str]) -> Set[str]:
        """
        Search across all platforms for the given keywords.
        Returns a set of unique URLs.
        """
        all_urls = set()
        
        for keyword in keywords:
            naver_urls = self.search_naver_blogs(keyword)
            all_urls.update(naver_urls)
            
            tistory_urls = self.search_tistory_blogs(keyword)
            all_urls.update(tistory_urls)
            
        return all_urls
