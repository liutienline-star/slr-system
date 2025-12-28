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

# 設定頁面配置
st.set_page_config(page_title="學思戰術指揮系統", layout="wide", page_icon="📈")

# --- 2. 視覺風格與寬度優化 (CSS) ---
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
    .special-box { 
        background-color: #2e3440; padding: 30px; border-radius: 15px; border: 1px solid #88c0d0; 
        margin-bottom: 20px; box-shadow: 0px 8px 16px rgba(0,0,0,0.4); line-height: 1.8;
    }
    .warning-note { background-color: #444b5a; padding: 15px; border-radius: 8px; font-size: 0.85rem; color: #ebcb8b; border: 1px dashed #ebcb8b; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 3. 初始化服務與連線 ---
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
        st.error(f"系統初始化異常，請檢查祕鑰設定：{e}")
        return None, None

# --- 4. 登入驗證機制 ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, col_m, _ = st.columns([0.5, 1, 0.5])
    with col_m:
        st.markdown("<h2 style='text-align:center; color:#88c0d0;'>戰情系統登入</h2>", unsafe_allow_html=True)
        pwd = st.text_input("輸入授權碼：", type="password")
        if pwd == AUTH_CODE:
            st.session_state.authenticated = True
            st.rerun()
        elif pwd:
            st.error("授權碼錯誤")
    st.stop()

# --- 5. 主程式邏輯 ---
st.markdown('<h1 class="main-header">🏫 「學思戰情」深度段考診斷系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view, tab_analysis = st.tabs(["📝 影像深度診斷", "🔍 歷史數據庫", "📊 戰術分析室"])

# --- Tab 1: 影像診斷錄入區 ---
with tab_entry:
    st.markdown('<div class="warning-note">💡 專家提示：本分析具備高度學術精確性。嚴禁編造頁碼，請針對列出之「知識點」進行精準指導。</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        with col2: subject = st.selectbox("📚 學科類別", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        
        exam_range = st.text_input("🎯 段考範圍", placeholder="例：第一次段考範圍")
        score = st.number_input("💯 測驗成績", 0, 100, 60)
        uploaded_file = st.file_uploader("📷 上傳考卷影像 (執行深度診斷)", type=["jpg", "jpeg", "png"])
        
        if "v_obs" not in st.session_state:
            st.session_state.v_obs = ""
        
        if uploaded_file and st.button("🔍 執行深度事實診讀"):
            with st.spinner("影像事實深度分析中..."):
                img = Image.open(uploaded_file)
                v_res = ai_engine.generate_content([
                    f"""你是一位教育診斷專家。請對考卷影像產出以下深度事實報告：
                    1. 【錯題明細】：條列錯題題號與正確答案。
                    2. 【知識點定位】：明確標註每道錯題考驗的具體學術觀念。
                    3. 【錯誤本質分析】：詳述錯誤原因(如:公式誤用、觀念混淆、題意理解偏差)。
                    4. 【修正行動指令】：提供具指導意義的動作(如:重新演練某原理題目)。
                    要求：敘述詳盡、具備指導價值，但禁止美化、禁止情緒字眼、嚴禁編造頁碼。""", 
                    img
                ])
                st.session_state.v_obs = v_res.text
        
        obs = st.text_area("🔍 深度錯誤分析紀錄", value=st.session_state.v_obs, height=450)

        if st.button("🚀 同步數據至雲端戰情庫"):
            if stu_id and obs:
                with st.spinner("同步中..."):
                    diag_prompt = f"針對錯誤事實：{obs}。請產出 200 字內補強指導。要求：詳盡、去美化、嚴禁頁碼、提供具體複習動作。"
                    diag = ai_engine.generate_content(diag_prompt).text
                    hub_sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), stu_id, subject, exam_range, score, obs, diag])
                    st.success("✅ 數據已歸檔！")
                    st.session_state.v_obs = ""
            else:
                st.warning("請填寫學生代號與分析內容。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2: 歷史數據庫瀏覽 ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 刷新全校紀錄庫"):
            st.rerun()
        raw_df = pd.DataFrame(hub_sheet.get_all_records())
        if not raw_df.empty:
            st.dataframe(raw_df.sort_values(by="日期時間", ascending=False), use_container_width=True)
        else:
            st.info("目前尚無存檔紀錄。")

