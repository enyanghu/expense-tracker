import streamlit as st
from google.oauth2 import service_account
from google.auth.transport.requests import Request

st.set_page_config(page_title="維修模式", page_icon="🔧")
st.title("🔧 記帳本維修模式：錯誤檢測")

# --- 測試 1: 檢查 Secrets 是否存在 ---
st.subheader("1. 檢查設定檔 (Secrets)")
try:
    # 嘗試讀取設定
    info = st.secrets["connections"]["gsheets"]["service_account_info"]
    st.success("✅ 成功讀取到 Secrets 設定檔")
    
    # 顯示部分資訊讓你核對
    st.write(f"**Project ID:** `{info.get('project_id', '未找到')}`")
    st.write(f"**機器人 Email:** `{info.get('client_email', '未找到')}`")
    
    # 檢查私鑰格式
    private_key = info.get("private_key", "")
    if "-----BEGIN PRIVATE KEY-----" in private_key:
        st.success("✅ 私鑰開頭格式正確")
    else:
        st.error("❌ 私鑰格式錯誤：找不到 `-----BEGIN PRIVATE KEY-----`")
        
    if "\\n" in private_key:
        st.warning("⚠️ 注意：程式偵測到你的私鑰包含文字符號 `\\n`，這可能是問題所在。")
    else:
        st.info("ℹ️ 私鑰看起來已正確換行。")

except Exception as e:
    st.error(f"❌ 讀取 Secrets 失敗，請檢查標題是否為 [connections.gsheets] \n錯誤訊息: {e}")
    st.stop()

# --- 測試 2: 嘗試連線 Google ---
st.subheader("2. 測試 Google 伺服器連線")
try:
    # 建立憑證物件
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    st.write("正在嘗試與 Google 握手...")
    
    # 強制重新整理 token (這一步會抓出 401 的真兇)
    creds.refresh(Request())
    
    st.success("🎉 恭喜！Google 認證成功！你的金鑰是有效的！")
    st.balloons()
    st.write("👉既然這裡成功，代表問題出在舊的程式碼寫法，我們可以換回記帳程式了。")

except Exception as e:
    st.error("❌ 連線失敗！Google 拒絕了這把鑰匙。")
    st.markdown("### 👇 請截圖下面這段錯誤訊息給我：")
    st.code(str(e))
    
    # 常見錯誤判斷
    err_msg = str(e)
    if "Invalid rsa_key" in err_msg:
        st.warning("診斷：私鑰格式壞掉了。請重新複製 JSON 裡的 private_key。")
    elif "Not a valid email" in err_msg:
        st.warning("診斷：Email 欄位填錯了。")
    elif "401" in err_msg or "invalid_grant" in err_msg:

        st.warning("診斷：401 錯誤。通常是 API 沒開，或是私鑰內容複製不完整。")
