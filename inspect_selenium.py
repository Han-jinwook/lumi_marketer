from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.common.by import By # Re-add
import time

URL = "https://m.place.naver.com/place/1503740004"

def inspect():
    options = webdriver.EdgeOptions()
    # options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    print("Launching Edge (Selenium)...")
    try:
        driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)
    except Exception as e:
        print(f"Edge Driver Manager failed: {e}")
        print("Trying default Edge...")
        driver = webdriver.Edge(options=options)
        
    try:
        print(f"Visiting {URL}...")
        driver.get(URL)
        time.sleep(3)
        
        title = driver.title
        print(f"Title: {title}")
        
        # Check source for JSON
        src = driver.page_source
        if 'application/ld+json' in src:
            print("FOUND application/ld+json!")
            # Extract
            import re
            matches = re.search(r'<script type="application/ld+json">(.*?)</script>', src, re.DOTALL)
            if matches:
                print(matches.group(1)[:200])
        else:
            print("No JSON LD found.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    inspect()
