import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Trade Manager Dashboard", layout="wide")

st.title("📊 Trade Manager Dashboard")

CSV_FILE = "trades_history_all.csv"

# Sidebar: ระบบอัปโหลดไฟล์ CSV สำหรับผู้ใช้อื่น
st.sidebar.header("⚙️ ตัวเลือกข้อมูล")
uploaded_file = st.sidebar.file_uploader("อัปโหลดไฟล์ CSV ประวัติการเทรดของคุณ", type=["csv"])

df = None

# ตรวจสอบการอัปโหลดไฟล์ หรือใช้ไฟล์เดิมในระบบ
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
elif os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)

if df is None or df.empty:
    st.info("👋 กรุณาอัปโหลดไฟล์ CSV ประวัติการเทรดผ่านแถบเมนูด้านข้าง (Sidebar) เพื่อเริ่มใช้งาน")
else:
    # ตรวจสอบและแปลงคอลัมน์เวลา
    time_col = None
    for col in ['time', 'open_time', 'close_time', 'Time', 'Open Time']:
        if col in df.columns:
            time_col = col
            break
            
    if time_col:
        # หากเวลาเป็นตัวเลข Unix Timestamp (เช่น 1700000000 หรือ มิลลิวินาที)
        if pd.api.types.is_numeric_dtype(df[time_col]):
            # ตรวจสอบว่าเป็นมิลลิวินาทีหรือไม่
            unit = 'ms' if df[time_col].max() > 1e11 else 's'
            df['datetime_parsed'] = pd.to_datetime(df[time_col], unit=unit, errors='coerce')
        else:
            df['datetime_parsed'] = pd.to_datetime(df[time_col], errors='coerce')
            
        # แปลงเป็นข้อความวันที่ YYYY-MM-DD เพื่อป้องกันปัญหากราฟ 1970
        df['Date'] = df['datetime_parsed'].dt.strftime('%Y-%m-%d')
    
    # ตัวเลือกกรองตามเลขพอร์ต
    account_col = None
    for col in ['account', 'Account', 'login', 'Login']:
        if col in df.columns:
            account_col = col
            break
            
    if account_col:
        accounts = ["ทั้งหมด (All Accounts)"] + sorted(list(df[account_col].astype(str).unique()))
        selected_account = st.sidebar.selectbox("เลือกพอร์ตการเทรด (Account):", accounts)
        
        if selected_account != "ทั้งหมด (All Accounts)":
            df_filtered = df[df[account_col].astype(str) == selected_account].copy()
        else:
            df_filtered = df.copy()
    else:
        df_filtered = df.copy()

    # คอลัมน์กำไร
    profit_col = 'profit' if 'profit' in df_filtered.columns else ('Profit' if 'Profit' in df_filtered.columns else None)
    
    # คำนวณสรุปผล
    total_profit = df_filtered[profit_col].sum() if profit_col else 0.0
    total_trades = len(df_filtered)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("กำไรรวมทั้งหมด (Net Profit)", f"${total_profit:,.2f}")
    col2.metric("จำนวนไม้ออเดอร์ทั้งหมด", f"{total_trades} ไม้")
    
    if profit_col:
        win_trades = len(df_filtered[df_filtered[profit_col] > 0])
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
        col3.metric("Win Rate", f"{win_rate:.1f}%")
    
    st.markdown("---")
    
    # 🗓️ ปฏิทินสรุปกำไรรายวัน
    st.subheader("🗓️ ปฏิทินสรุปกำไร/ขาดทุน รายวัน (Daily Profit Summary)")
    if 'Date' in df_filtered.columns and profit_col:
        daily_profit = df_filtered.groupby('Date')[profit_col].sum().reset_index()
        daily_profit = daily_profit.dropna().sort_values('Date', ascending=True)
        
        daily_profit['Status'] = daily_profit[profit_col].apply(lambda x: '🟢 กำไร' if x >= 0 else '🔴 ขาดทุน')
        
        fig_bar = px.bar(
            daily_profit, 
            x='Date', 
            y=profit_col, 
            color='Status',
            color_discrete_map={'🟢 กำไร': '#2ECC71', '🔴 ขาดทุน': '#E74C3C'},
            labels={'Date': 'วันที่', profit_col: 'กำไร/ขาดทุน ($)'},
            title="สรุปกำไร/ขาดทุน สุทธิแยกตามวัน"
        )
        # ปรับแกน X เป็นหมวดหมู่ (Category) เพื่อแก้ปัญหาวันที่ผิดเพี้ยน
        fig_bar.update_xaxes(type='category')
        st.plotly_chart(fig_bar, use_container_width=True)
        
        st.dataframe(daily_profit.sort_values('Date', ascending=False), use_container_width=True)
    
    st.markdown("---")

    # 📈 กราฟการเติบโตของพอร์ต
    if 'datetime_parsed' in df_filtered.columns and profit_col:
        df_filtered = df_filtered.sort_values('datetime_parsed')
        df_filtered['cum_profit'] = df_filtered[profit_col].cumsum()
        
        st.subheader("📈 กราฟการเติบโตของพอร์ต (Cumulative Profit)")
        fig_line = px.line(df_filtered, x='datetime_parsed', y='cum_profit', labels={'datetime_parsed': 'เวลา', 'cum_profit': 'กำไรสะสม ($)'})
        st.plotly_chart(fig_line, use_container_width=True)
        
    # 📋 ประวัติการเทรดทั้งหมด
    st.subheader("📋 ประวัติการเทรดทั้งหมด (Trade Logs)")
    st.dataframe(df_filtered, use_container_width=True)
