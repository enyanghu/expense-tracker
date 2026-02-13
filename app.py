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
        
        # ⚠️ 更新了預設欄位，加入 "收支"
        if not data:
            df = pd.DataFrame(columns=["日期", "收支", "類別", "金額", "備註"])
        else:
            df = pd.DataFrame(data)
            # 防呆：如果舊資料沒有收支欄位，自動補上並預設為支出
            if "收支" not in df.columns:
                df.insert(1, "收支", "支出")
                
            if "金額" in df.columns:
                df["金額"] = pd.to_numeric(df["金額"].astype(str).str.replace(r'[$,]', '', regex=True), errors='coerce').fillna(0)
            if "日期" in df.columns:
                df["日期"] = pd.to_datetime(df["日期"], errors='coerce')

        # 2. 處理預算資料
        try:
            budget_sheet = sh.worksheet("budget")
        except gspread.WorksheetNotFound:
            budget_sheet = sh.add_worksheet(title="budget", rows=2, cols=2)
            budget_sheet.update(range_name="A1:B1", values=[["項目", "金額"]])
            budget_sheet.update(range_name="A2:B2", values=[["每月預算", 20000]]) 

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
    st.write(f"目前每月支出預算：**${monthly_budget:,}**")
    
    new_budget = st.number_input("修改預算金額", value=monthly_budget, step=1000)
    if st.button("更新預算"):
        budget_sheet.update_acell("B2", new_budget)
        st.success("預算已更新！")
        st.rerun()

# --- 主畫面 ---
tab1, tab2 = st.tabs(["➕ 新增帳目", "📊 報表分析"])

# === 分頁 1: 記帳 ===
with tab1:
    st.subheader("輸入收支細項")
    with st.form("entry_form", clear_on_submit=True):
        
        # 👇 新功能：收支切換
        record_type = st.radio("類型", ["支出 💸", "收入 💰"], horizontal=True)
        
        col1, col2 = st.columns(2)
        with col1:
            date_input = st.date_input("日期", datetime.now())
        with col2:
            amount = st.number_input("金額 ($)", min_value=0, step=10, value=100)
            
        # 👇 新功能：根據類型改變分類選單
        if record_type == "支出 💸":
            cat_options = ["飲食", "交通", "購物", "娛樂", "居住", "醫療", "投資", "其他"]
            db_type = "支出"
        else:
            cat_options = ["薪水", "零用錢", "獎金", "投資獲利", "紅包", "其他收入"]
            db_type = "收入"
            
        category = st.selectbox("分類", cat_options)
        note = st.text_input("備註 (選填)")
        
        submitted = st.form_submit_button("💾 儲存紀錄", use_container_width=True)

    if submitted:
        date_str = date_input.strftime("%Y-%m-%d")
        # 寫入包含「收支」的新欄位
        new_row = [date_str, db_type, category, amount, note]
        sheet.append_row(new_row)
        st.success(f"✅ 已記錄：{db_type} - {category} ${amount}")
        st.rerun()

# === 分頁 2: 分析 (含結餘計算) ===
with tab2:
    st.subheader("本月收支概況")
    
    if not df.empty:
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        mask = (df['日期'].dt.month == current_month) & (df['日期'].dt.year == current_year)
        month_df = df.loc[mask]
        
        # 👇 新功能：分離收入與支出並計算結餘
        month_expense = month_df[month_df["收支"] == "支出"]["金額"].sum()
        month_income = month_df[month_df["收支"] == "收入"]["金額"].sum()
        month_balance = month_income - month_expense
        
        # --- 1. 核心儀表板 ---
        col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
        col_metrics1.metric("本月收入", f"${month_income:,.0f}")
        col_metrics2.metric("本月支出", f"${month_expense:,.0f}")
        # 結餘如果是正的會顯示綠色，負的會顯示紅色
        col_metrics3.metric("本月結餘", f"${month_balance:,.0f}", delta=float(month_balance))
        
        st.divider()

        # --- 2. 預算進度條 ---
        st.write("支出預算使用率：")
        percent = min(month_expense / monthly_budget, 1.0) if monthly_budget > 0 else 0
        bar_color = "red" if percent >= 1.0 else ("orange" if percent >= 0.8 else "green")
        
        st.progress(percent)
        
        c1, c2 = st.columns(2)
        with c1:
            if percent >= 1.0:
                st.error("⚠️ 注意：本月已超支！")
            elif percent >= 0.8:
                st.warning("⚠️ 警告：預算即將用盡！")
            else:
                st.caption("✅ 預算控制良好")
        with c2:
            st.markdown(f"<div style='text-align: right;'>剩餘可用預算：<b>${monthly_budget - month_expense:,.0f}</b></div>", unsafe_allow_html=True)

        st.divider()

        # --- 3. 圓餅圖 (只分析支出) ---
        expense_df = month_df[month_df["收支"] == "支出"]
        if not expense_df.empty:
            pie_data = expense_df.groupby("類別")["金額"].sum().reset_index()
            fig = px.pie(pie_data, values='金額', names='類別', 
                         title=f'{current_month} 月支出分佈', 
                         hole=0.4, 
                         color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("這個月還沒有支出紀錄喔！")

        # --- 4. 全部明細 (加上完美編號排序) ---
        with st.expander("查看所有歷史明細"):
            display_df = df.copy()
            display_df["日期"] = display_df["日期"].dt.strftime("%Y-%m-%d")
            
            # 依照日期排序，並將最新的排在上面
            display_df = display_df.sort_values(by="日期", ascending=False)
            
            # 👇 套用我們之前討論的「編號重置魔法」
            display_df = display_df.reset_index(drop=True)
            display_df.index = display_df.index + 1
            
            st.dataframe(display_df, use_container_width=True)
    else:
        st.info("目前沒有資料，快去記下第一筆帳吧！")
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

