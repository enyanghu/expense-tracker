import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 頁面設定 ---
st.set_page_config(page_title="我的記帳本", page_icon="💰", layout="centered")
st.title("💰 個人雲端記帳本")

# --- 連接 Google Sheets ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0")
    
    # 資料清理：移除全空的行，並確保金額是數字
    df = df.dropna(how="all")
    if "金額" in df.columns:
        df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0)
        
except Exception as e:
    st.error(f"資料庫連線失敗，請檢查 Secrets 設定。\n錯誤訊息: {e}")
    st.stop()

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
        new_entry = pd.DataFrame([{
            "日期": date.strftime("%Y-%m-%d"),
            "類別": category,
            "金額": amount,
            "備註": note
        }])
        
        try:
            updated_df = pd.concat([df, new_entry], ignore_index=True)
            conn.update(data=updated_df)
            st.success("✅ 記帳成功！已同步至 Google 試算表")
            st.rerun()
        except Exception as e:
            st.error(f"儲存失敗，請稍後再試。錯誤: {e}")

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
        
        # 明細表
        with st.expander("查看詳細明細列表"):
            st.dataframe(df.sort_values(by="日期", ascending=False), use_container_width=True)
    else:
        st.info("目前沒有資料，快去記下第一筆帳吧！")
