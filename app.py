import streamlit as st
import pandas as pd
import plotly.express as px
import os
import calendar
from datetime import datetime

st.set_page_config(page_title="Trade Manager Dashboard", layout="wide")

# CSS สำหรับจัดแต่งตารางปฏิทิน
st.markdown("""
<style>
    .cal-header {
        text-align: center;
        font-weight: bold;
        padding: 8px;
        background-color: #1e222d;
        color: #d1d4dc;
        border-radius: 4px;
        margin-bottom: 5px;
    }
    .cal-day-box {
        background-color: #131722;
        border: 1px solid #2a2e39;
        border-radius: 6px;
        padding: 10px 5px;
        min-height: 75px;
        text-align: center;
        margin-bottom: 5px;
    }
    .cal-day-num {
        font-size: 14px;
        color: #848e9c;
        font-weight: bold;
    }
    .profit-green {
        color: #089981;
        font-weight: bold;
        font-size: 13px;
        margin-top: 5px;
    }
    .profit-red {
        color: #f23645;
        font-weight: bold;
        font-size: 13px;
        margin-top: 5px;
    }
    .profit-zero {
        color: #787b86;
        font-size: 12px;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Trade Manager Dashboard")

CSV_FILE = "trades_history_all.csv"

# Sidebar: สำหรับผู้ใช้อื่นอัปโหลดไฟล์
st.sidebar.header("⚙️ ตัวเลือกข้อมูล")
uploaded_file = st.sidebar.file_uploader("อัปโหลดไฟล์ CSV ประวัติการเทรดของคุณ", type=["csv"])

df = None
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
elif os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)

if df is None or df.empty:
    st.info("👋 กรุณาอัปโหลดไฟล์ CSV ประวัติการเทรดผ่านแถบเมนูด้านข้าง (Sidebar) เพื่อเริ่มใช้งาน")
else:
    # 1. จัดการคอลัมน์เวลา
    time_col = None
    for col in ['time', 'open_time', 'close_time', 'Time', 'Open Time']:
        if col in df.columns:
            time_col = col
            break
            
    if time_col:
        if pd.api.types.is_numeric_dtype(df[time_col]):
            unit = 'ms' if df[time_col].max() > 1e11 else 's'
            df['datetime_parsed'] = pd.to_datetime(df[time_col], unit=unit, errors='coerce')
        else:
            df['datetime_parsed'] = pd.to_datetime(df[time_col], errors='coerce')
        df['Date'] = df['datetime_parsed'].dt.date

    # 2. ตัวเลือกพอร์ต
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

    profit_col = 'profit' if 'profit' in df_filtered.columns else ('Profit' if 'Profit' in df_filtered.columns else None)

    # 3. คำนวณเหตุผลการปิดออเดอร์ (TP / SL / ปิดมือ)
    def detect_close_reason(row):
        comment = str(row.get('comment', '')).lower()
        if '[tp]' in comment or 'tp' in comment:
            return '🎯 ชน TP'
        elif '[sl]' in comment or 'sl' in comment:
            return '🛑 ชน SL'
        
        # เช็กจากราคาปิดกับค่า TP/SL
        price_close = row.get('price_close', row.get('close_price', None))
        tp = row.get('tp', row.get('TP', 0))
        sl = row.get('sl', row.get('SL', 0))
        
        if pd.notnull(price_close):
            if tp and abs(price_close - tp) < 0.0001:
                return '🎯 ชน TP'
            if sl and abs(price_close - sl) < 0.0001:
                return '🛑 ชน SL'
                
        return '✋ ปิดมือ (Manual)'

    df_filtered['การปิดออเดอร์'] = df_filtered.apply(detect_close_reason, axis=1)

    # แสดงการ์ดสรุปยอด
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

    tab1, tab2, tab3 = st.tabs(["📅 ตารางปฏิทิน (ปฏิทิน)", "📈 กราฟสถิติ (ชาร์ต)", "📜 ประวัติออเดอร์ (ประวัติศาสตร์)"])

    with tab1:
        st.subheader("📅 ตารางปฏิทินกำไร/ขาดทุนรายวัน")
        if 'Date' in df_filtered.columns and profit_col:
            daily_pnl = df_filtered.groupby('Date')[profit_col].sum().to_dict()
            
            all_dates = [d for d in df_filtered['Date'].dropna()]
            if all_dates:
                latest_date = max(all_dates)
                available_years = sorted(list(set(d.year for d in all_dates)), reverse=True)
            else:
                latest_date = datetime.now().date()
                available_years = [latest_date.year]

            c_year, c_month = st.columns(2)
            sel_year = c_year.selectbox("ปี:", available_years, index=0)
            
            thai_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", 
                           "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
            
            sel_month_name = c_month.selectbox("เดือน:", thai_months, index=latest_date.month - 1)
            sel_month = thai_months.index(sel_month_name) + 1

            st.markdown(f"### {sel_month_name} {sel_year}")

            days_header = ["วันจันทร์", "วันอังคาร", "วันพุธ", "วันพฤหัสบดี", "วันศุกร์", "วันเสาร์", "วันอาทิตย์"]
            cols = st.columns(7)
            for i, h in enumerate(days_header):
                cols[i].markdown(f"<div class='cal-header'>{h}</div>", unsafe_allow_html=True)

            cal = calendar.monthcalendar(sel_year, sel_month)
            for week in cal:
                cols = st.columns(7)
                for day_idx, day_num in enumerate(week):
                    if day_num == 0:
                        cols[day_idx].markdown("<div class='cal-day-box'></div>", unsafe_allow_html=True)
                    else:
                        cur_date = datetime(sel_year, sel_month, day_num).date()
                        val = daily_pnl.get(cur_date, None)
                        
                        if val is not None:
                            if val > 0:
                                val_str = f"<div class='profit-green'>+{val:,.2f}</div>"
                            elif val < 0:
                                val_str = f"<div class='profit-red'>{val:,.2f}</div>"
                            else:
                                val_str = "<div class='profit-zero'>0.00</div>"
                        else:
                            val_str = ""

                        cols[day_idx].markdown(
                            f"<div class='cal-day-box'>"
                            f"<div class='cal-day-num'>{day_num}</div>"
                            f"{val_str}"
                            f"</div>", 
                            unsafe_allow_html=True
                        )

    with tab2:
        st.subheader("📈 กราฟการเติบโตของพอร์ต (Cumulative Profit)")
        if 'datetime_parsed' in df_filtered.columns and profit_col:
            df_sorted = df_filtered.sort_values('datetime_parsed')
            df_sorted['cum_profit'] = df_sorted[profit_col].cumsum()
            fig = px.line(df_sorted, x='datetime_parsed', y='cum_profit', labels={'datetime_parsed': 'เวลา', 'cum_profit': 'กำไรสะสม ($)'})
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("📋 ประวัติการเทรดทั้งหมด (Trade Logs)")
        
        display_df = df_filtered.copy()
        
        # จัดคอลัมน์ "การปิดออเดอร์" มาไว้ด้านหน้าให้เห็นชัดเจน
        cols = ['การปิดออเดอร์'] + [c for c in display_df.columns if c != 'การปิดออเดอร์']
        display_df = display_df[cols]
        
        # ซ่อนคอลัมน์คำนวณชั่วคราว
        cols_to_drop = ['datetime_parsed', 'Date', 'cum_profit']
        display_df = display_df.drop(columns=[c for c in cols_to_drop if c in display_df.columns])
        
        st.dataframe(display_df, use_container_width=True)
