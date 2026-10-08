import streamlit as st
import pandas as pd
import plotly.express as px
import os
import calendar
from datetime import datetime

st.set_page_config(page_title="Trade Manager Dashboard", layout="wide")

# CSS สำหรับจัดแต่งตารางปฏิทินให้เหมือนภาพตัวอย่าง
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

CSV_FILE = "trades_history_all.csv"

# Sidebar: สำหรับผู้ใช้อื่นอัปโหลดไฟล์
st.sidebar.header("⚙️ ตัวเลือกข้อมูล")
uploaded_file = st.sidebar.file_uploader("อัปโหลดไฟล์ CSV ประวัติการเทรด (XM / Exness)", type=["csv"])

df = None
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
elif os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)

if df is None or df.empty:
    st.info("👋 กรุณาอัปโหลดไฟล์ CSV ประวัติการเทรดผ่านแถบเมนูด้านข้าง (Sidebar) เพื่อเริ่มใช้งาน")
else:
    # -------------------------------------------------------------
    # 1. Standardize Columns (รองรับทั้ง XM & Exness)
    # -------------------------------------------------------------
    # รวมคอลัมน์เวลากับ Exness/XM
    time_col = None
    for col in ['close_time', 'Close Time', 'time', 'Time', 'open_time', 'Open Time', 'Timestamp']:
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

    # รวมคอลัมน์กำไร
    profit_col = None
    for col in ['profit', 'Profit', 'Profit/Loss', 'Profit ($)']:
        if col in df.columns:
            profit_col = col
            break
            
    if profit_col:
        df[profit_col] = pd.to_numeric(df[profit_col].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce').fillna(0.0)

    # รวมคอลัมน์บัญชี / โบรกเกอร์
    account_col = None
    for col in ['account', 'Account', 'login', 'Login', 'Broker', 'broker']:
        if col in df.columns:
            account_col = col
            break

    # Filter เลือกพอร์ต
    if account_col:
        accounts = ["ทั้งหมด (All Accounts)"] + sorted(list(df[account_col].astype(str).unique()))
        selected_account = st.sidebar.selectbox("เลือกพอร์ตการเทรด (Account):", accounts)
        if selected_account != "ทั้งหมด (All Accounts)":
            df_filtered = df[df[account_col].astype(str) == selected_account].copy()
        else:
            df_filtered = df.copy()
    else:
        df_filtered = df.copy()

    # -------------------------------------------------------------
    # 2. คำนวณเหตุผลการปิดออเดอร์ (TP / SL / ปิดมือ)
    # -------------------------------------------------------------
    def detect_close_reason(row):
        comment = str(row.get('comment', row.get('Comment', ''))).lower()
        if '[tp]' in comment or 'tp' in comment:
            return '🎯 ชน TP'
        elif '[sl]' in comment or 'sl' in comment:
            return '🛑 ชน SL'
        
        price_close = row.get('price_close', row.get('close_price', row.get('Close Price', None)))
        tp = row.get('tp', row.get('TP', 0))
        sl = row.get('sl', row.get('SL', 0))
        
        if pd.notnull(price_close):
            try:
                price_close = float(price_close)
                tp = float(tp) if tp else 0
                sl = float(sl) if sl else 0
                if tp and abs(price_close - tp) < 0.0001:
                    return '🎯 ชน TP'
                if sl and abs(price_close - sl) < 0.0001:
                    return '🛑 ชน SL'
            except:
                pass
                
        return '✋ ปิดมือ (Manual)'

    df_filtered['การปิดออเดอร์'] = df_filtered.apply(detect_close_reason, axis=1)

    # แปลงค่า type จาก 0/1 เป็น Buy/Sell
    type_col = 'type' if 'type' in df_filtered.columns else ('Type' if 'Type' in df_filtered.columns else None)
    if type_col:
        type_map = {0: 'Buy 🔵', 1: 'Sell 🔴', '0': 'Buy 🔵', '1': 'Sell 🔴', 'buy': 'Buy 🔵', 'sell': 'Sell 🔴'}
        df_filtered['type_display'] = df_filtered[type_col].astype(str).str.lower().map(lambda x: type_map.get(x, x))

    # -------------------------------------------------------------
    # 3. แสดงการ์ดสรุปยอด
    # -------------------------------------------------------------
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

    # -------------------------------------------------------------
    # TAB 1: CALENDAR GRID WITH WEEKLY SUMMARY
    # -------------------------------------------------------------
    with tab1:
        st.subheader("📅 ตารางปฏิทินกำไร/ขาดทุนรายวัน และสรุปรายสัปดาห์")
        
        if 'Date' in df_filtered.columns and profit_col:
            # สรุปข้อมูลตามวัน: [Profit Sum, Trades Count, Win Count, Loss Count]
            daily_stats = {}
            grouped = df_filtered.groupby('Date')
            for date_val, group in grouped:
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

            # Header 8 คอลัมน์ (Sun -> Sat + Weekly Total)
            days_header = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            cols = st.columns(8)
            for i, h in enumerate(days_header):
                cols[i].markdown(f"<div class='cal-header'>{h}</div>", unsafe_allow_html=True)
            cols[7].markdown("<div class='cal-header-sum'>Weekly Sum</div>", unsafe_allow_html=True)

            # Calendar Matrix (Sunday First)
            cal_obj = calendar.Calendar(firstweekday=6)
            month_weeks = cal_obj.monthdayscalendar(sel_year, sel_month)

            for week in month_weeks:
                cols = st.columns(8)
                
                # ตัวแปรเก็บผลรวมรายสัปดาห์
                w_pnl = 0.0
                w_trades = 0
                w_win = 0
                w_loss = 0

                # 7 วันในสัปดาห์
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

                # คอลัมน์ที่ 8: Weekly Total
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

    # -------------------------------------------------------------
    # TAB 2: PERFORMANCE GRAPH
    # -------------------------------------------------------------
    with tab2:
        st.subheader("📈 กราฟการเติบโตของพอร์ต (Cumulative Profit)")
        if 'datetime_parsed' in df_filtered.columns and profit_col:
            df_sorted = df_filtered.sort_values('datetime_parsed')
            df_sorted['cum_profit'] = df_sorted[profit_col].cumsum()
            fig = px.line(df_sorted, x='datetime_parsed', y='cum_profit', 
                          labels={'datetime_parsed': 'เวลา', 'cum_profit': 'กำไรสะสม ($)'},
                          template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------
    # TAB 3: TRADE LOGS
    # -------------------------------------------------------------
    with tab3:
        st.subheader("📋 ประวัติการเทรดทั้งหมด (Trade Logs)")
        
        display_df = df_filtered.copy()
        
        # จัดเรียงคอลัมน์ให้อยู่ในรูปแบบที่อ่านง่าย
        cols = ['การปิดออเดอร์'] + [c for c in display_df.columns if c != 'การปิดออเดอร์']
        display_df = display_df[cols]
        
        # นำคอลัมน์ส่วนเกินที่ใช้นับค่าออก
        cols_to_drop = ['commission', 'swap', 'fee', 'time_msc', 'datetime_parsed', 'Date', 'cum_profit', 'type_display']
        display_df = display_df.drop(columns=[c for c in cols_to_drop if c in display_df.columns])
        
        st.dataframe(display_df, use_container_width=True)
