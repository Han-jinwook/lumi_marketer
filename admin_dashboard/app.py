import streamlit as st
import pandas as pd
import requests
import sys
import os
import time
import json
import subprocess
import base64

# Add parent dir to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# ---------------------------------------------------------
# 1. Config & Setup
# ---------------------------------------------------------
st.set_page_config(page_title="루미PLUS 어드민", page_icon="✦", layout="wide", initial_sidebar_state="collapsed")

# Initialize session state for navigation and selection
if 'active_page' not in st.session_state:
    st.session_state['active_page'] = 'Shop Search'
if 'show_collector' not in st.session_state:
    st.session_state['show_collector'] = False
if 'last_selected_shop' not in st.session_state:
    st.session_state['last_selected_shop'] = None

# Initialize selection states for tracks
for track in ['A', 'B', 'C']:
    if f'sel_track_{track}' not in st.session_state:
        st.session_state[f'sel_track_{track}'] = {}

# Helper for Logo
def get_base64_logo(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = f.read()
            return base64.b64encode(data).decode()
    return ""

logo_base64 = get_base64_logo(os.path.join(os.path.dirname(__file__), "logo.png"))

# ---------------------------------------------------------
# 1.1 UI CSS (V12: Perfectionist Alignment & UX)
# ---------------------------------------------------------
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    :root {{
        --primary: #9d7dfa;
        --bg: #ffffff;
        --text-main: #1e293b;
        --text-muted: #94a3b8;
        --border: #f1f5f9;
        --radius: 16px;
    }}

    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background: white; }}

    /* Tighten Layout Space */
    .block-container {{
        padding-top: 0.4rem !important;
        padding-bottom: 2rem !important;
        padding-left: 4rem !important;
        padding-right: 4rem !important;
    }}

    hr {{ margin: 0.5rem 0 !important; }}

    /* Hide Streamlit elements */
    .stHeader {{ display: none; }}
    [data-testid="stSidebar"] {{ display: none; }}
    #MainMenu {{ visibility: hidden; }}
    header {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}

    /* Navigation Styles */
    .nav-link-box button {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 8px 0 !important;
        min-height: 0 !important;
        height: auto !important;
        width: auto !important;
        margin: 0 auto !important;
        display: block !important;
        transition: all 0.2s ease !important;
    }}
    
    .nav-btn-active button p {{
        color: var(--text-main) !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        border-bottom: 2px solid var(--primary);
    }}
    
    .nav-btn-inactive button p {{
        color: var(--text-muted) !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
    }}
    
    .nav-btn-inactive button:hover p {{ color: var(--primary) !important; }}

    /* Detail Panel Card Alignment (Tuned for Table Header) */
    .detail-panel-box {{
        background: #fcfaff;
        border: 1px solid #f1f5f9;
        border-radius: var(--radius);
        padding: 1.5rem;
        margin-top: 24px; /* Precision alignment with table header */
    }}

    /* Container Styling */
    div.stBlock, [data-testid="stExpander"] {{
        background: white;
        border: 1px solid #f8fafc;
        border-radius: var(--radius);
        padding: 2rem;
    }}

    /* Data Table */
    div.stDataFrame {{
        border: 1px solid #f1f5f9;
        border-radius: 14px;
        overflow: hidden;
    }}

    /* Primary Action Buttons */
    .stButton > button[kind="primary"] {{
        background: var(--primary);
        border: none;
        border-radius: 10px;
        font-weight: 700;
        padding: 0.6rem 1.5rem;
    }}
    
    /* Selection Toggle Buttons (Small) */
    .small-toggle-btn button {{
        padding: 2px 8px !important;
        font-size: 0.75rem !important;
        border-radius: 4px !important;
        min-height: 24px !important;
    }}
    
    .delete-btn button {{
        background: #fee2e2 !important;
        color: #ef4444 !important;
        border: none !important;
        padding: 2px 10px !important;
        font-size: 0.8rem !important;
        border-radius: 6px !important;
    }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1.2 Header Navigation
# ---------------------------------------------------------
with st.container():
    h_col1, h_col2, h_col3 = st.columns([1, 4, 0.5])
    
    with h_col1:
        if logo_base64:
            st.markdown(f'<img src="data:image/png;base64,{logo_base64}" style="height: 48px; object-fit: contain;">', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-weight:800; font-size:1.6rem; color:#1e293b;">루미PLUS</div>', unsafe_allow_html=True)
            
    with h_col2:
        m_spacer1, m_crawl, m1, m2, m3, m4, m_spacer2 = st.columns([0.2, 0.7, 1, 1, 1, 1, 0.2])
        
        with m_crawl:
            st.markdown(f'<div class="nav-link-box {"nav-btn-active" if st.session_state["show_collector"] else "nav-btn-inactive"}">', unsafe_allow_html=True)
            if st.button("Crawling", key="n_crawl_v12"):
                st.session_state['show_collector'] = not st.session_state['show_collector']
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        pages = ["Shop Search", "Track A", "Track B", "Track C"]
        labels = ["검색 및 분석", "Track A: 이메일", "Track B: 톡톡", "Track C: 인스타"]
        
        for i, (p, label) in enumerate(zip(pages, labels)):
            with [m1, m2, m3, m4][i]:
                is_active = st.session_state['active_page'] == p
                st.markdown(f'<div class="nav-link-box {"nav-btn-active" if is_active else "nav-btn-inactive"}">', unsafe_allow_html=True)
                if st.button(label, key=f"n_v12_{p}"):
                    st.session_state['active_page'] = p
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    with h_col3:
        st.markdown('<div style="width:34px; height:34px; background:#fcfcfc; border:1px solid #f1f5f9; border-radius:50%; margin-top:8px; margin-left:auto;"></div>', unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------
# 2. Data & Business Logic
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def load_data():
    url = f"{config.SUPABASE_URL}/rest/v1/{config.SUPABASE_TABLE}?select=*"
    headers = {"apikey": config.SUPABASE_KEY, "Authorization": f"Bearer {config.SUPABASE_KEY}", "Content-Type": "application/json"}
    try:
        response = requests.get(url, headers=headers)
        df = pd.DataFrame(response.json())
        df = df.rename(columns={"id": "ID", "name": "상호명", "email": "이메일", "address": "주소", "phone": "번호", "talk_url": "톡톡링크", "instagram_handle": "인스타", "source_link": "플레이스링크"})
        def n_i(v):
            if not v or v == "None": return ""
            return v if v.startswith("http") else f"https://www.instagram.com/{v.replace('@', '').strip()}/"
        if '인스타' in df.columns: df['인스타'] = df['인스타'].apply(n_i)
        return df
    except: return pd.DataFrame()

def delete_shop(shop_id):
    url = f"{config.SUPABASE_URL}/rest/v1/{config.SUPABASE_TABLE}?id=eq.{shop_id}"
    headers = {"apikey": config.SUPABASE_KEY, "Authorization": f"Bearer {config.SUPABASE_KEY}", "Content-Type": "application/json"}
    try:
        res = requests.delete(url, headers=headers)
        if res.status_code in [200, 204]:
            st.toast("삭제 완료되었습니다.")
            st.cache_data.clear()
            st.session_state['last_selected_shop'] = None
            time.sleep(1)
            st.rerun()
        else: st.error(f"삭제 실패: {res.status_code}")
    except Exception as e: st.error(f"오류 발생: {e}")

df = load_data()

def render_filters_v12(df_input, key):
    with st.container(border=False):
        c1, c2, c3 = st.columns([1, 1, 2.5])
        with c1:
            df_input['시/도'] = df_input['주소'].apply(lambda x: x.split()[0] if isinstance(x, str) and x.split() else "")
            sel_city = st.selectbox("지역 (시/도)", ["전체"] + sorted(list(df_input['시/도'].unique())), key=f"{key}_city_v12")
        with c2:
            d_list = ["전체"]
            if sel_city != "전체":
                d_list = ["전체"] + sorted(list(df_input[df_input['시/도'] == sel_city]['주소'].apply(lambda x: x.split()[1] if len(x.split()) > 1 else "").unique()))
            sel_dist = st.selectbox("지역 (군/구)", d_list, key=f"{key}_dist_v12")
        with c3:
            s_q = st.text_input("업체명 검색", key=f"{key}_q_v12", placeholder="업체명을 입력하세요...")
            
    filtered = df_input.copy()
    if sel_city != "전체": filtered = filtered[filtered['시/도'] == sel_city]
    if sel_dist != "전체": filtered = filtered[filtered['주소'].str.contains(sel_dist, na=False)]
    if s_q: filtered = filtered[filtered['상호명'].str.contains(s_q, case=False, na=False)]
    return filtered

# --- Helper: Render Marketing Track ---
def render_track(track_id, label, icon, column_filter, config_expander_name, df):
    st.markdown(f"#### {icon} {label}")
    with st.expander(f"❖ {config_expander_name}"):
        sc1, sc2 = st.columns(2)
        if track_id == 'A':
            st.session_state['gmail_user'] = sc1.text_input("Gmail", value=st.session_state.get('gmail_user', ''))
            st.session_state['gmail_app_pw'] = sc2.text_input("App PW", type="password", value=st.session_state.get('gmail_app_pw', ''))
        elif track_id == 'B':
            st.session_state['naver_user'] = sc1.text_input("Naver ID", value=st.session_state.get('naver_user', ''))
            st.session_state['naver_pw'] = sc2.text_input("PW", type="password", value=st.session_state.get('naver_pw', ''))
        else:
            st.session_state['insta_user'] = sc1.text_input("Instagram ID", value=st.session_state.get('insta_user', ''))
            st.session_state['insta_pw'] = sc2.text_input("PW", type="password", value=st.session_state.get('insta_pw', ''))

    p_df = render_filters_v12(df, f"track{track_id}")
    t_df = p_df[p_df[column_filter].notna() & (p_df[column_filter] != "")].copy()
    
    if not t_df.empty:
        # Template (Track A only for now)
        if track_id == 'A':
            with st.expander("✧ 템플릿 마스터", expanded=True):
                st.text_input("메일 제목", value=st.session_state.get('email_subject', '제안서'))
                st.text_area("메일본문", value=st.session_state.get('email_body', '안녕하십니까 {상호명}...'), height=150)
        else:
            st.text_area("자동 발송 메시지", value=st.session_state.get(f'msg_{track_id}', "안녕하세요 {상호명}..."), height=100, key=f"txt_{track_id}")

        # Selection Control Row
        sel_c1, sel_c2, sel_c3 = st.columns([1, 1, 4])
        with sel_c1:
            if st.button("전체 선택", key=f"sa_{track_id}"):
                for idx in t_df.index: st.session_state[f'sel_track_{track_id}'][idx] = True
                st.rerun()
        with sel_c2:
            if st.button("전체 해제", key=f"da_{track_id}"):
                st.session_state[f'sel_track_{track_id}'] = {}
                st.rerun()

        # Data Editor with Selection
        t_df['선택'] = [st.session_state[f'sel_track_{track_id}'].get(i, False) for i in t_df.index]
        cols = ['선택', '상호명', column_filter, '주소']
        edited_df = st.data_editor(t_df[cols].reset_index(drop=True), use_container_width=True, hide_index=True, key=f"editor_{track_id}")
        
        if st.button(f"{icon} {label} 가동", type="primary"): st.toast(f"✦ {label} 프로세스 시작")
    else:
        st.info(f"{column_filter} 데이터가 있는 업체가 없습니다.")

# ---------------------------------------------------------
# 3. Page Router
# ---------------------------------------------------------
page = st.session_state['active_page']

# --- Page: 검색 및 분석 (Master-Detail Split View) ---
if page == 'Shop Search':
    st.markdown("#### ⬖ 타겟 샵 데이터 탐색 및 상권 분석")
    f_df = render_filters_v12(df, "search_final")
    
    m_col, d_col = st.columns([1.6, 1]) if st.session_state['last_selected_shop'] is not None else (st.container(), None)

    with m_col:
        h_col_l, h_col_r = st.columns([3, 1])
        h_col_l.caption("✦ 수집 데이터 리스트")
        if st.session_state['last_selected_shop'] is not None:
            with h_col_r:
                st.markdown('<div class="delete-btn" style="text-align:right;">', unsafe_allow_html=True)
                if st.button("✕ 데이터 삭제", key="btn_del_shop"):
                    delete_shop(st.session_state['last_selected_shop']['ID'])
                st.markdown('</div>', unsafe_allow_html=True)

        selection = st.dataframe(
            f_df[['상호명', '주소', '번호', '이메일', '인스타', '톡톡링크']].reset_index(drop=True),
            use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun", height=600
        )
        s_rows = selection.get("selection", {}).get("rows", [])
        if s_rows:
            st.session_state['last_selected_shop'] = f_df.iloc[s_rows[0]]
            if d_col is None: st.rerun()
        else:
            if st.session_state['last_selected_shop'] is not None:
                st.session_state['last_selected_shop'] = None
                st.rerun()

    if d_col is not None and st.session_state['last_selected_shop'] is not None:
        shop = st.session_state['last_selected_shop']
        with d_col:
            st.markdown(f"""
            <div class="detail-panel-box">
                <h5 style="margin-top:0; color:var(--primary); font-weight:800;">✦ {shop['상호명']} 상세 분석</h5>
                <p style="font-size:0.85rem; color:#64748b; margin-bottom:0.8rem;">📍 {shop['주소']}</p>
                <div style="background:white; border-radius:12px; padding:1.2rem; border:1px solid #f1f5f9; margin-bottom:1rem;">
                    <p style="font-size:0.9rem; margin-bottom:6px;"><b>✆ 전화번호:</b> {shop['번호']}</p>
                    <p style="font-size:0.9rem; margin-bottom:0;"><b>✉ 이메일:</b> {shop.get('이메일', '-')}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            if shop['인스타']: c1.link_button("◈ 인스타", shop['인스타'], use_container_width=True)
            if shop['톡톡링크']: c2.link_button("🗨 톡톡", shop['톡톡링크'], use_container_width=True)
            if shop['플레이스링크']: c3.link_button("✦ 플레이스", shop['플레이스링크'], use_container_width=True)
            
            st.write("")
            st.markdown("##### ✦ 주변 경쟁 업체 분석 (TOP 9)")
            c_data = shop.get('top_9_competitors')
            if c_data:
                try:
                    comps = json.loads(c_data) if isinstance(c_data, str) else c_data
                    for i, c_item in enumerate(comps[:9]):
                        st.markdown(f"<p style='font-size:0.85rem; margin-bottom:4px;'>{i+1}. <b>{c_item['name']}</b> ({c_item['distance_m']}m)</p>", unsafe_allow_html=True)
                except: st.caption("분석 데이터 로드 중...")
            else: st.info("수집된 경쟁 업체 데이터 없음.")

elif page == 'Track A': render_track('A', 'TRACK A: 이메일 마케팅', '✉', '이메일', '계정 설정', df)
elif page == 'Track B': render_track('B', 'TRACK B: 네이버 톡톡 자동화', '🗨', '톡톡링크', '네이버 로그인', df)
elif page == 'Track C': render_track('C', 'TRACK C: 인스타그램 Auto-DM', '◈', '인스타', '인스타그램 로그인', df)

if st.session_state['show_collector']:
    # Crawling panel remains accessible
    pass
