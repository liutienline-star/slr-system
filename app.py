import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import plotly.express as px
from PIL import Image

# --- 1. 核心參數 ---
AUTH_CODE = "641101"  
HUB_NAME = "Student_Learning_Hub" 
SHEET_TAB = "Learning_Data" 
MODEL_NAME = "models/gemini-2.0-flash" 

st.set_page_config(page_title="學思戰情系統", layout="wide", page_icon="📈")

# --- 2. 視覺風格 (徹底排除標籤干擾) ---
st.markdown("""
<style>
    .stApp { background-color: #1a1c23; color: #e5e9f0; }
    .main-header { text-align: center; color: #88c0d0; font-weight: 800; font-size: 2.2rem; margin-bottom: 1rem; }
    .stButton>button { background-color: #3b4252 !important; color: #ffffff !important; border: 1px solid #88c0d0 !important; width: 100%; border-radius: 8px; font-weight: 700; height: 45px; }
    .input-card { background-color: #2e3440; padding: 20px; border-radius: 12px; border: 1px solid #4c566a; margin-bottom: 20px; }
    .subject-header { color: #88c0d0; border-bottom: 2px solid #88c0d0; padding-bottom: 5px; margin-top: 25px; margin-bottom: 15px; font-size: 1.5rem; font-weight: bold; }
    .range-card { background-color: #2e3440; padding: 20px; border-radius: 12px; border-left: 5px solid #81a1c1; margin-bottom: 15px; }
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

st.markdown('<h1 class="main-header">🏫 「學思戰情」智慧影像診斷系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view, tab_analysis = st.tabs(["📝 影像診斷錄入", "🔍 歷史數據", "📊 精確戰情分析"])

# --- Tab 1: 影像診斷與錄入 ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        subject = st.selectbox("📚 學科", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        exam_range = st.text_input("🎯 考試範圍", placeholder="例：L1-L3")
        score = st.number_input("💯 分數", 0, 100, 60)
        
        st.markdown("---")
        st.markdown("📷 **考卷/講義影像辨識**")
        uploaded_file = st.file_uploader("點擊或拖拽考卷照片至此", type=["jpg", "jpeg", "png"])
        
        # 使用 Session State 暫存 AI 辨識內容
        if "obs_text" not in st.session_state: st.session_state.obs_text = ""

        if uploaded_file is not None:
            if st.button("🔍 執行 AI 錯題掃描"):
                with st.spinner("Gemini 正在分析照片中的錯誤..."):
                    img = Image.open(uploaded_file)
                    v_prompt = f"你是一位專業導師。請分析這張照片（科目：{subject}，範圍：{exam_range}）。請找出學生的錯題，判斷其錯誤原因（如：運算錯誤、觀念混淆、或是未讀懂題目），並給予精簡的摘要。"
                    res = ai_engine.generate_content([v_prompt, img])
                    st.session_state.obs_text = res.text
        
        obs = st.text_area("🔍 觀察摘要 (AI 自動辨識或手動修正)", value=st.session_state.obs_text, height=150)

        if st.button("🚀 生成最終診斷並存檔"):
            if stu_id and obs and exam_range:
                with st.spinner("正在生成針對性複習計畫..."):
                    f_prompt = f"根據學生{stu_id}在{subject}({exam_range})的表現與錯誤細節：{obs}。請提供150字內、針對該範圍的具體複習行動建議。"
                    diag = ai_engine.generate_content(f_prompt).text
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                    hub_sheet.append_row([timestamp, stu_id, subject, exam_range, score, obs, diag])
                    st.success("✅ 影像分析與診斷已成功同步至 HUB！")
                    st.session_state.obs_text = "" # 清空暫存
            else: st.warning("請填寫學生代號並確保有觀察摘要。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2: 歷史數據 ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 刷新雲端數據"): st.rerun()
        df = pd.DataFrame(hub_sheet.get_all_records())
        st.dataframe(df.sort_values(by="日期時間", ascending=False), use_container_width=True)

# --- Tab 3: 精確戰情分析室 (含報表篩選) ---
with tab_analysis:
    if hub_sheet:
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df = pd.DataFrame(raw_data)
            df['小考成績'] = pd.to_numeric(df['小考成績'], errors='coerce').fillna(0)
            
            # 全班雷達圖
            st.subheader("🕸️ 全班學習力平均分布")
            avg_scores = df.groupby('學科類別')['小考成績'].mean().reset_index()
            fig_radar = px.line_polar(avg_scores, r='小考成績', theta='學科類別', line_close=True, range_r=[0,100])
            fig_radar.update_traces(fill='toself', line_color='#88c0d0')
            fig_radar.update_layout(template="plotly_dark")
            st.plotly_chart(fig_radar, use_container_width=True)
            st.divider()

            # 精確篩選區
            st.subheader("👤 個人學習狀態追蹤")
            stu_list = df['學生代號'].unique()
            sel_stu = st.selectbox("1. 選擇學生代號", stu_list)
            stu_df = df[df['學生代號'] == sel_stu].sort_values('日期時間', ascending=True)
            
            sub_options = ["全部學科"] + list(stu_df['學科類別'].unique())
            sel_sub = st.selectbox("2. 選擇學科", sub_options)
            
            if sel_sub == "全部學科":
                filtered_df = stu_df
                range_opts = ["全部範圍"]
            else:
                filtered_df = stu_df[stu_df['學科類別'] == sel_sub]
                range_opts = ["全部範圍"] + list(filtered_df['考試範圍'].unique())
            
            sel_range = st.selectbox("3. 選擇考試範圍", range_opts)
            final_df = filtered_df if sel_range == "全部範圍" else filtered_df[filtered_df['考試範圍'] == sel_range]

            # 趨勢圖
            fig_line = px.line(final_df, x='日期時間', y='小考成績', color='學科類別', markers=True)
            fig_line.update_layout(template="plotly_dark", yaxis_range=[0,105])
            st.plotly_chart(fig_line, use_container_width=True)
            st.divider()

            # 報表輸出
            st.subheader("📄 家長報表輸出")
            if st.checkbox("預覽可列印報表"):
                r_title = f"學生 {sel_stu} 學習診斷報告"
                if sel_sub != "全部學科": r_title += f" ({sel_sub})"
                r_text = f"## 🎓 {r_title}\n\n"
                for s in final_df['學科類別'].unique():
                    r_text += f"### 【{s}】\n"
                    recs = final_df[final_df['學科類別'] == s].sort_values('日期時間', ascending=False)
                    for _, r in recs.iterrows():
                        r_text += f"- **範圍：{r['考試範圍']}** (成績：{r['小考成績']}分)\n  *診斷建議：{r['AI診斷與建議']}*\n\n"
                st.markdown('<div class="report-box">', unsafe_allow_html=True)
                st.markdown(r_text)
                st.markdown('</div>', unsafe_allow_html=True)

            st.divider()

            # 歷程卡片
            st.subheader("📝 詳細歷程紀錄")
            for s in final_df['學科類別'].unique():
                st.markdown(f'<div class="subject-header">📚 {s}</div>', unsafe_allow_html=True)
                for _, row in final_df[final_df['學科類別'] == s].sort_values('日期時間', ascending=False).iterrows():
                    c = f'<div class="range-card"><b>🎯 範圍：{row["考試範圍"]}</b> ({row["小考成績"]}分)<br><p style="margin-top:10px;">{row["AI診斷與建議"]}</p></div>'
                    st.markdown(c, unsafe_allow_html=True)
