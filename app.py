import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd

# --- 1. 核心參數設定 ---
AUTH_CODE = "641101"  
HUB_NAME = "Student_Learning_Hub" 
SHEET_TAB = "Learning_Data" 
MODEL_NAME = "models/gemini-2.0-flash" 

st.set_page_config(page_title="學思戰情系統", layout="wide", page_icon="📈")

# --- 2. 視覺風格 (校長專屬：深色專業風) ---
st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e5e9f0; }
    .main-header { text-align: center; color: #88c0d0; font-weight: 800; font-size: 2.2rem; margin-bottom: 1rem; }
    .stButton>button { background-color: #3b4252 !important; color: #ffffff !important; border: 1px solid #88c0d0 !important; width: 100%; height: 45px; font-weight: 700; border-radius: 8px; }
    .input-card { background-color: #2e3440; padding: 25px; border-radius: 15px; border: 1px solid #4c566a; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    [data-testid="stWidgetLabel"] p { color: #88c0d0 !important; font-size: 1.05rem; font-weight: 600; }
    .status-msg { padding: 10px; border-radius: 5px; background-color: #3b4252; border-left: 5px solid #88c0d0; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 核心初始化服務 ---
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
        return None, None, f"❌ 連線異常：{str(e)}"

# --- 4. AI 診斷引擎 ---
def generate_ai_diagnosis(model, student_id, subject, score, observation):
    prompt = f"""
    你是一位專業的國中導師。請根據以下數據提供精簡的診斷與策略（100字內）：
    - 學生代號：{student_id} | 學科：{subject} | 成績：{score}
    - 觀察：{observation}
    請包含：1.學習現況診斷 2.具體輔導建議。
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "AI 診斷暫時不可用，請稍後再試。"

# --- 5. 身份驗證機制 ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    _, col_m, _ = st.columns([1, 1.2, 1])
    with col_m:
        st.markdown("<div style='text-align:center; margin-top:100px;'><h1>📊</h1><h2 style='color:#88c0d0;'>學思戰情系統</h2></div>", unsafe_allow_html=True)
        pwd = st.text_input("輸入授權碼：", type="password")
        if st.button("啟動系統"):
            if pwd == AUTH_CODE:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("授權碼錯誤")
    st.stop()

# --- 6. 主介面配置 ---
st.markdown('<h1 class="main-header">🏫 「學思戰情」智慧學習資源系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet, status_msg = init_services()

# 側邊欄：穩定度檢查儀
with st.sidebar:
    st.title("⚙️ 系統設定")
    st.markdown(f'<div class="status-msg">{status_msg}</div>', unsafe_allow_html=True)
    
    st.divider()
    st.markdown("### 🧪 穩定度測試")
    if st.button("🔌 測試連線"):
        with st.spinner("測試中..."):
            try:
                res = ai_engine.generate_content("Ping")
                st.success("AI 連動正常")
                rows = hub_sheet.get_all_values()
                st.success(f"HUB 讀取正常 (共 {len(rows)} 筆)")
                st.balloons()
            except Exception as e:
                st.error(f"連線異常: {e}")

# 主介面分頁
tab_entry, tab_view = st.tabs(["📝 數據錄入與診斷", "🔍 HUB 歷史數據"])

# --- 分頁一：錄入與 AI 診斷 ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1: stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        with c2: subject = st.selectbox("📚 學科", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        with c3: score = st.number_input("💯 小考成績", 0, 100, 60)
        
        obs = st.text_area("🔍 導師觀察摘要", placeholder="在此輸入或貼上語音轉錄的觀察內容...", height=120)
        
        if st.button("🚀 啟動 AI 診斷並同步至 HUB"):
            if stu_id and obs:
                with st.spinner("AI 分析中..."):
                    diagnosis = generate_ai_diagnosis(ai_engine, stu_id, subject, score, obs)
                with st.spinner("存入 HUB..."):
                    try:
                        timestamp = datetime.now().strftime("%m/%d %H:%M")
                        hub_sheet.append_row([timestamp, stu_id, subject, score, obs, diagnosis])
                        st.success("✅ 數據已成功存檔！")
                        st.info(f"**AI 建議：**\n\n{diagnosis}")
                    except Exception as e:
                        st.error(f"存檔失敗：{e}")
            else:
                st.warning("請完整填寫學生代號與觀察內容。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 分頁二：歷史數據查閱 ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 刷新數據"): st.rerun()
        try:
            df = pd.DataFrame(hub_sheet.get_all_records())
            if not df.empty:
                st.dataframe(df.sort_values(by="日期時間", ascending=False), use_container_width=True)
            else:
                st.info("目前 HUB 內無數據。")
        except:
            st.warning("請檢查試算表標題列是否正確。")
