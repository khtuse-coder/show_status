import streamlit as st
import pandas as pd
from supabase import create_client

# --- 1. Supabase 連線設定 (請換成你的 Key) ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. CSS 樣式 (模仿你的 VB.NET 顏色風格) ---
st.markdown("""
    <style>
    /* 卡片標題樣式 */
    .card-header {
        color: white;
        padding: 10px;
        text-align: center;
        font-weight: bold;
        font-size: 18px;
        border-radius: 8px 8px 0 0;
        margin-bottom: 0px;
    }
    /* 卡片容器 */
    .card-container {
        background-color: white;
        border-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
        margin-bottom: 20px;
        border: 1px solid #444;
    }
    /* 小計文字 */
    .card-footer {
        text-align: right;
        padding: 5px 10px;
        font-weight: bold;
        color: #333;
        background-color: #f0f0f0;
        border-radius: 0 0 8px 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 取得資料函數 ---
def get_dashboard_data():
    # 這裡假設你的 Supabase 有一個表叫 internal_orders (或是你同步上去的表)
    # 欄位包含: work_order, customer_wo, status, qty, due_date
    try:
        # 範例：從 vendor_orders 抓 (實際請改成你同步上去的表名)
        res = supabase.table("vendor_orders").select("*").execute()
        df = pd.DataFrame(res.data)
        return df
    except Exception as e:
        st.error(f"資料讀取失敗: {e}")
        return pd.DataFrame()

# --- 4. 繪製單張卡片函數 ---
def draw_card(col, title, bg_color, df_filtered):
    with col:
        # 1. 顯示標題 (HTML)
        st.markdown(f"""
            <div class='card-container'>
                <div class='card-header' style='background-color: {bg_color};'>
                    {title}
                </div>
        """, unsafe_allow_html=True)

        # 2. 處理資料與變色邏輯
        if not df_filtered.empty:
            # 整理要顯示的欄位
            display_df = df_filtered[["customer_wo", "order_qty", "customer_model"]].copy() # 欄位名稱請依實際調整
            display_df.columns = ["客戶工單", "數量", "機種"] # 表頭名稱

            # 🔥 關鍵：Pandas Styler 實作 "-S" 變黃色
            def highlight_s(row):
                # 判斷客戶工單是否以 -S 結尾 (不分大小寫)
                cwo = str(row["客戶工單"])
                if cwo.upper().endswith("-S"):
                    return ['background-color: #FFFF00; color: black'] * len(row)
                else:
                    return [''] * len(row)

            # 套用樣式
            styled_df = display_df.style.apply(highlight_s, axis=1)
            
            # 顯示表格 (使用 dataframe 比較美觀，hide_index 隱藏索引)
            st.dataframe(styled_df, use_container_width=True, hide_index=True, height=200)
            
            # 計算小計
            total_qty = df_filtered["order_qty"].sum()
        else:
            st.info("無資料")
            total_qty = 0

        # 3. 顯示小計 (HTML)
        st.markdown(f"""
                <div class='card-footer'>小計：{total_qty}</div>
            </div>
        """, unsafe_allow_html=True)

# --- 5. 主程式 ---
st.title("🏭 產線即時戰情看板")

if st.button("🔄 更新數據"):
    st.rerun()

df = get_dashboard_data()

if not df.empty:
    # 定義六張卡片的過濾邏輯 (請依你的 Supabase 狀態值修改)
    # 這裡 status 對應你的 VB.NET: WAIT, IN_PROGRESS, OUTSOURCE...
    
    # --- 第一排 ---
    c1, c2, c3 = st.columns(3)
    
    # 卡片 1: 未投入 (灰色)
    draw_card(c1, "未投入", "gray", df[df['vendor_status'] == '未接收']) 
    
    # 卡片 2: Check-in (藍色)
    draw_card(c2, "Check-in", "#4682B4", df[df['vendor_status'] == '加工中'])
    
    # 卡片 3: 捷安達 (橘色 - 對應 OUTSOURCE)
    draw_card(c3, "捷安達", "#FF8C00", df[df['vendor_status'] == '已回貨']) # 範例狀態

    # --- 第二排 ---
    c4, c5, c6 = st.columns(3)
    
    # 卡片 4: 回貨待檢 (沙褐色)
    draw_card(c4, "回貨待檢", "#F4A460", df[df['vendor_status'] == '回貨待檢']) # 範例
    
    # 卡片 5: 可出貨 (綠色)
    draw_card(c5, "可出貨", "#2E8B57", df[df['vendor_status'] == '可出貨']) # 範例
    
    # 卡片 6: 今日出貨 (紫色 - 這裡邏輯比較特別，通常要撈 Event 表)
    # 這裡先用空 DataFrame 示意，你需要同步 Material_Ship_Daily 上來
    draw_card(c6, "今日出貨", "#9370DB", pd.DataFrame()) 

else:
    st.warning("目前無資料，請確認同步程式是否執行。")
