import json
import re

FILE = "debug_청라동 피부관리.html"

def inspect():
    with open(FILE, "r", encoding="utf-8") as f:
        html = f.read()
        
    print(f"HTML size: {len(html)}")
    
    # 1. Search for __PLACE_STATE__
    match = re.search(r'window\.__PLACE_STATE__\s*=\s*({.*?});', html, re.DOTALL)
    if not match:
        # Maybe it doesn't end with ; or uses different format
        # Try finding the start and balancing braces (hard with regex)
        # Or just take a large chunk
        print("Regex didn't match perfectly. Trying to find start...")
        start = html.find('window.__PLACE_STATE__ = {')
        if start != -1:
            # simple heuristic: read until </script>
            end = html.find('</script>', start)
            json_str = html[start + 25 : end]
            # Strip potential trailing semicolon
            json_str = json_str.strip()
            if json_str.endswith(';'): json_str = json_str[:-1]
            try:
                data = json.loads(json_str)
                print("Parsed __PLACE_STATE__ successfully!")
                analyze_state(data)
                return
            except Exception as e:
                print(f"JSON Parse Error: {e}")
                # Save chunk for manual inspection
                with open("debug_state.json", "w", encoding="utf-8") as f:
                    f.write(json_str)
    # 2. Search for __APOLLO_STATE__
    print("Searching for __APOLLO_STATE__...")
    match_apollo = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.*?});', html, re.DOTALL)
    if match_apollo:
        try:
            db_json = match_apollo.group(1)
            apollo_data = json.loads(db_json)
            print("Parsed __APOLLO_STATE__!")
            with open("debug_apollo_dump.json", "w", encoding="utf-8") as f:
                json.dump(apollo_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Apollo JSON Parse Error: {e}")
    else:
        print("__APOLLO_STATE__ not found via regex. Trying simple find...")
        start = html.find('window.__APOLLO_STATE__ = {')
        if start != -1:
             end = html.find('</script>', start)
             json_str = html[start + 26 : end] # 26 = len('window.__APOLLO_STATE__ = ')
             json_str = json_str.strip()
             if json_str.endswith(';'): json_str = json_str[:-1]
             try:
                 apollo_data = json.loads(json_str)
                 print("Parsed __APOLLO_STATE__ via index!")
                 with open("debug_apollo_dump.json", "w", encoding="utf-8") as f:
                     json.dump(apollo_data, f, indent=2, ensure_ascii=False)
             except Exception as e:
                 print(f"Apollo index parse error: {e}")


def analyze_state(data):
    # Recursively search for "list" or "items"
    # Or specific keys like "name", "address"
    keys = list(data.keys())
    print(f"Top keys: {keys}")
    
    # Usually it's in something like data['business'] or data['search']
    # Let's write the whole nicely formatted json
    with open("debug_state_dump.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Dumped structure to debug_state_dump.json")

if __name__ == "__main__":
    inspect()
