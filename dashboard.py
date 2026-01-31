import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="產線戰情", layout="wide", page_icon="🏭")

# --- 1. 連線設定 ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    st.error("Secrets 設定錯誤")
    st.stop()

# --- 2. 核心：自定義 HTML/CSS (這裡就是「自己畫」的部分) ---
# 我們定義一個 CSS Grid 版面，讓卡片會自動排好
custom_css = """
<style>
    /* 移除預設邊距 */
    .block-container { padding: 1rem 0.5rem !important; }
    
    /* 定義卡片容器：手機上是 2 欄，電腦上是 3 欄 */
    .grid-container {
        display: grid;
        grid-template-columns: repeat(2, 1fr); 
        gap: 12px;
        padding: 10px;
    }
    
    /* 如果螢幕夠寬，就變 3 欄 (RWD設計) */
    @media (min-width: 768px) {
        .grid-container { grid-template-columns: repeat(3, 1fr); }
    }

    /* 卡片本體設計 */
    .status-card {
        background-color: white;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #eee;
        transition: transform 0.2s; /* 點擊特效準備 */
        position: relative;
        overflow: hidden;
    }
    
    /* 左邊的彩色條 */
    .color-bar {
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 6px;
    }

    /* 數字樣式 */
    .card-number {
        font-size: 32px;
        font-weight: 800;
        color: #333;
        line-height: 1.2;
    }

    /* 標題樣式 */
    .card-title {
        font-size: 14px;
        color: #666;
        font-weight: 500;
        margin-bottom: 5px;
        display: flex;
        align-items: center;
        gap: 5px;
    }

    /* 右上角的圓點裝飾 */
    .dot {
        height: 10px;
        width: 10px;
        background-color: #bbb;
        border-radius: 50%;
        display: inline-block;
        opacity: 0.5;
    }

    /* 強調 -S 的樣式 */
    .warning-badge {
        background-color: #fff3cd;
        color: #856404;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 12px;
        margin-top: 5px;
        display: inline-block;
    }
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

# --- 3. 資料處理 ---
def get_data():
    try:
        res = supabase.table("internal_dashboard").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

df = get_data()

# --- 4. 產生卡片 HTML 的函數 ---
def generate_card_html(title, count, color, icon, detail_text=""):
    """
    這就是我們的畫筆！把資料填入 HTML 模板中
    """
    return f"""
    <div class="status-card">
        <div class="color-bar" style="background-color: {color};"></div>
        <div class="card-title">
            <span>{icon} {title}</span>
            <span class="dot" style="background-color: {color}; margin-left: auto;"></span>
        </div>
        <div class="card-number">{count}</div>
        <div style="font-size: 12px; color: #999;">{detail_text}</div>
    </div>
    """

# --- 5. 主程式 ---
st.markdown("### 🏭 戰情中心 (自定義UI版)")

if st.button("🔄 更新數據", use_container_width=True):
    st.rerun()

if df.empty:
    st.info("無資料")
else:
    df["status"] = df["status"].fillna("")
    
    # 計算各狀態數量
    cnt_wait = len(df[df['status'] == 'WAIT'])
    cnt_checkin = len(df[df['status'] == 'IN_PROGRESS'])
    cnt_out = len(df[df['status'] == 'OUTSOURCE'])
    cnt_return = len(df[df['status'] == 'OUTSOURCE_RETURNED'])
    cnt_ready = df[df['status'] == 'READY_TO_SHIP']['qty'].sum()
    
    # 今日出貨比較特殊
    df_today_ok = df[df['status'] == 'TODAY_OK']
    cnt_today = df_today_ok['qty'].sum()

    # 檢查有沒有 -S (為了顯示警告文字)
    s_warning = ""
    # 簡單檢查全部資料有沒有 -S
    has_s = df['customer_wo'].str.contains('-S', na=False, case=False).any()
    if has_s:
        s_warning = "<span class='warning-badge'>⚠ 含有 -S 工單</span>"

    # --- 組合 HTML 字串 ---
    # 這裡我們手動拼湊出 6 張卡片的 HTML
    html_content = f"""
    <div class="grid-container">
        {generate_card_html("未投入", cnt_wait, "gray", "⚪", "待處理")}
        {generate_card_html("加工中", cnt_checkin, "#4682B4", "🔵", "產線運作中")}
        {generate_card_html("捷安達", cnt_out, "#FF8C00", "🟠", "委外加工")}
        {generate_card_html("待檢驗", cnt_return, "#F4A460", "🟤", "回貨區")}
        {generate_card_html("可出貨", int(cnt_ready), "#2E8B57", "🟢", f"準備中 {s_warning}")}
        {generate_card_html("今日出貨", int(cnt_today), "#9370DB", "🚀", "本日業績")}
    </div>
    """

    # --- 渲染 HTML ---
    st.markdown(html_content, unsafe_allow_html=True)

    # --- 下方放詳細清單 (Expander) ---
    with st.expander("查看詳細清單", expanded=False):
        # 這裡用回 Streamlit 原生表格，因為表格真的很難自己畫得比它好
        st.dataframe(
            df[["customer_wo", "status", "qty", "due_date"]],
            use_container_width=True,
            hide_index=True
        )
