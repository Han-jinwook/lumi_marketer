import firebase_admin
from firebase_admin import credentials, firestore
import config
import pandas as pd

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(config.FIREBASE_SERVICE_ACCOUNT)
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    collection_ref = db.collection(config.FIREBASE_COLLECTION)
    
    # Analyze non-Seoul addresses
    docs = collection_ref.stream()
    
    spillover_data = []

    for doc in docs:
        data = doc.to_dict()
        addr = data.get("address", "").strip()
        keyword = data.get("keyword", "UNKNOWN")
        name = data.get("name", "Unknown")
        
        if not addr: continue
            
        first_word = addr.split()[0]
        
        # If address is NOT Seoul, but collected
        if first_word not in ["서울", "서울특별시"]:
            spillover_data.append({
                "name": name,
                "address": addr,
                "found_via_keyword": keyword,
                "region": first_word
            })

    if spillover_data:
        df = pd.DataFrame(spillover_data)
        print(f"🔥 FOUND {len(df)} Spillover Records!")
        print("\n--- Sample Analysis (Top 10) ---")
        print(df[["region", "found_via_keyword", "address"]].head(10).to_string())
        
        # Check if they were searched with '서울'
        seoul_keywords = df[df['found_via_keyword'].str.contains("서울", na=False)]
        print(f"\n--- Origin Check ---")
        print(f"Records found using '서울' keywords: {len(seoul_keywords)} / {len(df)}")
    else:
        print("No non-Seoul data found.")

except Exception as e:
    print(f"❌ Error: {e}")
