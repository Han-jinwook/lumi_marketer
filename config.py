import os
try:
    from dotenv import load_dotenv
    # Load environment variables (Local development)
    load_dotenv()
except ImportError:
    # On Streamlit Cloud, variables are managed via Secrets, so dotenv is optional
    pass

# Supabase Settings
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_TABLE = "t_crawled_shops" # Standard table name for leads
LEADS_TABLE = "t_crawled_shops"    # Unified name

# Firebase Settings
FIREBASE_KEY_PATH = os.path.join(os.path.dirname(__file__), "firebase_key.json")
FIREBASE_COLLECTION = "crawled_shops"
FIREBASE_SESSION_COLLECTION = "browser_sessions"

# Load Firebase Service Account Info
FIREBASE_SERVICE_ACCOUNT = None

# 1. Try to load from Streamlit Secrets (Recommended for Cloud)
try:
    import streamlit as st
    if "firebase" in st.secrets:
        # Convert st.secrets proxy to a real dict
        FIREBASE_SERVICE_ACCOUNT = dict(st.secrets["firebase"])
except:
    pass

# 2. Try to load from Environment Variable (Single JSON String)
if not FIREBASE_SERVICE_ACCOUNT:
    env_key = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if env_key:
        try:
            import json
            FIREBASE_SERVICE_ACCOUNT = json.loads(env_key)
        except:
            pass

# 3. Fallback to local file path (Local Development)
if not FIREBASE_SERVICE_ACCOUNT:
    FIREBASE_SERVICE_ACCOUNT = FIREBASE_KEY_PATH

# Output Settings
OUTPUT_CSV = "확장_피부샵_원장_데이터.csv"

# Crawling Settings
MIN_DELAY = 5
MAX_DELAY = 15
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

# User Agents for Rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
]

# Search Keywords by Category
# Search Keywords by Category
KEYWORDS = {
    "acne_whitening": [
        "여드름 관리 후기", "성인 여드름 관리", "부산 피부미백 관리", 
        "대구 리프팅 케어", "주름 개선 관리", "고주파 관리"
    ],
    "basic_care": [
        "민감성 피부 관리 후기", "피부 수분 관리", "블랙헤드 제거 후기", 
        "인천 피부 재생 관리", "LDM 관리"
    ],
    "business": [
        "피부샵 창업", "1인 피부샵 운영", "피부샵 마케팅", 
        "피부샵 운영 노하우", "에스테티션 일상", "피부샵 매출 올리기"
    ],
    "consumer": [
        "피부샵 추천", "내돈내산 피부샵 후기", "결혼 전 피부관리"
    ]
}

# ==========================================
# [Module 1] Lumi-Link Crawler Settings
# ==========================================

# Target URL
NAVER_PLACE_URL = "https://m.place.naver.com/place/list?query={}"

# File Paths
RAW_DATA_FILE = "raw_shops_with_coords.csv"
ENRICHED_DATA_FILE = "enriched_target_list.csv"
FINAL_TARGET_FILE = "final_target_selection.csv"

# Crawler Config
SCROLL_COUNT = 10  # Number of times to scroll down the list (Adjust as needed)
HEADLESS_MODE = False # Set to False for debugging visibility

# Target Locations/Keywords for Module 1
# Base Keyword
BASE_KEYWORD = "피부관리샵"

# Major Korean Regions (Si/Gun/Gu)
# This is a representative list. For full nationwide, ALL districts should be added.
REGIONS = [
    # Seoul
    "서울 강남구", "서울 서초구", "서울 송파구", "서울 마포구", "서울 용산구", 
    "서울 영등포구", "서울 종로구", "서울 중구", "서울 성동구", "서울 광진구",
    "서울 강서구", "서울 양천구", "서울 구로구", "서울 금천구", "서울 관악구",
    "서울 동작구", "서울 강동구", "서울 성북구", "서울 강북구", "서울 도봉구",
    "서울 노원구", "서울 은평구", "서울 서대문구", "서울 중랑구", "서울 동대문구",
    
    # Gyeonggi
    "경기 수원시", "경기 성남시", "경기 고양시", "경기 용인시", "경기 부천시",
    "경기 안산시", "경기 안양시", "경기 남양주시", "경기 화성시", "경기 평택시",
    "경기 의정부시", "경기 시흥시", "경기 파주시", "경기 김포시", "경기 광명시",
    "경기 광주시", "경기 군포시", "경기 오산시", "경기 이천시", "경기 양주시",
    "경기 구리시", "경기 안성시", "경기 하남시", "경기 의왕시",
    
    # Incheon
    "인천 연수구", "인천 남동구", "인천 부평구", "인천 서구", "인천 미추홀구",
    "인천 중구", "인천 동구", "인천 계양구",
    
    # Other Major Cities (Samples)
    "부산 해운대구", "부산 부산진구", "부산 수영구",
    "대구 수성구", "대구 중구",
    "대전 서구", "대전 유성구",
    "광주 서구", "광주 광산구",
    "울산 남구", "세종시"
]

TARGET_KEYWORDS = [f"{region} {BASE_KEYWORD}" for region in REGIONS]
