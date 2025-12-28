import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import plotly.express as px
from PIL import Image
from fpdf import FPDF
import os

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
    .tactical-advice { background-color: #3e4451; padding: 25px; border-radius: 15px; border: 2px dashed #ebcb8b; color: #ebcb8b; margin-top: 20px; line-height: 1.8; }
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
        st.error(f"系統異常：{e}"); return None, None

# --- 4. 驗證機制 ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    _, col_m, _ = st.columns([0.5, 1, 0.5])
    with col_m:
        st.markdown("<h2 style='text-align:center; color:#88c0d0;'>戰術系統登入</h2>", unsafe_allow_html=True)
        if st.text_input("輸入授權碼：", type="password") == AUTH_CODE:
            st.session_state.authenticated = True; st.rerun()
    st.stop()

# --- 5. 工具函式：PDF 格式優化 ---
def generate_pdf_report(stu_id, subject, exam_range, tags, obs, diag):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    font_path = "font.ttf"
    # 設定標題 (大字體)
    if os.path.exists(font_path):
        pdf.add_font('CustomFont', '', font_path)
        pdf.set_font('CustomFont', size=20)
    else: pdf.set_font('Arial', 'B', 18)
    
    pdf.cell(0, 15, txt=f"學習診斷個人報告：{stu_id}", ln=True, align='C')
    pdf.ln(5)

    # 設定基本資訊 (中字體)
    if os.path.exists(font_path): pdf.set_font('CustomFont', size=13)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 10, txt=f"科目：{subject}  |  考試範圍：{exam_range}", ln=True)
    pdf.cell(0, 10, txt=f"核心行為標籤：{tags}", ln=True)
    pdf.ln(5)
    
    # 畫一條橫線
    pdf.set_draw_color(136, 192, 208)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # 設定內容 (標準字體 12pt, 增加行距)
    if os.path.exists(font_path): pdf.set_font('CustomFont', size=12)
    pdf.set_text_color(0, 0, 0)
    
    pdf.set_font('CustomFont', size=14)
    pdf.cell(0, 12, txt="【 錯題事實與描述 】", ln=True)
    if os.path.exists(font_path): pdf.set_font('CustomFont', size=12)
    pdf.multi_cell(0, 10, txt=obs) # 行高設為 10
    
    pdf.ln(8)
    pdf.set_font('CustomFont', size=14)
    pdf.cell(0, 12, txt="【 專業補強指導建議 】", ln=True)
    if os.path.exists(font_path): pdf.set_font('CustomFont', size=12)
    pdf.multi_cell(0, 10, txt=diag) # 行高設為 10
    
    return bytes(pdf.output())

# --- 6. 主程式 ---
st.markdown('<h1 class="main-header">🏫 「學思戰情」深度段考診斷系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view, tab_analysis = st.tabs(["📝 影像/PDF 深度診讀", "🔍 歷史數據庫", "📊 戰術分析室"])

# --- Tab 1: 診斷錄入 ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        with col2: subject = st.selectbox("📚 學科類別", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        
        exam_range = st.text_input("🎯 段考範圍")
        score = st.number_input("💯 測驗成績", 0, 100, 60)
        uploaded_files = st.file_uploader("📷 上傳考卷", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=True)
        
        if "v_obs" not in st.session_state: st.session_state.v_obs = ""
        if "v_diag" not in st.session_state: st.session_state.v_diag = ""
        
        if uploaded_files and st.button("🔍 執行事實診讀"):
            with st.spinner("正在生成整齊的診斷報告..."):
                input_data = []
                for f in uploaded_files:
                    if f.type == "application/pdf": input_data.append({"mime_type": "application/pdf", "data": f.read()})
                    else: input_data.append(Image.open(f))
                
                # 修改 Prompt：嚴禁表格，改用整齊列表
                prompt = """你是一位專業的教育診斷官。請分析檔案，並產出以下內容：
                1. 【事實紀錄】：請使用「題號. 知識點：錯誤原因」的整齊條列格式。禁止使用 Markdown 表格 (| 或 - 符號)。
                2. 【行為標籤】：提取 1-3 個標籤如 #閱讀不周。
                3. 【補強建議】：針對該生漏洞提供具體做法。
                要求：去除所有開場白（如「好的，這是...」），直接進入主題。字跡清晰，去美化，嚴禁頁碼。"""
                
                v_res = ai_engine.generate_content([prompt] + input_data).text
                
                if "【補強建議】" in v_res:
                    st.session_state.v_obs, st.session_state.v_diag = v_res.split("【補強建議】")
                else:
                    st.session_state.v_obs = v_res
                    st.session_state.v_diag = "請補充專業指導..."
        
        edited_obs = st.text_area("🔍 錯誤事實 (建議檢查是否有多餘符號)", value=st.session_state.v_obs, height=350)
        edited_diag = st.text_area("💡 補強指導建議", value=st.session_state.v_diag, height=200)

        if st.button("🚀 同步至戰術庫"):
            if stu_id and edited_obs:
                with st.spinner("歸檔中..."):
                    tag_res = ai_engine.generate_content(f"從以下文字提取標籤內容：{edited_obs}").text
                    hub_sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), stu_id, subject, exam_range, score, edited_obs, edited_diag, tag_res])
                    st.success("✅ 數據已更新！請前往「戰術分析室」下載排版優化後的 PDF。")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2 & 3 維持原有邏輯，但調用優化後的 PDF 函式 ---
with tab_view:
    if hub_sheet:
        if st.button("🔄 刷新數據"): st.rerun()
        raw_df = pd.DataFrame(hub_sheet.get_all_records())
        if not raw_df.empty: st.dataframe(raw_df.sort_values(by="日期時間", ascending=False), use_container_width=True)

with tab_analysis:
    if hub_sheet:
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df = pd.DataFrame(raw_data)
            stu_list = df['學生代號'].unique()
            sel_stu = st.selectbox("🎯 選擇學生代號", stu_list)
            stu_df = df[df['學生代號'] == sel_stu].sort_values('日期時間', ascending=False)
            if not stu_df.empty:
                # 繪圖... (省略重複繪圖代碼)
                st.divider()
                sub_list_hist = sorted(list(stu_df['學科類別'].unique()))
                sel_sub_hist = st.selectbox("🔍 科目明細：", sub_list_hist)
                target_records = stu_df[stu_df['學科類別'] == sel_sub_hist]
                
                for _, row in target_records.iterrows():
                    with st.expander(f"🎯 {row['考試範圍']} - {row['測驗成績']}分"):
                        pdf_bytes = generate_pdf_report(sel_stu, sel_sub_hist, row['考試範圍'], row['錯誤屬性標籤'], row['導師觀察摘要'], row['AI診斷與建議'])
                        st.download_button(label="📥 下載優化版中文報告 (PDF)", data=pdf_bytes, file_name=f"Report_{sel_stu}.pdf", mime="application/pdf", key=f"dl_{row['日期時間']}")
