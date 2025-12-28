import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd

# --- 1. 核心參數 (維持不變) ---
AUTH_CODE = "641101"  
HUB_NAME = "Student_Learning_Hub" 
SHEET_TAB = "Learning_Data" 
MODEL_NAME = "models/gemini-2.0-flash" 

st.set_page_config(page_title="學思戰情系統", layout="wide", page_icon="📈")

# --- 2. 視覺風格 (維持校長專業深色風) ---
st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e5e9f0; }
    .main-header { text-align: center; color: #88c0d0; font-weight: 800; font-size: 2.2rem; margin-bottom: 1rem; }
    .stButton>button { background-color: #3b4252 !important; color: #ffffff !important; border: 1px solid #88c0d0 !important; width: 100%; height: 50px; font-weight: 700; }
    .input-card { background-color: #2e3440; padding: 25px; border-radius: 15px; border: 1px solid #4c566a; margin-bottom: 20px; }
    [data-testid="stWidgetLabel"] p { color: #88c0d0 !important; font-size: 1.1rem; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 初始化服務 ---
@st.cache_resource
def init_services():
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        model = genai.GenerativeModel(MODEL_NAME)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        sheet = gspread.authorize(creds).open(HUB_NAME).worksheet(SHEET_TAB)
        return model, sheet
    except: return None, None

# --- 4. 驗證機制 (維持不變) ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    _, col_m, _ = st.columns([1, 1.2, 1])
    with col_m:
        st.markdown("<div style='text-align:center;'><h1>📈</h1><h2 style='color:#88c0d0;'>導師戰情系統</h2></div>", unsafe_allow_html=True)
        if st.text_input("授權碼：", type="password") == AUTH_CODE:
            st.session_state.authenticated = True; st.rerun()
    st.stop()

# --- 5. 主介面：分頁規劃 ---
st.markdown('<h1 class="main-header">🏫 「學思戰情」智慧學習資源系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view = st.tabs(["📝 數據與觀察錄入", "🔍 HUB 數據查閱"])

# --- 分頁一：錄入介面 ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        with c2:
            subject = st.selectbox("📚 學科", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        with c3:
            score = st.number_input("💯 小考成績", 0, 100, 60)
        
        obs = st.text_area("🔍 導師觀察摘要 (語音輸入轉貼處)", placeholder="輸入學生的學習狀況、心理狀態或課堂表現...", height=120)
        
        if st.button("🚀 同步至系統 HUB"):
            if stu_id and obs:
                with st.spinner("正在存入 Google 雲端數據庫..."):
                    try:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        # 這裡預留一格給未來的 AI 診斷
                        new_row = [timestamp, stu_id, subject, score, obs, "等待診斷..."]
                        hub_sheet.append_row(new_row)
                        st.success(f"✅ {stu_id} 的數據已成功寫入 HUB！")
                    except Exception as e:
                        st.error(f"存入失敗：{e}")
            else:
                st.warning("請填寫學生代號與觀察摘要。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 分頁二：查看數據 ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 重新整理數據"): st.rerun()
        try:
            data = pd.DataFrame(hub_sheet.get_all_records())
            if not data.empty:
                st.dataframe(data.sort_values(by="日期時間", ascending=False), use_container_width=True)
            else:
                st.info("目前 HUB 內無數據內容。")
        except: st.error("讀取失敗，請確認試算表標題列是否正確。")
