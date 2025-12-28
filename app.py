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

# --- 2. 視覺風格 (深色戰情室、垂直排版、家長報表風格) ---
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

# --- 3. 初始化 AI 與 Google Sheets 服務 ---
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
        st.error(f"連線失敗：{e}")
        return None, None

# --- 4. 登入機制 ---
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

# --- Tab 1: 影像診斷與數據錄入 ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        subject_cat = st.selectbox("📚 學科類別", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        exam_range = st.text_input("🎯 考試範圍", placeholder="例：L1-L3")
        score = st.number_input("💯 小考成績", 0, 100, 60)
        
        st.markdown("---")
        st.markdown("📷 **考卷/講義影像辨識 (手機拍照)**")
        uploaded_file = st.file_uploader("點擊拍照或上傳學生照片", type=["jpg", "jpeg", "png"])
        
        if "ai_vision_result" not in st.session_state: st.session_state.ai_vision_result = ""

        if uploaded_file is not None:
            if st.button("🔍 執行 AI 影像診斷"):
                with st.spinner("Gemini 正在分析照片中的錯誤規律..."):
                    img = Image.open(uploaded_file)
                    vision_prompt = f"你是一位專業導師。請分析這張{subject_cat}考卷的照片（範圍：{exam_range}）。請辨識出學生的錯題內容，並判斷錯誤原因（如：觀念混淆、運算粗心或未讀懂題目），給予精簡的摘要。"
                    response = ai_engine.generate_content([vision_prompt, img])
                    st.session_state.ai_vision_result = response.text
                    st.rerun()

        obs_val = st.text_area("🔍 導師觀察摘要", value=st.session_state.ai_vision_result, height=150, placeholder="AI 辨識結果將出現在此，也可手動修改...")

        if st.button("🚀 生成最終診斷並存檔"):
            if stu_id and obs_val and exam_range:
                with st.spinner("生成複習建議中..."):
                    diag_prompt = f"根據學生{stu_id}在{subject_cat}({exam_range})的分數{score}以及細節：{obs_val}。請提供150字內具體且可執行的複習策略。"
                    diagnosis = ai_engine.generate_content(diag_prompt).text
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                    # 嚴格對應欄位：日期時間, 學生代號, 學科類別, 考試範圍, 小考成績, 導師觀察摘要, AI診斷與建議
                    hub_sheet.append_row([timestamp, stu_id, subject_cat, exam_range, score, obs_val, diagnosis])
                    st.success("✅ 數據與影像診斷已同步至雲端！")
                    st.session_state.ai_vision_result = ""
            else: st.warning("請確保填寫代號、範圍與觀察摘要。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2: 歷史數據查看 ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 刷新雲端數據"): st.rerun()
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df_history = pd.DataFrame(raw_data)
            st.dataframe(df_history.sort_values(by="日期時間", ascending=False), use_container_width=True)

# --- Tab 3: 戰術分析室 (整合獵殺計畫與資源調度) ---
with tab_analysis:
    if hub_sheet:
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df = pd.DataFrame(raw_data)
            df['小考成績'] = pd.to_numeric(df['小考成績'], errors='coerce').fillna(0)
            
            # 全班雷達圖：平均學習力
            st.subheader("🕸️ 全班學習力平均分布")
            avg_scores = df.groupby('學科類別')['小考成績'].mean().reset_index()
            fig_radar = px.line_polar(avg_scores, r='小考成績', theta='學科類別', line_close=True, range_r=[0,100])
            fig_radar.update_traces(fill='toself', line_color='#88c0d0')
            fig_radar.update_layout(template="plotly_dark")
            st.plotly_chart(fig_radar, use_container_width=True)
            st.divider()

            # 個人深度診斷
            stu_list = df['學生代號'].unique()
            sel_stu = st.selectbox("👤 選擇要分析的學生代號", stu_list)
            stu_df = df[df['學生代號'] == sel_stu].sort_values('日期時間', ascending=False)
            
            # 功能二：考前精準獵殺計畫
            st.markdown("### 🏹 考前精準獵殺計畫")
            if st.button(f"生成 {sel_stu} 的 3 天複習清單"):
                with st.spinner("分析最近錯誤紀錄中..."):
                    recent_errors = "\n".join([f"科目:{r['學科類別']}, 範圍:{r['考試範圍']}, 觀察:{r['導師觀察摘要']}" for _, r in stu_df.head(5).iterrows()])
                    hunt_prompt = f"你是一位學習教練。根據這位學生最近的錯誤點：\n{recent_errors}\n請生成一個 3 天的『精準補強時程表』，告訴他每天要針對哪些題型進行特訓，語氣戰鬥且有效率。"
                    hunt_res = ai_engine.generate_content(hunt_prompt).text
                    st.markdown(f'<div class="special-box"><h4 style="color:#88c0d0;">🎯 個人化 3 天獵殺清單</h4>{hunt_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            
            st.divider()

            # 功能三：跨科調度診斷
            st.markdown("### 📡 跨科學習資源調度模式")
            if st.button(f"分析 {sel_stu} 的跨科瓶頸核心"):
                with st.spinner("AI 正在尋找學習底層關聯性..."):
                    cross_context = "\n".join([f"{r['學科類別']}：{r['AI診斷與建議']}" for _, r in stu_df.head(8).iterrows()])
                    dispatch_prompt = f"分析以下多科診斷紀錄：\n{cross_context}\n請找出該生底層的共同問題（例如：長文本閱讀耐力不足、邏輯推演斷層、或時間分配失衡），提供導師跨科調度的建議，200字內。"
                    dispatch_res = ai_engine.generate_content(dispatch_prompt).text
                    st.markdown(f'<div class="special-box" style="border-left: 8px solid #bf616a;"><h4 style="color:#bf616a;">📡 導師跨科戰略洞察</h4>{dispatch_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

            st.divider()

            # 家長報表與詳細歷程
            st.subheader("📊 精確學科報表篩選")
            sub_options = ["全部學科"] + list(stu_df['學科類別'].unique())
            sel_sub = st.selectbox("1. 選擇學科", sub_options)
            
            final_df = stu_df if sel_sub == "全部學科" else stu_df[stu_df['學科類別'] == sel_sub]
            
            if st.checkbox("開啟預覽家長診斷報告 (可列印)"):
                r_text = f"## 🎓 {sel_stu} 學生學習診斷報告\n"
                for s in final_df['學科類別'].unique():
                    r_text += f"### 【{s}】\n"
                    for _, r in final_df[final_df['學科類別'] == s].iterrows():
                        r_text += f"- **考試範圍：{r['考試範圍']}** ({r['小考成績']}分)\n  *複習策略：{r['AI診斷與建議']}*\n\n"
                st.markdown('<div class="report-box">', unsafe_allow_html=True)
                st.markdown(r_text)
                st.markdown('</div>', unsafe_allow_html=True)

            # 詳細歷程卡片
            for s in final_df['學科類別'].unique():
                st.markdown(f'<div class="subject-header">📚 {s} 歷史紀錄</div>', unsafe_allow_html=True)
                for _, row in final_df[final_df['學科類別'] == s].iterrows():
                    c_html = f'<div class="range-card"><b>🎯 範圍：{row["考試範圍"]}</b> ({row["小考成績"]}分)<br><p style="margin-top:10px;">{row["AI診斷與建議"]}</p></div>'
                    st.markdown(c_html, unsafe_allow_html=True)
