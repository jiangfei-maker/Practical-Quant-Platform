import streamlit as st
import pandas as pd
import sys
import os
import plotly.graph_objects as go

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(app_dir)
sys.path.append(root_dir)

from core.strategy.backtest_engine import BacktestEngine
from core.strategy.strategies.dual_ma import DualMAStrategy
from core.strategy.strategies.rsi_bollinger import RSIBollingerStrategy
from core.data.financial_fetcher import FinancialDataFetcher
from app.utils import load_style

st.set_page_config(page_title="策略回测 | 实战量化交易平台", page_icon="🧪", layout="wide")

load_style()

st.title("🧪 策略回测 (Strategy Backtest)")

col_b1, col_b2 = st.columns([1, 3])

with col_b1:
    st.subheader("策略配置")
    strategy_name = st.selectbox("选择策略", ["Dual MA (双均线)", "RSI + Bollinger (均值回归)"])
    
    stock_code = st.text_input("回测标的", "600519", key="bt_stock")
    start_date = st.date_input("开始日期", value=pd.to_datetime("2023-01-01"))
    end_date = st.date_input("结束日期", value=pd.to_datetime("2024-01-01"))
    initial_cash = st.number_input("初始资金", value=100000.0, step=10000.0)
    
    st.divider()
    
    if strategy_name == "Dual MA (双均线)":
        short_window = st.number_input("短期窗口", value=5)
        long_window = st.number_input("长期窗口", value=20)
        strategy = DualMAStrategy(short_window=short_window, long_window=long_window)
        
    elif strategy_name == "RSI + Bollinger (均值回归)":
        rsi_period = st.number_input("RSI 周期", value=14)
        boll_window = st.number_input("布林带窗口", value=20)
        strategy = RSIBollingerStrategy(rsi_period=rsi_period, boll_window=boll_window)

    btn_run_backtest = st.button("开始回测", type="primary")

