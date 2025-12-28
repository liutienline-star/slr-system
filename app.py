import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. 核心參數設定 ---
AUTH_CODE = "641101"  
HUB_NAME = "Student_Learning_Hub" 
SHEET_TAB = "Learning_Data" 
MODEL_NAME = "models/gemini-2.0-flash" 

st.set_page_config(page_title="學思戰情系統 v1.2", layout="wide", page_icon="📊")

# --- 2. 視覺風格 (校長專屬：深色專業風) ---
st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e5e9f0; }
    .main-header { text-align: center; color: #88c0d0; font-weight: 800; font-size: 2.2rem; margin-bottom: 1rem; }
    .stButton>button { background-color: #3b4252 !important; color: #ffffff !important; border: 1px solid #88c0d0 !important; width: 100%; border-radius: 8px; }
    .input-card { background-color: #2e3440; padding: 20px; border-radius: 12px; border: 1px solid #4c566a; margin-bottom: 20px; }
    [data-testid="stWidgetLabel"] p { color: #88c0d0 !important; font-weight: 600; }
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
    except Exception as e:
        return None, None

# --- 4. AI 診斷引擎 ---
def generate_ai_diagnosis(model, student_id, subject, score, observation):
    prompt = f"你是一位國中導師，請針對學生{student_id}在{subject}拿{score}分及觀察『{observation}』提供100字內診斷與輔導建議。"
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "AI 診斷暫時離線。"

# --- 5. 身份驗證 ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    _, col_m, _ = st.columns([1, 1.2, 1])
    with col_m:
        st.markdown("<div style='text-align:center; margin-top:100px;'><h2>📈 導師戰情系統登入</h2></div>", unsafe_allow_html=True)
        if st.text_input("授權碼：", type="password") == AUTH_CODE:
            st.session_state.authenticated = True; st.rerun()
    st.stop()

# --- 6. 主介面規劃 ---
st.markdown('<h1 class="main-header">🏫 「學思戰情」智慧學習資源系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view, tab_analysis = st.tabs(["📝 數據錄入", "🔍 歷史數據", "📊 戰情分析室"])

# --- Tab 1: 數據錄入 ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        with c2: subject = st.selectbox("📚 學科", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        with c3: score = st.number_input("💯 分數", 0, 100, 60)
        obs = st.text_area("🔍 觀察摘要", placeholder="請輸入觀察內容...", height=100)
        
        if st.button("🚀 啟動 AI 診斷並存檔"):
            if stu_id and obs:
                with st.spinner("AI 分析中..."):
                    diagnosis = generate_ai_diagnosis(ai_engine, stu_id, subject, score, obs)
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                    hub_sheet.append_row([timestamp, stu_id, subject, score, obs, diagnosis])
                    st.success(f"✅ {stu_id} 數據已存檔！")
                    st.info(f"**AI 診斷：** {diagnosis}")
            else: st.warning("請填寫代號與觀察。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2: 歷史數據 ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 刷新 HUB"): st.rerun()
        df = pd.DataFrame(hub_sheet.get_all_records())
        if not df.empty:
            st.dataframe(df.sort_values(by="日期時間", ascending=False), use_container_width=True)
        else: st.info("尚無數據。")

# --- Tab 3: 戰情分析室 ---
with tab_analysis:
    if hub_sheet:
        raw_df = pd.DataFrame(hub_sheet.get_all_records())
        if not raw_df.empty:
            raw_df['小考成績'] = pd.to_numeric(raw_df['小考成績'], errors='coerce')
            
            col_radar, col_trend = st.columns(2)
            
            # A. 全班雷達圖
            with col_radar:
                st.subheader("🕸️ 全班學習力雷達")
                avg_df = raw_df.groupby('學科類別')['小考成績'].mean().reset_index()
                fig_radar = px.line_polar(avg_df, r='小考成績', theta='學科類別', line_close=True, range_r=[0,100])
                fig_radar.update_traces(fill='toself', line_color='#88c0d0')
                fig_radar.update_layout(template="plotly_dark")
                st.plotly_chart(fig_radar, use_container_width=True)
            
            # B. 個人趨勢圖
            with col_trend:
                st.subheader("📈 個人進步趨勢")
                selected_stu = st.selectbox("查看學生：", raw_df['學生代號'].unique())
                stu_df = raw_df[raw_df['學生代號'] == selected_stu]
                fig_line = px.line(stu_df, x='日期時間', y='小考成績', color='學科類別', markers=True)
                fig_line.update_layout(template="plotly_dark", yaxis_range=[0,105])
                st.plotly_chart(fig_line, use_container_width=True)
