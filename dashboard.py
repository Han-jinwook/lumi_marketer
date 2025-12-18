import streamlit as st
import pandas as pd
import subprocess
import os
import time
import config

# Set page config
st.set_page_config(
    page_title="피부샵 크롤러 대시보드",
    page_icon="💆‍♀️",
    layout="wide"
)

# Title
st.title("💆‍♀️ 피부샵 원장 블로그 크롤러 관리자")

# Sidebar for controls
with st.sidebar:
    st.header("⚙️ 컨트롤 패널")
    
    if st.button("🚀 크롤링 지금 실행", type="primary"):
        with st.spinner('크롤러가 실행 중입니다... (로그 탭을 확인하세요)'):
            # Run the crawler as a subprocess to keep independent
            process = subprocess.Popen(
                ["py", "main.py"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8' # Force encoding
            )
            # Wait for it to finish for immediate feedback (optional, or just fire and forget)
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                st.success("크롤링이 완료되었습니다!")
            else:
                st.error("크롤링 중 오류가 발생했습니다.")
                st.error(stderr)
                
    st.markdown("---")
    st.info(f"""
    **설정 정보**
    - 최소 지연시간: {config.MIN_DELAY}초
    - 최대 지연시간: {config.MAX_DELAY}초
    - 키워드 수: {sum(len(v) for v in config.KEYWORDS.values())}개
    """)

# Main Content: Tabs
tab1, tab2 = st.tabs(["📊 수집 데이터", "📝 시스템 로그"])

with tab1:
    st.subheader("수집된 원장님 데이터 목록")
    
    csv_file = config.OUTPUT_CSV
    
    if os.path.exists(csv_file):
        try:
            # Read CSV
            df = pd.read_csv(csv_file)
            
            # Show stats
            col1, col2 = st.columns(2)
            col1.metric("총 수집된 블로그", f"{len(df)}개")
            col2.metric("이메일 확보 수", f"{len(df[df['이메일'].notna()])}개")
            
            # Show dataframe
            st.dataframe(df, use_container_width=True)
            
            # Download button
            with open(csv_file, "rb") as f:
                st.download_button(
                    label="📥 CSV 다운로드",
                    data=f,
                    file_name="skin_shop_leads.csv",
                    mime="text/csv"
                )
        except Exception as e:
            st.error(f"데이터 파일을 읽는 중 오류가 발생했습니다: {e}")
    else:
        st.warning("아직 수집된 데이터가 없습니다. 크롤링을 실행해 주세요.")

with tab2:
    st.subheader("실시간 로그")
    log_file = "crawler.log"
    
    if st.button("🔄 로그 새로고침"):
        st.rerun()
        
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Show last 50 lines
            log_content = "".join(lines[-50:])
            st.code(log_content, language="text")
    else:
        st.info("로그 파일이 아직 생성되지 않았습니다.")
