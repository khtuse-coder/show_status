import streamlit as st
import pandas as pd
from supabase import create_client

# ==========================================
# 1. 設定與連線
# ==========================================
st.set_page_config(page_title="產線戰情看板", layout="wide", page_icon="🏭")

# 讀取 Secrets
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("找不到 Secrets，請檢查 .streamlit/secrets.toml")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 2. CSS 樣式 (優化版)
# ==========================================
st.markdown("""
    <style>
    /* 卡片容器 */
    .card-container {
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
        overflow: hidden;
    }
    /* 卡片標題 */
    .card-header {
        color: white;
        padding: 10px 0;
        text-align: center;
        font-weight: bold;
        font-size: 18px;
        letter-spacing: 1px;
    }
    /* 卡片底部小計 */
    .card-footer {
        text-align: right;
        padding: 8px 15px;
        font-weight: bold;
        color: #666;
        background-color: #f8f9fa;
        border-top: 1px solid #eee;
        font-size: 14px;
    }
    /* 調整表格字體與行高 */
    .stDataFrame { font-size: 14px; }
    
    /* 讓 Metric 數字大一點 */
    [data-testid="stMetricValue"] {
        font-size: 28px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 核心函數
# ==========================================

def get_dashboard_data():
    """從 Supabase 抓取 internal_dashboard 資料表"""
    try:
        res = supabase.table("internal_dashboard").select("*").execute()
        df = pd.DataFrame(res.data)
        return df
    except Exception as e:
        st.error(f"資料讀取失敗: {e}")
        return pd.DataFrame()

def draw_card(col, title, bg_color, df_filtered, is_today_ship=False):
    """繪製單張卡片"""
    with col:
        st.markdown(f"""
            <div class='card-container'>
                <div class='card-header' style='background-color: {bg_color};'>
                    {title}
                </div>
        """, unsafe_allow_html=True)

        total_qty = 0

        if not df_filtered.empty:
            # A. 今日出貨特殊處理
            if is_today_ship:
                df_filtered = df_filtered.copy() # 避免 SettingWithCopyWarning
                df_filtered["DisplayStatus"] = df_filtered["status"].apply(
                    lambda x: "OK" if x == "TODAY_OK" else ("NG" if x == "TODAY_NG" else x)
                )
                display_df = df_filtered[["work_order", "customer_wo", "DisplayStatus", "qty"]].copy()
                display_df.columns = ["工單", "客戶工單", "狀態", "數量"]
            
            # B. 一般卡片處理
            else:
                cols_to_show = ["work_order", "customer_wo", "qty", "due_date"]
                existing_cols = [c for c in cols_to_show if c in df_filtered.columns]
                display_df = df_filtered[existing_cols].copy()
                
                rename_map = {
                    "work_order": "工單",
                    "customer_wo": "客戶工單",
                    "qty": "數量",
                    "due_date": "需求日"
                }
                display_df.rename(columns=rename_map, inplace=True)

            # --- 變色邏輯 (-S 變黃色) ---
            def highlight_row(row):
                wo_val = str(row.get("工單", ""))
                cwo_val = str(row.get("客戶工單", ""))
                is_s_type = wo_val.strip().upper().endswith("-S") or cwo_val.strip().upper().endswith("-S")
                
                return ['background-color: #fffacd; color: black'] * len(row) if is_s_type else [''] * len(row)

            # 顯示表格
            st.dataframe(
                display_df.style.apply(highlight_row, axis=1), 
                use_container_width=True, 
                hide_index=True, 
                height=250
            )
            total_qty = df_filtered["qty"].sum()
        
        else:
            st.info("目前無資料")
            st.markdown("<div style='height: 215px;'></div>", unsafe_allow_html=True)

        st.markdown(f"<div class='card-footer'>小計：{int(total_qty)}</div></div>", unsafe_allow_html=True)

# ==========================================
# 4. 主程式執行
# ==========================================

st.title("🏭 產線即時戰情看板")

# 重新整理按鈕
if st.button("🔄 立即更新數據"):
    st.rerun()

# 抓取資料
df = get_dashboard_data()

if df.empty:
    st.warning("⚠️ 目前無資料，請確認廠內同步程式 (liteontest.py) 是否已執行。")
else:
    df["status"] = df["status"].fillna("")

    # ==========================================
    # 🔥 重點升級 1：頂部關鍵指標 (CEO 視角)
    # ==========================================
    
    # 計算關鍵數字
    total_wos = len(df[~df['status'].isin(['TODAY_OK', 'TODAY_NG'])]) # 扣掉今日出貨紀錄，算在庫工單數
    ready_qty = df[df['status'] == 'READY_TO_SHIP']['qty'].sum()
    today_ng_qty = df[df['status'] == 'TODAY_NG']['qty'].sum()
    today_ship_qty = df[df['status'] == 'TODAY_OK']['qty'].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📋 在庫工單數", f"{total_wos} 張")
    m2.metric("📦 待出貨庫存", f"{int(ready_qty)}", delta="可立即出貨")
    m3.metric("🚚 今日已出貨", f"{int(today_ship_qty)}", delta="今日業績")
    m4.metric("⚠ 今日 NG", f"{int(today_ng_qty)}", delta="需注意", delta_color="inverse")

    st.divider() # 分隔線

    # ==========================================
    # 🔥 重點升級 2：分頁切換 (Tabs)
    # ==========================================
    tab1, tab2 = st.tabs(["📊 看板模式 (六卡片)", "🔍 詳細清單模式"])

    with tab1:
        # --- 第一排 ---
        c1, c2, c3 = st.columns(3)
        draw_card(c1, "未投入", "gray", df[df['status'] == 'WAIT'])
        draw_card(c2, "Check-in", "#4682B4", df[df['status'] == 'IN_PROGRESS'])
        draw_card(c3, "捷安達", "#FF8C00", df[df['status'] == 'OUTSOURCE'])

        # --- 第二排 ---
        c4, c5, c6 = st.columns(3)
        draw_card(c4, "回貨待檢", "#F4A460", df[df['status'] == 'OUTSOURCE_RETURNED'])
        draw_card(c5, "可出貨", "#2E8B57", df[df['status'] == 'READY_TO_SHIP'])
        
        # 今日出貨
        df_today = df[df['status'].isin(['TODAY_OK', 'TODAY_NG'])]
        draw_card(c6, "今日出貨", "#9370DB", df_today, is_today_ship=True)

    with tab2:
        st.caption("💡 這裡顯示所有原始資料，可點擊欄位排序或右上角放大鏡搜尋")
        # 簡單處理一下資料讓它好看一點
        df_detail = df.copy()
        df_detail = df_detail.rename(columns={
            "work_order": "工單號碼",
            "customer_wo": "客戶工單",
            "customer_model": "機種",
            "status": "目前狀態",
            "qty": "數量",
            "due_date": "需求日"
        })
        # 顯示大表格
        st.dataframe(df_detail, use_container_width=True, height=600)
