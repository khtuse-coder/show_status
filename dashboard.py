import streamlit as st
import pandas as pd
from supabase import create_client

# ==========================================
# 1. 設定與連線
# ==========================================
st.set_page_config(page_title="產線看板", layout="wide", page_icon="🏭")

# 讀取 Secrets
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("找不到 Secrets")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 2. CSS 樣式 (極致緊湊版)
# ==========================================
st.markdown("""
    <style>
    /* 1. 暴力移除 Streamlit 預設的上下左右留白 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    
    /* 2. 卡片容器：減少陰影與邊距 */
    .card-container {
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 8px; /* 卡片間距縮小 */
        border: 1px solid #ddd;
        overflow: hidden;
    }
    
    /* 3. 卡片標題：變矮、字體適中 */
    .card-header {
        color: white;
        padding: 6px 0; /* 高度縮小 */
        text-align: center;
        font-weight: bold;
        font-size: 16px; /* 字體縮小 */
        letter-spacing: 1px;
    }
    
    /* 4. 卡片底部小計：變矮 */
    .card-footer {
        text-align: right;
        padding: 4px 10px;
        font-weight: bold;
        color: #666;
        background-color: #f8f9fa;
        border-top: 1px solid #eee;
        font-size: 13px;
    }
    
    /* 5. 表格內容字體縮小，讓手機顯示更多欄位 */
    .stDataFrame { font-size: 13px !important; }
    
    /* 6. Metric 大數字調整 */
    [data-testid="stMetricValue"] {
        font-size: 24px !important; /* 數字不要大到換行 */
    }
    [data-testid="stMetricLabel"] {
        font-size: 14px !important;
    }
    
    /* 7. 隱藏 dataframe 上面的索引列空白 */
    thead tr th:first-child {display:none}
    tbody th {display:none}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 核心函數
# ==========================================

def get_dashboard_data():
    try:
        res = supabase.table("internal_dashboard").select("*").execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()

def draw_card(col, title, bg_color, df_filtered, is_today_ship=False):
    with col:
        st.markdown(f"""
            <div class='card-container'>
                <div class='card-header' style='background-color: {bg_color};'>
                    {title}
                </div>
        """, unsafe_allow_html=True)

        total_qty = 0

        if not df_filtered.empty:
            if is_today_ship:
                df_filtered = df_filtered.copy()
                df_filtered["DisplayStatus"] = df_filtered["status"].apply(
                    lambda x: "OK" if x == "TODAY_OK" else ("NG" if x == "TODAY_NG" else x)
                )
                display_df = df_filtered[["customer_wo", "DisplayStatus", "qty"]].copy()
                display_df.columns = ["客工", "狀態", "數"] # 簡化欄位名稱以省空間
            else:
                cols_to_show = ["customer_wo", "qty", "due_date"] # 移除工單號，手機看重點就好
                existing_cols = [c for c in cols_to_show if c in df_filtered.columns]
                display_df = df_filtered[existing_cols].copy()
                
                rename_map = {
                    "customer_wo": "客工", # 簡寫
                    "qty": "數",
                    "due_date": "期" # 簡寫
                }
                display_df.rename(columns=rename_map, inplace=True)

            def highlight_row(row):
                # 這裡只判斷客戶工單有無 -S
                cwo_val = str(row.get("客工", ""))
                is_s_type = cwo_val.strip().upper().endswith("-S")
                return ['background-color: #fffacd; color: black'] * len(row) if is_s_type else [''] * len(row)

            # 表格高度設為 150 (約顯示 4 行)，讓手機版更緊湊
            st.dataframe(
                display_df.style.apply(highlight_row, axis=1), 
                use_container_width=True, 
                hide_index=True, 
                height=150 
            )
            total_qty = df_filtered["qty"].sum()
        else:
            # 無資料時的高度佔位也縮小
            st.info("無資料")
        
        st.markdown(f"<div class='card-footer'>共：{int(total_qty)}</div></div>", unsafe_allow_html=True)

# ==========================================
# 4. 主程式執行
# ==========================================

# 標題縮小一點
st.markdown("### 🏭 產線看板")

if st.button("🔄 更新"):
    st.rerun()

df = get_dashboard_data()

if df.empty:
    st.warning("⚠️ 無資料")
else:
    df["status"] = df["status"].fillna("")

    # --- 頂部關鍵指標 (用 columns 控制排版) ---
    # 手機上 Streamlit 會自動把 Columns 變成直排，這無法避免
    # 但我們字體改小了，看起來會好一點
    total_wos = len(df[~df['status'].isin(['TODAY_OK', 'TODAY_NG'])])
    ready_qty = df[df['status'] == 'READY_TO_SHIP']['qty'].sum()
    today_ship_qty = df[df['status'] == 'TODAY_OK']['qty'].sum()
    today_ng_qty = df[df['status'] == 'TODAY_NG']['qty'].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("在庫工單", f"{total_wos}")
    m2.metric("待出貨", f"{int(ready_qty)}")
    m3.metric("今日出貨", f"{int(today_ship_qty)}")
    m4.metric("今日NG", f"{int(today_ng_qty)}")

    st.markdown("---") # 細分隔線

    # --- 分頁 ---
    tab1, tab2 = st.tabs(["看板", "清單"])

    with tab1:
        # 調整：手機版 Streamlit columns 會強制堆疊
        # 這裡我們維持 columns 寫法，電腦版會並排，手機版會自動變直排
        c1, c2, c3 = st.columns(3)
        draw_card(c1, "未投入", "gray", df[df['status'] == 'WAIT'])
        draw_card(c2, "Check-in", "#4682B4", df[df['status'] == 'IN_PROGRESS'])
        draw_card(c3, "捷安達", "#FF8C00", df[df['status'] == 'OUTSOURCE'])

        c4, c5, c6 = st.columns(3)
        draw_card(c4, "回貨待檢", "#F4A460", df[df['status'] == 'OUTSOURCE_RETURNED'])
        draw_card(c5, "可出貨", "#2E8B57", df[df['status'] == 'READY_TO_SHIP'])
        
        df_today = df[df['status'].isin(['TODAY_OK', 'TODAY_NG'])]
        draw_card(c6, "今日出貨", "#9370DB", df_today, is_today_ship=True)

    with tab2:
        df_detail = df.copy()
        df_detail = df_detail.rename(columns={
            "work_order": "工單",
            "customer_wo": "客工",
            "status": "狀態",
            "qty": "數",
            "due_date": "期"
        })
        # 移除不必要的欄位以省空間
        if "customer_model" in df_detail.columns:
            df_detail = df_detail.drop(columns=["customer_model"])
            
        st.dataframe(df_detail, use_container_width=True, height=500)
