import streamlit as st
import pandas as pd
import time
import sys
import os
import logging
import asyncio
import json

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(app_dir)
sys.path.append(root_dir)

from core.data.db_manager import db_manager
from core.data.market_crawler import MarketDataCrawler
from core.data.financial_fetcher import FinancialDataFetcher
from app.utils import load_style, plot_kline

# Try importing lightweight charts
try:
    from streamlit_lightweight_charts import renderLightweightCharts
except ImportError:
    renderLightweightCharts = None
    # st.error("请安装依赖: pip install streamlit-lightweight-charts")

st.set_page_config(page_title="实时行情 | 实战量化交易平台", page_icon="📈", layout="wide")

# Load Style
load_style()

# Initialize Session State
if 'market_code' not in st.session_state:
    st.session_state['market_code'] = '600519'

# --- Sidebar Control ---
with st.sidebar:
    st.header("🔍 股票搜索")
    stock_code_input = st.text_input("代码", st.session_state['market_code'], key="market_code_input")
    if stock_code_input != st.session_state['market_code']:
        st.session_state['market_code'] = stock_code_input
        st.rerun()
        
    st.divider()
    
    st.header("⚙️ 行情设置")
    period_label = st.selectbox("K线周期", ["日K", "周K", "月K", "1分钟", "5分钟", "60分钟", "120分钟"], index=0)
    period_map = {
        "日K": "daily",
        "周K": "weekly",
        "月K": "monthly",
        "1分钟": "1",
        "5分钟": "5",
        "60分钟": "60",
        "120分钟": "120"
    }
    selected_period = period_map[period_label]
    
    st.divider()
    refresh_btn = st.button("🔄 立即刷新")
    auto_refresh = st.toggle("⏱️ 自动刷新 (5s)")

# --- Helper Functions ---

# def render_tradingview_chart(df: pd.DataFrame, height: int = 400):
#    ... (Removed in favor of Plotly Pro Chart)

# --- Main Logic ---
stock_code = st.session_state['market_code']

# Fetch Data Async
async def fetch_all_data(code, period="daily"):
    fetcher = FinancialDataFetcher()
    crawler = MarketDataCrawler(headless=True)
    
    # Parallel tasks
    t1 = fetcher.get_stock_history_async(code, period=period)
    t2 = fetcher.get_stock_capital_flow_async(code)
    t3 = fetcher.get_stock_news_async(code)
    t4 = fetcher.get_stock_institutions_async(code)
    t5 = fetcher.get_financial_summary_async(code, save_db=False)
    # Crawler is separate, usually don't wait for it if it takes too long, but let's try
    t6 = crawler.fetch_and_save_data_async(code)
    
    # We might want to handle failures individually, so using gather with return_exceptions=True
    results = await asyncio.gather(t1, t2, t3, t4, t5, t6, return_exceptions=True)
    return results

