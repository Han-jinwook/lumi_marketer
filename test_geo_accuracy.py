from geopy.geocoders import Nominatim
import json

geolocator = Nominatim(user_agent="accuracy_test")

addresses = [
    "인천 부평구 부평동 738-43",
    "인천 부평구 부평동 152-1",
    "인천 부평구 부평동 185-51"
]

for addr in addresses:
    # Try with "South Korea" appended
    test_addr = f"{addr}, South Korea"
    print(f"Testing: {test_addr}")
    location = geolocator.geocode(test_addr)
    if location:
        print(f"  Result: {location.latitude}, {location.longitude}")
        print(f"  Display Name: {location.address}")
        # print(f"  Raw: {json.dumps(location.raw, indent=2, ensure_ascii=False)}")
    else:
        print("  Failed")
