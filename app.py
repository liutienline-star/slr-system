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

# --- 2. 視覺風格與寬度優化 ---
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
        border: 1px solid #88c0d0 !important; width: 100%; border-radius: 10px; font-weight: 700; height: 45px;
    }
    .input-card { background-color: #2e3440; padding: 25px; border-radius: 15px; border: 1px solid #4c566a; margin-bottom: 20px; }
    .subject-header { color: #88c0d0; border-bottom: 2px solid #88c0d0; padding-bottom: 8px; margin-top: 30px; margin-bottom: 15px; font-size: 1.4rem; font-weight: bold; }
    .range-card { background-color: #3b4252; padding: 18px; border-radius: 12px; border-left: 5px solid #81a1c1; margin-bottom: 15px; }
    .special-box { 
        background-color: #2e3440; padding: 30px; border-radius: 15px; border: 1px solid #88c0d0; 
        margin-bottom: 20px; box-shadow: 0px 8px 16px rgba(0,0,0,0.4); line-height: 1.8;
    }
    [data-testid="stWidgetLabel"] p { color: #88c0d0 !important; font-weight: 600; font-size: 1rem; }
    .warning-note { background-color: #444b5a; padding: 15px; border-radius: 8px; font-size: 0.85rem; color: #ebcb8b; border: 1px dashed #ebcb8b; margin-bottom: 20px; }
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
        st.error(f"初始化異常：{e}")
        return None, None

# --- 4. 驗證機制 ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    _, col_m, _ = st.columns([0.5, 1, 0.5])
    with col_m:
        st.markdown("<h2 style='text-align:center; color:#88c0d0;'>戰情系統登入</h2>", unsafe_allow_html=True)
        pwd = st.text_input("輸入授權碼：", type="password")
        if pwd == AUTH_CODE:
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

st.markdown('<h1 class="main-header">🏫 「學思戰情」學期段考調度系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view, tab_analysis = st.tabs(["📝 影像診斷錄入", "🔍 歷史數據庫", "📊 戰術分析室"])

# --- Tab 1: 影像診斷錄入 ---
with tab_entry:
    st.markdown('<div class="warning-note">⚠️ 系統提示：所有 AI 建議皆基於學術事實。建議中提及之章節名稱為觀念索引，請依據校內實際教材版本進行對照。</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        with col2: subject = st.selectbox("📚 學科類別", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        
        exam_range = st.text_input("🎯 段考範圍", placeholder="例：第一次段考")
        score = st.number_input("💯 測驗成績", 0, 100, 60)
        uploaded_file = st.file_uploader("📷 上傳考卷照片", type=["jpg", "jpeg", "png"])
        
        if "v_obs" not in st.session_state: st.session_state.v_obs = ""
        
        if uploaded_file and st.button("🔍 執行事實導向影像診讀"):
            with st.spinner("AI 事實掃描中..."):
                img = Image.open(uploaded_file)
                v_res = ai_engine.generate_content([
                    f"""你是一位嚴謹的教育診斷專家。請分析這張{subject}考卷：
                    1. 條列具體錯題題號。
                    2. 標註對應的【知識點名稱】(嚴禁編造課本頁碼)。
                    3. 判讀錯誤本質(運算/觀念/理解)。
                    僅提供事實清單，嚴禁美化或情緒鼓勵。""", 
                    img
                ])
                st.session_state.v_obs = v_res.text
        
        obs = st.text_area("🔍 錯誤事實摘要", value=st.session_state.v_obs, height=400)

        if st.button("🚀 生成數據診斷並存檔"):
            if stu_id and obs:
                with st.spinner("數據同步中..."):
                    diag_prompt = f"""
                    你是段考顧問。針對事實紀錄：{obs}。
                    請給出 150 字內補強策略。
                    要求：
                    1. 建議必須精確對應上述知識點。
                    2. 提供可執行的物理動作。
                    3. 嚴禁編造具體課本頁碼。
                    """
                    diag = ai_engine.generate_content(diag_prompt).text
                    hub_sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), stu_id, subject, exam_range, score, obs, diag])
                    st.success("✅ 數據存檔成功！")
                    st.session_state.v_obs = ""
            else: st.warning("請填寫學生代號。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2: 歷史數據庫 ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 刷新紀錄"): st.rerun()
        raw_df = pd.DataFrame(hub_sheet.get_all_records())
        if not raw_df.empty:
            st.dataframe(raw_df.sort_values(by="日期時間", ascending=False), use_container_width=True)

# --- Tab 3: 戰術分析室 ---
with tab_analysis:
    if hub_sheet:
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df = pd.DataFrame(raw_data)
            df['成績'] = pd.to_numeric(df['測驗成績'], errors='coerce').fillna(0)
            
            stu_list = df['學生代號'].unique()
            sel_stu = st.selectbox("🎯 選擇分析代號", stu_list)
            stu_df = df[df['學生代號'] == sel_stu].sort_values('日期時間', ascending=False)
            
            if not stu_df.empty:
                st.subheader("📊 學期分科數據分布")
                avg_scores = stu_df.groupby('學科類別')['成績'].mean().reset_index()
                fig_radar = px.line_polar(avg_scores, r='成績', theta='學科類別', line_close=True, range_r=[0,100])
                fig_radar.update_traces(fill='toself', line_color='#88c0d0')
                fig_radar.update_layout(template="plotly_dark")
                st.plotly_chart(fig_radar, use_container_width=True)
                
                st.divider()

                st.markdown(f"### ⚡ {sel_stu} 段考戰術診斷")
                analysis_modes = ["📡 跨科學習行為分析"] + sorted(list(stu_df['學科類別'].unique()))
                sel_mode = st.radio("選擇維度：", analysis_modes, horizontal=True)

                if sel_mode == "📡 跨科學習行為分析":
                    if st.button(f"執行 {sel_stu} 跨科共性分析"):
                        with st.spinner("數據交叉比對中..."):
                            cross_context = "\n".join([f"{r['學科類別']}：{r['AI診斷與建議']}" for _, r in stu_df.head(10).iterrows()])
                            dispatch_prompt = f"""
                            分析以下錯誤模式：{cross_context}
                            1. 指出跨科共同錯誤習慣。
                            2. 優先解決的兩項弱點。
                            (嚴禁編造頁碼，事實導向)
                            """
                            dispatch_res = ai_engine.generate_content(dispatch_prompt).text
                            st.markdown(f'<div class="special-box" style="border-left: 8px solid #bf616a;">{dispatch_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

                else:
                    target_sub = sel_mode
                    if st.button(f"生成 {target_sub} 精準補強建議"):
                        with st.spinner(f"分析 {target_sub} 趨勢..."):
                            history_context = "\n".join([f"範圍:{r['考試範圍']}, 紀錄:{r['導師觀察摘要']}" for _, r in stu_df[stu_df['學科類別'] == target_sub].head(5).iterrows()])
                            hunt_prompt = f"""
                            針對 {target_sub} 的歷史紀錄：{history_context}
                            請生成建議：
                            1. 核心陷阱辨識。
                            2. 動作導向複習建議(禁止頁碼，指引至章節標題)。
                            3. 段考考前必讀觀念。
                            """
                            hunt_res = ai_engine.generate_content(hunt_prompt).text
                            st.markdown(f'<div class="special-box">{hunt_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
