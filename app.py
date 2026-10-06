import streamlit as st
import MetaTrader5 as mt5
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import calendar
import os

st.set_page_config(page_title="Trade Manager Multi-Account", page_icon="📈", layout="wide")

DB_FILE = "trades_history_all.csv"

# ฟังก์ชันระบุประเภทการปิดออเดอร์ (TP / SL / ปิดมือ)
def parse_close_reason(row):
    comment = str(row.get('comment', '')).lower()
    
    if 'tp' in comment:
        return '🎯 TP'
    elif 'sl' in comment:
        return '🛑 SL'
    elif 'so' in comment or 'stop out' in comment:
        return '💥 Stop Out'
    
    # กรณี comment ไม่ระบุ ให้เช็กจากราคาปิดเทียบกับ tp/sl ของออเดอร์
    return '✋ ปิดมือ'

# โหลดข้อมูลประวัติเดิม
def load_all_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        if not df.empty:
            df['time_dt'] = pd.to_datetime(df['time_dt'])
            df['date'] = pd.to_datetime(df['date']).dt.date
            return df
    return pd.DataFrame()

# บันทึกข้อมูล
def save_all_data(df):
    if not df.empty:
        df.to_csv(DB_FILE, index=False)

# ดึงข้อมูลสดจาก MT5
def fetch_and_sync():
    saved_df = load_all_data()
    mt5_connected = mt5.initialize()
    
    current_acc = None
    if mt5_connected:
        current_acc = mt5.account_info()
        now = datetime.now()
        from_date = datetime(2020, 1, 1)
        deals = mt5.history_deals_get(from_date, now)
        
        if deals is not None and len(deals) > 0:
            df_raw = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
            
            # กรองเฉพาะรายการปิดออเดอร์จริง (entry == 1) และตัดรายการ Deposit/Withdrawal (type == 2) ออก
            closed = df_raw[(df_raw['entry'] == 1) & (df_raw['type'].isin([0, 1]))].copy()
            
            if not closed.empty:
                closed['account'] = current_acc.login
                # แปลงประเภทออเดอร์: MT5 Deal type 0 คือ Sell (ปิด L), 1 คือ Buy (ปิด S) -> ระบุฝั่งออเดอร์เดิม
                closed['order_type'] = closed['type'].apply(lambda x: 'SELL' if x == 0 else 'BUY')
                
                # ระบุสาเหตุการปิด
                closed['close_reason'] = closed.apply(parse_close_reason, axis=1)
                
                # คำนวณกำไรสุทธิ
                closed['net_profit'] = closed['profit'] + closed['swap'] + closed['commission']
                closed['time_dt'] = pd.to_datetime(closed['time'], unit='s')
                closed['date'] = closed['time_dt'].dt.date
                
                if not saved_df.empty:
                    combined = pd.concat([saved_df, closed]).drop_duplicates(subset=['ticket', 'order', 'account'])
                else:
                    combined = closed
                    
                save_all_data(combined)
                saved_df = combined
        mt5.shutdown()
        
    return current_acc, saved_df

current_acc, all_trades = fetch_and_sync()

st.title("📈 Trade Manager Dashboard")

if all_trades.empty and current_acc is None:
    st.error("❌ ไม่พบประวัติการเทรด และไม่สามารถเชื่อมต่อ MT5 ได้")