# Trigger Data Fetch
with st.spinner(f"正在建立神经连接... [{stock_code}]"):
    # Run async loop
    try:
        results = asyncio.run(fetch_all_data(stock_code, period=selected_period))
        hist_data, cap_flow, news_data, inst_data, fin_data, crawler_data = results
        
        # Log errors if any
        if isinstance(hist_data, Exception): st.error(f"历史行情获取失败: {hist_data}")
        if isinstance(cap_flow, Exception): st.error(f"资金流向获取失败: {cap_flow}")
        if isinstance(news_data, Exception): st.error(f"新闻获取失败: {news_data}")
        if isinstance(inst_data, Exception): st.error(f"机构持仓获取失败: {inst_data}")
        if isinstance(fin_data, Exception): st.error(f"财务摘要获取失败: {fin_data}")
        if isinstance(crawler_data, Exception): 
            st.error(f"实时行情获取失败: {crawler_data}")
            crawler_data = None # Reset if error
        
        # Debug Info
        with st.expander("🛠️ 调试信息 (开发者模式)"):

            st.write(f"Hist Data: {type(hist_data)} {hist_data.shape if hasattr(hist_data, 'shape') else ''}")
            st.write(f"Cap Flow: {type(cap_flow)} {cap_flow.shape if hasattr(cap_flow, 'shape') else ''}")
            st.write(f"News Data: {type(news_data)} {news_data.shape if hasattr(news_data, 'shape') else ''}")
            st.write(f"Inst Data: {type(inst_data)} {inst_data.shape if hasattr(inst_data, 'shape') else ''}")
            st.write(f"Fin Data: {type(fin_data)} {fin_data.shape if hasattr(fin_data, 'shape') else ''}")
            st.write(f"Crawler Task Result: {results[5]}")
            
            # Check DB content directly
            try:
                count_ob = conn.execute("SELECT count(*) FROM market_order_book WHERE stock_code = ?", [stock_code]).fetchone()[0]
                st.write(f"DB Order Book Count: {count_ob}")
                count_tx = conn.execute("SELECT count(*) FROM market_transactions WHERE stock_code = ?", [stock_code]).fetchone()[0]
                st.write(f"DB Transactions Count: {count_tx}")
            except Exception as e:
                st.error(f"DB Check Failed: {e}")

    except Exception as e:
        st.error(f"数据连接中断: {e}")
        hist_data, cap_flow, news_data, inst_data, fin_data = None, None, None, None, None

# --- 1. Top Header (Ticker & Badges) ---
# Get latest price from crawler data (Real-time) or DB or history
conn = db_manager.get_connection()
latest_price = 0.0
pct_change = 0.0

# 1. Try Crawler Data (Real-time)
if crawler_data and isinstance(crawler_data, dict) and crawler_data.get('bid_ask') is not None:
    try:
        df_ba = crawler_data['bid_ask']
        # df_ba has 'item' and 'value' columns
        # item: 最新, 均价, 涨幅, ...
        # Ensure values are float
        price_row = df_ba[df_ba['item'] == '最新']
        pct_row = df_ba[df_ba['item'] == '涨幅']
        
        if not price_row.empty:
            latest_price = float(price_row['value'].values[0])
        if not pct_row.empty:
            pct_change = float(pct_row['value'].values[0])
    except Exception as e:
        # st.error(f"Parse crawler data failed: {e}")
        pass

# 2. If missing, Try DB Transactions (Slightly delayed)
if latest_price == 0:
    try:
        df_trans = conn.execute("SELECT * FROM market_transactions WHERE stock_code = ? ORDER BY captured_at DESC LIMIT 1", [stock_code]).df()
        if not df_trans.empty:
             latest_price = float(df_trans.iloc[0]['price'])
    except:
        pass

# 3. If still 0, Use History (Daily close)
if latest_price == 0 and hist_data is not None and not isinstance(hist_data, Exception) and not hist_data.empty:
    try:
        # Note: '收盘' is renamed to 'close' in financial_fetcher
        if 'close' in hist_data.columns:
            latest_price = hist_data.iloc[-1]['close']
        elif '收盘' in hist_data.columns:
            latest_price = hist_data.iloc[-1]['收盘']
            
        # Pct change usually keeps its name or is not renamed
        if '涨跌幅' in hist_data.columns:
            pct_change = hist_data.iloc[-1]['涨跌幅']
        elif 'p_change' in hist_data.columns:
            pct_change = hist_data.iloc[-1]['p_change']
    except Exception as e:
        pass

col_head1, col_head2 = st.columns([1, 4])
with col_head1:
    st.metric("最新价", f"{latest_price}", f"{pct_change}%")

with col_head2:
    st.markdown(f"## {stock_code} 深度行情指挥舱")
    st.caption("Real-time Quantitative Trading Dashboard (Cyberpunk Edition)")

st.divider()

# --- 2. Center Stage (Chart + Depth) ---
col_chart, col_depth = st.columns([3, 1])

