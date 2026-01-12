import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from google.oauth2 import service_account
import gspread

# --- 頁面設定 ---
st.set_page_config(page_title="我的記帳本", page_icon="💰", layout="centered")
st.title("💰 個人雲端記帳本")

# --- 核心：連線設定 ---
def get_client():
    try:
        info = st.secrets["connections"]["gsheets"]["service_account_info"]
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 連線失敗：{e}")
        st.stop()

def load_data(client, url):
    try:
        sh = client.open_by_url(url)
        
        # 1. 處理記帳資料 (Sheet1)
        sheet1 = sh.sheet1
        data = sheet1.get_all_records()
        if not data:
            df = pd.DataFrame(columns=["日期", "類別", "金額", "備註"])
        else:
            df = pd.DataFrame(data)
            if "金額" in df.columns:
                df["金額"] = pd.to_numeric(df["金額"].astype(str).str.replace(r'[$,]', '', regex=True), errors='coerce').fillna(0)
            if "日期" in df.columns:
                df["日期"] = pd.to_datetime(df["日期"], errors='coerce')

        # 2. 處理預算資料 (嘗試讀取或建立 'budget' 分頁)
        try:
            budget_sheet = sh.worksheet("budget")
        except gspread.WorksheetNotFound:
            # 如果沒有，自動建立一個
            budget_sheet = sh.add_worksheet(title="budget", rows=2, cols=2)
            budget_sheet.update(range_name="A1:B1", values=[["項目", "金額"]])
            budget_sheet.update(range_name="A2:B2", values=[["每月預算", 20000]]) # 預設 20000

        # 讀取預算金額
        try:
            budget_val = budget_sheet.cell(2, 2).value
            monthly_budget = int(budget_val) if budget_val else 20000
        except:
            monthly_budget = 20000

        return sheet1, budget_sheet, df, monthly_budget

    except Exception as e:
        st.error(f"讀取資料錯誤：{e}")
        st.stop()

# --- 初始化 ---
url = st.secrets["connections"]["gsheets"]["spreadsheet"]
client = get_client()
sheet, budget_sheet, df, monthly_budget = load_data(client, url)

# --- 側邊欄：預算設定 ---
with st.sidebar:
    st.header("⚙️ 設定")
    st.write(f"目前每月預算：**${monthly_budget:,}**")
    
    new_budget = st.number_input("修改預算金額", value=monthly_budget, step=1000)
    if st.button("更新預算"):
        budget_sheet.update_acell("B2", new_budget)
        st.success("預算已更新！")
        st.rerun()

# --- 主畫面 ---
tab1, tab2 = st.tabs(["➕ 新增支出", "📊 報表分析"])

# === 分頁 1: 記帳 ===
with tab1:
    st.subheader("輸入支出細項")
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date_input = st.date_input("日期", datetime.now())
        with col2:
            amount = st.number_input("金額 ($)", min_value=0, step=10, value=100)
            
        category = st.selectbox("分類", ["飲食", "交通", "購物", "娛樂", "居住", "醫療", "投資", "其他"])
        note = st.text_input("備註 (選填)")
        
        submitted = st.form_submit_button("💾 儲存紀錄", use_container_width=True)

    if submitted:
        date_str = date_input.strftime("%Y-%m-%d")
        new_row = [date_str, category, amount, note]
        sheet.append_row(new_row)
        st.success(f"✅ 已記錄：{category} ${amount}")
        st.rerun()

# === 分頁 2: 分析 (含預算條) ===
with tab2:
    st.subheader("本月收支概況")
    
    if not df.empty:
        # 篩選「本月」的資料
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # 確保日期欄位是 datetime 物件
        mask = (df['日期'].dt.month == current_month) & (df['日期'].dt.year == current_year)
        month_df = df.loc[mask]
        
        month_total = month_df["金額"].sum()
        
        # --- 1. 預算進度條 (這是新功能!) ---
        col_metrics1, col_metrics2 = st.columns(2)
        col_metrics1.metric("本月已花費", f"${month_total:,.0f}")
        col_metrics2.metric("剩餘預算", f"${monthly_budget - month_total:,.0f}", 
                           delta_color="normal" if monthly_budget >= month_total else "inverse")
        
        # 計算百分比
        percent = min(month_total / monthly_budget, 1.0)
        bar_color = "red" if percent >= 1.0 else ("orange" if percent >= 0.8 else "green")
        
        st.write("預算使用率：")
        st.progress(percent)
        if percent >= 1.0:
            st.error("⚠️ 注意：本月已超支！")
        elif percent >= 0.8:
            st.warning("⚠️ 警告：預算即將用盡！")
        else:
            st.caption("✅ 預算控制良好")

        st.divider()

        # --- 2. 圓餅圖 ---
        if not month_df.empty:
            pie_data = month_df.groupby("類別")["金額"].sum().reset_index()
            fig = px.pie(pie_data, values='金額', names='類別', 
                         title=f'{current_month} 月支出分佈', 
                         hole=0.4, 
                         color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("這個月還沒有支出紀錄喔！")

        # --- 3. 全部明細 ---
        with st.expander("查看所有歷史明細"):
            # 顯示時把日期轉回字串比較好看
            display_df = df.copy()
            display_df["日期"] = display_df["日期"].dt.strftime("%Y-%m-%d")
            st.dataframe(display_df.sort_values(by="日期", ascending=False), use_container_width=True)
    else:
        st.info("目前沒有資料，快去記下第一筆帳吧！")
