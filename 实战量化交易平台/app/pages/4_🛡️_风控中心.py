import streamlit as st
import pandas as pd
import sys
import os

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(app_dir)
sys.path.append(root_dir)

from core.data.financial_fetcher import FinancialDataFetcher
from core.risk.volatility_predictor import VolatilityPredictor
from app.utils import load_style

st.set_page_config(page_title="风控中心 | 实战量化交易平台", page_icon="🛡️", layout="wide")

load_style()

st.title("🛡️ 全局风控中心 (Risk Management)")

r_col1, r_col2 = st.columns([1, 3])
with r_col1:
    risk_stock = st.text_input("风险评估标的", st.session_state.get('market_code', '600519'), key="risk_stock_input")
    risk_invest = st.number_input("假设持仓金额", value=100000.0, step=10000.0)
    btn_calc_risk = st.button("计算风险指标", type="primary")
    
with r_col2:
    if btn_calc_risk or risk_stock:
        with st.spinner("正在进行蒙特卡洛模拟与波动率分析..."):
            fetcher = FinancialDataFetcher()
            # 获取足够长的历史数据以计算波动率 (至少1年)
            df_hist = fetcher.get_stock_history(risk_stock, start_date="20200101")
            
            if df_hist is not None and len(df_hist) > 60:
                vp = VolatilityPredictor(df_hist)
                
                # 1. VaR 仪表盘
                var_metrics = vp.calculate_var(investment=risk_invest)
                
                st.subheader("核心风险指标 (Key Risk Indicators)")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("当前波动率 (年化)", f"{var_metrics['Current Volatility (Annualized)']}%", help="基于EWMA模型")
                c2.metric("VaR (95%)", f"￥{var_metrics['Parametric VaR (95%)']}", help="参数法: 95%置信度下的最大单日预期亏损")
                c3.metric("历史 VaR (95%)", f"￥{var_metrics['Historical VaR (95%)']}", help="历史模拟法: 基于过去数据分布")
                c4.metric("安全边际 (Z-Score)", var_metrics['Z-Score'])
                
                st.divider()
                
                # 2. 波动率锥 (Volatility Cone)
                st.subheader("波动率锥 (Volatility Cone Analysis)")
                st.caption("分析当前波动率在历史长河中的位置，判断期权/对冲策略的性价比")
                
                cone_data = vp.get_volatility_cone_data()
                if cone_data:
                    # 构造展示数据
                    cone_df_data = []
                    for w, d in cone_data.items():
                        cone_df_data.append({
                            "Window": f"{w}D",
                            "Max": d['Max'],
                            "Min": d['Min'],
                            "Median": d['Median'],
                            "Current": d['Current']
                        })
                    df_cone = pd.DataFrame(cone_df_data)
                    st.dataframe(df_cone, width="stretch")
            else:
                st.warning("数据不足，无法计算风险指标")
