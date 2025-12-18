import json

def analyze():
    fname = "debug_state_dump.json"
    print(f"Loading {fname}...")
    with open(fname, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Keys: {list(data.keys())}")
    
    # Traverse to find lists
    # Usually data['busines'] or something
    
    def find_list(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                find_list(v, f"{path}.{k}")
        elif isinstance(obj, list):
            if len(obj) > 0:
                print(f"Found list at {path}: length={len(obj)}")
                # Check first item type
                first = obj[0]
                if isinstance(first, dict):
                    print(f"  First item keys: {list(first.keys())}")
                    if "name" in first:
                        print(f"  Sample Name: {first['name']}")
                    if "x" in first:
                        print(f"  Sample X: {first['x']}")
                    if "y" in first:
                        print(f"  Sample Y: {first['y']}")
                    
    # Only go 3 levels deep to avoid recursion hell if it's huge
    # Actually, let's just inspect common keys
    
    # 1. Check if there is a 'items' or 'list' in the root
    # or iterate top level values
    
    find_list(data)

if __name__ == "__main__":
    analyze()
