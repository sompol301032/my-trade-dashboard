import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Trade Manager Dashboard", layout="wide")

st.title("📊 Trade Manager Dashboard")

CSV_FILE = "trades_history_all.csv"

if not os.path.exists(CSV_FILE):
    st.error(f"ไม่พบไฟล์ข้อมูลประวัติการเทรด (`{CSV_FILE}`) กรุณาอัปโหลดไฟล์ลงใน GitHub")
else:
    df = pd.read_csv(CSV_FILE)
    
    if df.empty:
        st.warning("ยังไม่มีข้อมูลประวัติการเทรดในระบบ")
    else:
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
            df['Date'] = df['time'].dt.date
        
        #Sidebar ตัวเลือกกรองตามเลขพอร์ต
        accounts = ["ทั้งหมด (All Accounts)"] + sorted(list(df['account'].unique().astype(str))) if 'account' in df.columns else ["ทั้งหมด"]
        selected_account = st.sidebar.selectbox("เลือกพอร์ตการเทรด (Account):", accounts)
        
        if selected_account != "ทั้งหมด (All Accounts)" and 'account' in df.columns:
            df_filtered = df[df['account'].astype(str) == selected_account]
        else:
            df_filtered = df.copy()
            
        # คำนวณสรุปผลกำไร
        total_profit = df_filtered['profit'].sum() if 'profit' in df.columns else 0.0
        total_trades = len(df_filtered)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("กำไรรวมทั้งหมด (Net Profit)", f"${total_profit:,.2f}")
        col2.metric("จำนวนไม้ออเดอร์ทั้งหมด", f"{total_trades} ไม้")
        
        if 'profit' in df.columns:
            win_trades = len(df_filtered[df_filtered['profit'] > 0])
            win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
            col3.metric("Win Rate", f"{win_rate:.1f}%")
        
        st.markdown("---")
        
        # 🗓️ ส่วนปฏิทินสรุปกำไรรายวัน (Daily Profit Calendar)
        st.subheader("🗓️ ปฏิทินสรุปกำไร/ขาดทุน รายวัน (Daily Profit Summary)")
        if 'Date' in df_filtered.columns and 'profit' in df_filtered.columns:
            daily_profit = df_filtered.groupby('Date')['profit'].sum().reset_index()
            daily_profit['Status'] = daily_profit['profit'].apply(lambda x: '🟢 กำไร (Profit)' if x >= 0 else '🔴 ขาดทุน (Loss)')
            
            fig_bar = px.bar(
                daily_profit, 
                x='Date', 
                y='profit', 
                color='Status',
                color_discrete_map={'🟢 กำไร (Profit)': '#2ECC71', '🔴 ขาดทุน (Loss)': '#E74C3C'},
                labels={'Date': 'วันที่', 'profit': 'กำไร/ขาดทุน ($)'},
                title="กำไรสุทธิแยกตามวัน"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
            st.dataframe(daily_profit.sort_values('Date', ascending=False), use_container_width=True)
        
        st.markdown("---")

        # 📈 กราฟการเติบโตพอร์ต
        if 'time' in df_filtered.columns and 'profit' in df_filtered.columns:
            df_filtered = df_filtered.sort_values('time')
            df_filtered['cum_profit'] = df_filtered['profit'].cumsum()
            
            st.subheader("📈 กราฟการเติบโตของพอร์ต (Cumulative Profit)")
            fig = px.line(df_filtered, x='time', y='cum_profit', labels={'time': 'เวลา', 'cum_profit': 'กำไรสะสม ($)'})
            st.plotly_chart(fig, use_container_width=True)
            
        # 📋 ประวัติการเทรดแบบละเอียด
        st.subheader("📋 ประวัติการเทรดทั้งหมด (Trade Logs)")
        st.dataframe(df_filtered, use_container_width=True)
