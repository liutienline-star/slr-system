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
    /* 限制最大寬度，避免在大螢幕上太寬難以閱讀 */
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
    
    /* 輸入欄位標籤字體 */
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

st.markdown('<h1 class="main-header">🏫 「學思戰情」教育會考調度系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view, tab_analysis = st.tabs(["📝 影像診斷錄入", "🔍 歷史數據庫", "📊 戰術分析室"])

# --- Tab 1: 影像診斷錄入 ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        with col2: subject = st.selectbox("📚 學科類別", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        
        exam_range = st.text_input("🎯 考試範圍", placeholder="例：L1-L3 / 複習模考一")
        score = st.number_input("💯 小考成績", 0, 100, 60)
        uploaded_file = st.file_uploader("📷 拍照上傳考卷 (執行 AI 弱點掃描)", type=["jpg", "jpeg", "png"])
        
        if "v_obs" not in st.session_state: st.session_state.v_obs = ""
        if uploaded_file and st.button("🔍 啟動專業家教影像分析"):
            with st.spinner("AI 家教閱卷中..."):
                img = Image.open(uploaded_file)
                # 強化影像診斷的 Prompt，使其更具備家教視野
                v_res = ai_engine.generate_content([
                    f"你是一位專業國中家教，請分析這張{subject}({exam_range})考卷。1.列出錯誤題目 2.指出學生在 108 課綱要求的何種能力(如運算、圖表分析、閱讀)上受挫 3.摘要核心弱點。", 
                    img
                ])
                st.session_state.v_obs = v_res.text
        
        obs = st.text_area("🔍 導師觀察摘要 (AI 診讀結果可在此修改)", value=st.session_state.v_obs, height=400)

        if st.button("🚀 彙整專家建議並存檔"):
            if stu_id and obs and exam_range:
                with st.spinner("戰術數據同步中..."):
                    # 強化存檔建議的專業度
                    diag_prompt = f"你是精通會考出題趨勢的權威家教。針對{subject}({exam_range})表現：{obs}。請給出 150 字內、極具針對性的應試策略建議。"
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
                # 學習分布可視化
                st.subheader("📊 會考五科均衡度分析")
                avg_scores = stu_df.groupby('學科類別')['小考成績'].mean().reset_index()
                fig_radar = px.line_polar(avg_scores, r='小考成績', theta='學科類別', line_close=True, range_r=[0,100])
                fig_radar.update_traces(fill='toself', line_color='#88c0d0')
                fig_radar.update_layout(template="plotly_dark", margin=dict(l=50, r=50, t=20, b=20))
                st.plotly_chart(fig_radar, use_container_width=True)
                
                st.divider()

                # --- 核心角色定位：專業家教戰術調度 ---
                st.markdown(f"### ⚡ {sel_stu} 專家戰術調度")
                analysis_modes = ["📡 跨科素養診斷"] + sorted(list(stu_df['學科類別'].unique()))
                sel_mode = st.radio("請選擇分析維度：", analysis_modes, horizontal=True)

                st.markdown("---")

                if sel_mode == "📡 跨科素養診斷":
                    st.info("💡 系統正彙整所有學科紀錄，分析學生的『底層學習障礙』。")
                    if st.button(f"執行 {sel_stu} 跨科專家診斷"):
                        with st.spinner("首席家教分析中..."):
                            cross_context = "\n".join([f"{r['學科類別']}：{r['AI診斷與建議']}" for _, r in stu_df.head(10).iterrows()])
                            dispatch_prompt = f"""
                            你是一位精通 108 課綱與國中教育會考趨勢的權威首席家教。
                            請分析以下學生的多科表現紀錄：
                            {cross_context}
                            
                            請針對『會考應試能力』提出三項關鍵洞察：
                            1. 底層弱點分析（如：閱讀耐力不足、跨領域連結弱、圖表理解偏差）。
                            2. 針對會考 A++ 目標的具體調度建議。
                            3. 導師如何介入心理層面或讀書習慣。
                            (250字內，條列式)
                            """
                            dispatch_res = ai_engine.generate_content(dispatch_prompt).text
                            st.markdown(f'<div class="special-box" style="border-left: 8px solid #bf616a;"><h4 style="color:#bf616a;">📡 首席家教：全科戰術指導</h4>{dispatch_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

                else:
                    target_sub = sel_mode
                    sub_specific_df = stu_df[stu_df['學科類別'] == target_sub]
                    st.info(f"💡 針對 {target_sub} 進行會考趨勢重點補強提示。")
                    
                    if st.button(f"生成 {target_sub} 會考重點提示"):
                        with st.spinner(f"正在鎖定 {target_sub} 會考考點..."):
                            history_context = "\n".join([f"範圍:{r['考試範圍']}, 摘要:{r['導師觀察摘要']}" for _, r in sub_specific_df.head(5).iterrows()])
                            # 強化家教角色與會考趨勢
                            hunt_prompt = f"""
                            你是一位專門輔導國中教育會考 A++ 等級的專業家教。
                            針對學生在 {target_sub} 的歷史錯誤紀錄：
                            {history_context}
                            
                            請給出該科的『會考前重點補強提示』：
                            1. 核心陷阱辨識：根據錯題分析，哪些會考常考觀念學生最容易混淆？
                            2. 素養題型應對：針對 108 課綱的長難句或圖表題，學生應注意什麼？
                            3. 具體搶分策略：考前 24 小時最值得複習的關鍵點。
                            (條列式，語氣專業且精準)
                            """
                            hunt_res = ai_engine.generate_content(hunt_prompt).text
                            st.markdown(f'<div class="special-box"><h4 style="color:#88c0d0;">🎯 {target_sub} 會考重點補強建議</h4>{hunt_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

                st.divider()

                # 報表預覽
                st.subheader("📊 歷程診斷報告預覽")
                if st.checkbox("開啟家長端診斷報告 (正式格式)"):
                    r_text = f"## 🎓 {sel_stu} 學生學習診斷報告 (會考專用)\n"
                    r_text += "---\n"
                    for s in stu_df['學科類別'].unique():
                        r_text += f"### 【{s}：應試弱點分析】\n"
                        for _, r in stu_df[stu_df['學科類別'] == s].head(3).iterrows():
                            r_text += f"- **{r['考試範圍']}**：成績 {r['小考成績']}\n  *專家策略：{r['AI診斷與建議']}*\n\n"
                    st.markdown('<div class="report-box">' + r_text + '</div>', unsafe_allow_html=True)

                # 詳細歷史清單
                for s in stu_df['學科類別'].unique():
                    st.markdown(f'<div class="subject-header">📚 {s} 歷史診斷</div>', unsafe_allow_html=True)
                    for _, row in stu_df[stu_df['學科類別'] == s].iterrows():
                        c_html = f'<div class="range-card"><b>🎯 範圍：{row["考試範圍"]}</b> ({row["小考成績"]}分)<br><p style="margin-top:10px; font-size:0.95rem;">{row["AI診斷與建議"]}</p></div>'
                        st.markdown(c_html, unsafe_allow_html=True)
        else:
            st.info("💡 目前資料庫尚無數據。")
