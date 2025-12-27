import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd

# --- 1. 核心設定 ---
AUTH_CODE = "641101"  
HUB_NAME = "Student_Learning_Hub" 
SHEET_TAB = "Learning_Data" 
MODEL_NAME = "models/gemini-2.0-flash" 

st.set_page_config(page_title="學思戰情：智慧學習資源系統", layout="wide", page_icon="📈")

# --- 2. 視覺風格 (校長鎖定：深色專業風) ---
st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e5e9f0; }
    .main-header { text-align: center; color: #88c0d0; font-weight: 800; font-size: 2.2rem; margin-bottom: 2rem; }
    .status-card { background-color: #2e3440; padding: 20px; border-radius: 12px; border: 1px solid #4c566a; }
    [data-testid="stWidgetLabel"] p { color: #88c0d0 !important; font-weight: 600; }
    .stButton>button { background-color: #3b4252 !important; color: #ffffff !important; border: 1px solid #88c0d0 !important; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 初始化服務 ---
@st.cache_resource
def init_services():
    try:
        # A. 初始化 Gemini
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        model = genai.GenerativeModel(MODEL_NAME)
        
        # B. 初始化 Google Sheets HUB
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(HUB_NAME).worksheet(SHEET_TAB)
        
        return model, sheet, "✅ 系統中樞連線正常"
    except Exception as e:
        return None, None, f"❌ 連線失敗：{str(e)}"

# --- 4. 驗證頁面 ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, col_m, _ = st.columns([1, 1.2, 1])
    with col_m:
        st.markdown("<div style='text-align:center;'><h1>📈</h1><h2 style='color:#88c0d0;'>導師戰情系統登入</h2></div>", unsafe_allow_html=True)
        pwd = st.text_input("請輸入授權碼：", type="password")
        if st.button("啟動系統"):
            if pwd == AUTH_CODE:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("授權碼錯誤")
    st.stop()

# --- 5. 主介面內容 ---
st.markdown('<h1 class="main-header">🏫 「學思戰情」智慧學習資源輔助系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet, status_msg = init_services()

st.markdown(f'<div class="status-card"><h3>中樞狀態報告：</h3><p>{status_msg}</p></div>', unsafe_allow_html=True)

if hub_sheet:
    st.success(f"已成功連結 HUB：{HUB_NAME}")
    try:
        data = hub_sheet.get_all_records()
        if data:
            st.write("### 📂 目前 HUB 數據預覽")
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.info("HUB 目前為空，請確認試算表首行標題是否正確。")
    except:
        st.warning("請確認試算表首行已填入標題：日期時間, 學生代號, 學科類別, 小考成績, 導師觀察摘要, AI診斷與建議")
