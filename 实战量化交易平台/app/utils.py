import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from core.data.db_manager import db_manager
from core.strategy.indicator_calculator import IndicatorCalculator
import os

def load_style():
    """Load custom CSS"""
    # Adjust path to find assets relative to this file
    css_file = os.path.join(os.path.dirname(__file__), "assets", "style.css")
    if os.path.exists(css_file):
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def get_db_stats():
    """获取数据库统计信息"""
    stats = {}
    try:
        conn = db_manager.get_connection()
        tables = conn.execute("SHOW TABLES").fetchall()
        for table in tables:
            table_name = table[0]
            count = conn.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
            stats[table_name] = count
    except Exception as e:
        # Fail silently or log
        pass
    return stats

def plot_kline(df, title="K线图", overlays=[], sub_indicator=None):
    """
    绘制专业K线图 (Plotly) - Cyberpunk Theme
    :param overlays: 主图叠加指标 ['MA', 'BOLL']
    :param sub_indicator: 副图指标 'MACD', 'RSI', 'KDJ'
    """
    # Overlays
    if 'MA' in overlays:
        df['MA5'] = IndicatorCalculator.calculate_ma(df, 5)
        df['MA10'] = IndicatorCalculator.calculate_ma(df, 10)
        df['MA20'] = IndicatorCalculator.calculate_ma(df, 20)
        df['MA30'] = IndicatorCalculator.calculate_ma(df, 30)
    
    if 'BOLL' in overlays:
        df['upper'], df['mid'], df['lower'] = IndicatorCalculator.calculate_boll(df)
        
    # Sub-indicators
    if sub_indicator == 'MACD':
        df['dif'], df['dea'], df['macd_hist'] = IndicatorCalculator.calculate_macd(df)
    elif sub_indicator == 'RSI':
        df['rsi'] = IndicatorCalculator.calculate_rsi(df)
    elif sub_indicator == 'KDJ':
        df['k'], df['d'], df['j'] = IndicatorCalculator.calculate_kdj(df)

    # 2. 定义子图结构
    if sub_indicator and sub_indicator != 'None':
        rows = 3
        row_heights = [0.6, 0.2, 0.2]
        subplot_titles = (title, '成交量', sub_indicator)
    else:
        rows = 2
        row_heights = [0.7, 0.3]
        subplot_titles = (title, '成交量')
        
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=subplot_titles, 
                        row_heights=row_heights)

    # --- Row 1: Price ---
    # Candlestick
    # Red Up, Green Down
    fig.add_trace(go.Candlestick(x=df['date'],
                    open=df['open'], high=df['high'],
                    low=df['low'], close=df['close'],
                    increasing_line_color='#ef5350',  # Red for Up
                    decreasing_line_color='#26a69a',  # Green for Down
                    name='K线'), row=1, col=1)
    
    # Overlays
    if 'MA' in overlays:
        fig.add_trace(go.Scatter(x=df['date'], y=df['MA5'], opacity=0.7, line=dict(color='#ffffff', width=1), name='MA5'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['MA10'], opacity=0.7, line=dict(color='#ffe244', width=1), name='MA10'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['MA20'], opacity=0.7, line=dict(color='#ff00ff', width=1), name='MA20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['MA30'], opacity=0.7, line=dict(color='#00ff00', width=1), name='MA30'), row=1, col=1)
        
    if 'BOLL' in overlays:
        fig.add_trace(go.Scatter(x=df['date'], y=df['upper'], line=dict(color='#8b949e', width=1, dash='dot'), name='Upper'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['lower'], line=dict(color='#8b949e', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(200,200,200,0.1)', name='Lower'), row=1, col=1)

    # --- Row 2: Volume ---
    # Red if Close > Open (Up), Green if Close < Open (Down)
    # Wait, df['open'] < df['close'] is Up.
    colors = ['#ef5350' if row['close'] > row['open'] else '#26a69a' for i, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df['date'], y=df['volume'], marker=dict(color=colors), name='成交量'), row=2, col=1)

    # --- Row 3: Sub-indicator ---
    if sub_indicator == 'MACD':
        fig.add_trace(go.Scatter(x=df['date'], y=df['dif'], line=dict(color='#e0e0e0', width=1), name='DIF'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['dea'], line=dict(color='#ffa726', width=1), name='DEA'), row=3, col=1)
        # MACD Bar
        # Red if > 0, Green if < 0 ? Or Up/Down?
        # Usually Red for positive momentum, Green for negative.
        macd_colors = ['#ef5350' if v > 0 else '#26a69a' for v in df['macd_hist']]
        fig.add_trace(go.Bar(x=df['date'], y=df['macd_hist'], marker=dict(color=macd_colors), name='MACD'), row=3, col=1)
        
    elif sub_indicator == 'RSI':
        fig.add_trace(go.Scatter(x=df['date'], y=df['rsi'], line=dict(color='#bc13fe', width=1), name='RSI'), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ef5350", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#26a69a", row=3, col=1)
        
    elif sub_indicator == 'KDJ':
        fig.add_trace(go.Scatter(x=df['date'], y=df['k'], line=dict(color='#e0e0e0', width=1), name='K'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['d'], line=dict(color='#ffa726', width=1), name='D'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['j'], line=dict(color='#bc13fe', width=1), name='J'), row=3, col=1)

    # Layout updates for Cyberpunk
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=700 if sub_indicator and sub_indicator != 'None' else 600,
        margin=dict(l=50, r=50, t=30, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#e0e0e0')),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e0e0'),
        xaxis=dict(showgrid=True, gridcolor='#30363d'),
        yaxis=dict(showgrid=True, gridcolor='#30363d'),
    )
    # Update axes specifically
    fig.update_xaxes(gridcolor='#30363d', zerolinecolor='#30363d')
    fig.update_yaxes(gridcolor='#30363d', zerolinecolor='#30363d')
    
    return fig
