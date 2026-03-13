import streamlit as st
import pandas as pd
import sys
import os
import logging

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(app_dir)
sys.path.append(root_dir)

from core.data.db_manager import db_manager
from core.data.market_crawler import MarketDataCrawler
from core.data.news_fetcher import NewsFetcher
from app.utils import load_style

st.set_page_config(page_title="系统管理 | 实战量化交易平台", page_icon="⚙️", layout="wide")

load_style()

st.title("⚙️ 系统管理 (System Admin)")

col_sys1, col_sys2 = st.columns(2)

with col_sys1:
    st.subheader("数据采集任务")
    
    st.markdown("#### 0. 基础信息更新")
    st.caption("初始化或更新全市场股票列表 (包含代码、名称、行业、市值等)")
    if st.button("更新股票基础信息 (stock_basic)", key="btn_basic_update"):
        with st.spinner("正在获取全市场快照及行业数据..."):
            crawler = MarketDataCrawler()
            msg = crawler.fetch_and_save_stock_basic()
        st.success(msg)

    st.caption("更新全市场核心财务指标 (ROE, 净利润增长率等)")
    if st.button("更新财务选股指标 (stock_financial_indicators)", key="btn_fin_ind_update"):
        from core.data.financial_fetcher import FinancialDataFetcher
        import asyncio
        import nest_asyncio
        
        with st.spinner("正在批量获取财务业绩报表..."):
            fetcher = FinancialDataFetcher()
            # Handle asyncio loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                nest_asyncio.apply()
                msg = loop.run_until_complete(fetcher.fetch_and_save_market_financials())
            else:
                msg = loop.run_until_complete(fetcher.fetch_and_save_market_financials())
        
        st.success(msg)

    st.markdown("#### 1. 市场数据同步")
    
    sync_mode = st.radio("同步范围", ["快速同步 (市值 Top 50)", "深度同步 (市值 Top 300)", "全市场同步 (慎用)"], index=0)
    start_date_sync = st.date_input("起始日期", value=pd.to_datetime("2023-01-01"))
    
    if st.button("启动日线行情更新", key="btn_daily_update"):
        limit = 50
        if "Top 300" in sync_mode:
            limit = 300
        elif "全市场" in sync_mode:
            limit = 0
            
        st.info(f"正在启动同步任务... 目标: {limit if limit > 0 else 'All'} 只股票, 起始: {start_date_sync}")
        
        crawler = MarketDataCrawler()
        # Create a placeholder for progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # We can't easily get real-time progress from the sync method unless we change it to yield or use a callback.
        # For now, just show a spinner.
        with st.spinner("正在后台疯狂抓取数据，请稍候..."):
            msg = crawler.sync_all_stocks_daily_data(limit=limit, start_date=start_date_sync.strftime("%Y%m%d"))
        
        st.success(msg)
        st.toast("行情同步完成！")
            
    st.markdown("#### 2. 新闻舆情同步")
    if st.button("抓取最新财经新闻", key="btn_news_update"):
        with st.spinner("正在抓取新闻..."):
            news_fetcher = NewsFetcher()
            # 模拟抓取
            df_news = news_fetcher.get_financial_news()
            st.success(f"已获取 {len(df_news)} 条新闻")

with col_sys2:
    st.subheader("系统日志")
    log_file = "system.log"
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Show last 20 lines
            st.text_area("Log Output", "".join(lines[-20:]), height=300)
    else:
        st.info("暂无日志文件")
