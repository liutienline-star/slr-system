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
import re

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

# --- 5. 工具函式：清除 Markdown 雜訊 ---
def clean_text(text):
    # 移除 Markdown 表格符號 (| 和 -)
    text = re.sub(r'\|', '', text)
    text = re.sub(r'^-+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*', '', text) # 移除粗體符號
    return text.strip()

# --- 6. 工具函式：排版優化的 PDF 生成 ---
def generate_pdf_report(stu_id, subject, exam_range, tags, obs, diag):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    font_path = "font.ttf"
    if os.path.exists(font_path):
        pdf.add_font('CustomFont', '', font_path)
        pdf.set_font('CustomFont', size=22)
    else: pdf.set_font('Arial', 'B', 20)

    # 1. 標題 (置中加大)
    pdf.set_text_color(26, 28, 35)
    pdf.cell(0, 20, txt=f"學 生 學 習 診 斷 報 告", ln=True, align='C')
    pdf.ln(5)

    # 2. 基本資訊區塊
    if os.path.exists(font_path): pdf.set_font('CustomFont', size=14)
    pdf.set_fill_color(240, 240, 240) # 淺灰背景
    pdf.cell(0, 12, txt=f" 學生代號：{stu_id}  |  科目：{subject}  |  範圍：{exam_range}", ln=True, fill=True)
    pdf.cell(0, 12, txt=f" 核心行為標籤：{tags}", ln=True, fill=True)
    pdf.ln(10)

    # 3. 錯題事實紀錄 (左對齊，條列式)
    pdf.set_font('CustomFont', size=16)
    pdf.set_text_color(136, 192, 208) # 藍色標題
    pdf.cell(0, 10, txt="■ 錯誤事實與描述紀錄", ln=True)
    pdf.set_draw_color(136, 192, 208)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y()) # 裝飾線
    pdf.ln(4)
    
    pdf.set_font('CustomFont', size=12)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 10, txt=clean_text(obs))
    pdf.ln(10)

    # 4. 指導建議區塊
    pdf.set_font('CustomFont', size=16)
    pdf.set_text_color(136, 192, 208)
    pdf.cell(0, 10, txt="■ 專業補強指導建議", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    
    pdf.set_font('CustomFont', size=12)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 10, txt=clean_text(diag))
    
    return bytes(pdf.output())

# --- 7. 主程式 ---
st.markdown('<h1 class="main-header">🏫 「學思戰情」深度段考診斷系統</h1>', unsafe_allow_html=True)
ai_engine, hub_sheet = init_services()

tab_entry, tab_view, tab_analysis = st.tabs(["📝 影像/PDF 深度診讀", "🔍 歷史數據庫", "📊 戰術分析室"])

# --- Tab 1: 診斷錄入 (優化 AI Prompt) ---
with tab_entry:
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: stu_id = st.text_input("📍 學生代號", placeholder="例：809-01")
        with col2: subject = st.selectbox("📚 學科類別", ["國文", "英文", "數學", "理化", "歷史", "地理", "公民"])
        
        exam_range = st.text_input("🎯 段考範圍")
        score = st.number_input("💯 測驗成績", 0, 100, 60)
        uploaded_files = st.file_uploader("📷 上傳檔案", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=True)
        
        if "v_obs" not in st.session_state: st.session_state.v_obs = ""
        if "v_diag" not in st.session_state: st.session_state.v_diag = ""
        
        if uploaded_files and st.button("🔍 執行事實診讀"):
            with st.spinner("AI 正在優化排版中..."):
                input_data = []
                for f in uploaded_files:
                    if f.type == "application/pdf": input_data.append({"mime_type": "application/pdf", "data": f.read()})
                    else: input_data.append(Image.open(f))
                
                # 嚴格約束 AI 不准使用表格
                prompt = """你是一位專業教育診斷官。分析檔案並產出：
                1. 【事實紀錄】：請使用條列式（例如：● 題號. 內容...）。禁止使用任何表格 | 或 --- 符號。
                2. 【行為標籤】：列出標籤如 #閱讀不周。
                3. 【補強建議】：提供具體的學習指引。
                格式要求：文字簡潔，層次分明，絕對禁止使用表格形式。"""
                
                v_res = ai_engine.generate_content([prompt] + input_data).text
                if "【補強建議】" in v_res:
                    st.session_state.v_obs, st.session_state.v_diag = v_res.split("【補強建議】")
                else:
                    st.session_state.v_obs = v_res; st.session_state.v_diag = "請補充建議內容..."
        
        edited_obs = st.text_area("🔍 錯誤事實 (已自動清除表格符號)", value=clean_text(st.session_state.v_obs), height=350)
        edited_diag = st.text_area("💡 補強建議", value=clean_text(st.session_state.v_diag), height=200)

        if st.button("🚀 同步至戰術庫"):
            if stu_id and edited_obs:
                with st.spinner("同步中..."):
                    tag_res = ai_engine.generate_content(f"從此內容提取標籤：{edited_obs}").text
                    hub_sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), stu_id, subject, exam_range, score, edited_obs, edited_diag, tag_res])
                    st.success("✅ 數據已校正同步！")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2 & 3 維持原有分析邏輯，但使用新排版 PDF ---
with tab_view:
    if hub_sheet:
        raw_df = pd.DataFrame(hub_sheet.get_all_records())
        if not raw_df.empty: st.dataframe(raw_df.sort_values(by="日期時間", ascending=False), use_container_width=True)

with tab_analysis:
    if hub_sheet:
        raw_data = hub_sheet.get_all_records()
        if raw_data:
            df = pd.DataFrame(raw_data)
            stu_list = df['學生代號'].unique()
            sel_stu = st.selectbox("🎯 選擇學生", stu_list)
            stu_df = df[df['學生代號'] == sel_stu].sort_values('日期時間', ascending=False)
            if not stu_df.empty:
                # 此處省略雷達圖代碼以保持簡潔
                st.divider()
                sub_list = sorted(list(stu_df['學科類別'].unique()))
                sel_sub = st.selectbox("🔍 科目明細：", sub_list)
                recs = stu_df[stu_df['學科類別'] == sel_sub]
                for _, row in recs.iterrows():
                    with st.expander(f"🎯 {row['考試範圍']} - {row['測驗成績']}分"):
                        pdf_bytes = generate_pdf_report(sel_stu, sel_sub, row['考試範圍'], row['錯誤屬性標籤'], row['導師觀察摘要'], row['AI診斷與建議'])
                        st.download_button(label="📥 下載排版優化版報告 (PDF)", data=pdf_bytes, file_name=f"Report_{sel_stu}.pdf", mime="application/pdf", key=f"dl_{row['日期時間']}")
