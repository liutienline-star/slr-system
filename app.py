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

# --- 2. 視覺風格 (深色戰術介面 + 優化閱讀寬度) ---
st.markdown("""
<style>
    /* 限制最大寬度：確保長文本在寬螢幕上不會過度分散，提升閱讀正確性 */
    .main .block-container {
        max-width: 1000px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    .stApp { background-color: #1a1c23; color: #e5e9f0; }
    .main-header { text-align: center; color: #88c0d0; font-weight: 800; font-size: 2.2rem; margin-bottom: 1.5rem; }
    
    /* 按鈕樣式：強化點擊感 */
    .stButton>button { 
        background-color: #3b4252 !important; 
        color: #ffffff !important; 
        border: 1px solid #88c0d0 !important; 
        width: 100%; 
        border-radius: 10px; 
        font-weight: 700; 
        height: 45px;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #4c566a !important; border-color: #8fbcbb !important; }

    /* 各類資訊卡片樣式 */
    .input-card { background-color: #2e3440; padding: 25px; border-radius: 15px; border: 1px solid #4c566a; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .subject-header { color: #88c0d0; border-bottom: 2px solid #88c0d0; padding-bottom: 8px; margin-top: 30px; margin-bottom: 15px; font-size: 1.4rem; font-weight: bold; }
    .range-card { background-color: #3b4252; padding: 18px; border-radius: 12px; border-left: 5px solid #81a1c1; margin-bottom: 15px; }
    
    /* 診斷建議專用區塊 (事實導向) */
    .special-box { 
        background-color: #2e3440; 
        padding: 30px; 
        border-radius: 15px; 
        border: 1px solid #88c0d0; 
        margin-bottom: 20px; 
        box-shadow: 0px 8px 16px rgba(0,0,0,0.4);
        line-height: 1.8;
    }
    
    /* 報表風格區塊 (模擬實體文件) */
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
    
    /* 輸入欄位標籤 */
    [data-testid="stWidgetLabel"] p { color: #88c0d0 !important; font-weight: 600; font-size: 1rem; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 3. 初始化服務 (Gemini 與 Google Sheets) ---
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
        st.error(f"服務初始化失敗：{e}")
        return None, None

# --- 4. 驗證機制 ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    _, col_m, _ = st.columns([0.5, 1, 0.5])
    with col_m:
        st.markdown("<h2 style='text-align:center; color:#88c0d0;'>導師戰情系統登入</h2>", unsafe_allow_html=True)
        pwd = st.text_input("輸入授權碼：", type="password")
        if pwd == AUTH_CODE:
            st.session_state.authenticated = True
            st.rerun()
        elif pwd:
            st.error("授權碼不正確")
    st.stop()

# --- 主程式介面 ---
st.markdown('<h1 class="main-header">🏫 「學思戰情」學期段考調度系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view, tab_analysis = st.tabs(["📝 影像診斷錄入", "🔍 歷史數據庫", "📊 戰術分析室"])

# --- Tab 1: 影像診斷錄入 (證據導向) ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        with col2: subject = st.selectbox("📚 學科類別", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        
        exam_range = st.text_input("🎯 段考/週考範圍", placeholder="例：第一次段考 / L1-L3")
        score = st.number_input("💯 測驗成績", 0, 100, 60)
        uploaded_file = st.file_uploader("📷 上傳考卷照片 (執行事實弱點掃描)", type=["jpg", "jpeg", "png"])
        
        if "v_obs" not in st.session_state: st.session_state.v_obs = ""
        
        if uploaded_file and st.button("🔍 執行事實導向影像診讀"):
            with st.spinner("AI 專家分析中..."):
                img = Image.open(uploaded_file)
                # 提示詞強化：要求具備可檢核的正確性，排除美化
                v_res = ai_engine.generate_content([
                    f"""你是一位嚴謹的教育診斷專家。請精確分析這張{subject}({exam_range})考卷：
                    1. 條列具體錯題題號。
                    2. 針對錯題標註其對應的知識點/單元。
                    3. 判讀錯誤本質：是屬於「基礎運算失誤」、「知識點記憶模糊」還是「長難句閱讀理解偏差」。
                    嚴禁使用鼓勵性修辭，請產出可供老師檢視的事實清單。""", 
                    img
                ])
                st.session_state.v_obs = v_res.text
        
        # 觀察摘要區：校長要求的高度 400px
        obs = st.text_area("🔍 錯誤事實與觀察紀錄 (AI 建議可在此細修)", value=st.session_state.v_obs, height=400)

        if st.button("🚀 生成數據診斷並存檔"):
            if stu_id and obs and exam_range:
                with st.spinner("戰術數據同步中..."):
                    # 補強建議必須基於錄入的事實
                    diag_prompt = f"""
                    你是學科段考專家。根據以下錄入的錯誤事實：{obs}。
                    請給出 150 字內的補強策略建議。
                    要求：
                    1. 建議必須精確對應到錄入的知識點錯誤。
                    2. 不要美化，要提供具體且具備正確性的執行動作（如：重新演算某單元課本習題）。
                    """
                    diag = ai_engine.generate_content(diag_prompt).text
                    hub_sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), stu_id, subject, exam_range, score, obs, diag])
                    st.success("✅ 數據已同步至雲端戰情庫！")
                    st.session_state.v_obs = ""
            else: st.warning("請填寫代號與觀察內容。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2: 歷史數據庫 ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 刷新數據庫紀錄"): st.rerun()
        raw_df = pd.DataFrame(hub_sheet.get_all_records())
        if not raw_df.empty:
            # 排序：最新日期在前
            st.dataframe(raw_df.sort_values(by="日期時間", ascending=False), use_container_width=True)

# --- Tab 3: 戰術分析室 (交叉比對與重點提示) ---
with tab_analysis:
    if hub_sheet:
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df = pd.DataFrame(raw_data)
            # 確保成績為數字格式
            df['成績數字'] = pd.to_numeric(df['小考成績'], errors='coerce').fillna(0)
            
            stu_list = df['學生代號'].unique()
            sel_stu = st.selectbox("🎯 選擇受測學生代號", stu_list)
            stu_df = df[df['學生代號'] == sel_stu].sort_values('日期時間', ascending=False)
            
            if not stu_df.empty:
                # 可視化分佈
                st.subheader("📊 學期分科均衡度事實分析")
                avg_scores = stu_df.groupby('學科類別')['成績數字'].mean().reset_index()
                fig_radar = px.line_polar(avg_scores, r='成績數字', theta='學科類別', line_close=True, range_r=[0,100])
                fig_radar.update_traces(fill='toself', line_color='#88c0d0')
                fig_radar.update_layout(template="plotly_dark", margin=dict(l=50, r=50, t=20, b=20))
                st.plotly_chart(fig_radar, use_container_width=True)
                
                st.divider()

                st.markdown(f"### ⚡ {sel_stu} 段考專家戰術調度")
                analysis_modes = ["📡 跨科學習障礙診斷"] + sorted(list(stu_df['學科類別'].unique()))
                sel_mode = st.radio("請選擇分析維度：", analysis_modes, horizontal=True)

                st.markdown("---")

                if sel_mode == "📡 跨科學習障礙診斷":
                    st.info("💡 系統正分析跨科紀錄，尋找底層邏輯漏洞（如：閱讀跳行、圖表誤讀）。")
                    if st.button(f"執行 {sel_stu} 跨科專家分析"):
                        with st.spinner("數據交叉比對中..."):
                            # 彙整最近 10 筆 AI 診斷
                            cross_context = "\n".join([f"{r['學科類別']}：{r['AI診斷與建議']}" for _, r in stu_df.head(10).iterrows()])
                            dispatch_prompt = f"""
                            分析以下學生的多科錯誤模式事實：
                            {cross_context}
                            
                            請排除所有修辭，直接指出：
                            1. 學生在不同學科間呈現的「共同錯誤習慣」。
                            2. 段考衝刺階段應優先解決的兩個核心弱點。
                            3. 具備正確性的具體修正動作。
                            (250字內)
                            """
                            dispatch_res = ai_engine.generate_content(dispatch_prompt).text
                            st.markdown(f'<div class="special-box" style="border-left: 8px solid #bf616a;"><h4 style="color:#bf616a;">📡 專家觀察：跨科底層弱點</h4>{dispatch_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

                else:
                    target_sub = sel_mode
                    sub_specific_df = stu_df[stu_df['學科類別'] == target_sub]
                    st.info(f"💡 針對 {target_sub} 的錯誤事實，生成具體段考補強清單。")
                    
                    if st.button(f"生成 {target_sub} 精準補強建議"):
                        with st.spinner(f"正在分析 {target_sub} 關鍵錯誤趨勢..."):
                            history_context = "\n".join([f"範圍:{r['考試範圍']}, 紀錄:{r['導師觀察摘要']}" for _, r in sub_specific_df.head(5).iterrows()])
                            hunt_prompt = f"""
                            你是一位擅長幫助學生在段考奪取高分的專業家教。
                            針對學生在 {target_sub} 的歷史錯誤紀錄：
                            {history_context}
                            
                            請生成具備正確性的『段考重點補強建議』：
                            1. 陷阱辨識：根據該生紀錄，列出最容易再次失分的 3 個特定觀念。
                            2. 具體複習建議：不要描述性語言，請提供可檢核的行為（如：複習課本 P35-P40 範例）。
                            3. 段考考前必看：提供三個最具搶分效果的觀念點。
                            """
                            hunt_res = ai_engine.generate_content(hunt_prompt).text
                            st.markdown(f'<div class="special-box"><h4 style="color:#88c0d0;">🎯 {target_sub} 段考事實補強建議</h4>{hunt_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

                st.divider()

                # 詳細紀錄細節
                st.subheader("📊 歷程診斷事實細節")
                if st.checkbox("開啟家長端段考分析報告"):
                    r_text = f"## 🎓 {sel_stu} 學期段考診斷報告\n"
                    r_text += "---\n"
                    for s in stu_df['學科類別'].unique():
                        r_text += f"### 【{s}】\n"
                        for _, r in stu_df[stu_df['學科類別'] == s].head(3).iterrows():
                            r_text += f"- **範圍：{r['考試範圍']}** (成績：{r['小考成績']})\n  *專家策略：{r['AI診斷與建議']}*\n\n"
                    st.markdown('<div class="report-box">' + r_text + '</div>', unsafe_allow_html=True)

                # 以學科分類展開所有紀錄
                for s in stu_df['學科類別'].unique():
                    st.markdown(f'<div class="subject-header">📚 {s} 歷史數據明細</div>', unsafe_allow_html=True)
                    for _, row in stu_df[stu_df['學科類別'] == s].iterrows():
                        c_html = f'<div class="range-card"><b>🎯 範圍：{row["考試範圍"]}</b> ({row["小考成績"]}分)<br><p style="margin-top:10px; font-size:0.95rem;"><b>事實紀錄：</b>{row["AI診斷與建議"]}</p></div>'
                        st.markdown(c_html, unsafe_allow_html=True)
        else:
            st.info("💡 目前資料庫尚無數據。")