with col_chart:
    st.subheader("📈 K线趋势 (Pro)")
    
    # Chart Controls
    c1, c2 = st.columns([1, 1])
    with c1:
        main_overlays = st.multiselect("主图指标", ["MA", "BOLL"], default=["MA"])
    with c2:
        sub_ind = st.selectbox("副图指标", ["MACD", "KDJ", "RSI", "None"], index=0)
        
    if hist_data is not None and not isinstance(hist_data, Exception) and not hist_data.empty:
        # Plotly Chart
        try:
            fig = plot_kline(hist_data, title=f"{stock_code} {period_label}", overlays=main_overlays, sub_indicator=sub_ind if sub_ind != 'None' else None)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"图表绘制失败: {e}")
    else:
        st.warning("暂无行情数据")

    # News Section (Moved below chart)
    st.divider()
    st.subheader("📰 实时资讯")
    if news_data is not None and not isinstance(news_data, Exception) and not news_data.empty:
        for i, row in news_data.head(5).iterrows():
            # Handle variable column names from AkShare
            title = row.get('title', row.get('新闻标题', '无标题'))
            pub_time = row.get('publish_time', row.get('发布时间', ''))
            url = row.get('url', row.get('新闻链接', row.get('文章链接', '#')))
            content = row.get('content', row.get('新闻内容', '点击查看详情...'))
            
            with st.expander(f"{title} ({pub_time})"):
                 st.write(content)
                 st.markdown(f"[原文链接]({url})")
    else:
        st.caption("暂无相关资讯")

