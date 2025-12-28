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

# --- 2. 視覺風格 (優化閱讀寬度，確保專業度) ---
st.markdown("""
<style>
    .main .block-container {
        max-width: 1000px;
        padding-top: 2rem;
    }
    .stApp { background-color: #1a1c23; color: #e5e9f0; }
    .main-header { text-align: center; color: #88c0d0; font-weight: 800; font-size: 2.2rem; margin-bottom: 1.5rem; }
    .stButton>button { 
        background-color: #3b4252 !important; color: #ffffff !important; 
        border: 1px solid #88c0d0 !important; width: 100%; border-radius: 10px; font-weight: 700;
    }
    .input-card { background-color: #2e3440; padding: 25px; border-radius: 15px; border: 1px solid #4c566a; margin-bottom: 20px; }
    .subject-header { color: #88c0d0; border-bottom: 2px solid #88c0d0; padding-bottom: 8px; margin-top: 30px; margin-bottom: 15px; font-size: 1.4rem; font-weight: bold; }
    .range-card { background-color: #3b4252; padding: 18px; border-radius: 12px; border-left: 5px solid #81a1c1; margin-bottom: 15px; }
    .special-box { 
        background-color: #2e3440; padding: 30px; border-radius: 15px; border: 1px solid #88c0d0; 
        margin-bottom: 20px; box-shadow: 0px 8px 16px rgba(0,0,0,0.4); line-height: 1.8;
    }
    .report-box { 
        background-color: #ffffff; color: #2e3440; padding: 35px; border-radius: 12px; 
        font-family: sans-serif; line-height: 1.7; border: 1px solid #d8dee9;
    }
    [data-testid="stWidgetLabel"] p { color: #88c0d0 !important; font-weight: 600; font-size: 1rem; }
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
    _, col_m, _ = st.columns([0.5, 1, 0.5])
    with col_m:
        st.markdown("<h2 style='text-align:center; color:#88c0d0;'>戰情系統登入</h2>", unsafe_allow_html=True)
        if st.text_input("輸入授權碼：", type="password") == AUTH_CODE:
            st.session_state.authenticated = True; st.rerun()
    st.stop()

st.markdown('<h1 class="main-header">🏫 「學思戰情」學期段考調度系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view, tab_analysis = st.tabs(["📝 影像診斷錄入", "🔍 歷史數據庫", "📊 戰術分析室"])

# --- Tab 1: 影像診斷錄入 (嚴謹分析版) ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        with col2: subject = st.selectbox("📚 學科類別", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        
        exam_range = st.text_input("🎯 段考/週考範圍", placeholder="例：第一次段考")
        score = st.number_input("💯 測驗成績", 0, 100, 60)
        uploaded_file = st.file_uploader("📷 上傳考卷影像 (執行精準弱點掃描)", type=["jpg", "jpeg", "png"])
        
        if "v_obs" not in st.session_state: st.session_state.v_obs = ""
        if uploaded_file and st.button("🔍 執行事實導向影像診讀"):
            with st.spinner("影像分析中..."):
                img = Image.open(uploaded_file)
                # 強化 Prompt：要求事實，嚴禁美化
                v_res = ai_engine.generate_content([
                    f"你是一位嚴謹的教育分析師。請精確掃描這張{subject}考卷：1.列出錯誤的具體題號。2.標註每個錯題對應的單元知識點。3.分析學生的錯誤是屬於「計算錯誤」、「觀念誤解」還是「題目閱讀理解偏差」。嚴禁給予鼓勵性言論，請提供事實清單。", 
                    img
                ])
                st.session_state.v_obs = v_res.text
        
        obs = st.text_area("🔍 錯誤事實摘要 (請確認內容是否與考卷相符)", value=st.session_state.v_obs, height=400)

        if st.button("🚀 生成數據診斷並存檔"):
            if stu_id and obs and exam_range:
                with st.spinner("數據分析中..."):
                    # 強調補強建議必須與錯誤事實精確對應
                    diag_prompt = f"你是教學診斷專家。根據以下事實紀錄：{obs}。請產出 150 字內的補強策略。要求：每個策略必須對應到前述的一項具體錯誤。不要美化建議，要具備可執行的正確性。"
                    diag = ai_engine.generate_content(diag_prompt).text
                    hub_sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), stu_id, subject, exam_range, score, obs, diag])
                    st.success("✅ 數據存檔成功！"); st.session_state.v_obs = ""
            else: st.warning("請確保填寫代號與摘要。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2: 歷史數據庫 ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 刷新雲端紀錄"): st.rerun()
        raw_df = pd.DataFrame(hub_sheet.get_all_records())
        if not raw_df.empty:
            st.dataframe(raw_df.sort_values(by="日期時間", ascending=False), use_container_width=True)

# --- Tab 3: 戰術分析室 (事實交叉檢核版) ---
with tab_analysis:
    if hub_sheet:
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df = pd.DataFrame(raw_data)
            df['測驗成績'] = pd.to_numeric(df['測驗成績'], errors='coerce').fillna(0)
            
            stu_list = df['學生代號'].unique()
            sel_stu = st.selectbox("🎯 選擇分析對象代號", stu_list)
            stu_df = df[df['學生代號'] == sel_stu].sort_values('日期時間', ascending=False)
            
            if not stu_df.empty:
                st.subheader("📊 學期分科數據分布")
                avg_scores = stu_df.groupby('學科類別')['測驗成績'].mean().reset_index()
                fig_radar = px.line_polar(avg_scores, r='測驗成績', theta='學科類別', line_close=True, range_r=[0,100])
                fig_radar.update_traces(fill='toself', line_color='#88c0d0')
                fig_radar.update_layout(template="plotly_dark")
                st.plotly_chart(fig_radar, use_container_width=True)
                
                st.divider()

                st.markdown(f"### ⚡ {sel_stu} 段考戰術診斷")
                analysis_modes = ["📡 跨科錯誤共性診斷"] + sorted(list(stu_df['學科類別'].unique()))
                sel_mode = st.radio("請選擇分析維度：", analysis_modes, horizontal=True)

                st.markdown("---")

                if sel_mode == "📡 跨科錯誤共性診斷":
                    st.info("💡 跨科分析旨在找出學生的底層邏輯漏洞（如：閱讀跳行、符號誤判等事實）。")
                    if st.button(f"執行 {sel_stu} 跨科共性分析"):
                        with st.spinner("數據交叉比對中..."):
                            cross_context = "\n".join([f"{r['學科類別']}：{r['AI診斷與建議']}" for _, r in stu_df.head(10).iterrows()])
                            dispatch_prompt = f"""
                            分析以下學生的多科錯誤診斷：
                            {cross_context}
                            
                            請排除所有修辭與美化，直接指出：
                            1. 學生在不同學科中反覆出現的「具體錯誤行為」（例如：皆在圖表判讀失誤）。
                            2. 根據數據，下階段最應優先解決的兩項學術弱點。
                            3. 具體可檢核的修正方法。
                            (250字內，事實導向)
                            """
                            dispatch_res = ai_engine.generate_content(dispatch_prompt).text
                            st.markdown(f'<div class="special-box" style="border-left: 8px solid #bf616a;"><h4 style="color:#bf616a;">📡 數據觀察：跨科底層弱點分析</h4>{dispatch_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

                else:
                    target_sub = sel_mode
                    sub_specific_df = stu_df[stu_df['學科類別'] == target_sub]
                    st.info(f"💡 針對 {target_sub} 歷次錯誤，生成具體補強提示。")
                    
                    if st.button(f"生成 {target_sub} 具體補強提示"):
                        with st.spinner(f"正在分析 {target_sub} 錯誤趨勢..."):
                            history_context = "\n".join([f"範圍:{r['考試範圍']}, 摘要:{r['導師觀察摘要']}" for _, r in sub_specific_df.head(5).iterrows()])
                            hunt_prompt = f"""
                            你是一位專精{target_sub}的學術顧問。請檢視該生以下錯誤史：
                            {history_context}
                            
                            請生成『段考重點補強提示』。要求具備可檢視的正確性：
                            1. 精確知識點：根據歷史紀錄，列出該生最常出錯的 3 個特定章節或觀念。
                            2. 陷阱辨識：針對該生的錯誤型態，指出段考中相對應的陷阱題型。
                            3. 複習動作：提供具體、非描述性的複習動作（如：重新計算某類題目）。
                            (條列式，語氣專業且精準，嚴禁美化)
                            """
                            hunt_res = ai_engine.generate_content(hunt_prompt).text
                            st.markdown(f'<div class="special-box"><h4 style="color:#88c0d0;">🎯 {target_sub} 精準補強清單</h4>{hunt_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

                st.divider()

                # 詳細歷史清單 (增加數據透明度)
                for s in stu_df['學科類別'].unique():
                    st.markdown(f'<div class="subject-header">📚 {s} 歷史數據明細</div>', unsafe_allow_html=True)
                    for _, row in stu_df[stu_df['學科類別'] == s].iterrows():
                        c_html = f'<div class="range-card"><b>🎯 範圍：{row["考試範圍"]}</b> ({row["測驗成績"]}分)<br><p style="margin-top:10px; font-size:0.95rem;"><b>事實紀錄：</b>{row["AI診斷與建議"]}</p></div>'
                        st.markdown(c_html, unsafe_allow_html=True)
        else:
            st.info("💡 目前資料庫尚無數據。")
