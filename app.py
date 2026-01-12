import streamlit as st
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import pandas as pd

st.set_page_config(page_title="維修模式", page_icon="🔧")
st.title("🔧 記帳本維修模式：錯誤檢測")

# --- 讀取 Secrets ---
st.info("正在讀取鑰匙...")
try:
    # 嘗試讀取設定
    info = st.secrets["connections"]["gsheets"]["service_account_info"]
    st.write(f"**Project ID:** `{info.get('project_id', '未找到')}`")
    st.write(f"**Client Email:** `{info.get('client_email', '未找到')}`")
    
    # 檢查私鑰
    private_key = info.get("private_key", "")
    if "-----BEGIN PRIVATE KEY-----" in private_key:
        st.success("✅ 私鑰開頭格式正確")
    else:
        st.error("❌ 私鑰格式錯誤：找不到 `-----BEGIN PRIVATE KEY-----`")

except Exception as e:
    st.error(f"讀取 Secrets 失敗: {e}")
    st.stop()

# --- 測試連線 ---
st.info("正在嘗試連線 Google...")
try:
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    creds.refresh(Request()) # 這一步會測試鑰匙有沒有效
    st.success("🎉 Google 認證成功！API 與金鑰都是正常的！")
    st.balloons()
    
except Exception as e:
    st.error("❌ 連線失敗 (這就是 401 的原因)")
    st.code(str(e))
    st.write("請截圖這個錯誤代碼給我看！")
