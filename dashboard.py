import streamlit as st
import pandas as pd
from supabase import create_client

# ==========================================
# 1. 設定與連線 (放在最前面)
# ==========================================
st.set_page_config(page_title="產線看板", layout="wide", page_icon="🏭")

# 讀取 Secrets
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("找不到 Secrets，請檢查 .streamlit/secrets.toml")
    st.stop()

# 建立連線
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 2. CSS 樣式 (強制淺色模式 + 緊湊優化)
# ==========================================
st.markdown("""
    <style>
    /* 1. 移除預設留白 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 3rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    
    /* 2. 上方儀表板背景框 */
    .dashboard-box {
        background-color: #f8f9fa; 
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 15px;
        border: 1px solid #e9ecef;
    }
    
    /* 3. Expander (折疊卡片) 樣式優化 */
    .streamlit-expanderHeader {
        background-color: white;
        border: 1px solid #ddd;
        border-radius: 8px;
        font-weight: bold;
        font-size: 16px !important;
        color: #333;
    }
    
    /* 4. 表格字體縮小 */
    .stDataFrame { font-size: 13px !important; }
    
    /* 5. 調整 Metric 顯示 */
    [data-testid="stMetricValue"] { font-size: 24px !important; }
    [data-testid="stMetricLabel"] { font-size: 13px !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 核心函數 (必須定義在主程式執行之前)
# ==========================================

def get_dashboard_data():
    """從 Supabase 抓取資料"""
    try:
        res = supabase.table("internal_dashboard").select("*").execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        # 發生錯誤時回傳空 DataFrame 避免報錯
        return pd.DataFrame()

def draw_expander_card(title, icon, df_filtered, is_today_ship=False):
    """
    繪製折疊式卡片
    :param title: 標題
    :param icon: 前面的圖示 (Emoji)
    :param df_filtered: 該狀態的資料
    """
    # 計算總數
    count = 0
    if not df_filtered.empty:
        count = int(df_filtered["qty"].sum())

    # 標題顯示： 圖示 狀態名稱 (數量)
    label = f"{icon} {title} ({count})"

    # 建立折疊區塊 (Expander)
    with st.expander(label, expanded=False):
        if not df_filtered.empty and count > 0:
            # --- 1. 資料整理 ---
            if is_today_ship:
                # 今日出貨特殊處理
                df_show = df_filtered.copy()
                df_show["DisplayStatus"] = df_show["status"].apply(
                    lambda x: "OK" if x == "TODAY_OK" else "NG"
                )
                # 欄位：客工、數量、狀態
                display_df = df_show[["customer_wo", "qty", "DisplayStatus"]].copy()
                display_df.columns = ["客工", "數", "況"]
            else:
                # 一般狀態：客工、數量、需求日
                cols = ["customer_wo", "qty", "due_date"]
                # 防呆：確保欄位存在
                existing = [c for c in cols if c in df_filtered.columns]
                display_df = df_filtered[existing].copy()
                
                # 改名
                rename_map = {
                    "customer_wo": "客工",
                    "qty": "數",
                    "due_date": "期"
                }
                display_df.rename(columns=rename_map, inplace=True)

            # --- 2. 變色邏輯 (-S 變黃) ---
            def highlight_s(row):
                cwo = str(row.get("客工", ""))
                # 只要包含 -S 就變色 (例如 -S, -S8, -S10)
                if "-S" in cwo.upper():
                    return ['background-color: #fffacd; color: black'] * len(row)
                else:
                    return [''] * len(row)

            # --- 3. 顯示表格 ---
            st.dataframe(
                display_df.style.apply(highlight_s, axis=1),
                use_container_width=True,
                hide_index=True,
                height=200 # 固定高度
            )
        else:
            st.info("無資料")

# ==========================================
# 4. 主程式執行邏輯
# ==========================================

# 1. 抓取資料
df = get_dashboard_data()

# 2. 計算上方儀表板數字
if not df.empty:
    df["status"] = df["status"].fillna("")
    # 在庫工單 = 全部扣掉今日出貨紀錄
    total_wos = len(df[~df['status'].isin(['TODAY_OK', 'TODAY_NG'])])
    # 待出貨
    ready_qty = df[df['status'] == 'READY_TO_SHIP']['qty'].sum()
    # 今日出貨
    today_ship_qty = df[df['status'] == 'TODAY_OK']['qty'].sum()
    # 今日NG
    today_ng_qty = df[df['status'] == 'TODAY_NG']['qty'].sum()
else:
    total_wos = 0
    ready_qty = 0
    today_ship_qty = 0
    today_ng_qty = 0

# 3. 繪製頂部儀表板
with st.container():
    st.markdown("<div class='dashboard-box'>", unsafe_allow_html=True)
    
    # 標題列
    c_title, c_btn = st.columns([4, 1])
    with c_title:
        st.markdown("<h4 style='margin:0; color:#444;'>🏭 產線看板</h4>", unsafe_allow_html=True)
    with c_btn:
        if st.button("🔄"):
            st.rerun()
            
    st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)

    # 關鍵指標 (2x2 排列)
    r1c1, r1c2 = st.columns(2)
    with r1c1: st.metric("📋 在庫工單", f"{total_wos}")
    with r1c2: st.metric("📦 待出貨", f"{int(ready_qty)}")
    
    r2c1, r2c2 = st.columns(2)
    with r2c1: st.metric("🚚 今日出貨", f"{int(today_ship_qty)}")
    with r2c2: st.metric("⚠ 今日 NG", f"{int(today_ng_qty)}")
    
    st.markdown("</div>", unsafe_allow_html=True)

# 4. 繪製下方折疊卡片列表
if df.empty:
    st.warning("⚠️ 無資料")
else:
    # 為了讓手機好點，我們用直排列表顯示 6 個 Expander
    
    # 卡片 1: 未投入 (WAIT)
    draw_expander_card("未投入", "⚪", df[df['status'] == 'WAIT'])
    
    # 卡片 2: Check-in (IN_PROGRESS)
    draw_expander_card("Check-in", "🔵", df[df['status'] == 'IN_PROGRESS'])
    
    # 卡片 3: 捷安達 (OUTSOURCE)
    draw_expander_card("捷安達", "🟠", df[df['status'] == 'OUTSOURCE'])
    
    # 卡片 4: 回貨待檢 (OUTSOURCE_RETURNED)
    draw_expander_card("回貨待檢", "🟤", df[df['status'] == 'OUTSOURCE_RETURNED'])
    
    # 卡片 5: 可出貨 (READY_TO_SHIP)
    draw_expander_card("可出貨", "🟢", df[df['status'] == 'READY_TO_SHIP'])
    
    # 卡片 6: 今日出貨 (TODAY_OK + TODAY_NG)
    df_today = df[df['status'].isin(['TODAY_OK', 'TODAY_NG'])]
    draw_expander_card("今日出貨", "🟣", df_today, is_today_ship=True)
