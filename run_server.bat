@echo off
chcp 65001
echo ==========================================
echo   피부샵 블로그 크롤러 - 서버 모드 실행
echo ==========================================
echo.

echo 1. 필수 라이브러리 확인 중...
py -m pip install schedule requests beautifulsoup4 lxml selenium webdriver-manager pandas python-dotenv supabase

echo.
echo 2. 스케줄러를 시작합니다. (6시간마다 실행)
echo ** 창을 닫으면 종료됩니다. 최소화만 해주세요. **
echo.

py scheduler.py

pause
