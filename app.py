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

# --- 2. 視覺風格 (確保深色模式與垂直排版) ---
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
    except Exception as e:
        return None, None

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

# --- Tab 1: 影像診斷錄入 (對齊校長欄位) ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        sub_cat = st.selectbox("📚 學科類別", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        ex_range = st.text_input("🎯 考試範圍", placeholder="例：L1-L3")
        score_val = st.number_input("💯 小考成績", 0, 100, 60)
        
        uploaded_file = st.file_uploader("📷 拍照上傳考卷或講義", type=["jpg", "jpeg", "png"])
        
        if "obs_temp" not in st.session_state: st.session_state.obs_temp = ""
        if uploaded_file and st.button("🔍 執行 AI 影像掃描"):
            with st.spinner("Gemini 正在辨識錯題..."):
                img = Image.open(uploaded_file)
                v_res = ai_engine.generate_content([f"分析這張{sub_cat}({ex_range})考卷。找出錯題並說明錯誤原因。", img])
                st.session_state.obs_temp = v_res.text
        
        # 關鍵欄位名稱：導師觀察摘要
        obs_input = st.text_area("🔍 導師觀察摘要 (AI 自動辨識結果)", value=st.session_state.obs_temp, height=120)

        if st.button("🚀 生成補強診斷並同步雲端"):
            if stu_id and obs_input and ex_range:
                with st.spinner("正在生成補強計畫..."):
                    # 關鍵欄位名稱：AI診斷與建議
                    f_prompt = f"根據學生{stu_id}在{sub_cat}({ex_range})的分數{score_val}與細節：{obs_input}。請提供150字內具體補強建議。"
                    diag_result = ai_engine.generate_content(f_prompt).text
                    # 存入順序：日期時間, 學生代號, 學科類別, 考試範圍, 小考成績, 導師觀察摘要, AI診斷與建議
                    hub_sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), stu_id, sub_cat, ex_range, score_val, obs_input, diag_result])
                    st.success("✅ 數據已成功同步！"); st.session_state.obs_temp = ""
            else: st.warning("請填寫必要欄位。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2: 歷史數據 ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 刷新雲端數據"): st.rerun()
        df_all = pd.DataFrame(hub_sheet.get_all_records())
        st.dataframe(df_all.sort_values(by="日期時間", ascending=False), use_container_width=True)

# --- Tab 3: 戰術分析室 (徹底修正 KeyError) ---
with tab_analysis:
    if hub_sheet:
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df = pd.DataFrame(raw_data)
            df['小考成績'] = pd.to_numeric(df['小考成績'], errors='coerce').fillna(0)
            
            # 1. 學生選擇
            stu_list = df['學生代號'].unique()
            sel_stu = st.selectbox("🎯 選取分析對象", stu_list)
            stu_df = df[df['學生代號'] == sel_stu].sort_values('日期時間', ascending=False)
            
            st.divider()

            # 2. 考前精準獵殺計畫 (此處為原報錯位置，已修正欄位名)
            st.markdown("### 🏹 二、考前精準獵殺計畫")
            if st.button(f"🚀 生成 {sel_stu} 的 3 天精準補強單"):
                with st.spinner("分析最近錯誤點..."):
                    # 修正：將 '觀察摘要' 改為 '導師觀察摘要'
                    history_context = "\n".join([f"科目:{r['學科類別']}, 範圍:{r['考試範圍']}, 觀察:{r['導師觀察摘要']}" for _, r in stu_df.head(5).iterrows()])
                    hunt_prompt = f"你是教練。根據學生近期紀錄：\n{history_context}\n請生成一個3天補強時程表，針對弱點練習題型，簡潔有力。"
                    hunt_res = ai_engine.generate_content(hunt_prompt).text
                    st.markdown(f'<div class="special-box"><h4 style="color:#88c0d0;">🎯 3 天精準補強清單</h4>{hunt_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

            st.divider()

            # 3. 跨科資源調度模式
            st.markdown("### 🧠 三、跨科學習資源調度洞察")
            if st.button(f"📡 分析 {sel_stu} 的核心瓶頸"):
                with st.spinner("跨科掃描中..."):
                    # 修正：確保引用 '學科類別' 與 'AI診斷與建議'
                    cross_context = "\n".join([f"{r['學科類別']}：{r['AI診斷與建議']}" for _, r in stu_df.head(8).iterrows()])
                    dispatch_prompt = f"分析以下多科診斷：\n{cross_context}\n找出底層共同問題（如：閱讀耐力、邏輯斷層）。提供導師建議，200字內。"
                    dispatch_res = ai_engine.generate_content(dispatch_prompt).text
                    st.markdown(f'<div class="special-box" style="border-left: 8px solid #bf616a;"><h4 style="color:#bf616a;">📡 導師跨科調度洞察</h4>{dispatch_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

            st.divider()

            # 4. 家長報表與歷程 (修正所有篩選邏輯)
            st.subheader("📊 學科歷程與報表輸出")
            sub_opts = ["全部學科"] + list(stu_df['學科類別'].unique())
            sel_sub = st.selectbox("篩選學科", sub_opts)
            
            final_df = stu_df if sel_sub == "全部學科" else stu_df[stu_df['學科類別'] == sel_sub]
            
            if st.checkbox("預覽家長診斷報告"):
                r_text = f"## 🎓 {sel_stu} 學習診斷報告\n"
                for s in final_df['學科類別'].unique():
                    r_text += f"### 【{s}】\n"
                    for _, r in final_df[final_df['學科類別'] == s].iterrows():
                        r_text += f"- **範圍：{r['考試範圍']}** ({r['小考成績']}分)\n  *診斷建議：{r['AI診斷與建議']}*\n\n"
                st.markdown('<div class="report-box">', unsafe_allow_html=True)
                st.markdown(r_text)
                st.markdown('</div>', unsafe_allow_html=True)

            # 詳細歷程卡片
            for s in final_df['學科類別'].unique():
                st.markdown(f'<div class="subject-header">📚 {s}</div>', unsafe_allow_html=True)
                for _, row in final_df[final_df['學科類別'] == s].iterrows():
                    c_html = f'<div class="range-card"><b>🎯 範圍：{row["考試範圍"]}</b> ({row["小考成績"]}分)<br><p style="margin-top:10px;">{row["AI診斷與建議"]}</p></div>'
                    st.markdown(c_html, unsafe_allow_html=True)
