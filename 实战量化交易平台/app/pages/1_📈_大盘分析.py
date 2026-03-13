import streamlit as st
import sys
import os

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Apply network patch for data source access
from core.utils.network_patch import apply_browser_headers_patch
apply_browser_headers_patch()

# Configure logging to show network patch debug info
import logging
logging.basicConfig(level=logging.INFO)
# Specifically enable debug logs for network patch to see DNS overrides
logging.getLogger("core.utils.network_patch").setLevel(logging.DEBUG)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import importlib
import time
import core.analysis.market_monitor as mm_module

# Force reload the module to ensure latest code is used (dev mode fix)
importlib.reload(mm_module)
from core.analysis.market_monitor import MarketMonitor
import asyncio

# Instantiate locally to ensure latest class definition is used
market_monitor = MarketMonitor()

st.set_page_config(page_title="大盘分析", page_icon="📈", layout="wide")

st.title("📈 大盘全景分析")

# 侧边栏刷新
st.sidebar.subheader("⚙️ 刷新设置")
if st.sidebar.button("🔄 立即刷新"):
    st.cache_data.clear()
    st.rerun()

auto_refresh = st.sidebar.toggle("⏱️ 开启自动刷新")
if auto_refresh:
    refresh_rate = st.sidebar.slider("刷新频率 (秒)", 10, 300, 30)
else:
    refresh_rate = 30

# --- 1. 核心指数 ---
st.subheader("📊 核心指数")

@st.cache_data(ttl=60) # 缓存 1 分钟
def load_index_data():
    return market_monitor.get_main_indices()

@st.cache_data(ttl=60)
def load_sector_stocks(sector):
    return market_monitor.get_sector_stocks(sector)

indices_data = load_index_data()

if indices_data:
    cols = st.columns(3)
    idx_map = {"上证指数": 0, "深证成指": 1, "创业板指": 2}
    
    for name, df in indices_data.items():
        if not df.empty and name in idx_map:
            with cols[idx_map[name]]:
                last_row = df.iloc[-1]
                prev_row = df.iloc[-2]
                change = last_row['close'] - prev_row['close']
                pct_change = (change / prev_row['close']) * 100
                
                # 颜色
                color = "normal"
                if pct_change > 0: color = "normal" # Streamlit metric handles red/green automatically based on delta
                
                st.metric(
                    label=name,
                    value=f"{last_row['close']:.2f}",
                    delta=f"{change:.2f} ({pct_change:.2f}%)",
                    delta_color="inverse"
                )
                
                # 迷你 K 线图
                fig = go.Figure(data=[go.Candlestick(
                    x=df['date'],
                    open=df['open'], high=df['high'],
                    low=df['low'], close=df['close'],
                    increasing_line_color='red', 
                    decreasing_line_color='green'
                )])
                fig.update_layout(
                    xaxis_rangeslider_visible=False,
                    height=200,
                    margin=dict(l=0, r=0, t=0, b=0),
                    yaxis=dict(showgrid=False),
                    xaxis=dict(showgrid=False)
                )
                st.plotly_chart(fig, use_container_width=True)

# --- 2. 市场情绪 ---
st.markdown("---")
st.subheader("🌡️ 市场情绪")

@st.cache_data(ttl=60)
def load_market_breadth():
    return market_monitor.get_market_breadth()

breadth_data = load_market_breadth()

