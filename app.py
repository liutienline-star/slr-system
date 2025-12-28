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

# --- 2. 視覺風格 (優化閱讀寬度與層次感) ---
st.markdown("""
<style>
    /* 限制最大寬度，改善長文本閱讀體驗 */
    .main .block-container {
        max-width: 1000px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    .stApp { background-color: #1a1c23; color: #e5e9f0; }
    .main-header { text-align: center; color: #88c0d0; font-weight: 800; font-size: 2.2rem; margin-bottom: 1.5rem; }
    
    /* 按鈕樣式 */
    .stButton>button { 
        background-color: #3b4252 !important; 
        color: #ffffff !important; 
        border: 1px solid #88c0d0 !important; 
        width: 100%; 
        border-radius: 10px; 
        font-weight: 700; 
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #4c566a !important; border-color: #8fbcbb !important; }

    /* 卡片設計 */
    .input-card { background-color: #2e3440; padding: 25px; border-radius: 15px; border: 1px solid #4c566a; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .subject-header { color: #88c0d0; border-bottom: 2px solid #88c0d0; padding-bottom: 8px; margin-top: 30px; margin-bottom: 15px; font-size: 1.4rem; font-weight: bold; }
    .range-card { background-color: #3b4252; padding: 18px; border-radius: 12px; border-left: 5px solid #81a1c1; margin-bottom: 15px; }
    
    /* 診斷建議專用區塊 */
    .special-box { 
        background-color: #2e3440; 
        padding: 30px; 
        border-radius: 15px; 
        border: 1px solid #88c0d0; 
        margin-bottom: 20px; 
        box-shadow: 0px 8px 16px rgba(0,0,0,0.4);
        line-height: 1.8;
    }
    .report-box { 
        background-color: #ffffff; 
        color: #2e3440; 
        padding: 35px; 
        border-radius: 12px; 
        font-family: "Microsoft JhengHei", sans-serif; 
        line-height: 1.7; 
        border: 1px solid #d8dee9;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    }
    
    [data-testid="stWidgetLabel"] p { color: #88c0d0 !important; font-weight: 600; font-size: 1rem; margin-bottom: 5px; }
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

# --- Tab 1: 影像診斷錄入 ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        with col2: subject = st.selectbox("📚 學科類別", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        
        exam_range = st.text_input("🎯 段考/週考範圍", placeholder="例：第一次段考 / L1-L2")
        score = st.number_input("💯 測驗成績", 0, 100, 60)
        uploaded_file = st.file_uploader("📷 拍照上傳考卷 (執行段考弱點分析)", type=["jpg", "jpeg", "png"])
        
        if "v_obs" not in st.session_state: st.session_state.v_obs = ""
        if uploaded_file and st.button("🔍 啟動專業家教影像分析"):
            with st.spinner("AI 專業家教閱卷中..."):
                img = Image.open(uploaded_file)
                # 調整 Prompt 專注於段考進度
                v_res = ai_engine.generate_content([
                    f"你是一位精通校內教學進度與段考命題邏輯的專業家教，請分析這張{subject}({exam_range})考卷。1.列出錯誤題目 2.指出學生在段考常見題型(如基礎運算、觀念辨析、課文理解)上受挫的原因 3.摘要核心弱點。", 
                    img
                ])
                st.session_state.v_obs = v_res.text
        
        obs = st.text_area("🔍 導師觀察摘要 (AI 建議可在此細修)", value=st.session_state.v_obs, height=400)

        if st.button("🚀 彙整專家建議並存檔"):
            if stu_id and obs and exam_range:
                with st.spinner("戰術數據同步中..."):
                    # 強調段考拿高分的精準策略
                    diag_prompt = f"你是精通學期段考出題趨勢的專業家教。針對{subject}({exam_range})表現：{obs}。請提供 150 字內、針對該段考進度的精準補強建議。"
                    diag = ai_engine.generate_content(diag_prompt).text
                    hub_sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), stu_id, subject, exam_range, score, obs, diag])
                    st.success("✅ 戰術數據已存入雲端！"); st.session_state.v_obs = ""
            else: st.warning("請確保填寫代號與觀察內容。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2: 歷史數據庫 ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 刷新雲端戰略庫"): st.rerun()
        raw_df = pd.DataFrame(hub_sheet.get_all_records())
        if not raw_df.empty:
            st.dataframe(raw_df.sort_values(by="日期時間", ascending=False), use_container_width=True)

# --- Tab 3: 戰術分析室 ---
with tab_analysis:
    if hub_sheet:
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df = pd.DataFrame(raw_data)
            df['小考成績'] = pd.to_numeric(df['小考成績'], errors='coerce').fillna(0)
            
            stu_list = df['學生代號'].unique()
            sel_stu = st.selectbox("🎯 選擇受測學生代號", stu_list)
            stu_df = df[df['學生代號'] == sel_stu].sort_values('日期時間', ascending=False)
            
            if not stu_df.empty:
                st.subheader("📊 學期各科均衡度分析")
                avg_scores = stu_df.groupby('學科類別')['小考成績'].mean().reset_index()
                fig_radar = px.line_polar(avg_scores, r='小考成績', theta='學科類別', line_close=True, range_r=[0,100])
                fig_radar.update_traces(fill='toself', line_color='#88c0d0')
                fig_radar.update_layout(template="plotly_dark", margin=dict(l=50, r=50, t=20, b=20))
                st.plotly_chart(fig_radar, use_container_width=True)
                
                st.divider()

                # --- 核心角色定位：專業段考家教 ---
                st.markdown(f"### ⚡ {sel_stu} 段考專家戰術調度")
                analysis_modes = ["📡 跨科學習診斷"] + sorted(list(stu_df['學科類別'].unique()))
                sel_mode = st.radio("請選擇分析維度：", analysis_modes, horizontal=True)

                st.markdown("---")

                if sel_mode == "📡 跨科學習診斷":
                    st.info("💡 系統正分析多學科表現，找尋該學生的學術底層問題。")
                    if st.button(f"執行 {sel_stu} 跨科專家分析"):
                        with st.spinner("專業家教深度分析中..."):
                            cross_context = "\n".join([f"{r['學科類別']}：{r['AI診斷與建議']}" for _, r in stu_df.head(10).iterrows()])
                            dispatch_prompt = f"""
                            你是一位深耕校內課程、精通段考命題趨勢的專業家教。
                            請分析以下學生的多科段考/測驗表現：
                            {cross_context}
                            
                            請針對『段考成績提升』提出三項關鍵戰術：
                            1. 底層弱點分析（如：基礎概念不穩、題目理解偏差、粗心規律）。
                            2. 針對該年級高分目標的具體調度建議（如何調整讀書比例）。
                            3. 導師如何輔助學生改善該階段的讀書習慣。
                            (250字內，條列式，語氣專業且精準)
                            """
                            dispatch_res = ai_engine.generate_content(dispatch_prompt).text
                            st.markdown(f'<div class="special-box" style="border-left: 8px solid #bf616a;"><h4 style="color:#bf616a;">📡 專家戰略：跨科補強指導</h4>{dispatch_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

                else:
                    target_sub = sel_mode
                    sub_specific_df = stu_df[stu_df['學科類別'] == target_sub]
                    st.info(f"💡 針對 {target_sub} 進行段考高頻考點與重點補強提示。")
                    
                    if st.button(f"生成 {target_sub} 段考重點提示"):
                        with st.spinner(f"正在分析 {target_sub} 關鍵考點..."):
                            history_context = "\n".join([f"範圍:{r['考試範圍']}, 摘要:{r['導師觀察摘要']}" for _, r in sub_specific_df.head(5).iterrows()])
                            hunt_prompt = f"""
                            你是一位擅長幫助學生在段考奪取高分的專業家教。
                            針對學生在 {target_sub} 的歷史錯誤紀錄：
                            {history_context}
                            
                            請產出該科的『段考重點補強提示』：
                            1. 觀念陷阱分析：根據錯題紀錄，哪些常見的段考題型是學生的盲區？
                            2. 精準搶分策略：針對接下來的段考範圍，最需要注意的細節與觀念為何？
                            3. 考前重點建議：提供三個考前 24 小時的必看點。
                            (條列式，專業精煉)
                            """
                            hunt_res = ai_engine.generate_content(hunt_prompt).text
                            st.markdown(f'<div class="special-box"><h4 style="color:#88c0d0;">🎯 {target_sub} 段考精準補強建議</h4>{hunt_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

                st.divider()

                # 報表預覽 (調整為段考診斷格式)
                st.subheader("📊 段考歷程診斷報告預覽")
                if st.checkbox("開啟家長端段考分析報告"):
                    r_text = f"## 🎓 {sel_stu} 學習診斷報告 (學期段考專用)\n"
                    r_text += "---\n"
                    for s in stu_df['學科類別'].unique():
                        r_text += f"### 【{s} 段考表現分析】\n"
                        for _, r in stu_df[stu_df['學科類別'] == s].head(3).iterrows():
                            r_text += f"- **{r['考試範圍']}**：成績 {r['小考成績']}\n  *專家診斷：{r['AI診斷與建議']}*\n\n"
                    st.markdown('<div class="report-box">' + r_text + '</div>', unsafe_allow_html=True)

                # 詳細歷史清單
                for s in stu_df['學科類別'].unique():
                    st.markdown(f'<div class="subject-header">📚 {s} 歷史診斷</div>', unsafe_allow_html=True)
                    for _, row in stu_df[stu_df['學科類別'] == s].iterrows():
                        c_html = f'<div class="range-card"><b>🎯 範圍：{row["考試範圍"]}</b> ({row["小考成績"]}分)<br><p style="margin-top:10px; font-size:0.95rem;">{row["AI診斷與建議"]}</p></div>'
                        st.markdown(c_html, unsafe_allow_html=True)
        else:
            st.info("💡 目前資料庫尚無數據。")
