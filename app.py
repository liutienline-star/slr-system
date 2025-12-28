import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import plotly.express as px
from PIL import Image

# --- 1. 核心參數設定 ---
AUTH_CODE = "641101"  
HUB_NAME = "Student_Learning_Hub" 
SHEET_TAB = "Learning_Data" 
MODEL_NAME = "models/gemini-2.0-flash" 

st.set_page_config(page_title="學思戰術指揮系統", layout="wide", page_icon="📈")

# --- 2. 視覺風格 (CSS 控制) ---
st.markdown("""
<style>
    .main .block-container { max-width: 1000px; padding-top: 2rem; }
    .stApp { background-color: #1a1c23; color: #e5e9f0; }
    .main-header { text-align: center; color: #88c0d0; font-weight: 800; font-size: 2.2rem; margin-bottom: 1.5rem; }
    .stButton>button { 
        background-color: #3b4252 !important; color: #ffffff !important; 
        border: 1px solid #88c0d0 !important; width: 100%; border-radius: 10px; font-weight: 700; height: 45px;
    }
    .input-card { background-color: #2e3440; padding: 25px; border-radius: 15px; border: 1px solid #4c566a; margin-bottom: 20px; }
    .subject-header { color: #88c0d0; border-bottom: 2px solid #88c0d0; padding-bottom: 8px; margin-top: 30px; margin-bottom: 15px; font-size: 1.4rem; font-weight: bold; }
    .range-card { background-color: #3b4252; padding: 18px; border-radius: 12px; border-left: 5px solid #81a1c1; margin-bottom: 15px; }
    .special-box { background-color: #2e3440; padding: 30px; border-radius: 15px; border: 1px solid #88c0d0; margin-bottom: 20px; line-height: 1.8; }
    .tactical-advice { background-color: #3e4451; padding: 25px; border-radius: 15px; border: 2px dashed #ebcb8b; color: #ebcb8b; margin-top: 20px; }
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
        st.error(f"系統初始化異常：{e}"); return None, None

# --- 4. 驗證機制 ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    _, col_m, _ = st.columns([0.5, 1, 0.5])
    with col_m:
        st.markdown("<h2 style='text-align:center; color:#88c0d0;'>戰情系統登入</h2>", unsafe_allow_html=True)
        if st.text_input("輸入授權碼：", type="password") == AUTH_CODE:
            st.session_state.authenticated = True; st.rerun()
    st.stop()

# --- 5. 主程式 ---
st.markdown('<h1 class="main-header">🏫 「學思戰情」深度段考診斷系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view, tab_analysis = st.tabs(["📝 影像深度診讀", "🔍 歷史數據庫", "📊 戰術分析室"])

# --- Tab 1: 診斷錄入 (保留詳盡敘述) ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        with col2: subject = st.selectbox("📚 學科類別", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        
        exam_range = st.text_input("🎯 段考範圍", placeholder="例：第一次段考")
        score = st.number_input("💯 測驗成績", 0, 100, 60)
        uploaded_file = st.file_uploader("📷 上傳考卷影像", type=["jpg", "jpeg", "png"])
        
        diag_mode = st.radio("🛠️ 診斷模式", ["⚡ 快速掃描 (含詳盡錯誤描述)", "🧠 深度運算 (含步驟驗證分析)"], horizontal=True)

        if "v_obs" not in st.session_state: st.session_state.v_obs = ""
        
        if uploaded_file and st.button("🔍 執行事實診讀"):
            with st.spinner("AI 事實掃描中..."):
                img = Image.open(uploaded_file)
                if "快速掃描" in diag_mode:
                    prompt = "你是一位教育診斷專家。請產出售錯題號、正確答案、知識點，並【詳述】學生的具體錯誤點與思維漏洞。去美化，嚴禁頁碼。"
                else:
                    prompt = "你是一位數理診斷專家。請驗證學生的計算路徑，【詳盡分析】出錯的具體步驟與邏輯。去美化，嚴禁頁碼。"
                v_res = ai_engine.generate_content([prompt, img])
                st.session_state.v_obs = v_res.text
        
        obs = st.text_area("🔍 錯誤事實紀錄", value=st.session_state.v_obs, height=450)

        if st.button("🚀 同步至戰情庫"):
            if stu_id and obs:
                with st.spinner("歸檔中..."):
                    diag = ai_engine.generate_content(f"基於事實：{obs}。產出具備指導價值的複習建議，去美化，嚴禁頁碼。").text
                    hub_sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), stu_id, subject, exam_range, score, obs, diag])
                    st.success("✅ 數據已歸檔！"); st.session_state.v_obs = ""
            else: st.warning("請填寫必要欄位。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2: 歷史數據庫 ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 刷新紀錄"): st.rerun()
        raw_df = pd.DataFrame(hub_sheet.get_all_records())
        if not raw_df.empty:
            st.dataframe(raw_df.sort_values(by="日期時間", ascending=False), use_container_width=True)

# --- Tab 3: 戰術分析室 (新增考前重點提示) ---
with tab_analysis:
    if hub_sheet:
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df = pd.DataFrame(raw_data)
            df['成績'] = pd.to_numeric(df['測驗成績'], errors='coerce').fillna(0)
            stu_list = df['學生代號'].unique()
            sel_stu = st.selectbox("🎯 選擇學生代號", stu_list)
            stu_df = df[df['學生代號'] == sel_stu].sort_values('日期時間', ascending=False)
            
            if not stu_df.empty:
                # 雷達圖
                avg_scores = stu_df.groupby('學科類別')['成績'].mean().reset_index()
                fig_radar = px.line_polar(avg_scores, r='成績', theta='學科類別', line_close=True, range_r=[0,100])
                fig_radar.update_traces(fill='toself', line_color='#88c0d0')
                st.plotly_chart(fig_radar, use_container_width=True)
                
                st.divider()

                # 科目過濾明細
                sub_list_hist = sorted(list(stu_df['學科類別'].unique()))
                sel_sub_hist = st.selectbox("🔍 選擇科目檢視與生成戰術提示：", sub_list_hist)
                
                target_records = stu_df[stu_df['學科類別'] == sel_sub_hist]

                # --- 新增：考前戰術重點提示功能 ---
                st.markdown(f"### 🚀 {sel_sub_hist} 科：考前戰術重點提示")
                if st.button(f"🧠 彙整 {sel_sub_hist} 歷史漏洞，產出考前指令"):
                    with st.spinner("戰術建模中..."):
                        history_blob = "\n".join([f"範圍:{r['考試範圍']}, 分析:{r['導師觀察摘要']}" for _, r in target_records.head(5).iterrows()])
                        tips_prompt = f"""分析該生在 {sel_sub_hist} 的歷史錯誤紀錄：{history_blob}。
                        請為其產出「考前戰術指令」：
                        1. 該生最常掉入的「陷阱類型」。
                        2. 考前 10 分鐘必須複習的「核心事實」。
                        3. 針對其個人習慣的「操作提醒」（如：檢查單位、注意題目關鍵字）。
                        要求：條列式、敘述詳盡、絕對去美化、嚴禁頁碼。"""
                        tips_res = ai_engine.generate_content(tips_prompt).text
                        st.markdown(f'<div class="tactical-advice">{tips_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

                st.divider()
                st.markdown(f"### 📋 {sel_sub_hist} 歷史診斷紀錄明細")
                for _, row in target_records.iterrows():
                    st.markdown(f"""
                    <div class="range-card">
                        <b>🎯 範圍：{row["考試範圍"]}</b> ({row["測驗成績"]}分)<br>
                        <p style="margin-top:10px;"><b>[ 內容敘述 ]</b><br>{row["導師觀察摘要"].replace("\n", "<br>")}</p>
                    </div>
                    """, unsafe_allow_html=True)
        else: st.info("💡 資料庫尚無數據。")