with col_depth:
    st.subheader("🕸️ 深度盘口")
    # Display Order Book (Prefer real-time crawler data, fallback to DB)
    df_ob = pd.DataFrame()
    
    # Process from crawler data if available
    if crawler_data and isinstance(crawler_data, dict) and crawler_data.get('bid_ask') is not None:
         # Need to transform flat bid_ask DF to sell/buy structure
         # Crawler returns flat DF with 'item' and 'value'
         # Reuse logic or just query DB since we saved it? 
         # Saving to DB is fast, but querying back might have latency or old data if save failed.
         # Let's rely on DB for Order Book as it's complex to re-parse here and less critical than ticks for "freshness" sensation
         # But to be consistent, let's try to query DB again *after* save.
         # Since we waited for crawler task, DB should be updated.
         pass

    try:
        df_ob = conn.execute("SELECT * FROM market_order_book WHERE stock_code = ? ORDER BY captured_at DESC LIMIT 10", [stock_code]).df()
        if not df_ob.empty:
            df_sell = df_ob[df_ob['position'].str.contains('卖')].sort_values('position', ascending=False)
            df_buy = df_ob[df_ob['position'].str.contains('买')].sort_values('position', ascending=True)
            
            st.markdown("###### 卖盘")
            for _, row in df_sell.iterrows():
                cols = st.columns([1, 1, 1])
                cols[0].caption(row['position'])
                cols[1].markdown(f"<span style='color:#26a69a'>{row['price']}</span>", unsafe_allow_html=True)
                cols[2].caption(str(row['volume']))
                
            st.markdown("###### 买盘")
            for _, row in df_buy.iterrows():
                cols = st.columns([1, 1, 1])
                cols[0].caption(row['position'])
                cols[1].markdown(f"<span style='color:#ef5350'>{row['price']}</span>", unsafe_allow_html=True)
                cols[2].caption(str(row['volume']))
        else:
            st.info("等待盘口数据...")
            
        st.divider()
        st.subheader("⚡ 成交明细")
        
        # Display Transactions (Prefer real-time crawler data, fallback to DB)
        df_trans = pd.DataFrame()
        if crawler_data and isinstance(crawler_data, dict) and crawler_data.get('tick') is not None:
             df_trans = crawler_data['tick']
             # Map crawler columns to DB columns for consistent display logic
             # Crawler: 成交时间, 成交价格, 成交量, 性质
             df_trans = df_trans.rename(columns={'成交时间': 'trade_time', '成交价格': 'price', '成交量': 'volume', '性质': 'nature'})
        else:
             # Fallback to DB
             df_trans = conn.execute("SELECT * FROM market_transactions WHERE stock_code = ? ORDER BY captured_at DESC LIMIT 20", [stock_code]).df()
        
        if not df_trans.empty:
            # Ensure columns exist
            # Columns: trade_time, price, volume, nature
            st.markdown(
                """
                <div style="display: flex; justify-content: space-between; font-size: 0.8em; color: #888; padding-bottom: 5px; border-bottom: 1px solid #333;">
                    <span style="flex:1">时间</span>
                    <span style="flex:1; text-align:right">价格</span>
                    <span style="flex:1; text-align:right">量</span>
                    <span style="flex:1; text-align:right">性质</span>
                </div>
                """, unsafe_allow_html=True
            )
            for _, row in df_trans.iterrows():
                t_str = row['trade_time']
                p_str = f"{row['price']}"
                v_str = f"{row['volume']}"
                
                # Try to get nature if exists, else default
                nature = row.get('nature', '')
                if pd.isna(nature): nature = ''
                
                # Color logic
                color = "#e0e0e0" # Default grey
                if '买' in str(nature):
                    color = "#ef5350" # Red
                elif '卖' in str(nature):
                    color = "#26a69a" # Green
                
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; font-size: 0.9em; border-bottom: 1px solid #222; padding: 2px 0;">
                        <span style="flex:1">{t_str}</span>
                        <span style="flex:1; text-align:right; color: #ffb74d;">{p_str}</span>
                        <span style="flex:1; text-align:right">{v_str}</span>
                        <span style="flex:1; text-align:right; color: {color};">{nature}</span>
                    </div>
                    """, unsafe_allow_html=True
                )
        else:
            st.caption("暂无成交明细")
            
    except Exception as e:
        st.error(f"盘口数据异常: {e}")

# --- 3. Bottom Tabs (Multi-dimensional Data) ---
st.divider()
tab1, tab2, tab3, tab4 = st.tabs(["📊 深度资料 (F10)", "💸 资金博弈", "🏛️ 机构透视", "📰 舆情新闻"])

with tab1:
    if fin_data is not None and not isinstance(fin_data, Exception) and not fin_data.empty:
        st.dataframe(fin_data.style.highlight_max(axis=0), width="stretch", height=400)
    else:
        st.info("暂无财务摘要数据")

with tab2:
    st.caption("主力资金流向 (近5日)")
    if cap_flow is not None and not isinstance(cap_flow, Exception) and not cap_flow.empty:
        # Simple bar chart for net flow
        # Try to find relevant columns. AkShare columns vary.
        # Assuming '主力净流入' or similar exists
        st.dataframe(cap_flow, width="stretch")
    else:
        st.info("暂无资金流数据")

with tab3:
    st.caption("机构持仓分布")
    if inst_data is not None and not isinstance(inst_data, Exception) and not inst_data.empty:
        st.dataframe(inst_data, width="stretch")
    else:
        st.info("暂无机构持仓数据")

with tab4:
    if news_data is not None and not isinstance(news_data, Exception) and not news_data.empty:
        for idx, row in news_data.iterrows():
            title = row.get('title', row.get('新闻标题', '无标题'))
            date = row.get('publish_time', row.get('发布时间', ''))
            url = row.get('url', row.get('新闻链接', row.get('文章链接', '#')))
            content = row.get('content', row.get('新闻内容', '...'))
            
            with st.expander(f"{date} | {title}"):
                st.markdown(f"[点击阅读原文]({url})")
                st.write(content[:200] + "...")
    else:
        st.info("暂无相关新闻")

# Auto-refresh logic
if auto_refresh:
    time.sleep(5)
    st.rerun()
