import streamlit as st
import pandas as pd
import plotly.express as px
import calendar
import re
from datetime import datetime

st.set_page_config(page_title="Trade Manager Dashboard", layout="wide")

st.markdown("""
<style>
    .cal-header { text-align: center; font-weight: bold; padding: 10px 4px; background-color: #161b22; color: #8b949e; border-radius: 6px; margin-bottom: 6px; font-size: 13px; border: 1px solid #21262d; }
    .cal-header-sum { text-align: center; font-weight: bold; padding: 10px 4px; background-color: #0d2818; color: #3fb950; border-radius: 6px; margin-bottom: 6px; font-size: 13px; border: 1px solid #238636; }
    .cal-day-box { background-color: #0d1117; border: 1px solid #21262d; border-radius: 8px; padding: 8px 6px; min-height: 95px; margin-bottom: 6px; display: flex; flex-direction: column; justify-content: space-between; }
    .cal-day-box-active { background-color: #122119; border: 1px solid #238636; border-radius: 8px; padding: 8px 6px; min-height: 95px; margin-bottom: 6px; display: flex; flex-direction: column; justify-content: space-between; }
    .cal-day-box-loss { background-color: #211213; border: 1px solid #862323; border-radius: 8px; padding: 8px 6px; min-height: 95px; margin-bottom: 6px; display: flex; flex-direction: column; justify-content: space-between; }
    .cal-day-box-sum { background-color: #0b1d13; border: 1px solid #238636; border-radius: 8px; padding: 8px 6px; min-height: 95px; margin-bottom: 6px; display: flex; flex-direction: column; justify-content: space-between; }
    .cal-day-num { font-size: 12px; color: #8b949e; font-weight: bold; text-align: right; }
    .profit-green { color: #3fb950; font-weight: 800; font-size: 14px; margin-top: 2px; }
    .profit-red { color: #f85149; font-weight: 800; font-size: 14px; margin-top: 2px; }
    .sub-trades { color: #c9d1d9; font-size: 11px; font-weight: 600; margin-top: 1px; }
    .sub-winloss { color: #8b949e; font-size: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Trade Manager Dashboard")

st.sidebar.header("⚙️ ตัวเลือกข้อมูล")

uploaded_file = st.sidebar.file_uploader("อัปโหลดไฟล์ CSV ประวัติการเทรด", type=["csv"])

def clean_number(val):
    if pd.isnull(val):
        return 0.0
    val_str = str(val).strip()
    if val_str.startswith('(') and val_str.endswith(')'):
        val_str = '-' + val_str[1:-1]
    val_str = re.sub(r'[^0-9.-]', '', val_str)
    try:
        return float(val_str)
    except:
        return 0.0

def process_trade_data(file):
    file.seek(0)
    raw_bytes = file.read()
    try:
        content = raw_bytes.decode('utf-8')
    except:
        content = raw_bytes.decode('latin-1', errors='ignore')

    lines = content.splitlines()
    header_idx = 0
    for idx, line in enumerate(lines):
        line_lower = line.lower()
        if ('profit' in line_lower or 'p/l' in line_lower) and ('time' in line_lower or 'date' in line_lower):
            header_idx = idx
            break

    file.seek(0)
    df = pd.read_csv(file, skiprows=header_idx)
    df.columns = [str(c).strip() for c in df.columns]

    type_col = next((c for c in df.columns if c.lower() in ['type', 'cmd', 'action']), None)
    profit_col = next((c for c in df.columns if 'profit' in c.lower() or 'p/l' in c.lower()), None)
    time_col = next((c for c in df.columns if 'close time' in c.lower() or 'time' in c.lower() or 'date' in c.lower()), None)
    ticket_col = next((c for c in df.columns if c.lower() in ['ticket', 'order', 'position', 'deal']), None)
    entry_col = next((c for c in df.columns if c.lower() in ['entry', 'direction', 'in/out']), None)

    # 1. กรองเอาเฉพาะประเภทออเดอร์ที่เป็น Buy หรือ Sell เท่านั้น
    if type_col:
        df = df[df[type_col].astype(str).str.lower().str.strip().isin(['buy', 'sell'])].copy()

    # 2. กรองเฉพาะรายการปิดออเดอร์ (out / in/out) ตัดรายการเปิด (in) ออกเพื่อไม่ให้นับซ้ำ
    if entry_col:
        df = df[df[entry_col].astype(str).str.lower().str.strip().isin(['out', 'in/out', 'in / out'])].copy()

    # 3. กรองเฉพาะแถวที่มีเลข Ticket สมบูรณ์
    if ticket_col:
        df = df[pd.to_numeric(df[ticket_col].astype(str).str.replace('#', ''), errors='coerce').notnull()].copy()

    if profit_col:
        df['Profit_Clean'] = df[profit_col].apply(clean_number)
    else:
        df['Profit_Clean'] = 0.0

    if time_col:
        df['datetime_parsed'] = pd.to_datetime(df[time_col], errors='coerce')
        df = df[df['datetime_parsed'].notnull()].copy()
        df['Date'] = df['datetime_parsed'].dt.date

    return df

if uploaded_file is not None:
    try:
        df = process_trade_data(uploaded_file)

        profit_col = 'Profit_Clean'
        total_profit = df[profit_col].sum()
        total_trades = len(df)
        win_trades = len(df[df[profit_col] > 0])
        loss_trades = len(df[df[profit_col] < 0])
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("กำไรรวมทั้งหมด (Net Profit)", f"${total_profit:,.2f}")
        col2.metric("จำนวนไม้ออเดอร์ทั้งหมด", f"{total_trades:,} ไม้")
        col3.metric("Win Rate", f"{win_rate:.1f}%")

        st.markdown("---")

        tab1, tab2, tab3 = st.tabs(["📅 ตารางปฏิทิน", "📈 กราฟสถิติ", "📜 ประวัติออเดอร์"])

        with tab1:
            st.subheader("📅 ตารางปฏิทินกำไร/ขาดทุนรายวัน และสรุปรายสัปดาห์")

            if 'Date' in df.columns and not df.empty:
                daily_stats = {}
                for date_val, group in df.groupby('Date'):
                    if pd.isnull(date_val):
                        continue
                    pnl = group[profit_col].sum()
                    daily_stats[date_val] = {
                        'pnl': pnl,
                        'trades': len(group),
                        'win': len(group[group[profit_col] > 0]),
                        'loss': len(group[group[profit_col] < 0])
                    }

                all_dates = list(df['Date'].dropna())
                latest_date = max(all_dates) if all_dates else datetime.now().date()
                available_years = sorted(list(set(d.year for d in all_dates)), reverse=True) if all_dates else [latest_date.year]

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
                    w_pnl, w_trades, w_win, w_loss = 0.0, 0, 0, 0

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
                                box_class = "cal-day-box-active" if pnl_val >= 0 else "cal-day-box-loss"
                                sign = "+" if pnl_val >= 0 else ""

                                content_html = f"""
                                <div class='{box_class}'>
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

        with tab2:
            st.subheader("📈 กราฟการเติบโตของพอร์ต (Cumulative Profit)")
            if 'datetime_parsed' in df.columns and not df.empty:
                df_sorted = df.sort_values('datetime_parsed')
                df_sorted['cum_profit'] = df_sorted[profit_col].cumsum()
                fig = px.line(df_sorted, x='datetime_parsed', y='cum_profit',
                              labels={'datetime_parsed': 'เวลา', 'cum_profit': 'กำไรสะสม ($)'},
                              template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.subheader("📋 ประวัติการเทรดทั้งหมด (Trade Logs)")
            display_df = df.copy()
            cols_to_drop = ['datetime_parsed', 'Date', 'Profit_Clean', 'cum_profit']
            display_df = display_df.drop(columns=[c for c in cols_to_drop if c in display_df.columns])
            st.dataframe(display_df, use_container_width=True)

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
else:
    st.info("👋 กรุณาอัปโหลดไฟล์ CSV ประวัติการเทรดผ่านแถบเมนูด้านข้าง (Sidebar) เพื่อเริ่มใช้งาน")
