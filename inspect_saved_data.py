from crawler.db_handler import DBHandler
import config

def inspect_data():
    db = DBHandler()
    if not db.db_fs:
        print("❌ DB Not connected")
        return

    print("🔍 Fetching last 5 shops from Firebase...")
    # Fetch all and take last 5 (since we don't have a reliable generic 'created_at' index yet, or maybe we do?)
    # DBHandler doesn't seem to enforce created_at on insert, only 'updated_at' on session? 
    # Let's just stream a few and check those that match "Gangnam-gu" or recent updates.
    
    docs = db.db_fs.collection(config.FIREBASE_COLLECTION).stream()
    shops = []
    for doc in docs:
        d = doc.to_dict()
        shops.append(d)
    
    # Filter for ones likely from our test (keyword "강남구" or just check the ones we saw in logs)
    # Log said: "정앤정피부관리실", "디유에스테틱"
    
    targets = ["정앤정피부관리실", "디유에스테틱"]
    
    found = 0
    for s in shops:
        name = s.get('name', '') or s.get('상호명', '')
        if any(t in name for t in targets) or "강남" in s.get('address', ''):
            print(f"\nShim: {name}")
            print(f" - Address: {s.get('address')}")
            print(f" - Email: {s.get('email')}")
            print(f" - Insta: {s.get('instagram_handle') or s.get('instagram')}")
            print(f" - Blog: {s.get('naver_blog_id') or s.get('blog_id')}")
            print(f" - Talk: {s.get('talk_url') or s.get('talktalk')}")
            found += 1
            if found >= 5: break
            
    if found == 0:
        print("❌ No matching shops found.")

if __name__ == "__main__":
    inspect_data()
