import streamlit as st
import os
import sys

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

# Apply network patch for data source access
try:
    from core.utils.network_patch import apply_browser_headers_patch
    apply_browser_headers_patch()
except ImportError:
    pass

from core.data.db_manager import db_manager
from app.utils import load_style, get_db_stats

st.set_page_config(
    page_title="实战量化交易平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load Custom Style
load_style()

# Initialize Session State
if 'market_code' not in st.session_state:
    st.session_state['market_code'] = '600519'

# Sidebar
with st.sidebar:
    st.header("控制面板")
    st.info("系统状态: 🟢 在线")
    
    # 数据库状态
    st.subheader("数据资产")
    stats = get_db_stats()
    if stats:
        for table, count in stats.items():
            st.caption(f"📊 {table}: {count} 条")
    else:
        st.warning("暂无数据")
        
    st.divider()
    st.markdown("© 2024 实战量化")

# Main Content - Dashboard
st.title("📈 实战量化交易平台 (OPC 版)")

st.markdown("""
### 欢迎回来，交易员
这里是您的全栈量化指挥中心。系统已准备就绪，支持 **Polars** 高速计算与 **DuckDB** 本地存储。
""")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("核心股票池", "1 (演示)", "+1")
with col2:
    st.metric("最新财务数据", "2024-Q3", "Updated")
with col3:
    st.metric("今日信号", "0", "Waiting")

st.divider()

st.markdown("### 🚀 快速导航")
c1, c2, c3 = st.columns(3)
with c1:
    st.info("👉 **实时行情**: 查看个股K线与盘口")
with c2:
    st.info("👉 **策略回测**: 验证您的交易想法")
with c3:
    st.info("👉 **智能投研**: 询问 AI 市场动态")

# Injecting CSS for Cyberpunk glow effect on metrics is handled by load_style()
