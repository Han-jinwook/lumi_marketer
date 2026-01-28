import firebase_admin
from firebase_admin import credentials, firestore
import config

try:
    # Initialize Firebase (reuse logic from db_handler)
    if not firebase_admin._apps:
        cred = credentials.Certificate(config.FIREBASE_SERVICE_ACCOUNT)
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    collection_ref = db.collection(config.FIREBASE_COLLECTION)
    
    # Analyze addresses
    docs = collection_ref.stream()
    total_count = 0
    seoul_count = 0
    no_address_count = 0
    other_region_count = 0
    
    address_prefixes = {}

    for doc in docs:
        total_count += 1
        data = doc.to_dict()
        addr = data.get("address", "").strip()
        
        if not addr:
            no_address_count += 1
            # print(f"Empty Address: {data.get('name')}")
            continue
            
        first_word = addr.split()[0]
        address_prefixes[first_word] = address_prefixes.get(first_word, 0) + 1
        
        if first_word == "서울" or first_word == "서울특별시":
            seoul_count += 1
        else:
            other_region_count += 1

    print(f"🔥 FINAL ANALYSIS:")
    print(f"Total: {total_count}")
    print(f"Seoul (Exact '서울'/'서울특별시'): {seoul_count}")
    print(f"No Address: {no_address_count}")
    print(f"Other Regions: {other_region_count}")
    print(f"Prefix Breakdown: {address_prefixes}")

except Exception as e:
    print(f"❌ Error counting: {e}")
