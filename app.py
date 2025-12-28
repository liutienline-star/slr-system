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

st.set_page_config(page_title="學思戰情系統", layout="wide", page_icon="📈")

# --- 2. 視覺風格 ---
st.markdown("""
<style>
    .stApp { background-color: #1a1c23; color: #e5e9f0; }
    .main-header { text-align: center; color: #88c0d0; font-weight: 800; font-size: 2.2rem; margin-bottom: 1rem; }
    .stButton>button { background-color: #3b4252 !important; color: #ffffff !important; border: 1px solid #88c0d0 !important; width: 100%; border-radius: 8px; font-weight: 700; height: 45px; }
    .input-card { background-color: #2e3440; padding: 20px; border-radius: 12px; border: 1px solid #4c566a; margin-bottom: 20px; }
    .suggestion-card { background-color: #2e3440; padding: 25px; border-radius: 15px; border-left: 8px solid #88c0d0; margin-bottom: 25px; box-shadow: 4px 4px 15px rgba(0,0,0,0.5); }
    [data-testid="stWidgetLabel"] p { color: #88c0d0 !important; font-weight: 600; font-size: 1.1rem; }
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
        st.markdown("<h2 style='text-align:center; color:#88c0d0;'>導師戰情系統登入</h2>", unsafe_allow_html=True)
        if st.text_input("輸入授權碼：", type="password") == AUTH_CODE:
            st.session_state.authenticated = True; st.rerun()
    st.stop()

st.markdown('<h1 class="main-header">🏫 「學思戰情」智慧學習資源系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view, tab_analysis = st.tabs(["📝 數據錄入", "🔍 歷史數據", "📊 戰情分析室"])

# --- Tab 1: 數據錄入 (強化考試範圍建議) ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        subject = st.selectbox("📚 學科", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        exam_range = st.text_input("🎯 考試範圍", placeholder="例：月考一、L1-L3 或 特定單元名稱")
        score = st.number_input("💯 分數", 0, 100, 60)
        obs = st.text_area("🔍 觀察摘要", placeholder="請描述學生目前的學習困難或錯誤類型...", height=100)
        
        if st.button("🚀 啟動 AI 家教深度診斷"):
            if stu_id and obs and exam_range:
                with st.spinner("AI 專屬家教正在分析考試範圍內容..."):
                    # 強化 AI Prompt，使其針對「考試範圍」給出具體建議
                    prompt = f"""你是一位專業的私人家教，擅長針對考試範圍精準補強。
                    請針對學生{stu_id}在【{subject}】科目的【{exam_range}】範圍表現給予具體診斷。
                    分數：{score}分。觀察：{obs}。
                    請包含：1. 該範圍的核心知識點診斷 2. 針對此範圍的具體複習策略 3. 推薦的學習技術。
                    (請控制在150字內，內容要精準具體)"""
                    try:
                        diagnosis = ai_engine.generate_content(prompt).text
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                        hub_sheet.append_row([timestamp, stu_id, subject, exam_range, score, obs, diagnosis])
                        st.success("✅ 深度診斷完成！")
                        st.info(f"**AI 家教建議：**\n\n{diagnosis}")
                    except Exception as e: st.error(f"存檔連線異常：{e}")
            else: st.warning("請填寫所有欄位。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2: 歷史數據 ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 刷新數據"): st.rerun()
        df = pd.DataFrame(hub_sheet.get_all_records())
        st.dataframe(df.sort_values(by="日期時間", ascending=False), use_container_width=True)

# --- Tab 3: 戰情分析室 (垂直垂直佈局) ---
with tab_analysis:
    if hub_sheet:
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df = pd.DataFrame(raw_data)
            df['小考成績'] = pd.to_numeric(df['小考成績'], errors='coerce').fillna(0)
            
            # A. 全班雷達圖
            st.subheader("🕸️ 全班學習力平均分布")
            avg_scores = df.groupby('學科類別')['小考成績'].mean().reset_index()
            fig_radar = px.line_polar(avg_scores, r='小考成績', theta='學科類別', line_close=True, range_r=[0,100])
            fig_radar.update_traces(fill='toself', line_color='#88c0d0')
            fig_radar.update_layout(template="plotly_dark")
            st.plotly_chart(fig_radar, use_container_width=True)
            
            st.divider()

            # B. 個人進步趨勢
            st.subheader("👤 個人學習趨勢追蹤")
            stu_list = df['學生代號'].unique()
            sel_stu = st.selectbox("切換學生代號：", stu_list)
            
            stu_df = df[df['學生代號'] == sel_stu].sort_values('日期時間')
            fig_line = px.line(stu_df, x='日期時間', y='小考成績', color='學科類別', markers=True, hover_data=['考試範圍'])
            fig_line.update_layout(template="plotly_dark", yaxis_range=[0,105])
            st.plotly_chart(fig_line, use_container_width=True)
            
            st.divider()

            # C. 個人學習建議單 (解決 </div> 殘留問題)
            st.subheader(f"📝 學生 {sel_stu} 各學科個人化建議單")
            latest_diag = stu_df.groupby('學科類別').tail(1)
            
            for index, row in latest_diag.iterrows():
                # 確保變數內容中的換行被正確轉譯
                clean_diagnosis = row['AI診斷與建議'].replace('\n', '<br>')
                
                # 使用無縮排字串防止 Markdown 錯誤解析
                card_html = f'<div class="suggestion-card"><h3 style="color:#88c0d0; margin-bottom:5px;">📚 {row["學科類別"]}</h3><p style="margin:0; color:#aeb3bb;"><b>測驗範圍：</b>{row["考試範圍"]} | <b>最新成績：</b>{row["小考成績"]} 分</p><hr style="border: 0.5px solid #4c566a; margin: 15px 0;"><div style="font-size:1.1rem; line-height:1.6; color:#e5e9f0;">{clean_diagnosis}</div></div>'
                
                st.markdown(card_html, unsafe_allow_html=True)
        else:
            st.info("💡 目前尚無數據紀錄。")
