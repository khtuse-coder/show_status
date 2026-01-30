import streamlit as st
import pandas as pd
from supabase import create_client

# ==========================================
# 1. 設定與連線
# ==========================================
st.set_page_config(page_title="產線戰情看板", layout="wide") # 設定為寬版模式

# 讀取 Secrets (請確保 .streamlit/secrets.toml 設定正確)
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("找不到 Secrets，請檢查 .streamlit/secrets.toml")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 2. CSS 樣式 (維持你的風格)
# ==========================================
st.markdown("""
    <style>
    .card-container {
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border: 1px solid #ddd;
        overflow: hidden; /* 確保圓角不被切掉 */
    }
    .card-header {
        color: white;
        padding: 12px;
        text-align: center;
        font-weight: bold;
        font-size: 20px;
        letter-spacing: 1px;
    }
    .card-footer {
        text-align: right;
        padding: 8px 15px;
        font-weight: bold;
        color: #555;
        background-color: #f8f9fa;
        border-top: 1px solid #eee;
    }
    /* 調整表格字體大小 */
    .stDataFrame { font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 核心函數
# ==========================================

def get_dashboard_data():
    """從 Supabase 抓取 internal_dashboard 資料表"""
    try:
        # 抓取所有資料
        res = supabase.table("internal_dashboard").select("*").execute()
        df = pd.DataFrame(res.data)
        return df
    except Exception as e:
        st.error(f"資料讀取失敗: {e}")
        return pd.DataFrame()

def draw_card(col, title, bg_color, df_filtered, is_today_ship=False):
    """
    繪製單張卡片
    :param is_today_ship: 是否為「今日出貨」卡片 (欄位顯示邏輯不同)
    """
    with col:
        # 1. 卡片外框與標題
        st.markdown(f"""
            <div class='card-container'>
                <div class='card-header' style='background-color: {bg_color};'>
                    {title}
                </div>
        """, unsafe_allow_html=True)

        total_qty = 0

        if not df_filtered.empty:
            # --- 資料整理 ---
            
            # A. 針對「今日出貨」的特殊處理
            if is_today_ship:
                # 把 status (TODAY_OK, TODAY_NG) 轉成顯示用的 "OK" / "NG"
                df_filtered["DisplayStatus"] = df_filtered["status"].apply(
                    lambda x: "OK" if x == "TODAY_OK" else ("NG" if x == "TODAY_NG" else x)
                )
                
                # 選取顯示欄位：工單, 客戶工單, 狀態(OK/NG), 數量
                display_df = df_filtered[["work_order", "customer_wo", "DisplayStatus", "qty"]].copy()
                display_df.columns = ["工單", "客戶工單", "狀態", "數量"]
            
            # B. 一般卡片的處理
            else:
                # 選取顯示欄位：工單, 客戶工單, 數量, 需求日
                # 確保欄位存在 (防止資料庫缺欄位報錯)
                cols_to_show = ["work_order", "customer_wo", "qty", "due_date"]
                existing_cols = [c for c in cols_to_show if c in df_filtered.columns]
                display_df = df_filtered[existing_cols].copy()
                
                # 重新命名表頭
                rename_map = {
                    "work_order": "工單",
                    "customer_wo": "客戶工單",
                    "qty": "數量",
                    "due_date": "需求日"
                }
                display_df.rename(columns=rename_map, inplace=True)

            # --- 變色邏輯 (-S 變黃色) ---
            def highlight_row(row):
                # 取得該行的「工單」或是「客戶工單」來判斷
                # 這裡依據 VB.NET 邏輯：判斷工單 (Work_Order) 是否結尾 -S
                # 但你的截圖看起來是客戶工單有 -S，保險起見我們兩個都檢查
                
                wo_val = str(row.get("工單", ""))
                cwo_val = str(row.get("客戶工單", ""))
                
                is_s_type = False
                if wo_val.strip().upper().endswith("-S"): is_s_type = True
                if cwo_val.strip().upper().endswith("-S"): is_s_type = True
                
                if is_s_type:
                    return ['background-color: #FFFF00; color: black'] * len(row)
                else:
                    return [''] * len(row)

            # 套用樣式
            styled_df = display_df.style.apply(highlight_row, axis=1)
            
            # 針對 "數量" 欄位不顯示千分位逗號 (例如 2024 不變成 2,024)
            # styled_df = styled_df.format({"數量": "{:.0f}"})

            # --- 顯示表格 ---
            st.dataframe(
                styled_df, 
                use_container_width=True, 
                hide_index=True, 
                height=250 # 固定高度讓版面整齊
            )
            
            total_qty = df_filtered["qty"].sum()
        
        else:
            # 無資料時顯示空狀態
            st.info("目前無資料")
            # 補一個高度佔位
            st.markdown("<div style='height: 215px;'></div>", unsafe_allow_html=True)

        # 3. 頁尾小計
        st.markdown(f"""
                <div class='card-footer'>小計：{int(total_qty)}</div>
            </div>
        """, unsafe_allow_html=True)

# ==========================================
# 4. 主程式執行
# ==========================================

st.title("🏭 產線即時戰情看板")

# 重新整理按鈕
col_btn, col_blank = st.columns([1, 10])
if col_btn.button("🔄 立即更新"):
    st.rerun()

# 抓取資料
df = get_dashboard_data()

if df.empty:
    st.warning("⚠️ 目前資料庫無資料，請確認廠內同步程式 (liteontest.py) 是否已執行。")
else:
    # 確保 status 欄位沒有空白，方便過濾
    df["status"] = df["status"].fillna("")

    # --- 第一排 (Row 1) ---
    c1, c2, c3 = st.columns(3)
    
    # 1. 未投入 (WAIT) - 灰色
    draw_card(c1, "未投入", "gray", df[df['status'] == 'WAIT'])
    
    # 2. Check-in (IN_PROGRESS) - 藍色
    draw_card(c2, "Check-in", "#4682B4", df[df['status'] == 'IN_PROGRESS'])
    
    # 3. 捷安達 (OUTSOURCE) - 橘色
    draw_card(c3, "捷安達", "#FF8C00", df[df['status'] == 'OUTSOURCE'])

    # --- 第二排 (Row 2) ---
    c4, c5, c6 = st.columns(3)
    
    # 4. 回貨待檢 (OUTSOURCE_RETURNED) - 沙褐色
    draw_card(c4, "回貨待檢", "#F4A460", df[df['status'] == 'OUTSOURCE_RETURNED'])
    
    # 5. 可出貨 (READY_TO_SHIP) - 綠色
    draw_card(c5, "可出貨", "#2E8B57", df[df['status'] == 'READY_TO_SHIP'])
    
    # 6. 今日出貨 (TODAY_OK / TODAY_NG) - 紫色
    # 這裡會啟用 is_today_ship=True 來改變欄位顯示
    df_today = df[df['status'].isin(['TODAY_OK', 'TODAY_NG'])]
    draw_card(c6, "今日出貨", "#9370DB", df_today, is_today_ship=True)

# 自動重新整理機制 (選擇性開啟，這裡設為每 60 秒刷新一次)
# from streamlit_autorefresh import st_autorefresh
# st_autorefresh(interval=60000, key="data_refresh")
