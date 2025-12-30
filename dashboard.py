import streamlit as st
import pandas as pd
import os
import time
import sys
import requests
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
            try:
                # Use current python executable for stability
                process = subprocess.Popen(
                    [sys.executable, "main.py"], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8'
                )
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    st.success("크롤링이 완료되었습니다!")
                else:
                    st.error(f"크롤링 중 오류가 발생했습니다. (Exit Code: {process.returncode})")
                    if stderr:
                        st.error(f"Error Log: {stderr}")
            except Exception as e:
                st.error(f"실행 중 예외 발생: {e}")
                
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
    st.subheader("수집된 원장님 데이터 목록 (From Supabase)")
    
    # Fetch data from Supabase directly
    url = f"{config.SUPABASE_URL}/rest/v1/{config.SUPABASE_TABLE}?select=*"
    headers = {
        "apikey": config.SUPABASE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data:
            df = pd.DataFrame(data)
            
            # Use appropriate column names based on the table schema
            # Mapping common fields if they exist
            if 'blog_url' in df.columns:
                df = df.rename(columns={'blog_url': '블로그 URL', 'title': '블로그 제목', 'email': '이메일'})
            elif 'name' in df.columns:
                # If t_crawled_shops schema is used
                df = df.rename(columns={'name': '상호명', 'address': '주소', 'phone': '전화번호', 'email': '이메일'})

            # Show stats
            col1, col2 = st.columns(2)
            col1.metric("총 수집된 업체", f"{len(df)}개")
            if '이메일' in df.columns:
                email_count = len(df[df['이메일'].notna() & (df['이메일'] != "")])
                col2.metric("이메일 확보 수", f"{email_count}개")
            
            # Show dataframe
            st.dataframe(df, use_container_width=True)
            
            # Download button
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 CSV 다운로드",
                data=csv_data,
                file_name="skin_shop_leads_live.csv",
                mime="text/csv"
            )
        else:
            st.warning("아직 수집된 데이터가 없습니다. 크롤링을 실행해 주세요.")
            
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        st.info("Supabase 연결 설정을 확인해 주세요.")

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
