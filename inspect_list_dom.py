FILE = "debug_청라동 피부관리.html"

def inspect():
    with open(FILE, "r", encoding="utf-8") as f:
        html = f.read()
    
    # Try to find a typical class name for the list item
    # e.g., "UEzoS" (title class often) or "place_bluelink"
    
    markers = ["UEzoS", "place_bluelink", "OXiLu", "3F7sJ", "li > div"]
    
    found = False
    for m in markers:
        idx = html.find(m)
        if idx != -1:
            print(f"[*] Found marker '{m}' at {idx}")
            start = max(0, idx - 200)
            end = min(len(html), idx + 800)
            print(f"--- Context ---\n{html[start:end]}\n----------------")
            found = True
            break
            
    if not found:
        print("[-] No common markers found. Dumping a random chunk from middle.")
        mid = len(html) // 2
        print(f"--- Context ---\n{html[mid:mid+1000]}\n----------------")

if __name__ == "__main__":
    inspect()
