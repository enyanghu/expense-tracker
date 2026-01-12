import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from google.oauth2 import service_account
import gspread

# --- 頁面設定 ---
st.set_page_config(page_title="我的記帳本", page_icon="💰", layout="centered")
st.title("💰 個人雲端記帳本")

# --- 核心：手動連接 Google Sheets (使用維修模式的成功邏輯) ---
def load_data():
    try:
        # 1. 讀取 Secrets
        info = st.secrets["connections"]["gsheets"]["service_account_info"]
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]

        # 2. 建立憑證 (跟維修模式一樣)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )

        # 3. 使用 gspread 連線 (這是更穩定的連線庫)
        client = gspread.authorize(creds)
        
        # 4. 開啟試算表
        sheet = client.open_by_url(url).sheet1 # 開啟第一個分頁
        data = sheet.get_all_records()
        
        # 5. 轉換成 Pandas 表格
        if not data:
            # 如果是空的，建立一個空的 DataFrame
            return sheet, pd.DataFrame(columns=["日期", "類別", "金額", "備註"])
            
        df = pd.DataFrame(data)
        
        # 資料清理
        if "金額" in df.columns:
            # 把 "$100" 或 "100" 統一轉成數字
            df["金額"] = pd.to_numeric(df["金額"].astype(str).str.replace(r'[$,]', '', regex=True), errors='coerce').fillna(0)
            
        return sheet, df

    except Exception as e:
        st.error(f"❌ 連線失敗！\n錯誤訊息: {e}")
        st.stop()

# 載入資料
sheet, df = load_data()

# --- 分頁設計 ---
tab1, tab2 = st.tabs(["➕ 新增支出", "📊 報表分析"])

# === 分頁 1: 記帳功能 ===
with tab1:
    st.subheader("輸入支出細項")
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("日期", datetime.now())
        with col2:
            amount = st.number_input("金額 ($)", min_value=0, step=10, value=100)
            
        category = st.selectbox("分類", ["飲食", "交通", "購物", "娛樂", "居住", "醫療", "投資", "其他"])
        note = st.text_input("備註 (選填)")
        
        submitted = st.form_submit_button("💾 儲存紀錄", use_container_width=True)

    if submitted:
        try:
            # 準備要寫入的資料 (轉成 list)
            date_str = date.strftime("%Y-%m-%d")
            new_row = [date_str, category, amount, note]
            
            # 直接寫入 Google Sheet
            sheet.append_row(new_row)
            
            st.success(f"✅ 成功記錄：{category} ${amount}")
            st.rerun() # 重新整理頁面
            
        except Exception as e:
            st.error(f"寫入失敗: {e}")

# === 分頁 2: 分析功能 ===
with tab2:
    st.subheader("收支概況")
    if not df.empty:
        total_expense = df["金額"].sum()
        st.metric(label="總支出", value=f"${total_expense:,.0f}")
        
        st.write("---")
        # 圓餅圖
        pie_data = df.groupby("類別")["金額"].sum().reset_index()
        fig = px.pie(pie_data, values='金額', names='類別', 
                     title='各類別支出比例', 
                     hole=0.4, 
                     color_discrete_sequence=px.colors.qualitative.Set3)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
        
        # 明細表 (依照日期排序)
        with st.expander("查看詳細明細列表"):
            # 確保日期欄位也是日期格式，方便排序
            df_sorted = df.copy()
            try:
                df_sorted = df_sorted.sort_values(by="日期", ascending=False)
            except:
                pass # 如果日期格式亂掉就不排序
            st.dataframe(df_sorted, use_container_width=True)
    else:
        st.info("目前沒有資料，快去記下第一筆帳吧！")
