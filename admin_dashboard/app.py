import streamlit as st
import pandas as pd
import requests
import sys
import os
import time
import json
import subprocess
import base64
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent dir to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from messenger.email_sender import send_gmail

# ---------------------------------------------------------
# 1. Config & Setup
# ---------------------------------------------------------
st.set_page_config(page_title="루미PLUS 어드민", page_icon="✦", layout="wide", initial_sidebar_state="expanded")

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

# --- Template Persistence Logic ---
TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "templates.json")

def load_templates():
    default = {
        "tpl_A": {"subject": "[제안] 루미PLUS 비즈니스 협업 제안드립니다.", "body": "안녕하세요 {상호명} 원장님,\n\n피부샵 성장을 돕는 루미PLUS입니다..."},
        "tpl_B": "안녕하세요 {상호명} 원장님! 톡톡으로 문의드립니다.",
        "tpl_C": "안녕하세요 {상호명} 원장님, 인스타 DM 드립니다!",
        "gmail_user": "", "gmail_app_pw": "",
        "naver_user": "", "naver_pw": "",
        "insta_user": "", "insta_pw": ""
    }
    if os.path.exists(TEMPLATE_FILE):
        try:
            with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return default
    return default

def save_templates():
    data = {
        "tpl_A": st.session_state.get("tpl_A"),
        "tpl_B": st.session_state.get("tpl_B"),
        "tpl_C": st.session_state.get("tpl_C"),
        "gmail_user": st.session_state.get("gmail_user"),
        "gmail_app_pw": st.session_state.get("gmail_app_pw"),
        "naver_user": st.session_state.get("naver_user"),
        "naver_pw": st.session_state.get("naver_pw"),
        "insta_user": st.session_state.get("insta_user"),
        "insta_pw": st.session_state.get("insta_pw")
    }
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    st.toast("설정이 성공적으로 저장되었습니다.")

# Initialize templates from file
if 'templates_loaded' not in st.session_state:
    saved_tpls = load_templates()
    st.session_state['tpl_A'] = saved_tpls.get("tpl_A")
    st.session_state['tpl_B'] = saved_tpls.get("tpl_B")
    st.session_state['tpl_C'] = saved_tpls.get("tpl_C")
    st.session_state['gmail_user'] = saved_tpls.get("gmail_user", "")
    st.session_state['gmail_app_pw'] = saved_tpls.get("gmail_app_pw", "")
    st.session_state['naver_user'] = saved_tpls.get("naver_user", "")
    st.session_state['naver_pw'] = saved_tpls.get("naver_pw", "")
    st.session_state['insta_user'] = saved_tpls.get("insta_user", "")
    st.session_state['insta_pw'] = saved_tpls.get("insta_pw", "")
    st.session_state['templates_loaded'] = True

