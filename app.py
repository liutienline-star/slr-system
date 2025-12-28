import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import plotly.express as px

# --- 1. 核心參數 ---
AUTH_CODE = "641101"  
HUB_NAME = "Student_Learning_Hub" 
SHEET_TAB = "Learning_Data" 
MODEL_NAME = "models/gemini-2.0-flash" 

st.set_page_config(page_title="學思戰情系統 v1.3", layout="wide", page_icon="📊")

# --- 2. 視覺風格 ---
st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e5e9f0; }
    .main-header { text-align: center; color: #88c0d0; font-weight: 800; font-size: 2.2rem; margin-bottom: 1rem; }
    .stButton>button { background-color: #3b4252 !important; color: #ffffff !important; border: 1px solid #88c0d0 !important; width: 100%; border-radius: 8px; font-weight: 700; }
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
    except: return None, None

# --- 4. 驗證機制 ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    _, col_m, _ = st.columns([1, 1.2, 1])
    with col_m:
        st.markdown("<div style='text-align:center; margin-top:100px;'><h2>📈 導師戰情系統登入</h2></div>", unsafe_allow_html=True)
        pwd = st.text_input("輸入授權碼：", type="password")
        if st.button("啟動系統"):
            if pwd == AUTH_CODE:
                st.session_state.authenticated = True; st.rerun()
    st.stop()

# --- 5. 主介面 ---
st.markdown('<h1 class="main-header">🏫 「學思戰情」智慧學習資源系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view, tab_analysis = st.tabs(["📝 數據錄入", "🔍 歷史數據", "📊 戰情分析室"])

# --- Tab 1: 數據錄入 (新增考試範圍) ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        with c2: subject = st.selectbox("📚 學科", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        
        c3, c4 = st.columns(2)
        with c3: exam_range = st.text_input("🎯 考試範圍", placeholder="例：L1-L3 或 第一次月考")
        with c4: score = st.number_input("💯 分數", 0, 100, 60)
        
        obs = st.text_area("🔍 觀察摘要", placeholder="輸入觀察內容...", height=100)
        
        if st.button("🚀 啟動 AI 診斷並同步至 HUB"):
            if stu_id and obs and exam_range:
                with st.spinner("AI 分析數據中..."):
                    # 強化 AI 指令：加入考試範圍
                    prompt = f"""你是一位專業導師。請根據數據提供100字內診斷與策略：
                    學生：{stu_id} | 學科：{subject} | 範圍：{exam_range} | 分數：{score}
                    觀察：{obs}
                    請針對此考試範圍的表現給予具體建議。"""
                    
                    try:
                        diagnosis = ai_engine.generate_content(prompt).text
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                        # 依照試算表新順序存入
                        hub_sheet.append_row([timestamp, stu_id, subject, exam_range, score, obs, diagnosis])
                        st.success("✅ 數據已成功存入 HUB！")
                        st.info(f"**AI 建議：**\n\n{diagnosis}")
                    except Exception as e: st.error(f"連線異常: {e}")
            else: st.warning("請完整填寫代號、範圍與觀察。")
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
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df = pd.DataFrame(raw_data)
            df['小考成績'] = pd.to_numeric(df['小考成績'], errors='coerce').fillna(0)
            c_radar, c_trend = st.columns(2)
            
            with c_radar:
                st.subheader("🕸️ 全班學習力雷達")
                avg_scores = df.groupby('學科類別')['小考成績'].mean().reset_index()
                fig_radar = px.line_polar(avg_scores, r='小考成績', theta='學科類別', line_close=True, range_r=[0,100])
                fig_radar.update_traces(fill='toself', line_color='#88c0d0')
                fig_radar.update_layout(template="plotly_dark")
                st.plotly_chart(fig_radar, use_container_width=True)
            
            with c_trend:
                st.subheader("📈 個人進步趨勢")
                stu_list = df['學生代號'].unique()
                sel_stu = st.selectbox("選擇學生：", stu_list)
                stu_df = df[df['學生代號'] == sel_stu].sort_values('日期時間')
                # 趨勢圖加入 hover 顯示考試範圍
                fig_line = px.line(stu_df, x='日期時間', y='小考成績', color='學科類別', markers=True, 
                                   hover_data=['考試範圍'])
                fig_line.update_layout(template="plotly_dark", yaxis_range=[0,105])
                st.plotly_chart(fig_line, use_container_width=True)
