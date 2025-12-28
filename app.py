# --- Tab 3: 戰情分析室 ---
with tab_analysis:
    if hub_sheet:
        raw_data = hub_sheet.get_all_records()
        if raw_data: # 確保有資料才跑
            raw_df = pd.DataFrame(raw_data)
            # 強制將成績轉為數字，避免報錯
            raw_df['小考成績'] = pd.to_numeric(raw_df['小考成績'], errors='coerce').fillna(0)
            
            if not raw_df.empty:
                col_radar, col_trend = st.columns(2)
                
                with col_radar:
                    st.subheader("🕸️ 全班學習力雷達")
                    avg_df = raw_df.groupby('學科類別')['小考成績'].mean().reset_index()
                    fig_radar = px.line_polar(avg_df, r='小考成績', theta='學科類別', line_close=True, range_r=[0,100])
                    fig_radar.update_traces(fill='toself', line_color='#88c0d0')
                    fig_radar.update_layout(template="plotly_dark", font=dict(size=14))
                    st.plotly_chart(fig_radar, use_container_width=True)
                
                with col_trend:
                    st.subheader("📈 個人進步趨勢")
                    all_students = raw_df['學生代號'].unique()
                    selected_stu = st.selectbox("請選擇要查看的學生：", all_students)
                    stu_df = raw_df[raw_df['學生代號'] == selected_stu].sort_values('日期時間')
                    fig_line = px.line(stu_df, x='日期時間', y='小考成績', color='學科類別', markers=True)
                    fig_line.update_layout(template="plotly_dark", yaxis_range=[0,105])
                    st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("數據分析中...請確認 HUB 內有包含成績的紀錄。")
        else:
            st.info("💡 目前 HUB 是空的，請先錄入第一筆成績數據。")－
