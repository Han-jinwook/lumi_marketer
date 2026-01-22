@echo off
chcp 65001
echo ==========================================
echo   루미-링크 B2B Admin 대시보드 실행
echo ==========================================
echo.
echo 로컬 서버를 실행합니다...
echo.

python -m streamlit run admin_dashboard/app.py

pause
