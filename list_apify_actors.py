"""
List available Apify actors for Naver Map scraping
"""
from apify_client import ApifyClient
import os
from dotenv import load_dotenv

load_dotenv()
client = ApifyClient(os.getenv("APIFY_TOKEN"))

print("🔍 Searching for Naver Map scraping actors...\n")

# Search for Naver-related actors
try:
    # Search in the store
    search_results = client.actors().list(search="naver map")
    
    print(f"Found {len(search_results.items)} actors:\n")
    
    for i, actor in enumerate(search_results.items[:10], 1):
        print(f"{i}. {actor['name']}")
        print(f"   ID: {actor['id']}")
        print(f"   Username: {actor['username']}")
        print(f"   Title: {actor.get('title', 'N/A')}")
        print(f"   Free: {actor.get('isFree', False)}")
        print(f"   Deprecated: {actor.get('isDeprecated', False)}")
        print()
        
except Exception as e:
    print(f"❌ Error: {e}")
    
print("\n💡 Alternative: Let's try a different approach")
print("   We can use a simpler, free actor or build our own solution")
