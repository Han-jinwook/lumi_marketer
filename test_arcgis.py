from geopy.geocoders import ArcGIS
import time

geolocator = ArcGIS()

addresses = [
    "인천 부평구 부평동 738-43",
    "인천 부평구 부평동 152-1",
    "인천 부평구 부평동 185-51"
]

for addr in addresses:
    print(f"Testing: {addr}")
    try:
        location = geolocator.geocode(addr)
        if location:
            print(f"  Result: {location.latitude}, {location.longitude}")
            print(f"  Display Name: {location.address}")
        else:
            print("  Failed")
    except Exception as e:
        print(f"  Error: {e}")
    time.sleep(1)