with col_b2:
    if btn_run_backtest:
        with st.spinner("正在执行回测..."):
            # 1. 获取数据
            fetcher = FinancialDataFetcher()
            df = fetcher.get_stock_history(stock_code, start_date=start_date.strftime("%Y%m%d"), end_date=end_date.strftime("%Y%m%d"))
            
            if df is not None and not df.empty:
                # 2. 运行回测
                engine = BacktestEngine(
                    start_date=start_date.strftime("%Y%m%d"), 
                    end_date=end_date.strftime("%Y%m%d"), 
                    initial_capital=initial_cash,
                    commission_rate=commission_rate,
                    min_commission=min_commission,
                    slippage_rate=slippage_rate
                )
                results = engine.run(strategy=strategy, df=df, symbol=stock_code)
                
                # 3. 展示结果
                st.success("回测完成!")
                
                # 绩效指标
                metrics = results['metrics']
                
                st.subheader("📊 绩效总览")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("总收益率", f"{metrics['total_return']:.2f}%", delta_color="normal")
                c2.metric("年化收益率", f"{metrics['annualized_return']:.2f}%")
                c3.metric("最大回撤", f"{metrics['max_drawdown']:.2f}%", delta_color="inverse")
                c4.metric("夏普比率", f"{metrics['sharpe_ratio']:.2f}")
                
                c5, c6, c7, c8 = st.columns(4)
                c5.metric("交易次数 (Round Trip)", f"{metrics['trade_count']}")
                c6.metric("胜率", f"{metrics['win_rate']:.2f}%")
                c7.metric("盈亏比", f"{metrics['profit_factor']:.2f}")
                c8.metric("平均盈亏", f"{metrics['avg_win']:.0f} / {metrics['avg_loss']:.0f}")

                # 资金曲线
                st.subheader("📈 账户净值 & 回撤")
                portfolio_value = results['portfolio_value']
                # Create DataFrame for plotting
                df_equity = pd.DataFrame({'Date': df['date'], 'Value': portfolio_value})
                # Calculate drawdown series
                df_equity['Max_Value'] = df_equity['Value'].cummax()
                df_equity['Drawdown'] = (df_equity['Value'] - df_equity['Max_Value']) / df_equity['Max_Value']
                
                # Plot Equity
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_equity['Date'], y=df_equity['Value'], mode='lines', name='账户净值', line=dict(color='#00f3ff')))
                
                # Add Drawdown as a filled area below
                fig.add_trace(go.Scatter(
                    x=df_equity['Date'], 
                    y=df_equity['Drawdown'] * df_equity['Value'].max() * 0.2 + df_equity['Value'].min(), # Scale it to fit? No, use secondary y-axis
                    mode='lines', 
                    name='回撤 (右轴)',
                    line=dict(color='rgba(255, 99, 71, 0.5)', width=0),
                    fill='tozeroy',
                    yaxis='y2'
                ))

                fig.update_layout(
                    title="账户净值 vs 回撤",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e0e0e0'),
                    xaxis=dict(showgrid=True, gridcolor='#30363d'),
                    yaxis=dict(title="净值", showgrid=True, gridcolor='#30363d'),
                    yaxis2=dict(
                        title="回撤 (%)",
                        overlaying='y',
                        side='right',
                        showgrid=False,
                        range=[-1, 0.1], # Drawdown is negative
                        tickformat='.0%'
                    ),
                    legend=dict(x=0, y=1, bgcolor='rgba(0,0,0,0.5)')
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # 4. 月度收益热力图 (Monthly Returns Heatmap)
                st.subheader("📅 月度收益表现")
                df_equity['Date'] = pd.to_datetime(df_equity['Date'])
                df_equity.set_index('Date', inplace=True)
                monthly_returns = df_equity['Value'].resample('ME').last().pct_change() * 100
                monthly_returns = monthly_returns.dropna()
                
                if not monthly_returns.empty:
                    # Transform to pivot table: Year vs Month
                    monthly_returns.index = pd.to_datetime(monthly_returns.index)
                    m_df = pd.DataFrame({
                        'Year': monthly_returns.index.year,
                        'Month': monthly_returns.index.month,
                        'Return': monthly_returns.values
                    })
                    pivot_table = m_df.pivot(index='Year', columns='Month', values='Return')
                    
                    # Fill missing months
                    for m in range(1, 13):
                        if m not in pivot_table.columns:
                            pivot_table[m] = float('nan')
                    pivot_table = pivot_table.sort_index(ascending=False).sort_index(axis=1)
                    
                    # Plot Heatmap
                    fig_heat = go.Figure(data=go.Heatmap(
                        z=pivot_table.values,
                        x=pivot_table.columns,
                        y=pivot_table.index,
                        colorscale='RdBu', # Red for loss, Blue for gain? Or RdGn (Red-Green)? 
                        # RdBu: Red is low (loss), Blue is high (gain). In China, Red is Gain.
                        # Custom colorscale: Green (Loss) -> White -> Red (Gain)
                        colorscale=[[0, 'green'], [0.5, 'white'], [1, 'red']],
                        zmid=0,
                        texttemplate="%{z:.1f}%",
                        textfont={"size": 10},
                        xgap=1, ygap=1
                    ))
                    fig_heat.update_layout(
                        title="月度收益率热力图",
                        xaxis_title="月份",
                        yaxis_title="年份",
                        xaxis=dict(tickmode='linear', tick0=1, dtick=1),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#e0e0e0')
                    )
                    st.plotly_chart(fig_heat, use_container_width=True)

                # 交易记录
                st.subheader("📝 交易明细")
                trades = results['trade_history']
                if trades is not None and not trades.empty:
                    df_trades = trades
                    st.dataframe(df_trades, width="stretch")
                    
                    # CSV Export
                    csv = df_trades.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 下载交易记录 CSV",
                        data=csv,
                        file_name=f'trades_{stock_code}_{strategy_name}.csv',
                        mime='text/csv',
                    )
                else:
                    st.info("无交易产生")
                    
            else:
                st.error("无法获取回测数据")
