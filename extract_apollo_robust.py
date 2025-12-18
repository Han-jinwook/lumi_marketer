import json

FILE = "debug_청라동 피부관리.html"

def extract():
    with open(FILE, "r", encoding="utf-8") as f:
        html = f.read()
        
    start_marker = "window.__APOLLO_STATE__ ="
    start_idx = html.find(start_marker)
    
    if start_idx == -1:
        print("[-] Start marker not found!")
        return
        
    print(f"[*] Found start marker at index {start_idx}")
    
    # Move to the first '{'
    json_start = html.find("{", start_idx)
    if json_start == -1:
        print("[-] Could not find opening brace.")
        return
        
    # Stack parser
    stack = 0
    in_string = False
    escape = False
    json_end = -1
    
    for i in range(json_start, len(html)):
        char = html[i]
        
        if escape:
            escape = False
            continue
            
        if char == '\\':
            escape = True
            continue
            
        if char == '"':
            in_string = not in_string
            continue
            
        if not in_string:
            if char == '{':
                stack += 1
            elif char == '}':
                stack -= 1
                if stack == 0:
                    json_end = i + 1
                    break
    
    if json_end != -1:
        json_str = html[json_start:json_end]
        print(f"[*] Extracted JSON string length: {len(json_str)}")
        try:
            data = json.loads(json_str)
            print("[+] Parse successful!")
            with open("debug_apollo_robust.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[-] JSON Parse Error: {e}")
            with open("debug_apollo_broken.txt", "w", encoding="utf-8") as f:
                f.write(json_str)
    else:
        print("[-] Could not find matching closing brace.")

if __name__ == "__main__":
    extract()
