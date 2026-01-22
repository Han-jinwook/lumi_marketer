import json

def analyze():
    with open("debug_apollo_dump.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Total keys: {len(data)}")
    
    # 1. Find keys that look like Shops
    shop_keys = [k for k in data.keys() if "Place" in k or "Business" in k]
    print(f"Shop-like keys: {len(shop_keys)}")
    
    # 2. Print one example
    for k in shop_keys[:3]:
        print(f"\n--- {k} ---")
        item = data[k]
        # Print interesting fields
        print(json.dumps(item, indent=2, ensure_ascii=False))

    # 3. Check for Search Results list
    # Usually in ROOT_QUERY -> "placeList" or similar
    if "ROOT_QUERY" in data:
        print("\n--- ROOT_QUERY ---")
        rq = data["ROOT_QUERY"]
        # Print keys of ROOT_QUERY
        for k in rq:
             if "list" in k.lower() or "search" in k.lower():
                 print(f"Found Query Key: {k}")
                 # usually it points to references
                 # print(rq[k])

if __name__ == "__main__":
    analyze()