else:
    # --- SIDEBAR เลือกพอร์ต ---
    st.sidebar.header("⚙️ จัดการพอร์ต")
    
    accounts_list = sorted(all_trades['account'].unique().tolist()) if not all_trades.empty else []
    
    if current_acc and current_acc.login not in accounts_list:
        accounts_list.append(current_acc.login)
        
    options = ["รวมทุกพอร์ต (All Accounts)"] + [str(acc) for acc in accounts_list]
    selected_acc = st.sidebar.selectbox("📂 เลือกพอร์ตที่ต้องการดูสถิติ:", options)
    
    # กรองข้อมูลพอร์ต
    if selected_acc == "รวมทุกพอร์ต (All Accounts)":
        df_display = all_trades.copy()
    else:
        df_display = all_trades[all_trades['account'] == int(selected_acc)].copy()

    # แสดงสถานะบัญชี
    if current_acc:
        st.success(f"💼 **พอร์ตที่เชื่อมต่อ MT5:** {current_acc.login} | **โบรกเกอร์:** {current_acc.company} | **ยอดคงเหลือ:** {current_acc.balance:,.2f} {current_acc.currency}")
    else:
        st.info("ℹ️ **สถานะ Offline (แสดงประวัติจากฐานข้อมูลล่าสุด)**")

    if df_display.empty:
        st.warning("📅 ยังไม่มีประวัติออเดอร์สำหรับพอร์ตนี้")
    else:
        now = datetime.now()
        today_date = now.date()
        week_start = today_date - timedelta(days=now.weekday())
        month_start = today_date.replace(day=1)

        today_trades = df_display[df_display['date'] == today_date]
        week_trades = df_display[df_display['date'] >= week_start]
        month_trades = df_display[df_display['date'] >= month_start]

        today_p = today_trades['net_profit'].sum() if not today_trades.empty else 0.0
        week_p = week_trades['net_profit'].sum() if not week_trades.empty else 0.0
        month_p = month_trades['net_profit'].sum() if not month_trades.empty else 0.0
        
        total_win = len(df_display[df_display['net_profit'] > 0])
        win_rate = (total_win / len(df_display)) * 100 if len(df_display) > 0 else 0

        # --- CARDS ยอดรวม ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("กำไรวันนี้", f"{today_p:+,.2f}")
        col2.metric("กำไรสัปดาห์นี้", f"{week_p:+,.2f}")
        col3.metric("กำไรเดือนนี้", f"{month_p:+,.2f}")
        col4.metric("อัตราการชนะ (Win Rate)", f"{win_rate:.1f}% ({total_win}/{len(df_display)})")

        st.markdown("---")

        tab1, tab2, tab3 = st.tabs(["📅 ตารางปฏิทิน", "📊 กราฟสถิติ", "📜 ประวัติออเดอร์"])

        # TAB 1: CALENDAR
        with tab1:
            st.subheader(f"📅 ตารางปฏิทินกำไร/ขาดทุนรายวัน ({selected_acc})")
            
            daily_summary = df_display.groupby('date')['net_profit'].sum().reset_index()
            daily_dict = dict(zip(daily_summary['date'], daily_summary['net_profit']))

            cal = calendar.monthcalendar(now.year, now.month)
            
            thai_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", 
                           "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
            month_name_th = f"{thai_months[now.month - 1]} {now.year + 543}"
            st.write(f"### {month_name_th}")

            days_name_th = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
            cols = st.columns(7)
            for idx, day in enumerate(days_name_th):
                cols[idx].markdown(f"**{day}**")

            for week in cal:
                cols = st.columns(7)
                for idx, day in enumerate(week):
                    if day == 0:
                        cols[idx].write(" ")
                    else:
                        d_obj = datetime(now.year, now.month, day).date()
                        p_val = daily_dict.get(d_obj, None)
                        
                        if p_val is not None:
                            color = "#00c853" if p_val >= 0 else "#ff5252"
                            cols[idx].markdown(f"**{day}**\n\n<span style='color:{color};font-weight:bold;'>{p_val:+.2f}</span>", unsafe_allow_html=True)
                        else:
                            cols[idx].write(f"{day}")

        # TAB 2: CHARTS
        with tab2:
            st.subheader("📊 กราฟการเติบโตของพอร์ต (Cumulative Profit)")
            df_sorted = df_display.sort_values('time_dt').copy()
            df_sorted['cum_profit'] = df_sorted['net_profit'].cumsum()
            
            fig_line = px.line(df_sorted, x='time_dt', y='cum_profit', title="สะสมกำไรสุทธิ (Cumulative Profit)")
            st.plotly_chart(fig_line, use_container_width=True)

        # TAB 3: HISTORY LOG (อัปเดตเพิ่มประเภทออเดอร์ และเหตุผลการปิด)
        with tab3:
            st.subheader("📜 ประวัติการเทรดทั้งหมด")
            
            # ปรับเปลี่ยนการแสดงชื่อคอลัมน์ให้เข้าใจง่าย
            df_table = df_display.copy()
            df_table = df_table.rename(columns={
                'account': 'พอร์ต',
                'order': 'Order ID',
                'time_dt': 'เวลาปิด',
                'symbol': 'สัญลักษณ์',
                'order_type': 'ฝั่ง',
                'volume': 'Volume',
                'price': 'ราคาปิด',
                'close_reason': 'สาเหตุการปิด',
                'profit': 'Profit',
                'swap': 'Swap',
                'commission': 'Comm',
                'net_profit': 'กำไรสุทธิ'
            })
            
            show_cols = ['พอร์ต', 'Order ID', 'เวลาปิด', 'สัญลักษณ์', 'ฝั่ง', 'Volume', 'ราคาปิด', 'สาเหตุการปิด', 'Profit', 'Swap', 'Comm', 'กำไรสุทธิ']
            st.dataframe(df_table[show_cols].sort_values('เวลาปิด', ascending=False), use_container_width=True)