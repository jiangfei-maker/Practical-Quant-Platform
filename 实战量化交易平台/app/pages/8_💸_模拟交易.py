import streamlit as st
import pandas as pd
import time
import sys
import os

# 添加根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from core.trading.simulation_trader import SimulationTrader
from core.data.market_crawler import MarketDataCrawler

# 页面配置
st.set_page_config(
    page_title="模拟交易系统",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 加载全局样式
def load_style():
    try:
        with open("app/assets/style.css", "r", encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except:
        pass

load_style()

# 初始化组件
if 'sim_trader' not in st.session_state:
    st.session_state.sim_trader = SimulationTrader()

@st.cache_resource
def get_crawler():
    return MarketDataCrawler()

crawler = get_crawler()
trader = st.session_state.sim_trader

st.title("💸 模拟交易系统 (Simulation Trading)")
st.markdown("---")

# --- 1. 账户概览 ---
# 实时计算总资产：现金 + 持仓市值
account = trader.get_account_summary()
cash = account['cash']
positions = trader.get_positions()

total_market_value = 0.0
position_updates = []

if not positions.empty:
    # 获取实时价格
    with st.spinner("正在刷新持仓市值..."):
        for index, row in positions.iterrows():
            code = row['stock_code']
            # 优先用 crawler 获取实时数据
            # 这里简化处理，假设 fetch_stock_info 返回包含 price
            # 但 crawler 主要是 fetch_daily_data, 我们可以用 akshare 的实时接口
            # 或者简单复用 crawler.fetch_and_save_daily_data 的最新收盘价 (如果是盘后)
            # 为了体验，我们最好有一个 get_realtime_price
            
            # 临时方案：尝试获取日线最新价
            try:
                import akshare as ak
                df_rt = ak.stock_zh_a_spot_em()
                price_row = df_rt[df_rt['代码'] == code]
                if not price_row.empty:
                    current_price = float(price_row.iloc[0]['最新价'])
                    name = price_row.iloc[0]['名称']
                else:
                    current_price = row['avg_cost'] # Fallback
                    name = row['stock_name']
            except:
                current_price = row['avg_cost']
                name = row['stock_name']
                
            mkt_val = current_price * row['quantity']
            pnl = (current_price - row['avg_cost']) * row['quantity']
            pnl_pct = (current_price / row['avg_cost'] - 1) * 100 if row['avg_cost'] > 0 else 0
            
            total_market_value += mkt_val
            
            position_updates.append({
                "代码": code,
                "名称": name,
                "持仓量": row['quantity'],
                "成本价": row['avg_cost'],
                "现价": current_price,
                "市值": mkt_val,
                "浮动盈亏": pnl,
                "盈亏比例": f"{pnl_pct:.2f}%"
            })

total_assets = cash + total_market_value

# 更新数据库中的总资产记录 (可选)
# trader.update_total_assets(total_assets)

c1, c2, c3, c4 = st.columns(4)
c1.metric("总资产 (Total Assets)", f"¥{total_assets:,.2f}")
c2.metric("可用资金 (Cash)", f"¥{cash:,.2f}")
c3.metric("持仓市值 (Market Value)", f"¥{total_market_value:,.2f}")
c4.metric("总盈亏 (Total PnL)", f"¥{total_assets - 1000000:,.2f}", 
          delta_color="normal" if total_assets >= 1000000 else "inverse")

st.markdown("---")

# --- 2. 交易面板 ---
col_trade, col_data = st.columns([1, 2])

with col_trade:
    st.subheader("下单交易")
    
    trade_action = st.radio("交易方向", ["买入 (Buy)", "卖出 (Sell)"], horizontal=True)
    
    t_code = st.text_input("股票代码", "600519")
    
    # 获取实时价格用于填入默认值
    current_price_ref = 0.0
    stock_name_ref = ""
    
    if len(t_code) == 6:
        try:
            import akshare as ak
            df_rt = ak.stock_zh_a_spot_em()
            price_row = df_rt[df_rt['代码'] == t_code]
            if not price_row.empty:
                current_price_ref = float(price_row.iloc[0]['最新价'])
                stock_name_ref = price_row.iloc[0]['名称']
                st.caption(f"当前行情: {stock_name_ref} ¥{current_price_ref}")
        except:
            pass
            
    t_price = st.number_input("委托价格", min_value=0.01, value=current_price_ref if current_price_ref > 0 else 100.0, step=0.01)
    t_qty = st.number_input("委托数量", min_value=100, value=100, step=100)
    
    if st.button("提交订单 (Submit Order)", type="primary", use_container_width=True):
        action_code = "BUY" if "Buy" in trade_action else "SELL"
        res = trader.place_order(t_code, action_code, t_price, t_qty, stock_name_ref)
        
        if res['status'] == 'success':
            st.success("✅ 订单已提交并成交！")
            time.sleep(1)
            st.rerun()
        else:
            st.error(f"❌ 下单失败: {res['message']}")

with col_data:
    tab1, tab2 = st.tabs(["📊 当前持仓", "📝 交易记录"])
    
    with tab1:
        if position_updates:
            df_pos = pd.DataFrame(position_updates)
            st.dataframe(df_pos, use_container_width=True, hide_index=True)
        else:
            st.info("暂无持仓")
            
    with tab2:
        df_orders = trader.get_orders()
        if not df_orders.empty:
            st.dataframe(df_orders, use_container_width=True, hide_index=True)
        else:
            st.info("暂无交易记录")

# --- 3. 管理功能 ---
with st.expander("🔧 账户管理"):
    if st.button("⚠️ 重置模拟账户 (Reset Account)"):
        trader.reset_account()
        st.warning("账户已重置为初始状态 (¥1,000,000)")
        time.sleep(1)
        st.rerun()
