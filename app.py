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

# --- 2. 視覺風格 (校長指定的深色戰術介面) ---
st.markdown("""
<style>
    .stApp { background-color: #1a1c23; color: #e5e9f0; }
    .main-header { text-align: center; color: #88c0d0; font-weight: 800; font-size: 2.2rem; margin-bottom: 1rem; }
    .stButton>button { background-color: #3b4252 !important; color: #ffffff !important; border: 1px solid #88c0d0 !important; width: 100%; border-radius: 8px; font-weight: 700; height: 45px; }
    .input-card { background-color: #2e3440; padding: 20px; border-radius: 12px; border: 1px solid #4c566a; margin-bottom: 20px; }
    .subject-header { color: #88c0d0; border-bottom: 2px solid #88c0d0; padding-bottom: 5px; margin-top: 25px; margin-bottom: 15px; font-size: 1.5rem; font-weight: bold; }
    .range-card { background-color: #2e3440; padding: 20px; border-radius: 12px; border-left: 5px solid #81a1c1; margin-bottom: 15px; }
    .special-box { background-color: #3b4252; padding: 25px; border-radius: 15px; border: 1px solid #88c0d0; margin-bottom: 20px; box-shadow: 0px 4px 10px rgba(0,0,0,0.3); }
    .report-box { background-color: #ffffff; color: #000000; padding: 30px; border-radius: 10px; font-family: sans-serif; line-height: 1.6; border: 2px solid #000; margin-top: 10px; }
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

st.markdown('<h1 class="main-header">🏫 「學思戰情」跨科調度整合系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view, tab_analysis = st.tabs(["📝 影像診斷錄入", "🔍 歷史數據庫", "📊 戰術分析室"])

# --- Tab 1: 影像診斷錄入 (視窗高度已調整) ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        subject = st.selectbox("📚 學科類別", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        exam_range = st.text_input("🎯 考試範圍", placeholder="例：L1-L3")
        score = st.number_input("💯 小考成績", 0, 100, 60)
        uploaded_file = st.file_uploader("📷 拍照上傳考卷", type=["jpg", "jpeg", "png"])
        
        if "v_obs" not in st.session_state: st.session_state.v_obs = ""
        if uploaded_file and st.button("🔍 執行 AI 影像診讀"):
            with st.spinner("影像分析中..."):
                img = Image.open(uploaded_file)
                v_res = ai_engine.generate_content([f"分析這張{subject}({exam_range})考卷。列出錯題並摘要弱點。", img])
                st.session_state.v_obs = v_res.text
        
        # --- 校長需求：這裡的高度已從 120 調整為 400 ---
        obs = st.text_area("🔍 導師觀察摘要", value=st.session_state.v_obs, height=400)

        if st.button("🚀 生成補強建議並存檔"):
            if stu_id and obs and exam_range:
                with st.spinner("存檔中..."):
                    diag = ai_engine.generate_content(f"針對{subject}({exam_range})表現：{obs}。給150字建議。").text
                    hub_sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), stu_id, subject, exam_range, score, obs, diag])
                    st.success("✅ 數據已同步！"); st.session_state.v_obs = ""
            else: st.warning("請填寫必要欄位。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2: 歷史數據庫 (完整保留) ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 刷新數據"): st.rerun()
        raw_df = pd.DataFrame(hub_sheet.get_all_records())
        if not raw_df.empty:
            st.dataframe(raw_df.sort_values(by="日期時間", ascending=False), use_container_width=True)

# --- Tab 3: 戰術分析室 (考前重點提示版) ---
with tab_analysis:
    if hub_sheet:
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df = pd.DataFrame(raw_data)
            df['小考成績'] = pd.to_numeric(df['小考成績'], errors='coerce').fillna(0)
            
            stu_list = df['學生代號'].unique()
            sel_stu = st.selectbox("🎯 選擇分析學生代號", stu_list)
            stu_df = df[df['學生代號'] == sel_stu].sort_values('日期時間', ascending=False)
            
            st.divider()
            
            if not stu_df.empty:
                st.subheader("📊 學習歷程雷達圖")
                avg_scores = stu_df.groupby('學科類別')['小考成績'].mean().reset_index()
                fig_radar = px.line_polar(avg_scores, r='小考成績', theta='學科類別', line_close=True, range_r=[0,100])
                fig_radar.update_traces(fill='toself', line_color='#88c0d0')
                fig_radar.update_layout(template="plotly_dark")
                st.plotly_chart(fig_radar, use_container_width=True)
                
                st.divider()

                st.markdown(f"### ⚡ {sel_stu} 戰術任務調度")
                analysis_modes = ["📡 跨科整合診斷"] + sorted(list(stu_df['學科類別'].unique()))
                sel_mode = st.radio("請選擇分析維度：", analysis_modes, horizontal=True)

                st.markdown("---")

                if sel_mode == "📡 跨科整合診斷":
                    st.info("💡 系統正分析所有學科的 AI 診斷建議，找尋底層共性問題。")
                    if st.button(f"執行 {sel_stu} 跨科深度診斷"):
                        with st.spinner("AI 跨科診斷中..."):
                            cross_context = "\n".join([f"{r['學科類別']}：{r['AI診斷與建議']}" for _, r in stu_df.head(10).iterrows()])
                            dispatch_prompt = f"分析以下多科診斷紀錄：\n{cross_context}\n請找出底層共同問題（如：閱讀理解、邏輯規律、粗心規律）。提供導師具體的調度建議，200字內。"
                            dispatch_res = ai_engine.generate_content(dispatch_prompt).text
                            st.markdown(f'<div class="special-box" style="border-left: 8px solid #bf616a;"><h4 style="color:#bf616a;">📡 導師跨科戰略洞察</h4>{dispatch_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

                else:
                    target_sub = sel_mode
                    sub_specific_df = stu_df[stu_df['學科類別'] == target_sub]
                    st.info(f"💡 系統將針對 {target_sub} 的錯誤摘要，生成考前重點補強提示。")
                    
                    if st.button(f"生成 {target_sub} 重點補強提示"):
                        with st.spinner(f"正在分析 {target_sub} 弱點..."):
                            history_context = "\n".join([f"範圍:{r['考試範圍']}, 摘要:{r['導師觀察摘要']}" for _, r in sub_specific_df.head(5).iterrows()])
                            hunt_prompt = f"針對學生在{target_sub}的歷史錯誤紀錄：\n{history_context}\n請產出『考前重點補強提示』。列出最需要注意的 3-5 個觀念陷阱、常見錯題型態與複習應對策略。"
                            hunt_res = ai_engine.generate_content(hunt_prompt).text
                            st.markdown(f'<div class="special-box"><h4 style="color:#88c0d0;">🎯 {target_sub} 考前重點補強提示</h4>{hunt_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

                st.divider()

                st.subheader("📊 詳細歷史紀錄與報表")
                if st.checkbox("開啟預覽家長診斷報告"):
                    r_text = f"## 🎓 {sel_stu} 學習診斷報告\n"
                    for s in stu_df['學科類別'].unique():
                        r_text += f"### 【{s}】\n"
                        for _, r in stu_df[stu_df['學科類別'] == s].iterrows():
                            r_text += f"- **範圍：{r['考試範圍']}** ({r['小考成績']}分)\n  *複習策略：{r['AI診斷與建議']}*\n\n"
                    st.markdown('<div class="report-box">' + r_text + '</div>', unsafe_allow_html=True)

                for s in stu_df['學科類別'].unique():
                    st.markdown(f'<div class="subject-header">📚 {s} 紀錄細節</div>', unsafe_allow_html=True)
                    for _, row in stu_df[stu_df['學科類別'] == s].iterrows():
                        c_html = f'<div class="range-card"><b>🎯 範圍：{row["考試範圍"]}</b> ({row["小考成績"]}分)<br><p style="margin-top:10px;">{row["AI診斷與建議"]}</p></div>'
                        st.markdown(c_html, unsafe_allow_html=True)
        else:
            st.info("💡 目前資料庫尚無數據。")
