import streamlit as st
import pandas as pd
import requests
import sys
import os

# Add parent dir to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# ---------------------------------------------------------
# 1. Config & Setup
# ---------------------------------------------------------
st.set_page_config(page_title="루미-링크 B2B Admin", layout="wide")

# ---------------------------------------------------------
# 2. Data Loading (REST API via Requests)
# ---------------------------------------------------------
def load_data():
    # Use direct REST API to avoid supabase-py/httpx dependency conflicts
    url = f"{config.SUPABASE_URL}/rest/v1/{config.SUPABASE_TABLE}?select=*"
    headers = {
        "apikey": config.SUPABASE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
    except Exception as e:
        st.error(f"데이터 로딩 실패: {e}")
        return pd.DataFrame()
    
    # Handle missing columns if any
    required_cols = ["name", "email", "address", "phone", "talk_url", "instagram_handle", "naver_blog_id", "source_link"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = "" # Fill missing cols
            
    # Rename for UI consistency
    df = df.rename(columns={
        "name": "상호명",
        "email": "이메일",
        "address": "주소",
        "phone": "번호",
        "talk_url": "톡톡링크",
        "instagram_handle": "인스타",
        "naver_blog_id": "블로그ID",
        "source_link": "플레이스링크"
    })
    
    # Normalize Instagram links (handle both full URLs and simple handles)
    def normalize_insta(val):
        if not val or not isinstance(val, str) or val == "None":
            return ""
        if val.startswith("http"):
            return val
        return f"https://www.instagram.com/{val.replace('@', '').strip()}/"
        
    if '인스타' in df.columns:
        df['인스타'] = df['인스타'].apply(normalize_insta)
        
    return df

df = load_data()

import subprocess

# ---------------------------------------------------------
# 3. Sidebar (Controls & Crawler)
# ---------------------------------------------------------
st.sidebar.title("🎮 통합 마케팅 센터")
mode = st.sidebar.radio("작업 모드", ["Track A (이메일 자동)", "Track B (톡톡/인스타 반자동)", "전체 리스트 (조회용)"])

st.sidebar.divider()
st.sidebar.subheader("🕵️‍♀️ 데이터 수집 (크롤러)")
crawl_city = st.sidebar.selectbox("수집 지역 (시/도)", ["서울", "인천", "경기", "부산", "대구", "대전", "광주", "울산", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"])
crawl_district = st.sidebar.text_input("상세 지역 (예: 부평구)", placeholder="구/동 단위 입력")

if st.sidebar.button("🚀 크롤링 시작"):
    if crawl_district:
        target_region = f"{crawl_city} {crawl_district}"
    else:
        target_region = crawl_city
        
    st.sidebar.info(f"'{target_region}' 수집을 시작합니다... (백그라운드)")
    
    # Run in background
    try:
        # Assuming test_detail_10_shops.py is in parent dir
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_detail_10_shops.py'))
        
        # Cross-platform subprocess handling
        popen_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "encoding": "utf-8"
        }
        if os.name == 'nt': # Windows only
            if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        
        # We start it, and wait 2 seconds to see if it crashes immediately
        process = subprocess.Popen([sys.executable, script_path, target_region], **popen_kwargs)
        
        try:
            outs, errs = process.communicate(timeout=2)
            if process.returncode != 0:
                st.sidebar.error(f"즉시 종료됨 (Code: {process.returncode})")
                st.sidebar.code(errs)
            else:
                st.sidebar.success("실행 완료!")
        except subprocess.TimeoutExpired:
            # Still running after 2s, probably good!
            st.sidebar.success("백그라운드에서 실행 중입니다. 잠시 후 새로고침하세요.")
            
    except Exception as e:
        st.sidebar.error(f"실행 실패: {e}")

# ---------------------------------------------------------
# 4. Roster Logic (Mock for now)
# ---------------------------------------------------------
def get_competitors(current_idx, full_df):
    try:
        # Simple random mock
        others = full_df[full_df.index != current_idx]['상호명'].tolist()
        import random
        selected = random.sample(others, min(len(others), 2))
        return ", ".join(selected) + " 등 9곳"
    except:
        return "인근 샵들"

# ---------------------------------------------------------
# 5. Main View
# ---------------------------------------------------------
st.title(f"🚀 {mode}")

# Initialize session state for email template if not exists
if 'email_subject' not in st.session_state:
    st.session_state['email_subject'] = "루미PLUS 독점 제휴 제안드립니다 (원장님 확인용)"
if 'email_body' not in st.session_state:
    st.session_state['email_body'] = """안녕하세요 {상호명} 원장님.
        
인근 샵들과 차별화된 매출 전략을 제안드립니다.
현재 {지역} 내 경쟁이 심화되고 있어, 우선권을 드리고자 합니다.

제안서 확인: [링크]"""

# --- Email Template Editor (Track A Only) ---
if mode == "Track A (이메일 자동)":
    st.info("💡 이메일이 있는 샵 목록입니다. 일괄 발송이 가능합니다.")
    
    with st.expander("📝 이메일 템플릿 수정", expanded=True):
        with st.form("email_form"):
            new_subject = st.text_input("메일 제목", value=st.session_state['email_subject'])
            new_body = st.text_area("메일 본문 (치환자: {상호명}, {지역})", value=st.session_state['email_body'], height=200)
            
            if st.form_submit_button("💾 템플릿 저장"):
                st.session_state['email_subject'] = new_subject
                st.session_state['email_body'] = new_body
                st.success("템플릿이 저장되었습니다!")

# --- Messenger Editor (Track B Only) ---
elif mode == "Track B (톡톡/인스타 반자동)":
    st.warning("🔥 이메일이 없는 샵을 위한 '스나이퍼 모드'입니다. 자동 발송 시 계정 차단에 주의하세요.")
    
    if 'msg_body' not in st.session_state:
        st.session_state['msg_body'] = """안녕하세요 {상호명} 원장님. 
인근 {지역} 내 1곳만 선정하는 루미PLUS 독점 제휴 제안입니다. 
확인해 보세요: [링크]"""

    with st.expander("🤖 자동 발송 설정 & 메시지 편집", expanded=True):
        st.session_state['msg_body'] = st.text_area("발송 메시지 (치환자: {상호명}, {지역})", value=st.session_state['msg_body'], height=150)
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.info("⚠️ 반드시 브라우저에서 먼저 로그인을 완료해야 합니다.")
        with col_m2:
            if st.button("🚀 선택 항목 자동 발송 시작", type="primary", use_container_width=True):
                if 'selected_targets' in st.session_state and st.session_state['selected_targets']:
                    targets = st.session_state['selected_targets']
                    st.toast(f"{len(targets)}건 발송 시도 중...")
                    
                    # Run messenger worker as subprocess
                    try:
                        import json
                        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'messenger', 'safe_messenger.py'))
                        targets_json = json.dumps(targets)
                        
                        # Background execution
                        subprocess.Popen([sys.executable, script_path, targets_json, st.session_state['msg_body']], 
                                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                        st.success("발송 프로세스가 백그라운드에서 시작되었습니다. 로그를 확인하세요.")
                    except Exception as e:
                        st.error(f"발송 실패: {e}")
                else:
                    st.error("발송할 대상을 먼저 선택해 주세요.")

# --- Region Filter (Main Area) ---
with st.container(border=True):
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        # 1. Extract "City"
        if not df.empty and '주소' in df.columns:
            df['시/도'] = df['주소'].apply(lambda x: x.split()[0] if isinstance(x, str) and len(x.split()) > 0 else "")
            unique_cities = [c for c in df['시/도'].unique() if c and isinstance(c, str)]
            cities = ["전체"] + sorted(unique_cities)
        else:
            cities = ["전체"]
        selected_city = st.selectbox("필터: 광역시/도", cities)
        
    with col_f2:
        # 2. Extract "District"
        districts = ["전체"]
        if not df.empty and '주소' in df.columns:
            if selected_city != "전체":
                district_df = df[df['시/도'] == selected_city]
                df['시/군/구'] = district_df['주소'].apply(lambda x: x.split()[1] if isinstance(x, str) and len(x.split()) > 1 else "")
            else:
                df['시/군/구'] = df['주소'].apply(lambda x: x.split()[1] if isinstance(x, str) and len(x.split()) > 1 else "")
            
            unique_districts = [d for d in df['시/군/구'].unique() if d and isinstance(d, str)]
            districts = ["전체"] + sorted(unique_districts)
            
        selected_district = st.selectbox("필터: 시/군/구", districts)

# Filter Logic
filtered_df = df.copy()
if selected_city != "전체":
    filtered_df = filtered_df[filtered_df['시/도'] == selected_city]

if selected_district != "전체":
    filtered_df = filtered_df[filtered_df['주소'].apply(lambda x: x.split()[1] if len(x.split())>1 else "") == selected_district]

# --- Display Data ---
if mode == "Track A (이메일 자동)":
    if not filtered_df.empty:
        # Filter rows with valid email
        target_df = filtered_df[
            (filtered_df['이메일'].notna()) & 
            (filtered_df['이메일'] != "")
        ]
        
        st.dataframe(
            target_df[['상호명', '이메일', '주소']], 
            use_container_width=True,
            hide_index=True
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("📧 전체 발송 (Gmail)"):
                st.toast(f"제목: '{st.session_state['email_subject']}' 로 {len(target_df)}건 발송 시작...")
    else:
        st.write("데이터가 없습니다.")

elif mode == "Track B (톡톡/인스타 반자동)":
    if not filtered_df.empty:
        # Filter rows WITHOUT email
        target_df = filtered_df[
            (filtered_df['이메일'].isna()) | 
            (filtered_df['이메일'] == "")
        ].copy()
        
        if target_df.empty:
            st.warning("이메일이 없는 샵이 없습니다. (모두 이메일 보유 중)")
        else:
            # Batch selection logic
            if 'selected_targets' not in st.session_state:
                st.session_state['selected_targets'] = []

            col_sel, col_stat = st.columns([1, 4])
            with col_sel:
                if st.button("✅ 전체 선택"):
                    st.session_state['selected_targets'] = target_df.to_dict('records')
                    st.rerun()
            with col_stat:
                st.write(f"현재 **{len(st.session_state['selected_targets'])}**개 업체 선택됨")

            for idx, row in target_df.iterrows():
                with st.container(border=True):
                    col_check, col_info, col_msg, col_action = st.columns([0.3, 1.2, 3, 1.2])
                    
                    # Checkbox for selection
                    with col_check:
                        is_selected = any(t['상호명'] == row['상호명'] for t in st.session_state['selected_targets'])
                        if st.checkbox("Pick", value=is_selected, key=f"check_{idx}", label_visibility="collapsed"):
                            if not is_selected:
                                st.session_state['selected_targets'].append(row.to_dict())
                        else:
                            if is_selected:
                                st.session_state['selected_targets'] = [t for t in st.session_state['selected_targets'] if t['상호명'] != row['상호명']]

                    with col_info:
                        st.subheader(row['상호명'])
                        st.caption(row['주소'])
                        
                        # TalkTalk URL Check
                        talk_url = row.get('톡톡링크', '')
                        if not isinstance(talk_url, str) or not talk_url.startswith("http"):
                            talk_url = None
                        
                        # Instagram Check
                        insta_url = row.get('인스타', '')
                        if not isinstance(insta_url, str) or not insta_url.startswith("http"):
                            insta_url = None

                    with col_msg:
                        competitors = get_competitors(idx, df) # Pass original df for context
                        # Use city/district if available
                        region = row.get('시/군/구', '인근 구/동')
                        personalized_msg = st.session_state['msg_body'].format(상호명=row['상호명'], 지역=region)
                        st.code(personalized_msg, language=None)

                    with col_action:
                        st.write("") # Spacer
                        if talk_url:
                            st.link_button("🚀 톡톡 열기", talk_url, type="primary", use_container_width=True)
                        else:
                            st.button("톡톡 없음", disabled=True, key=f"no_talk_{idx}", use_container_width=True)
                        
                        if insta_url:
                            st.link_button("📸 인스타 DM", insta_url, use_container_width=True)
                        else:
                            st.button("인스타 없음", disabled=True, key=f"no_insta_{idx}", use_container_width=True)
    else:
        st.write("데이터가 없습니다.")

elif mode == "전체 리스트 (조회용)":
    st.info("📊 DB에 등록된 전체 리스트입니다.")
    if not filtered_df.empty:
        # Reorder and filter columns for better view
        display_cols = ['상호명', '주소', '번호', '이메일', '블로그ID', '플레이스링크', '톡톡링크', '인스타']
        existing_cols = [c for c in display_cols if c in filtered_df.columns]
        
        st.dataframe(
            filtered_df[existing_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "플레이스링크": st.column_config.LinkColumn("플레이스링크", width="medium"),
                "톡톡링크": st.column_config.LinkColumn("톡톡링크", width="medium"),
                "인스타": st.column_config.LinkColumn("인스타", width="medium"),
                "주소": st.column_config.TextColumn("주소", width="large"),
                "이메일": st.column_config.TextColumn("이메일", width="medium"),
                "번호": st.column_config.TextColumn("번호", width="medium"),
                "블로그ID": st.column_config.TextColumn("블로그ID", width="small"),
            }
        )
        st.caption(f"총 {len(filtered_df)}개의 데이터가 검색되었습니다.")
    else:
        st.write("데이터가 없습니다.")