if breadth_data:
    c1, c2 = st.columns([2, 1])
    
    with c1:
        # 涨跌分布直方图
        dist = breadth_data['distribution']
        fig_dist = px.bar(
            x=dist.index, 
            y=dist.values,
            title="全市场涨跌幅分布",
            labels={'x': '涨跌幅区间', 'y': '股票数量'},
            text_auto=True
        )
        # 颜色映射：涨为红，跌为绿
        colors = []
        for label in dist.index:
            if '-' in label and '>' not in label: # 跌
                colors.append('#00AA00') # Green
            elif '0%' in label and ('-' in label or '<' in label): # 跌 (微跌)
                colors.append('#00AA00')
            else:
                colors.append('#FF0000') # Red
        
        fig_dist.update_traces(marker_color=colors)
        st.plotly_chart(fig_dist, use_container_width=True)
        
    with c2:
        # 涨跌停对比
        stats = breadth_data['stats']
        st.markdown(f"**📈 上涨家数**: {stats['up']}")
        st.markdown(f"**📉 下跌家数**: {stats['down']}")
        st.markdown(f"**➖ 平盘家数**: {stats['flat']}")
        st.markdown("---")
        
        # 涨跌停仪表盘 (或简单的对比条)
        limit_df = pd.DataFrame({
            'Type': ['涨停', '跌停'],
            'Count': [stats['limit_up'], stats['limit_down']]
        })
        fig_limit = px.bar(limit_df, x='Type', y='Count', color='Type', 
                          color_discrete_map={'涨停': '#FF0000', '跌停': '#00AA00'},
                          title="涨跌停家数对比")
        st.plotly_chart(fig_limit, use_container_width=True)
        
        # 涨停池详情
        with st.expander("🔥 查看今日涨停池详情"):
            @st.cache_data(ttl=60)
            def load_limit_pool():
                return market_monitor.get_limit_pool()
            
            df_limit = load_limit_pool()
            if not df_limit.empty:
                # 简化展示列
                cols_show = ['代码', '名称', '最新价', '涨跌幅', '成交额', '流通市值', '涨停统计', '连板数', '所属行业']
                # 筛选存在的列
                cols_final = [c for c in cols_show if c in df_limit.columns]
                
                st.dataframe(
                    df_limit[cols_final].sort_values('连板数', ascending=False),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("暂无涨停数据 (非交易时间或接口无数据)")

# --- 3. 板块资金流向 ---
st.markdown("---")
st.subheader("💸 板块资金流向")

@st.cache_data(ttl=300)
def load_fund_flow():
    return market_monitor.get_sector_fund_flow()

df_flow = load_fund_flow()

if not df_flow.empty:
    c_flow1, c_flow2 = st.columns(2)
    
    # 按净流入排序
    df_flow_sorted = df_flow.sort_values('net_inflow_100m', ascending=False)
    
    with c_flow1:
        st.markdown("##### 🔴 主力净流入 Top 10 (亿元)")
        top_inflow = df_flow_sorted.head(10)
        fig_in = px.bar(
            top_inflow, 
            x='net_inflow_100m', 
            y='名称', 
            orientation='h',
            text_auto='.2f',
            color='change_pct',
            color_continuous_scale=['green', 'red'], # 涨跌幅颜色映射
            labels={'net_inflow_100m': '净流入 (亿元)', '名称': '板块', 'change_pct': '涨跌幅(%)'}
        )
        fig_in.update_layout(yaxis={'categoryorder':'total ascending'}) # 最大的在上面
        st.plotly_chart(fig_in, use_container_width=True)
        
    with c_flow2:
        st.markdown("##### 🟢 主力净流出 Top 10 (亿元)")
        top_outflow = df_flow_sorted.tail(10)
        # 净流出通常是负数，取绝对值展示或者直接展示负数
        # 这里直接展示负数，条形图向左
        fig_out = px.bar(
            top_outflow, 
            x='net_inflow_100m', 
            y='名称', 
            orientation='h',
            text_auto='.2f',
            color='change_pct',
            color_continuous_scale=['green', 'red'],
            labels={'net_inflow_100m': '净流出 (亿元)', '名称': '板块', 'change_pct': '涨跌幅(%)'}
        )
        fig_out.update_layout(yaxis={'categoryorder':'total descending'}) # 最小(负得最多)的在上面
        st.plotly_chart(fig_out, use_container_width=True)

# --- 4. 板块热点分析 ---
st.markdown("---")
st.subheader("🔥 板块热点分析")

@st.cache_data(ttl=300) # 缓存 5 分钟
def load_sector_data():
    return market_monitor.get_sector_data()

df_sector = load_sector_data()

if not df_sector.empty:
    # 1. 矩形树图 (Treemap)
    # 颜色映射：红涨绿跌
    # 大小映射：涨跌幅绝对值 (User Request)
    
    # 预处理：确保数值型
    df_sector = df_sector.sort_values('涨跌幅', ascending=False)
    # 计算绝对值用于大小 (加一个微小值避免0)
    df_sector['abs_change'] = df_sector['涨跌幅'].abs() + 0.01
    
    # 交互式筛选
    col_map, col_list = st.columns([3, 1])
    
    with col_map:
        st.markdown("**板块热力图** (面积=涨跌幅绝对值, 颜色=涨跌幅)")
        # 为了颜色映射好看，限制涨跌幅范围在 -5 到 5 之间用于颜色显示
        df_sector['color_val'] = df_sector['涨跌幅'].clip(-5, 5)
        
        fig_tree = px.treemap(
            df_sector,
            path=['板块名称'],
            values='abs_change', # 修改为涨跌幅绝对值
            color='color_val',
            color_continuous_scale=['#00FF00', '#FFFFFF', '#FF0000'], # 绿 -> 白 -> 红
            color_continuous_midpoint=0,
            hover_data=['涨跌幅', '领涨股票', '上涨家数', '下跌家数'],
            custom_data=['涨跌幅']
        )
        # 更新显示文本
        fig_tree.update_traces(
            texttemplate="%{label}<br>%{customdata[0]:.2f}%",
            textposition="middle center"
        )
        st.plotly_chart(fig_tree, use_container_width=True)
        
    with col_list:
        st.markdown("**涨幅 Top 10 板块**")
        st.dataframe(
            df_sector[['板块名称', '涨跌幅', '领涨股票']].head(10).style.format({'涨跌幅': '{:.2f}%'}),
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("**跌幅 Top 10 板块**")
        st.dataframe(
            df_sector[['板块名称', '涨跌幅', '领涨股票']].tail(10).sort_values('涨跌幅').style.format({'涨跌幅': '{:.2f}%'}),
            use_container_width=True,
            hide_index=True
        )

# --- 5. 板块个股透视 ---
st.markdown("---")
st.subheader("🔍 板块个股透视 (个股热力图)")

# 默认选择涨幅最大的板块
default_sector_idx = 0
if not df_sector.empty and '板块名称' in df_sector.columns:
    default_sector = df_sector.iloc[0]['板块名称']
    
    selected_sector = st.selectbox("选择板块查看详情", df_sector['板块名称'].tolist(), index=default_sector_idx)

    if selected_sector:
        df_stocks = load_sector_stocks(selected_sector)
        
        if not df_stocks.empty:
            # 预处理个股数据
            # 确保数值型
            cols_to_numeric = ['最新价', '涨跌幅', '成交量']
            for c in cols_to_numeric:
                if c in df_stocks.columns:
                    df_stocks[c] = pd.to_numeric(df_stocks[c], errors='coerce')
            
            df_stocks['abs_change'] = df_stocks['涨跌幅'].abs() + 0.01
            df_stocks['color_val'] = df_stocks['涨跌幅'].clip(-10, 10) # 个股波动大，范围大一点
            
            c_chart, c_detail = st.columns([3, 1])
            
            with c_chart:
                st.markdown(f"**{selected_sector} - 个股热力图** (面积=涨跌幅绝对值)")
                fig_stock_tree = px.treemap(
                    df_stocks,
                    path=['名称'], # 显示名称
                    values='abs_change',
                    color='color_val',
                    color_continuous_scale=['#00FF00', '#FFFFFF', '#FF0000'],
                    color_continuous_midpoint=0,
                    hover_data=['代码', '最新价', '涨跌幅'],
                    custom_data=['涨跌幅', '代码']
                )
                fig_stock_tree.update_traces(
                    texttemplate="%{label}<br>%{customdata[0]:.2f}%",
                    textposition="middle center"
                )
                st.plotly_chart(fig_stock_tree, use_container_width=True)
                
            with c_detail:
                st.markdown("##### 🚀 个股跳转")
                st.info("点击个股热力图无法直接跳转，请在下方选择后点击按钮。")
                
                # 排序：按涨跌幅绝对值降序，方便找热点
                df_stocks_sorted = df_stocks.sort_values('abs_change', ascending=False)
                stock_options = df_stocks_sorted.apply(lambda x: f"{x['代码']} | {x['名称']} ({x['涨跌幅']:.2f}%)", axis=1).tolist()
                
                target_stock_str = st.selectbox("选择个股", stock_options)
                
                if st.button("📈 前往实时行情", type="primary"):
                    if target_stock_str:
                        code = target_stock_str.split(" | ")[0]
                        # 更新 Session State
                        st.session_state['market_code'] = code
                        # 跳转
                        st.switch_page("pages/1_📈_实时行情.py")

            # 详细列表
            with st.expander(f"查看 {selected_sector} 全部个股列表", expanded=False):
                 st.dataframe(
                    df_stocks[['代码', '名称', '最新价', '涨跌幅', '成交量', '换手率']].style.format({'最新价': '{:.2f}', '涨跌幅': '{:.2f}%', '换手率': '{:.2f}%'}),
                    use_container_width=True
                )

# 自动刷新逻辑
if auto_refresh:
    # 倒计时进度条 (可选优化，但 sleep 会阻塞 UI 更新，所以简单处理)
    time.sleep(refresh_rate)
    st.rerun()
