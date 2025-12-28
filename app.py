import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. 核心參數與連線 (維持不變) ---
AUTH_CODE = "641101"
HUB_NAME = "Student_Learning_Hub"
SHEET_TAB = "Learning_Data"
MODEL_NAME = "models/gemini-2.0-flash"

st.set_page_config(page_title="學思戰情系統 v1.1", layout="wide", page_icon="📈")

# --- 2. 視覺風格 (維持校長專業深色風) ---
st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e5e9f0; }
    .main-header { text-align: center; color: #88c0d0; font-weight: 800; font-size: 2.2rem; margin-bottom: 1rem; }
    .stButton>button { background-color: #3b4252 !important; color: #ffffff !important; border: 1px solid #88c0d0 !important; width: 100%; border-radius: 8px; }
    .input-card { background-color: #2e3440; padding: 25px; border-radius: 15px; border: 1px solid #4c566a; margin-bottom: 20px; }
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
        st.markdown("<h2 style='text-align:center; color:#88c0d0;'>導師戰情系統</h2>", unsafe_allow_html=True)
        if st.text_input("授權碼：", type="password") == AUTH_CODE:
            st.session_state.authenticated = True; st.rerun()
    st.stop()

# --- 5. 主程式邏輯 ---
st.markdown('<h1 class="main-header">🏫 「學思戰情」智慧學習資源系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view, tab_analysis = st.tabs(["📝 數據錄入", "🔍 HUB 數據查閱", "📊 數據分析戰情室"])

# --- 錄入與查閱 (省略細節，維持原本功能) ---
with tab_entry:
    st.info("請在此輸入學生成績與觀察。")
    # (此處保留原有的錄入表單代碼...)

with tab_view:
    if hub_sheet:
        df = pd.DataFrame(hub_sheet.get_all_records())
        st.dataframe(df, use_container_width=True)

# --- 6. 新增：數據分析戰情室 ---
with tab_analysis:
    if hub_sheet:
        all_data = pd.DataFrame(hub_sheet.get_all_records())
        if not all_data.empty:
            # 資料預處理
            all_data['小考成績'] = pd.to_numeric(all_data['小考成績'], errors='coerce')
            
            col_left, col_right = st.columns(2)

            with col_left:
                st.subheader("🕸️ 全班學習力雷達圖")
                # 計算各科平均分
                avg_scores = all_data.groupby('學科類別')['小考成績'].mean().reset_index()
                
                fig_radar = px.line_polar(avg_scores, r='小考成績', theta='學科類別', 
                                         line_close=True, range_r=[0,100],
                                         color_discrete_sequence=['#88c0d0'])
                fig_radar.update_traces(fill='toself')
                fig_radar.update_layout(template="plotly_dark", polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
                st.plotly_chart(fig_radar, use_container_width=True)
                st.caption("此圖反映全班在各學科的平均表現強弱。")

            with col_right:
                st.subheader("📈 個別學生進步趨勢圖")
                student_list = all_data['學生代號'].unique()
                selected_student = st.selectbox("選擇學生代號：", student_list)
                
                student_df = all_data[all_data['學生代號'] == selected_student].sort_values('日期時間')
                
                fig_trend = px.line(student_df, x='日期時間', y='小考成績', color='學科類別',
                                   markers=True, title=f"學生 {selected_student} 成績走勢",
                                   color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_trend.update_layout(template="plotly_dark", yaxis_range=[0,105])
                st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.warning("目前 HUB 尚無足夠數據進行分析。")
