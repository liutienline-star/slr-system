import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import plotly.express as px
from PIL import Image
from fpdf import FPDF  # 新增：用於生成 PDF

# --- 1. 核心參數設定 ---
AUTH_CODE = "641101"  
HUB_NAME = "Student_Learning_Hub" 
SHEET_TAB = "Learning_Data" 
MODEL_NAME = "models/gemini-2.0-flash" 

st.set_page_config(page_title="學思戰術指揮系統", layout="wide", page_icon="📈")

# --- 2. 視覺風格 (CSS) ---
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
    .range-card { background-color: #3b4252; padding: 18px; border-radius: 12px; border-left: 5px solid #81a1c1; margin-bottom: 15px; }
    .tactical-advice { background-color: #3e4451; padding: 25px; border-radius: 15px; border: 2px dashed #ebcb8b; color: #ebcb8b; margin-top: 20px; line-height: 1.8; }
    .tag-style { background-color: #4c566a; color: #88c0d0; padding: 2px 8px; border-radius: 5px; font-size: 0.8rem; margin-right: 5px; }
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
        st.error(f"系統初始化異常：{e}"); return None, None

# --- 4. 驗證機制 ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    _, col_m, _ = st.columns([0.5, 1, 0.5])
    with col_m:
        st.markdown("<h2 style='text-align:center; color:#88c0d0;'>戰術系統登入</h2>", unsafe_allow_html=True)
        if st.text_input("輸入授權碼：", type="password") == AUTH_CODE:
            st.session_state.authenticated = True; st.rerun()
    st.stop()

# --- 5. 工具函式：PDF 生成 ---
def generate_pdf_report(stu_id, subject, exam_range, tags, obs, diag):
    pdf = FPDF()
    pdf.add_page()
    # 這裡使用標準字體，若要顯示中文，需額外載入字體檔 (.ttf)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"Learning Diagnosis Report: {stu_id}", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Subject: {subject} | Range: {exam_range}", ln=True)
    pdf.cell(200, 10, txt=f"Behavioral Tags: {tags}", ln=True)
    pdf.ln(5)
    pdf.multi_cell(0, 10, txt=f"Analysis:\n{obs}")
    pdf.ln(5)
    pdf.multi_cell(0, 10, txt=f"AI Instruction:\n{diag}")
    return pdf.output(dest='S')

# --- 6. 主程式 ---
st.markdown('<h1 class="main-header">🏫 「學思戰情」深度段考診斷系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view, tab_analysis = st.tabs(["📝 影像/PDF 深度診讀", "🔍 歷史數據庫", "📊 戰術分析室"])

# --- Tab 1: 診斷錄入 (新增行為標籤參數) ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: stu_id = st.text_input("📍 學生代號")
        with col2: subject = st.selectbox("📚 學科類別", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        
        exam_range = st.text_input("🎯 段考範圍")
        score = st.number_input("💯 測驗成績", 0, 100, 60)
        uploaded_files = st.file_uploader("📷 上傳檔案", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=True)
        
        if "v_obs" not in st.session_state: st.session_state.v_obs = ""
        
        if uploaded_files and st.button("🔍 執行事實診讀"):
            with st.spinner("AI 正在解析內容..."):
                input_data = []
                for f in uploaded_files:
                    if f.type == "application/pdf": input_data.append({"mime_type": "application/pdf", "data": f.read()})
                    else: input_data.append(Image.open(f))
                
                # 修改 Prompt：加入行為標籤 (第 1 項需求)
                prompt = """你是一位教育診斷專家。請分析檔案，產出：
                1. 錯題題號、正答、知識點。
                2. 【詳述】學生的具體錯誤原因（內容敘述）。
                3. 【行為標籤】：請從以下選擇 1-3 個標籤：#閱讀不周、#邏輯斷層、#運算粗心、#概念混淆、#單字不足、#圖表判讀弱。
                要求：去美化，嚴禁頁碼。"""
                
                v_res = ai_engine.generate_content([prompt] + input_data)
                st.session_state.v_obs = v_res.text
        
        obs = st.text_area("🔍 錯誤事實紀錄", value=st.session_state.v_obs, height=350)

        if st.button("🚀 同步至戰術庫"):
            if stu_id and obs:
                with st.spinner("數據分析中..."):
                    # 讓 AI 抽離出標籤與補強建議
                    tag_res = ai_engine.generate_content(f"從以下內容提取標籤（僅回傳標籤）：{obs}").text
                    diag = ai_engine.generate_content(f"基於事實：{obs}。產出補強建議。去美化，嚴禁頁碼。").text
                    
                    # 第 8 欄寫入行為標籤
                    hub_sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), stu_id, subject, exam_range, score, obs, diag, tag_res])
                    st.success("✅ 數據與行為標籤已歸檔！"); st.session_state.v_obs = ""
            else: st.warning("請完整輸入資料。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2: 歷史數據庫 ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 刷新紀錄"): st.rerun()
        raw_df = pd.DataFrame(hub_sheet.get_all_records())
        if not raw_df.empty: st.dataframe(raw_df.sort_values(by="日期時間", ascending=False), use_container_width=True)

# --- Tab 3: 戰術分析室 (新增標籤統計與 PDF 生成) ---
with tab_analysis:
    if hub_sheet:
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df = pd.DataFrame(raw_data)
            stu_list = df['學生代號'].unique()
            sel_stu = st.selectbox("🎯 選擇學生代號", stu_list)
            stu_df = df[df['學生代號'] == sel_stu].sort_values('日期時間', ascending=False)
            
            if not stu_df.empty:
                # 繪製雷達圖 (維持原功能)
                avg_scores = stu_df.groupby('學科類別')['測驗成績'].mean().reset_index()
                fig_radar = px.line_polar(avg_scores, r='測驗成績', theta='學科類別', line_close=True, range_r=[0,100])
                fig_radar.update_traces(fill='toself', line_color='#88c0d0')
                st.plotly_chart(fig_radar, use_container_width=True)

                # --- 第 1 項需求：行為標籤趨勢分析 ---
                st.markdown("### 🏷️ 核心行為漏洞分析 (跨學科)")
                all_tags = stu_df['錯誤屬性標籤'].str.cat(sep=' ').split()
                if all_tags:
                    tag_counts = pd.Series(all_tags).value_counts().reset_index()
                    tag_counts.columns = ['標籤', '次數']
                    fig_tag = px.bar(tag_counts, x='次數', y='標籤', orientation='h', color_discrete_sequence=['#81a1c1'])
                    st.plotly_chart(fig_tag, use_container_width=True)
                
                st.divider()
                sub_list_hist = sorted(list(stu_df['學科類別'].unique()))
                sel_sub_hist = st.selectbox("🔍 選擇科目明細：", sub_list_hist)
                target_records = stu_df[stu_df['學科類別'] == sel_sub_hist]

                # 考前戰術指令 (維持原功能)
                st.markdown(f"### 🚀 {sel_sub_hist} 科：考前戰術指令")
                if st.button("🧠 彙整歷史漏洞"):
                    history_blob = "\n".join([f"{r['考試範圍']}:{r['導師觀察摘要']}" for _, r in target_records.head(5).iterrows()])
                    tips_res = ai_engine.generate_content(f"分析紀錄：{history_blob}。產出考前戰術指令。").text
                    st.markdown(f'<div class="tactical-advice">{tips_res.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

                st.divider()
                # --- 第 3 項需求：PDF 報告下載 ---
                for _, row in target_records.iterrows():
                    with st.expander(f"🎯 {row['考試範圍']} - {row['測驗成績']}分"):
                        st.markdown(f"**標籤：** `{row['錯誤屬性標籤']}`")
                        st.write(row['導師觀察摘要'])
                        
                        # 生成 PDF 並提供下載按鈕
                        pdf_data = generate_pdf_report(sel_stu, sel_sub_hist, row['考試範圍'], row['錯誤屬性標籤'], row['導師觀察摘要'], row['AI診斷與建議'])
                        st.download_button(
                            label="📥 下載單次診讀 PDF 報告",
                            data=pdf_data,
                            file_name=f"Report_{sel_stu}_{row['考試範圍']}.pdf",
                            mime="application/pdf"
                        )
        else: st.info("💡 資料庫尚無數據。")