# --- Tab 3: 戰術分析室 (數據分析與交叉診斷) ---
with tab_analysis:
    if hub_sheet:
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df = pd.DataFrame(raw_data)
            df['成績'] = pd.to_numeric(df['測驗成績'], errors='coerce').fillna(0)
            
            stu_list = df['學生代號'].unique()
            sel_stu = st.selectbox("🎯 選擇受測學生代號", stu_list, key="analysis_stu_sel")
            stu_df = df[df['學生代號'] == sel_stu].sort_values('日期時間', ascending=False)
            
            if not stu_df.empty:
                st.subheader("📊 學期分科數據分布")
                avg_scores = stu_df.groupby('學科類別')['成績'].mean().reset_index()
                fig_radar = px.line_polar(avg_scores, r='成績', theta='學科類別', line_close=True, range_r=[0,100])
                fig_radar.update_traces(fill='toself', line_color='#88c0d0')
                fig_radar.update_layout(template="plotly_dark", margin=dict(l=50, r=50, t=20, b=20))
                st.plotly_chart(fig_radar, use_container_width=True)
                
                st.divider()

                st.markdown(f"### ⚡ {sel_stu} 段考戰術診斷報告")
                analysis_modes = ["📡 跨科行為共性診斷"] + sorted(list(stu_df['學科類別'].unique()))
                sel_mode = st.radio("請選擇分析維度：", analysis_modes, horizontal=True)

                if sel_mode == "📡 跨科行為共性診斷":
                    if st.button(f"執行 {sel_stu} 跨科深度診斷"):
                        with st.spinner("數據交叉比對中..."):
                            cross_context = "\n".join([f"{r['學科類別']}分析：{r['AI診斷與建議']}" for _, r in stu_df.head(10).iterrows()])
                            dispatch_prompt = f"分析多科紀錄：{cross_context}。請詳述學生的底層邏輯漏洞與跨科共性問題。去美化、禁止頁碼、詳盡敘述。"
                            dispatch_res = ai_engine.generate_content(dispatch_prompt).text
                            st.markdown(f'<div class="special-box">{dispatch_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
                else:
                    target_sub = sel_mode
                    if st.button(f"生成 {target_sub} 詳盡補強指引"):
                        with st.spinner(f"分析 {target_sub} 趨勢..."):
                            history_context = "\n".join([f"範圍:{r['考試範圍']}, 紀錄:{r['導師觀察摘要']}" for _, r in stu_df[stu_df['學科類別'] == target_sub].head(5).iterrows()])
                            hunt_prompt = f"針對 {target_sub} 紀錄：{history_context}。生成詳盡複習建議：1.頻發弱點、2.修正動作、3.考前事實。去美化、禁止頁碼。"
                            hunt_res = ai_engine.generate_content(hunt_prompt).text
                            st.markdown(f'<div class="special-box">{hunt_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

                st.divider()
                # 歷史明細明細清單
                for s in stu_df['學科類別'].unique():
                    st.markdown(f'<div class="subject-header">📚 {s} 歷史診斷明細</div>', unsafe_allow_html=True)
                    for _, row in stu_df[stu_df['學科類別'] == s].iterrows():
                        st.markdown(f"""
                        <div class="range-card">
                            <b>🎯 範圍：{row["考試範圍"]}</b> ({row["測驗成績"]}分)<br>
                            <p style="margin-top:10px;"><b>事實分析紀錄：</b><br>{row["導師觀察摘要"].replace("\n", "<br>")}</p>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("💡 目前資料庫尚無數據可供分析。")

# --- END OF FILE ---
