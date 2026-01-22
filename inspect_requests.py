import requests
import json
import re

URL = "https://m.place.naver.com/place/1503740004"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"
}

def inspect():
    try:
        print(f"Fetching {URL}...")
        resp = requests.get(URL, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        
        html = resp.text
        print(f"Status: {resp.status_code}")
        print(f"Length: {len(html)}")
        
        # Check for Title
        if "<title>" in html:
            title = html.split("<title>")[1].split("</title>")[0]
            print(f"Title: {title}")
            
        # Check for JSON LD
        # Naver often puts it in <script type="application/ld+json">
        if 'application/ld+json' in html:
            print("FOUND application/ld+json!")
            # Extract it
            # Simple regex search
            matches = re.findall(r'<script type="application/ld+json">(.*?)</script>', html, re.DOTALL)
            print(f"Matches count: {len(matches)}")
            for i, m in enumerate(matches):
                print(f"--- Match {i} ---")
                print(m[:200])
        else:
            print("No application/ld+json found.")
            
        # Check for other state
        if '__APOLLO_STATE__' in html:
             print("Found __APOLLO_STATE__")
             
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect()
