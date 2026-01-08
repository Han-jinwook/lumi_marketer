import streamlit as st
import pandas as pd
import requests
import sys
import os
import time
import random
import json
import subprocess

# Add parent dir to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# ---------------------------------------------------------
# 1. Config & Setup
# ---------------------------------------------------------
st.set_page_config(page_title="루미-링크 B2B Admin", page_icon="🚀", layout="wide")

# ---------------------------------------------------------
# 1.1 Custom CSS (Premium UI/UX)
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background-color: #f8f9fa;
    }
    
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* Header styling */
    h1 {
        color: #1e293b;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #ffffff;
    }
    
    /* Card-like containers */
    div.stBlock {
        background-color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    /* Metrics styling */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
        color: #2563eb;
    }
</style>
""", unsafe_allow_html=True)

# Import email sender
try:
    from messenger.email_sender import send_gmail
except ImportError:
    # If path issues, absolute import or sys.path fix
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from messenger.email_sender import send_gmail

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
mode = st.sidebar.radio("작업 모드", ["샵 검색 및 분석", "Track A (이메일 자동)", "Track B (톡톡/인스타 반자동)", "전체 리스트 (조회용)"])

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

# --- Sidebar: Account Settings ---
st.sidebar.divider()
st.sidebar.subheader("🔐 계정 설정 (자동 발송용)")
with st.sidebar.expander("네이버/인스타 정보 입력"):
    st.session_state['naver_user'] = st.sidebar.text_input("네이버 ID", value=st.session_state.get('naver_user', ''))
    st.session_state['naver_pw'] = st.sidebar.text_input("네이버 PW", type="password", value=st.session_state.get('naver_pw', ''))
    st.session_state['insta_user'] = st.sidebar.text_input("인스타 ID", value=st.session_state.get('insta_user', ''))
    st.session_state['insta_pw'] = st.sidebar.text_input("인스타 PW", type="password", value=st.session_state.get('insta_pw', ''))
    
    st.divider()
    st.sidebar.subheader("📧 Gmail 설정 (Track A)")
    st.session_state['gmail_user'] = st.sidebar.text_input("Gmail 주소", value=st.session_state.get('gmail_user', ''))
    st.session_state['gmail_app_pw'] = st.sidebar.text_input("Gmail 앱 비밀번호", type="password", value=st.session_state.get('gmail_app_pw', ''))
    st.sidebar.caption("※ 설정 -> 보안 -> 2단계 인증 -> 앱 비밀번호에서 생성한 암호를 입력하세요.")
    
    st.divider()
    st.caption("※ 정보는 발송을 위해서만 사용됩니다.")
    
    # Session Status Indicator
    st.divider()
    st.subheader("📡 세션 상태")
    
    platforms = ["naver", "insta"]
    for p in platforms:
        state_file = os.path.join(os.getcwd(), "browser_session", f"{p}_state.json")
        if os.path.exists(state_file):
            st.success(f"✅ {p.upper()} 세션 로드됨")
        else:
            st.warning(f"❌ {p.upper()} 세션 없음 (로그인 필요)")

# --- Auto Install Playwright on Cloud ---
if os.path.exists("/mount/src") and not os.path.exists("/home/appuser/.cache/ms-playwright"):
    with st.spinner("서버 환경 설정 중 (최초 1회)..."):
        try:
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            st.toast("Playwright 엔진 설치 완료!")
        except Exception as e:
            st.error(f"엔진 설치 실패: {e}")

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
        
        # Check environment
        is_cloud = os.path.exists("/mount/src")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            send_type = st.radio("발송 플랫폼 선택", ["톡톡만", "인스타 DM만", "전체 시도(톡톡 우선)"], horizontal=True)
            method_map = {"톡톡만": "talk", "인스타 DM만": "insta", "전체 시도(톡톡 우선)": "both"}
            
            if is_cloud:
                st.warning("⚠️ **자동 발송은 로컬 PC에서만 작동합니다.** \n\n클라우드(웹) 환경에서는 로그인 창을 띄울 수 없기 때문입니다. 로컬에서 실행하시려면 아래 명령어를 터미널에 입력하세요:\n`playwright install`")
            else:
                st.info("⚠️ 반드시 브라우저에서 먼저 로그인을 완료해야 합니다.")
        
        with col_m2:
            st.write("") # Spacer
            if st.button(f"🚀 {send_type} 자동 발송 시작", type="primary", use_container_width=True):
                if 'selected_targets' in st.session_state and st.session_state['selected_targets']:
                    targets = st.session_state['selected_targets']
                    st.toast(f"{len(targets)}건 {send_type} 발송 시도 중...")
                    
                    # Prepare credentials
                    n_arg = f"{st.session_state['naver_user']}:{st.session_state['naver_pw']}" if st.session_state.get('naver_user') else "None"
                    i_arg = f"{st.session_state['insta_user']}:{st.session_state['insta_pw']}" if st.session_state.get('insta_user') else "None"

                    # Run messenger worker as subprocess
                    try:
                        import json
                        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'messenger', 'safe_messenger.py'))
                        targets_json = json.dumps(targets)
                        
                        # Use st.empty to show real-time logs
                        log_container = st.empty()
                        log_text = "🚀 메시징 엔진 시작 중...\n"
                        log_container.code(log_text)

                        # Background execution with credentials - Use Popen with PIPE to stream output
                        process = subprocess.Popen(
                            [sys.executable, "-u", script_path, targets_json, st.session_state['msg_body'], method_map[send_type], n_arg, i_arg], 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1, # Line buffered
                            universal_newlines=True,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                        )

                        # Let's try a non-blocking loop with a status spinner
                        with st.spinner("메시징 진행 중..."):
                            while process.poll() is None:
                                line = process.stdout.readline()
                                if line:
                                    log_text += line
                                    lines = log_text.split('\n')
                                    if len(lines) > 50:
                                        log_text = '\n'.join(lines[-50:])
                                    log_container.code(log_text)
                                time.sleep(0.1)
                        
                        st.success(f"{send_type} 발송 프로세스 완료!")
                    except Exception as e:
                        st.error(f"발송 실패: {e}")
                else:
                    st.error("발송할 대상을 먼저 선택해 주세요.")

# --- Shop Search & Analysis Mode ---
if mode == "샵 검색 및 분석":
    st.subheader("🔍 정밀 샵 검색 및 데이터 분석")
    
    with st.container():
        # Regional Filters
        col_s1, col_s2, col_s3 = st.columns([1, 1, 2])
        
        with col_s1:
            if not df.empty and '주소' in df.columns:
                df['시/도'] = df['주소'].apply(lambda x: x.split()[0] if isinstance(x, str) and len(x.split()) > 0 else "")
                unique_cities = [c for c in df['시/도'].unique() if c and isinstance(c, str)]
                cities = ["전체"] + sorted(unique_cities)
            else:
                cities = ["전체"]
            selected_city = st.selectbox("광역시/도", cities, key="search_city")
            
        with col_s2:
            districts = ["전체"]
            if not df.empty and '주소' in df.columns:
                temp_df = df.copy()
                if selected_city != "전체":
                    temp_df = temp_df[temp_df['시/도'] == selected_city]
                
                temp_df['시/군/구'] = temp_df['주소'].apply(lambda x: x.split()[1] if isinstance(x, str) and len(x.split()) > 1 else "")
                unique_districts = [d for d in temp_df['시/군/구'].unique() if d and isinstance(d, str)]
                districts = ["전체"] + sorted(unique_districts)
            selected_district = st.selectbox("시/군/구", districts, key="search_district")
            
        with col_s3:
            # Search input for shop name
            search_name = st.text_input("상호명 검색", placeholder="검색할 업체명을 입력하세요", key="search_name")
            
            # Filter pool for table
            pool_df = df.copy()
            if selected_city != "전체":
                pool_df = pool_df[pool_df['시/도'] == selected_city]
            if selected_district != "전체":
                pool_df = pool_df[pool_df['주소'].str.contains(selected_district, na=False)]
            if search_name:
                pool_df = pool_df[pool_df['상호명'].str.contains(search_name, case=False, na=False)]
            
            st.info("💡 아래 리스트에서 업체를 **클릭**하면 상세 정보가 표시됩니다.")

    # 1. Main Table with Selection
    st.write(f"현재 지역 검색 결과: **{len(pool_df)}**건")
    if not pool_df.empty:
        # Reset index to ensure selection index matches pool_df row index
        display_df = pool_df[['상호명', '주소', '번호', '이메일', '인스타', '톡톡링크']].reset_index(drop=True)
        # Also need to reset pool_df to keep it in sync for detail view
        pool_df = pool_df.reset_index(drop=True)
        
        selection = st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            column_config={
                "인스타": st.column_config.LinkColumn("인스타", width="small"),
                "톡톡링크": st.column_config.LinkColumn("톡톡", width="small"),
                "주소": st.column_config.TextColumn("주소", width="large")
            }
        )

        # 2. Detail View (Shows when a row is selected)
        selected_rows = selection.get("selection", {}).get("rows", [])
        if selected_rows:
            selected_idx = selected_rows[0]
            shop_detail = pool_df.iloc[selected_idx]
            
            st.divider()
            st.markdown(f"### 🎯 선택된 업체 상세 정보: {shop_detail['상호명']}")
            
            d_col1, d_col2 = st.columns([2, 1])
            
            with d_col1:
                st.markdown(f"#### 📍 기본 상세")
                st.write(f"**🏠 주소:** {shop_detail['주소']}")
                st.write(f"**📞 전화번호:** {shop_detail['번호']}")
                st.write(f"**📧 이메일:** {shop_detail.get('이메일', '없음')}")
                
                # Action Buttons
                st.write("")
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                if shop_detail['인스타']:
                    btn_col1.link_button("📸 인스타그램", shop_detail['인스타'], use_container_width=True)
                if shop_detail['톡톡링크']:
                    btn_col2.link_button("💬 네이버 톡톡", shop_detail['톡톡링크'], use_container_width=True)
                if shop_detail['플레이스링크']:
                    btn_col3.link_button("🗺️ 네이버 플레이스", shop_detail['플레이스링크'], type="primary", use_container_width=True)
            
            with d_col2:
                # Competitors Section
                st.markdown("#### 🏆 인근 9개 경쟁샵 분석")
                comp_data = shop_detail.get('top_9_competitors')
                if comp_data:
                    try:
                        if isinstance(comp_data, str):
                            comps = json.loads(comp_data)
                        else:
                            comps = comp_data
                            
                        for i, comp in enumerate(comps[:7]): # Show top 7
                            st.write(f"{i+1}. **{comp['name']}** ({comp['distance_m']}m)")
                            st.caption(f"  └ {comp['address']}")
                    except:
                        st.info("분석 데이터를 불러오는 중입니다...")
                else:
                    st.info("경쟁샵 분석 데이터가 아직 수집되지 않았습니다.")
            st.divider()
        
    # Stop here if in search mode to prevent showing redundant filters/lists below
    st.stop()

# --- Region Filter (Main Area for Track A/B/All) ---
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
        selected_city = st.selectbox("필터: 광역시/도", cities, key="main_city")
        
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
            
        selected_district = st.selectbox("필터: 시/군/구", districts, key="main_district")

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
        ].copy()
        
        if target_df.empty:
            st.warning("이메일이 있는 샵이 없습니다.")
        else:
            # Selection Logic for Track A
            if 'track_a_sel' not in st.session_state:
                st.session_state['track_a_sel'] = pd.DataFrame({'선택': [False] * len(target_df)})

            # Toggle All Button
            col_a1, col_a2 = st.columns([1, 4])
            with col_a1:
                if st.button("✅ 전체 선택", key="btn_a_all"):
                    st.session_state['track_a_sel'] = pd.DataFrame({'선택': [True] * len(target_df)})
                    st.rerun()
            with col_a2:
                if st.button("❌ 전체 해제", key="btn_a_none"):
                    st.session_state['track_a_sel'] = pd.DataFrame({'선택': [False] * len(target_df)})
                    st.rerun()

            # Data Editor for selection
            display_df = target_df[['상호명', '이메일', '주소']].reset_index(drop=True)
            # Merge with selection state
            if len(st.session_state['track_a_sel']) != len(display_df):
                st.session_state['track_a_sel'] = pd.DataFrame({'선택': [False] * len(display_df)})
            
            edited_df = st.data_editor(
                pd.concat([st.session_state['track_a_sel'], display_df], axis=1),
                use_container_width=True,
                hide_index=True,
                key="editor_track_a"
            )
            # Update selection state
            st.session_state['track_a_sel'] = edited_df[['선택']]
            selected_count = len(edited_df[edited_df['선택']])

            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button(f"📧 {selected_count}건 발송 (Gmail)"):
                    if selected_count > 0:
                        sender = st.session_state.get('gmail_user')
                        pw = st.session_state.get('gmail_app_pw')
                        
                        if not sender or not pw:
                            st.error("사이드바에서 Gmail 계정 정보를 먼저 설정해 주세요.")
                        else:
                            st.toast(f"메일 발송을 시작합니다...")
                            success_count = 0
                            fail_count = 0
                            
                            progress_bar = st.progress(0)
                            selected_items = edited_df[edited_df['선택']].to_dict('records')
                            
                            for i, shop in enumerate(selected_items):
                                try:
                                    # Personalize content
                                    subject = st.session_state['email_subject'].format(상호명=shop['상호명'], 지역=shop.get('주소', '인근 구/동').split()[1] if len(shop.get('주소', '').split()) > 1 else "인근")
                                    body = st.session_state['email_body'].format(상호명=shop['상호명'], 지역=shop.get('주소', '인근 구/동').split()[1] if len(shop.get('주소', '').split()) > 1 else "인근")
                                    
                                    ok, msg = send_gmail(sender, pw, shop['이메일'], subject, body)
                                    if ok:
                                        success_count += 1
                                    else:
                                        st.error(f"실패: {shop['상호명']} ({shop['이메일']}) - {msg}")
                                        fail_count += 1
                                except Exception as e:
                                    st.error(f"오류: {shop['상호명']} - {e}")
                                    fail_count += 1
                                
                                # Update progress
                                progress_bar.progress((i + 1) / len(selected_items))
                                time.sleep(random.uniform(1, 3)) # Anti-spam delay
                                
                            st.success(f"발송 완료! (성공: {success_count}건, 실패: {fail_count}건)")
                    else:
                        st.error("발송할 대상을 선택해 주세요.")
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
            # Selection Logic for Track B
            if 'track_b_sel' not in st.session_state:
                st.session_state['track_b_sel'] = pd.DataFrame({'선택': [False] * len(target_df)})

            # Toggle All Buttons
            col_b1, col_b2, col_b3 = st.columns([1, 1, 3])
            with col_b1:
                if st.button("✅ 전체 선택", key="btn_b_all"):
                    st.session_state['track_b_sel'] = pd.DataFrame({'선택': [True] * len(target_df)})
                    st.rerun()
            with col_b2:
                if st.button("❌ 전체 해제", key="btn_b_none"):
                    st.session_state['track_b_sel'] = pd.DataFrame({'선택': [False] * len(target_df)})
                    st.rerun()
            with col_b3:
                selected_count = len(st.session_state['track_b_sel'][st.session_state['track_b_sel']['선택']])
                st.write(f"현재 **{selected_count}**개 업체 선택됨")

            # Data Editor for selection - Simplified View (Name, Talk, Insta only)
            display_df = target_df[['상호명', '톡톡링크', '인스타']].reset_index(drop=True)
            if len(st.session_state['track_b_sel']) != len(display_df):
                st.session_state['track_b_sel'] = pd.DataFrame({'선택': [False] * len(display_df)})

            edited_df = st.data_editor(
                pd.concat([st.session_state['track_b_sel'], display_df], axis=1),
                use_container_width=True,
                hide_index=True,
                key="editor_track_b",
                column_config={
                    "톡톡링크": st.column_config.LinkColumn("톡톡링크", width="medium"),
                    "인스타": st.column_config.LinkColumn("인스타 DM", width="medium"),
                }
            )
            # Sync selection state
            st.session_state['track_b_sel'] = edited_df[['선택']]
            st.session_state['selected_targets'] = edited_df[edited_df['선택']].to_dict('records')

            # Show personalized message sample for the first selected item
            if not edited_df[edited_df['선택']].empty:
                st.divider()
                st.subheader("✉️ 발송 메시지 미리보기 (첫 번째 선택 대상)")
                first_row = edited_df[edited_df['선택']].iloc[0]
                region = first_row.get('시/군/구', '인근 구/동')
                sample_msg = st.session_state['msg_body'].format(상호명=first_row['상호명'], 지역=region)
                st.code(sample_msg, language=None)
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
