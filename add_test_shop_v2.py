import os
import sys
import json

# Add parent dir to path to import config
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import config
from crawler.db_handler import DBHandler

def create_test_data():
    db = DBHandler()
    if not db.db_fs:
        print("[-] Firebase not initialized.")
        return

    # Create a fresh test shop with specific details
    test_shop = {
        "상호명": "루미PLUS 2차 테스트샵",
        "주소": "인천 부평구 부평동 123-45",
        "번호": "032-111-2222",
        "플레이스링크": "https://m.place.naver.com/place/test_99999/home",
        "source_link": "https://m.place.naver.com/place/test_99999/home",
        "이메일": "lumi_test2@example.com",
        "인스타": "lumi_test_insta",
        "톡톡링크": "https://talk.naver.com/test2",
        "status": "active",
        "description": "인천 지역 데이터 로딩 및 필터링 테스트용 데이터입니다."
    }
    
    try:
        # Use existing insert_shop logic which handles Firestore injection
        db.insert_shop(test_shop)
        print("[+] Test shop '루미PLUS 2차 테스트샵' added successfuly.")
    except Exception as e:
        print(f"[-] Error: {e}")

if __name__ == "__main__":
    create_test_data()
