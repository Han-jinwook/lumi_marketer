import requests

url = "https://m.place.naver.com/place/21106619/home"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}

resp = requests.get(url, headers=headers)
with open("debug_requests_fail.html", "w", encoding="utf-8") as f:
    f.write(resp.text)

print(f"Saved {len(resp.text)} chars to debug_requests_fail.html")
