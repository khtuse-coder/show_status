import streamlit as st
import pandas as pd
from supabase import create_client

# ==========================================
# 1. 設定與連線
# ==========================================
st.set_page_config(page_title="產線戰情", layout="wide", page_icon="🏭")

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    st.error("Secrets 設定錯誤")
    st.stop()

# ==========================================
# 2. CSS 樣式 (修正切頭 + 卡片優化)
# ==========================================
custom_css = """
<style>
    /* 1. 修正表頭被切掉的問題 */
    /* 加大上方的 padding，把內容往下推 */
    .block-container { 
        padding-top: 3.5rem !important; 
        padding-bottom: 2rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    
    /* 2. 卡片排版容器 */
    .grid-container {
        display: grid;
        grid-template-columns: repeat(2, 1fr); /* 手機強制 2 欄 */
        gap: 10px;
        padding: 5px;
        margin-bottom: 20px;
    }
    @media (min-width: 768px) {
        .grid-container { grid-template-columns: repeat(3, 1fr); }
    }

    /* 3. 卡片外觀設計 */
    .status-card {
        background-color: white;
        border-radius: 10px;
        padding: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        border: 1px solid #e0e0e0;
        position: relative;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 100px;
    }
    
    /* 左側色條 */
    .color-bar {
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 5px;
    }

    /* 標題與圖示 */
    .card-title {
        font-size: 14px;
        color: #555;
        font-weight: bold;
        display: flex;
        align-items: center;
        gap: 5px;
        margin-bottom: 5px;
    }

    /* 核心數字：總數量 */
    .card-qty {
        font-size: 24px;
        font-weight: 800;
        color: #333;
        line-height: 1.1;
    }
    
    /* 次要數字：筆數 */
    .card-count {
        font-size: 12px;
        color: #888;
        margin-top: 4px;
        font-weight: 500;
        background-color: #f8f9fa;
        padding: 2px 6px;
        border-radius: 4px;
        display: inline-block;
        align-self: flex-start; /* 靠左對齊 */
    }

    /* -S 警告標籤 */
    .warning-badge {
        color: #856404;
        font-size: 12px;
        margin-left: auto;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# 3. 資料處理函數
# ==========================================
def get_data():
    try:
        res = supabase.table("internal_dashboard").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

def generate_card_html(title, qty, count, color, icon, has_s=False):
    """
    產生 HTML 卡片：同時顯示 數量 (Qty) 和 筆數 (Count)
    """
    s_html = "⚠️-S" if has_s else ""
    
    return f"""
    <div class="status-card">
        <div class="color-bar" style="background-color: {color};"></div>
        <div class="card-title">
            <span>{icon} {title}</span>
            <span class="warning-badge">{s_html}</span>
        </div>
        <div>
            <div class="card-qty">{int(qty):,}</div>
            <div class="card-count">{count} 筆</div>
        </div>
    </div>
    """

# ==========================================
# 4. 主程式
# ==========================================

# 標題區
c1, c2 = st.columns([5,1])
with c1:
    st.markdown("### 🏭 產線戰情中心")
with c2:
    if st.button("🔄"):
        st.rerun()

df = get_data()

if df.empty:
    st.info("目前無資料")
else:
    df["status"] = df["status"].fillna("")
    
    # --- 1. 計算統計數據 (同時算 數量 sum 與 筆數 count) ---
    # 使用 Pandas 的 groupby 一次算完
    # status_stats 變成一個 DataFrame，包含 sum 和 count
    stats = df.groupby('status')['qty'].agg(['sum', 'count'])
    
    # 輔助函數：安全取得數據
    def get_stats(status_key):
        if status_key in stats.index:
            return stats.loc[status_key, 'sum'], stats.loc[status_key, 'count']
        return 0, 0

    # 取得各狀態數據
    qty_wait, cnt_wait = get_stats('WAIT')
    qty_checkin, cnt_checkin = get_stats('IN_PROGRESS')
    qty_out, cnt_out = get_stats('OUTSOURCE')
    qty_return, cnt_return = get_stats('OUTSOURCE_RETURNED')
    qty_ready, cnt_ready = get_stats('READY_TO_SHIP')
    
    # 今日出貨 (TODAY_OK)
    qty_today, cnt_today = get_stats('TODAY_OK')

    # 檢查 -S (顯示在卡片上的小警告)
    def check_s(status_key):
        rows = df[df['status'] == status_key]
        if rows.empty: return False
        return rows['customer_wo'].str.contains('-S', na=False, case=False).any()

    # --- 2. 上半部：HTML 卡片儀表板 (視覺總覽) ---
    html_content = f"""
    <div class="grid-container">
        {generate_card_html("未投入", qty_wait, cnt_wait, "gray", "⚪", check_s('WAIT'))}
        {generate_card_html("Check-in", qty_checkin, cnt_checkin, "#4682B4", "🔵", check_s('IN_PROGRESS'))}
        {generate_card_html("捷安達", qty_out, cnt_out, "#FF8C00", "🟠", check_s('OUTSOURCE'))}
        {generate_card_html("回貨待檢", qty_return, cnt_return, "#F4A460", "🟤", check_s('OUTSOURCE_RETURNED'))}
        {generate_card_html("可出貨", qty_ready, cnt_ready, "#2E8B57", "🟢", check_s('READY_TO_SHIP'))}
        {generate_card_html("今日出貨", qty_today, cnt_today, "#9370DB", "🚀", check_s('TODAY_OK'))}
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

    # --- 3. 下半部：點擊頁籤看明細 (互動區) ---
    st.markdown("###### 🔽 點擊下方頁籤查看明細")
    
    # 定義頁籤
    tabs = st.tabs(["未投入", "Check-in", "捷安達", "回貨", "可出貨", "今日出貨"])
    
    # 定義要顯示的欄位與名稱
    cols_show = ["customer_wo", "qty", "due_date"]
    col_rename = {"customer_wo": "工單", "qty": "數量", "due_date": "需求日"}
    
    # -S 變色邏輯函數
    def highlight_s(row):
        cwo = str(row.get("工單", ""))
        if "-S" in cwo.upper():
            return ['background-color: #fffacd; color: black'] * len(row)
        return [''] * len(row)

    # 封裝一個顯示表格的函數
    def show_tab_content(tab, status_key, is_today=False):
        with tab:
            if is_today:
                # 今日出貨可能包含 NG，這裡只顯示 OK (或兩者都顯示，看你需求)
                filtered_df = df[df['status'].isin(['TODAY_OK', 'TODAY_NG'])].copy()
                # 如果是今日出貨，顯示狀態欄位(OK/NG)比較好
                filtered_df["況"] = filtered_df["status"].apply(lambda x: "OK" if x=="TODAY_OK" else "NG")
                display_cols = ["customer_wo", "qty", "況"]
                rename_dict = {"customer_wo": "工單", "qty": "數量"}
            else:
                filtered_df = df[df['status'] == status_key].copy()
                display_cols = cols_show
                rename_dict = col_rename

            if not filtered_df.empty:
                # 整理顯示資料
                display_df = filtered_df[display_cols].rename(columns=rename_dict)
                
                # 顯示表格
                st.dataframe(
                    display_df.style.apply(highlight_s, axis=1),
                    use_container_width=True,
                    hide_index=True,
                    height=300
                )
            else:
                st.info("無資料")

    # 依序填入各個 Tab 的內容
    show_tab_content(tabs[0], 'WAIT')
    show_tab_content(tabs[1], 'IN_PROGRESS')
    show_tab_content(tabs[2], 'OUTSOURCE')
    show_tab_content(tabs[3], 'OUTSOURCE_RETURNED')
    show_tab_content(tabs[4], 'READY_TO_SHIP')
    show_tab_content(tabs[5], '', is_today=True) # 今日出貨