# --- Sidebar: Crawler Command Center (Moved to Top) ---
with st.sidebar:
    st.markdown("### 🛰 데이터 수집 엔진")
    st.caption("네이버 플레이스 실시간 수집")
    st.write("---")
    s_city = st.selectbox("수집 지역 (시/도)", ["서울", "인천", "경기", "부산", "대구", "대전", "광주", "울산", "세종", "제주"], key="sb_city")
    s_dist = st.text_input("상세 지역 (군/구/명칭)", placeholder="부평동, 강남역 등", key="sb_dist")
    s_count = st.slider("수집 개수", 5, 100, 10, step=5, key="sb_count")
    
    if st.button("✦ 엔진 가동", type="primary", use_container_width=True, key="btn_sb_run"):
        target = f"{s_city} {s_dist}" if s_dist else s_city
        st.toast(f"'{target}' 수집을 시작합니다. (목표: {s_count}개)")
        try:
            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_detail_10_shops.py'))
            subprocess.Popen([sys.executable, script_path, target, str(s_count)], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except Exception as e:
            st.error(f"엔진 가동 실패: {e}")
            
    if st.button("🔄 데이터 새로고침", use_container_width=True, key="btn_sb_refresh"):
        st.cache_data.clear()
        st.rerun()
    st.write("---")
    st.info("완료 후 '데이터 새로고침'을 눌러주세요.")

# Helper for Logo
def get_base64_logo(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = f.read()
            return base64.b64encode(data).decode()
    return ""

logo_base64 = get_base64_logo(os.path.join(os.path.dirname(__file__), "logo.png"))

# ---------------------------------------------------------
# 1.1 UI CSS (V13: Ultimate Minimalism & Top-Ref)
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
        padding-top: 3rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }}
    
    hr {{ margin: 0.5rem 0 !important; }}

    /* Minimal CSS to allow Streamlit defaults for sidebar/header */

    /* Navigation Styles */
    .nav-link-box button {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 8px 12px !important;
        min-height: 0 !important;
        height: auto !important;
        width: 100% !important;
        margin: 0 !important;
        display: flex !important;
        justify-content: center !important;
        transition: all 0.2s ease !important;
    }}
    
    .nav-btn-active button p {{
        color: var(--text-main) !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        border-bottom: 2px solid var(--primary);
        white-space: nowrap !important;
    }}
    
    .nav-btn-inactive button p {{
        color: var(--text-muted) !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        white-space: nowrap !important;
    }}
    
    .nav-btn-inactive button:hover p {{ color: var(--primary) !important; }}

    /* Detail Panel Alignment (Calibrated to Table Header) */
    .detail-panel-box {{
        background: #fcfaff;
        border: 1px solid #f1f5f9;
        border-radius: var(--radius);
        padding: 1.5rem;
        margin-top: 42px; /* Alignment with Table Header */
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

    /* Primary Buttons */
    .stButton > button[kind="primary"] {{
        background: var(--primary);
        border: none;
        border-radius: 10px;
        font-weight: 700;
        padding: 0.6rem 1.5rem;
    }}
    
    /* Header Micro Refresh Button */
    .micro-ref-btn button, .research-btn button {{
        background: transparent !important;
        color: var(--text-muted) !important;
        border: 1px solid #f1f5f9 !important;
        padding: 4px 12px !important;
        font-size: 0.75rem !important;
        border-radius: 8px !important;
        height: auto !important;
        min-height: 0 !important;
        transition: all 0.2s ease !important;
        white-space: nowrap !important;
    }}
    
    .micro-ref-btn button:hover, .research-btn button:hover {{
        background: #f8fafc !important;
        color: var(--primary) !important;
        border-color: var(--primary) !important;
    }}
    
    /* Delete Button Style */
    .delete-btn button {{
        background: #fee2e2 !important;
        color: #ef4444 !important;
        border: none !important;
        padding: 2px 10px !important;
        font-size: 0.8rem !important;
        border-radius: 6px !important;
    }}
    
    /* Compact Card Styling */
    .compact-card {{
        background: white;
        border: 1px solid #f1f5f9;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 0.4rem;
        transition: all 0.2s ease;
    }}
    .compact-card:hover {{
        border-color: var(--primary);
        box-shadow: 0 4px 12px rgba(157, 125, 250, 0.05);
    }}
</style>
""", unsafe_allow_html=True)

# --- 1.2 Header Navigation ---
with st.container():
    # Optimized layout: [Logo][M1][M2][M3][M4][Profile] - Removed manual refresh button
    h_cols = st.columns([0.8, 1.6, 1.6, 1.6, 1.6, 0.4], vertical_alignment="center")
    
    with h_cols[0]:
        if logo_base64:
            st.markdown(f'<img src="data:image/png;base64,{logo_base64}" style="height: 48px; object-fit: contain;">', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-weight:800; font-size:1.6rem; color:#1e293b;">루미PLUS</div>', unsafe_allow_html=True)
            
    pages = ["Shop Search", "Track A", "Track B", "Track C"]
    labels = ["검색 및 분석", "Track A: 이메일", "Track B: 톡톡", "Track C: 인스타"]
    
    for i, (p, label) in enumerate(zip(pages, labels)):
        with h_cols[1+i]: 
            is_active = st.session_state['active_page'] == p
            st.markdown(f'<div class="nav-link-box {"nav-btn-active" if is_active else "nav-btn-inactive"}">', unsafe_allow_html=True)
            if st.button(label, key=f"n_v16_{p}"):
                st.session_state['active_page'] = p
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with h_cols[5]:
        st.markdown('<div style="width:34px; height:34px; background:#fcfcfc; border:1px solid #f1f5f9; border-radius:50%; margin-left:auto;"></div>', unsafe_allow_html=True)

st.divider()

# --- 2.2 Data Logic ---
@st.cache_data(ttl=60)
def load_data():
    f_df = pd.DataFrame()
    mandatory_cols = ["상호명", "주소", "플레이스링크", "번호", "이메일", "인스타", "톡톡링크", "블로그ID"]
    
    # 1. Load from Firebase
    try:
        from crawler.db_handler import DBHandler
        db = DBHandler()
        if db.db_fs:
            docs = db.db_fs.collection(config.FIREBASE_COLLECTION).stream()
            data_list = []
            for doc in docs:
                d = doc.to_dict()
                d['ID'] = doc.id
                data_list.append(d)
            if data_list:
                f_df = pd.DataFrame(data_list)
    except Exception as e:
        if "logger" in globals():
            logger.error(f"Firebase 로드 실패: {e}")
        else:
            print(f"Firebase 로드 실패: {e}")
        # Note: 'firebase_admin' might be missing until redeploy finishes
        if "firebase_admin" in str(e):
             st.warning("Firebase 모듈을 설치 중입니다. 잠시 후 새로고침 해주세요.")

    # 2. Rename and Normalize Columns
    rename_map = {
        "name": "상호명", "email": "이메일", "address": "주소", "phone": "번호", 
        "talktalk": "톡톡링크", "instagram": "인스타", "source_link": "플레이스링크",
        "blog_id": "블로그ID", "owner_name": "대표자", "talk_url": "톡톡링크", 
        "instagram_handle": "인스타", "naver_blog_id": "블로그ID"
    }
    f_df = f_df.rename(columns=rename_map)
    
    # Ensure mandatory columns exist even if empty
    for col in mandatory_cols:
        if col not in f_df.columns:
            f_df[col] = ""

    if f_df.empty: 
        return f_df

    # 3. Deduplicate and Format
    combined = f_df.drop_duplicates(subset=['상호명', '플레이스링크'], keep='last')
    
    def n_i(v):
        if not v or v == "None": return ""
        v = str(v)
        if v.startswith("http") or v.startswith("https"): return v
        return f"https://www.instagram.com/{v.replace('@', '').strip()}/"
    
    if '인스타' in combined.columns: 
        combined['인스타'] = combined['인스타'].apply(n_i)
    
    return combined

def delete_shop(shop_id, place_link=None):
    # Firebase Delete
    success = False
    try:
        from crawler.db_handler import DBHandler
        db = DBHandler()
        if db.db_fs:
            # 1. Delete by doc ID directly
            if shop_id:
                doc_ref = db.db_fs.collection(config.FIREBASE_COLLECTION).document(shop_id)
                doc_ref.delete()
            
            # 2. Identifier-based mass deletion (Handle duplicates)
            if place_link:
                # Query docs with same place link
                # In Firestore, it could be 'source_link' or '플레이스링크'
                for field in ["source_link", "플레이스링크"]:
                    docs = db.db_fs.collection(config.FIREBASE_COLLECTION).where(field, "==", place_link).stream()
                    for doc in docs:
                        doc.reference.delete()
                
            success = True
        else:
            st.error("데이터베이스 연결에 실패했습니다. (DBHandler.db_fs is None)")
    except Exception as e:
        st.error(f"삭제 작업 중 오류 발생: {e}")
    
    if success:
        st.toast("데이터가 성공적으로 삭제되었습니다.")
        st.cache_data.clear()
        st.session_state['last_selected_shop'] = None
        time.sleep(0.5)
        st.rerun()

df = load_data()

# --- Helper: Page Header with Ref Button ---
def render_page_header(title, key):
    st.markdown(f"#### {title}")

# --- Helper: Render Filter Bar (Full Width) ---
def render_filters_v14(df_input, key):
    if df_input.empty:
        st.info("표시할 데이터가 없습니다.")
        return df_input

    # Ensure required columns for filtering exist
    for col in ['주소', '상호명']:
        if col not in df_input.columns:
            df_input[col] = ""

    with st.container(border=False):
        c1, c2, c3 = st.columns([1, 1, 2.5])
        with c1:
            df_input['시/도'] = df_input['주소'].apply(lambda x: x.split()[0] if isinstance(x, str) and x.split() else "")
            sel_city = st.selectbox("지역 (시/도)", ["전체"] + sorted(list(df_input['시/도'].unique())), key=f"{key}_city_v14")
        with c2:
            d_list = ["전체"]
            if sel_city != "전체":
                d_list = ["전체"] + sorted(list(df_input[df_input['시/도'] == sel_city]['주소'].apply(lambda x: x.split()[1] if len(x.split()) > 1 else "").unique()))
            sel_dist = st.selectbox("지역 (군/구)", d_list, key=f"{key}_dist_v14")
        with c3:
            s_q = st.text_input("업체명 검색", key=f"{key}_q_v14", placeholder="업체명을 입력하세요...")
            
    filtered = df_input.copy()
    if sel_city != "전체": filtered = filtered[filtered['시/도'] == sel_city]
    if sel_dist != "전체": filtered = filtered[filtered['주소'].str.contains(sel_dist, na=False)]
    if s_q: filtered = filtered[filtered['상호명'].str.contains(s_q, case=False, na=False)]
    return filtered

# --- Helper: Personalize Message ---
def format_tpl(text, shop_name):
    if not text: return ""
    return text.replace("{상호명}", shop_name if shop_name else "원장님")

# --- Helper: Copy Only (JS) ---
def copy_to_clipboard(text):
    js = f"""
    <script>
    navigator.clipboard.writeText(`{text}`).then(() => {{
        parent.postMessage({{type: 'streamlit:toast', message: '메시지가 복사되었습니다!'}}, '*');
    }});
    </script>
    """
    st.components.v1.html(js, height=0)

# --- Helper: Render Marketing Track ---
def render_track(track_id, label, icon, column_filter, config_expander_name, df):
    # CENTERED LAYOUT (Constrained Width for Premium Feel)
    _, main_col, _ = st.columns([0.15, 0.7, 0.15])
    
    with main_col:
        st.markdown(f"#### {icon} {label}")
        with st.expander(f"❖ {config_expander_name}"):
            sc1, sc2 = st.columns(2)
            if track_id == 'A':
                st.session_state['gmail_user'] = sc1.text_input("Gmail 계정", value=st.session_state.get('gmail_user', ''), placeholder="example@gmail.com")
                st.session_state['gmail_app_pw'] = sc2.text_input("앱 비밀번호", type="password", value=st.session_state.get('gmail_app_pw', ''), placeholder="16자리 앱 비밀번호")
            elif track_id == 'B':
                st.session_state['naver_user'] = sc1.text_input("Naver ID", value=st.session_state.get('naver_user', ''))
                st.session_state['naver_pw'] = sc2.text_input("PW", type="password", value=st.session_state.get('naver_pw', ''))
            else:
                st.session_state['insta_user'] = sc1.text_input("Instagram ID", value=st.session_state.get('insta_user', ''))
                st.session_state['insta_pw'] = sc2.text_input("PW", type="password", value=st.session_state.get('insta_pw', ''))
            
            if st.button(f"💾 {label} 계정 정보 저장", key=f"save_creds_{track_id}", use_container_width=True):
                save_templates()

        p_df = render_filters_v14(df, f"track{track_id}")
        t_df = p_df[p_df[column_filter].notna() & (p_df[column_filter] != "")].copy()
        
        if not t_df.empty:
            # Templates
            with st.expander("✧ 메시지 템플릿 설정", expanded=True):
                if track_id == 'A':
                    st.session_state['tpl_A']['subject'] = st.text_input("메일 제목", value=st.session_state['tpl_A']['subject'])
                    st.session_state['tpl_A']['body'] = st.text_area("메일본문 ({상호명} 사용 가능)", value=st.session_state['tpl_A']['body'], height=300)
                    
                    # File Uploader for Attachments
                    st.session_state['mail_attachments'] = st.file_uploader("📥 첨부 이미지/파일 선택 (다중 선택 가능)", accept_multiple_files=True, key="mail_att_uploader")
                    
                    if st.button("💾 이메일 템플릿 저장", key="save_tpl_A", use_container_width=True):
                        save_templates()
                else:
                    st.session_state[f'tpl_{track_id}'] = st.text_area(f"{label} 메시지 ({{상호명}} 사용 가능)", value=st.session_state.get(f'tpl_{track_id}', ""), height=300)
                    
                    if track_id == 'C':
                        st.session_state['insta_image'] = st.file_uploader("🖼 이미지 첨부 (DM 발송 시 함께 전송)", type=["jpg", "jpeg", "png"], key="insta_img_uploader")
                    
                    if st.button(f"💾 {label} 템플릿 저장", key=f"save_tpl_{track_id}", use_container_width=True):
                        save_templates()

            if track_id != 'B': # Track A & C: Table Process
                a_c1, a_c2, a_c3, a_c4 = st.columns([0.6, 0.6, 2, 1.2], vertical_alignment="bottom")
                with a_c1:
                    if st.button("전체 선택", key=f"sa_{track_id}", use_container_width=True):
                        for idx in t_df.index: st.session_state[f'sel_track_{track_id}'][idx] = True
                        st.rerun()
                with a_c2:
                    if st.button("전체 해제", key=f"da_{track_id}", use_container_width=True):
                        st.session_state[f'sel_track_{track_id}'] = {}
                        st.rerun()
                with a_c4:
                    if st.button(f"{icon} {label} 가동", type="primary", key=f"run_{track_id}", use_container_width=True):
                        st.session_state[f'exec_{track_id}'] = True

                t_df['선택'] = [st.session_state[f'sel_track_{track_id}'].get(i, False) for i in t_df.index]
                editor_cols = ['선택', '상호명', column_filter, '주소']
                edited_df = st.data_editor(t_df[editor_cols].reset_index(drop=True), use_container_width=True, hide_index=True, key=f"editor_{track_id}")
                for i, row in edited_df.iterrows():
                    orig_idx = t_df.index[i]
                    st.session_state[f'sel_track_{track_id}'][orig_idx] = row['선택']
                
                selected_shops = t_df[t_df['선택'] == True]

                if st.session_state.get(f'exec_{track_id}'):
                    st.session_state[f'exec_{track_id}'] = False
                    if selected_shops.empty: st.warning("선택된 샵이 없습니다.")
                    else:
                        if track_id == 'A':
                            u, p = st.session_state.get('gmail_user'), st.session_state.get('gmail_app_pw')
                            if not u or not p: st.error("계정 정보를 입력해주세요.")
                            else:
                                success_count, progress = 0, st.progress(0)
                                # Prepare attachments
                                current_attachments = []
                                if st.session_state.get('mail_attachments'):
                                    for uploaded_file in st.session_state['mail_attachments']:
                                        current_attachments.append({
                                            "name": uploaded_file.name,
                                            "content": uploaded_file.getvalue()
                                        })

                                for idx, (_, s) in enumerate(selected_shops.iterrows()):
                                    subj = st.session_state['tpl_A']['subject']
                                    body = format_tpl(st.session_state['tpl_A']['body'], s['상호명'])
                                    ok, _ = send_gmail(u, p, s['이메일'], subj, body, attachments=current_attachments)
                                    if ok: success_count += 1
                                    progress.progress((idx + 1) / len(selected_shops))
                                st.success(f"{success_count}곳 발송 성공")
                        elif track_id == 'C':
                            u, p = st.session_state.get('insta_user'), st.session_state.get('insta_pw')
                            if not u or not p: st.error("계정 정보를 입력해주세요.")
                            else:
                                img_path = "NONE"
                                if st.session_state.get('insta_image'):
                                    import tempfile
                                    # Save to a temporary file that persists long enough for the subprocess
                                    t_ext = os.path.splitext(st.session_state['insta_image'].name)[1]
                                    temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=t_ext)
                                    temp_img.write(st.session_state['insta_image'].getvalue())
                                    temp_img.close()
                                    img_path = temp_img.name
                                
                                targets = [{"상호명": s['상호명'], "인스타": s['인스타']} for _, s in selected_shops.iterrows()]
                                script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'messenger', 'safe_messenger.py'))
                                subprocess.Popen([sys.executable, script_path, json.dumps(targets), st.session_state['tpl_C'], "insta", "NONE", f"{u}:{p}", img_path], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                                st.success(f"엔진 가동됨 (이미지: {'유' if img_path != 'NONE' else '무'})")

            else: # Track B: 3-Column Grid View
                st.write("---")
                cols = st.columns(3)
                for i, (_, s) in enumerate(t_df.iterrows()):
                    with cols[i % 3]:
                        st.markdown(f"""
                        <div class="compact-card">
                            <p style="margin:0; font-weight:700; color:var(--text-main);">{s['상호명']}</p>
                            <p style="margin:4px 0 12px 0; font-size:0.75rem; color:var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">📍 {s['주소']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        cc1, cc2 = st.columns(2)
                        p_msg = format_tpl(st.session_state['tpl_B'], s['상호명'])
                        if cc1.button("복사", key=f"copy_b_{s['ID']}", use_container_width=True):
                            copy_to_clipboard(p_msg)
                        cc2.link_button("톡톡 열기", s['톡톡링크'], use_container_width=True, type="primary")
                        st.write("") # Spacer
        else:
            st.info(f"{column_filter} 데이터 없음.")

# ---------------------------------------------------------
# 3. View Router
# ---------------------------------------------------------
page = st.session_state['active_page']

if page == 'Shop Search':
    st.markdown("#### ⬖ 검색 및 분석")
    f_df = render_filters_v14(df, "search_final")
    
    m_col, d_col = st.columns([1.6, 1]) if st.session_state['last_selected_shop'] is not None else (st.container(), None)

    # Initialize session state for multi-selection tracking
    if 'prev_rows' not in st.session_state:
        st.session_state['prev_rows'] = []

    with m_col:
        h_col1, h_col2, h_col3 = st.columns([1.1, 2.2, 2.8], vertical_alignment="center")
        h_col1.markdown('<p style="font-size:0.85rem; color:#64748b; margin:0;">✦ 수집 데이터 리스트</p>', unsafe_allow_html=True)
        if st.session_state['last_selected_shop'] is not None:
            with h_col2:
                c_del, c_res = st.columns([0.8, 1.4])
                with c_del:
                    st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                    if st.button("✕ 삭제", key="btn_del_shop"):
                        shop_to_del = st.session_state['last_selected_shop']
                        delete_shop(shop_to_del['ID'], place_link=shop_to_del.get('플레이스링크'))
                    st.markdown('</div>', unsafe_allow_html=True)
                with c_res:
                    st.markdown('<div class="research-btn">', unsafe_allow_html=True)
                    if st.button("✦ 데이터 재검색", key="btn_res_shop"):
                        shop_id = st.session_state['last_selected_shop']['ID']
                        with st.spinner(f"'{st.session_state['last_selected_shop']['상호명']}' 데이터 재검색 및 자동 업데이트 중..."):
                            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'research_single_shop.py'))
                            try:
                                # Run synchronously to wait for completion
                                subprocess.run([sys.executable, script_path, str(shop_id)], check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"재검색 실패: {e}")
                    st.markdown('</div>', unsafe_allow_html=True)

        selection = st.dataframe(
            f_df[['상호명', '주소', '번호', '이메일', '인스타', '톡톡링크']].reset_index(drop=True),
            use_container_width=True, hide_index=True, selection_mode="multi-row", on_select="rerun", height=600
        )
        s_rows = selection.get("selection", {}).get("rows", [])
        
        # Logic to find the most recently selected row
        if s_rows:
            # If a new row was added to the selection, focus on it
            newly_added = [r for r in s_rows if r not in st.session_state['prev_rows']]
            if newly_added:
                st.session_state['last_selected_shop'] = f_df.iloc[newly_added[-1]]
            elif st.session_state['last_selected_shop'] is not None:
                # If nothing new added but current focused shop is still in selection, keep it
                # Otherwise, if focused shop was removed, pick the last row from current selection
                current_id = st.session_state['last_selected_shop']['ID']
                if not any(f_df.iloc[r]['ID'] == current_id for r in s_rows):
                    st.session_state['last_selected_shop'] = f_df.iloc[s_rows[-1]]
            
            st.session_state['prev_rows'] = s_rows
            if d_col is None: st.rerun()
        else:
            st.session_state['prev_rows'] = []
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
                except: st.caption("분석 중...")
            else: st.info("경쟁 업체 없음.")

elif page == 'Track A': render_track('A', 'TRACK A: 이메일 마케팅', '✉', '이메일', '계정 설정', df)
elif page == 'Track B': render_track('B', 'TRACK B: 네이버 톡톡 자동화', '🗨', '톡톡링크', '네이버 로그인', df)
elif page == 'Track C': render_track('C', 'TRACK C: 인스타그램 Auto-DM', '◈', '인스타', '인스타그램 로그인', df)

# (Crawler UI Removed from footer)
