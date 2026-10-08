import streamlit as st
import pandas as pd
import plotly.express as px
import os
import calendar
from datetime import datetime

st.set_page_config(page_title="Trade Manager Dashboard", layout="wide")

st.markdown("""
<style>
    .cal-header {
        text-align: center;
        font-weight: bold;
        padding: 10px 4px;
        background-color: #161b22;
        color: #8b949e;
        border-radius: 6px;
        margin-bottom: 6px;
        font-size: 13px;
        border: 1px solid #21262d;
    }
    .cal-header-sum {
        text-align: center;
        font-weight: bold;
        padding: 10px 4px;
        background-color: #0d2818;
        color: #3fb950;
        border-radius: 6px;
        margin-bottom: 6px;
        font-size: 13px;
        border: 1px solid #238636;
    }
    .cal-day-box {
        background-color: #0d1117;
        border: 1px solid #21262d;
        border-radius: 8px;
        padding: 8px 6px;
        min-height: 95px;
        margin-bottom: 6px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .cal-day-box-active {
        background-color: #122119;
        border: 1px solid #238636;
        border-radius: 8px;
        padding: 8px 6px;
        min-height: 95px;
        margin-bottom: 6px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .cal-day-box-sum {
        background-color: #0b1d13;
        border: 1px solid #238636;
        border-radius: 8px;
        padding: 8px 6px;
        min-height: 95px;
        margin-bottom: 6px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .cal-day-num {
        font-size: 12px;
        color: #8b949e;
        font-weight: bold;
        text-align: right;
    }
    .profit-green {
        color: #3fb950;
        font-weight: 800;
        font-size: 14px;
        margin-top: 2px;
    }
    .profit-red {
        color: #f85149;
        font-weight: 800;
        font-size: 14px;
        margin-top: 2px;
    }
    .sub-trades {
        color: #c9d1d9;
        font-size: 11px;
        font-weight: 600;
        margin-top: 1px;
    }
    .sub-winloss {
        color: #8b949e;
        font-size: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Trade Manager Dashboard")

st.sidebar.header("⚙️ ตัวเลือกข้อมูล")
uploaded_file = st.sidebar.file_uploader("อัปโหลดไฟล์ CSV ประวัติการเทรด (XM / Exness)", type=["csv"])

def load_data(file_source):
    if hasattr(file_source, 'seek'):
        file_source.seek(0)
    lines = file_source.readlines()
    skip_rows = 0
    
    for idx, line in enumerate(lines):
        line_str = line.decode('utf-8', errors='ignore') if isinstance(line, bytes) else str(line)
        if any(keyword in line_str for keyword in ['Time', 'Position', 'Symbol', 'Profit', 'close_time']):
            skip_rows = idx
            break
            
    if hasattr(file_source, 'seek'):
        file_source.seek(0)
        
    df = pd.read_csv(file_source, skiprows=skip_rows)
    return df

df = None
if uploaded_file is not None:
    try:
        df = load_data(uploaded_file)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")

if df is None or df.empty:
    st.info("👋 กรุณาอัปโหลดไฟล์ CSV ประวัติการเทรดผ่านแถบเมนูด้านข้าง (Sidebar) เพื่อเริ่มใช้งาน")
else:
    # กรองเฉพาะแถบที่เป็นการเทรดจริง (ไม่เอา balance/credit)
    type_col = None
    for col in ['Type', 'type']:
        if col in df.columns:
            type_col = col
            break
    if type_col:
        df = df[~df[type_col].astype(str).str.lower().isin(['balance', 'credit', 'deposit', 'withdrawal'])].copy()

    # ค้นหาคอลัมน์เวลา
    time_col = None
    for col in ['Time', 'close_time', 'Close Time', 'time', 'open_time']:
        if col in df.columns:
            time_col = col
            break
            
    if time_col:
        df = df[df[time_col].notnull()].copy()
        df['datetime_parsed'] = pd.to_datetime(df[time_col], errors='coerce')
        df['Date'] = df['datetime_parsed'].dt.date

    # ค้นหาและแปลงคอลัมน์กำไร
    profit_col = None
    for col in ['Profit', 'profit', 'Profit/Loss']:
        if col in df.columns:
            profit_col = col
            break
            
    if profit_col:
        # แปลงข้อความให้เป็นตัวเลข รวมถึงติดลบ
        df[profit_col] = df[profit_col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.replace(' ', '', regex=False)
        df[profit_col] = pd.to_numeric(df[profit_col], errors='coerce').fillna(0.0)

    # Filter เลือกบัญชี
    account_col = None
    for col in ['Account', 'account', 'login', 'Login']:
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

    # การ์ดสรุปยอด
    total_profit = df_filtered[profit_col].sum() if profit_col else 0.0
    total_trades = len(df_filtered)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("กำไรรวมทั้งหมด (Net Profit)", f"${total_profit:,.2f}")
    col2.metric("จำนวนไม้ออเดอร์ทั้งหมด", f"{total_trades:,} ไม้")
    if profit_col:
        win_trades = len(df_filtered[df_filtered[profit_col] > 0])
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
        col3.metric("Win Rate", f"{win_rate:.1f}%")

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📅 ตารางปฏิทิน", "📈 กราฟสถิติ", "📜 ประวัติออเดอร์"])

    # TAB 1: CALENDAR GRID WITH WEEKLY SUMMARY
    with tab1:
        st.subheader("📅 ตารางปฏิทินกำไร/ขาดทุนรายวัน และสรุปรายสัปดาห์")
        
        if 'Date' in df_filtered.columns and profit_col:
            daily_stats = {}
            grouped = df_filtered.groupby('Date')
            for date_val, group in grouped:
                if pd.isnull(date_val):
                    continue
                pnl = group[profit_col].sum()
                trades = len(group)
                wins = len(group[group[profit_col] > 0])
                losses = len(group[group[profit_col] < 0])
                daily_stats[date_val] = {
                    'pnl': pnl,
                    'trades': trades,
                    'win': wins,
                    'loss': losses
                }
            
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

            days_header = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            cols = st.columns(8)
            for i, h in enumerate(days_header):
                cols[i].markdown(f"<div class='cal-header'>{h}</div>", unsafe_allow_html=True)
            cols[7].markdown("<div class='cal-header-sum'>Weekly Sum</div>", unsafe_allow_html=True)

            cal_obj = calendar.Calendar(firstweekday=6)
            month_weeks = cal_obj.monthdayscalendar(sel_year, sel_month)

            for week in month_weeks:
                cols = st.columns(8)
                
                w_pnl = 0.0
                w_trades = 0
                w_win = 0
                w_loss = 0

                for day_idx, day_num in enumerate(week):
                    if day_num == 0:
                        cols[day_idx].markdown("<div class='cal-day-box'></div>", unsafe_allow_html=True)
                    else:
                        cur_date = datetime(sel_year, sel_month, day_num).date()
                        stats = daily_stats.get(cur_date, None)
                        
                        if stats:
                            w_pnl += stats['pnl']
                            w_trades += stats['trades']
                            w_win += stats['win']
                            w_loss += stats['loss']

                            pnl_val = stats['pnl']
                            pnl_class = "profit-green" if pnl_val >= 0 else "profit-red"
                            sign = "+" if pnl_val >= 0 else ""
                            
                            content_html = f"""
                            <div class='cal-day-box-active'>
                                <div class='cal-day-num'>{day_num}</div>
                                <div>
                                    <div class='{pnl_class}'>{sign}${pnl_val:,.2f}</div>
                                    <div class='sub-trades'>{stats['trades']} Trades</div>
                                    <div class='sub-winloss'>{stats['win']} Win · {stats['loss']} Loss</div>
                                </div>
                            </div>
                            """
                        else:
                            content_html = f"""
                            <div class='cal-day-box'>
                                <div class='cal-day-num'>{day_num}</div>
                                <div></div>
                            </div>
                            """

                        cols[day_idx].markdown(content_html, unsafe_allow_html=True)

                w_pnl_class = "profit-green" if w_pnl >= 0 else "profit-red"
                w_sign = "+" if w_pnl >= 0 else ""
                
                sum_html = f"""
                <div class='cal-day-box-sum'>
                    <div class='cal-day-num' style='color:#3fb950;'>SUM</div>
                    <div>
                        <div class='{w_pnl_class}'>{w_sign}${w_pnl:,.2f}</div>
                        <div class='sub-trades'>{w_trades} Trades</div>
                        <div class='sub-winloss'>{w_win} Win · {w_loss} Loss</div>
                    </div>
                </div>
                """
                cols[7].markdown(sum_html, unsafe_allow_html=True)

    # TAB 2: PERFORMANCE GRAPH
    with tab2:
        st.subheader("📈 กราฟการเติบโตของพอร์ต (Cumulative Profit)")
        if 'datetime_parsed' in df_filtered.columns and profit_col:
            df_sorted = df_filtered.dropna(subset=['datetime_parsed']).sort_values('datetime_parsed')
            df_sorted['cum_profit'] = df_sorted[profit_col].cumsum()
            fig = px.line(df_sorted, x='datetime_parsed', y='cum_profit', 
                          labels={'datetime_parsed': 'เวลา', 'cum_profit': 'กำไรสะสม ($)'},
                          template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

    # TAB 3: TRADE LOGS
    with tab3:
        st.subheader("📋 ประวัติการเทรดทั้งหมด (Trade Logs)")
        display_df = df_filtered.copy()
        cols_to_drop = ['commission', 'swap', 'fee', 'time_msc', 'datetime_parsed', 'Date', 'cum_profit']
        display_df = display_df.drop(columns=[c for c in cols_to_drop if c in display_df.columns])
        st.dataframe(display_df, use_container_width=True)
