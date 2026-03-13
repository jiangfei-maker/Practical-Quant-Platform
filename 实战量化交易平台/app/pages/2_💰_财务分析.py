import streamlit as st
import pandas as pd
import polars as pl
import sys
import os
import asyncio
import importlib
import akshare as ak
import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(app_dir)
sys.path.append(root_dir)

from core.data.db_manager import db_manager
import core.data.financial_fetcher
importlib.reload(core.data.financial_fetcher)
from core.data.financial_fetcher import FinancialDataFetcher

from core.strategy.financial_analyzer import EnhancedFinancialAnalyzer
from core.analysis.valuation_models import ValuationModel
from app.utils import load_style

st.set_page_config(page_title="财务分析 | 实战量化交易平台", page_icon="💰", layout="wide")

load_style()

st.title("💰 财务透视 & 数据浏览")

# Sidebar Controls
with st.sidebar:
    st.header("🎯 分析对象")
    f_stock_code = st.text_input("股票代码", st.session_state.get('market_code', '600519'), key="fin_stock_code")
    btn_analyze = st.button("🚀 开始深度分析", type="primary", key="btn_fin_analyze")
    
    st.divider()
    st.info("💡 说明：\n- 财务概览：核心KPI与Z-Score风险\n- 深度诊断：杜邦分析与能力雷达\n- 行业对标：同业龙头对比分析")

# Main Tabs
tab_overview, tab_deep, tab_peer, tab_val, tab_data = st.tabs(["📊 财务概览", "🧬 深度诊断", "🆚 行业对标", "🧮 估值建模", "💾 数据透视 (DuckDB)"])

# Shared Data Container
data_container = {
    "valuation": None,
    "df_fin_pd": None,
    "df_fin_pl": pl.DataFrame()
}

if btn_analyze or f_stock_code:
    fetcher = FinancialDataFetcher()
    
    # Fetch Basic Data
    with st.spinner("正在获取核心财务数据及研报预测..."):
        try:
            # Parallel fetch
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def fetch_basic():
                v = await fetcher.get_stock_valuation_async(f_stock_code)
                f = await fetcher.get_financial_summary_async(f_stock_code, save_db=False)
                
                # Robustness check for new method (Hotfix for reload issues)
                g = None
                if hasattr(fetcher, 'get_earnings_forecast_async'):
                    g = await fetcher.get_earnings_forecast_async(f_stock_code)
                else:
                    # Fallback implementation if method is missing in loaded class
                    def _get_forecast_fallback(symbol):
                        try:
                            df = ak.stock_profit_forecast_em()
                            if df is not None and not df.empty:
                                row = df[df['代码'] == symbol]
                                if not row.empty:
                                    current_year = datetime.datetime.now().year
                                    eps_curr = row.get(f'{current_year}预测每股收益')
                                    eps_next = row.get(f'{current_year+1}预测每股收益')
                                    if eps_curr is not None and not eps_curr.empty and eps_next is not None and not eps_next.empty:
                                        val_curr = float(eps_curr.iloc[0])
                                        val_next = float(eps_next.iloc[0])
                                        if val_curr > 0:
                                            return round((val_next / val_curr) - 1, 4)
                            return None
                        except Exception:
                            return None
                    
                    g = await loop.run_in_executor(None, _get_forecast_fallback, f_stock_code)
                
                return v, f, g
            
            data_container["valuation"], data_container["df_fin_pd"], data_container["forecast_growth"] = loop.run_until_complete(fetch_basic())
            loop.close()
            
            if data_container["df_fin_pd"] is not None and not data_container["df_fin_pd"].empty:
                data_container["df_fin_pl"] = pl.from_pandas(data_container["df_fin_pd"])
                
                # Inject Market Cap for Z-Score (X4 = Market Value / Total Liabilities)
                # Note: Using current market cap for all historical periods is an approximation.
                # Ideally we should use historical market cap, but that requires daily history matching.
                if data_container["valuation"]:
                    mcap = float(data_container["valuation"].get('总市值', 0) or 0)
                    if mcap > 0:
                        data_container["df_fin_pl"] = data_container["df_fin_pl"].with_columns(
                            pl.lit(mcap).alias("market_cap")
                        )

                
        except Exception as e:
            st.error(f"数据获取失败: {e}")

# --- Tab 1: 财务概览 ---
with tab_overview:
    val = data_container["valuation"]
    df = data_container["df_fin_pd"]
    df_pl = data_container["df_fin_pl"]
    
    if val:
        st.subheader(f"{val.get('股票名称', f_stock_code)} ({f_stock_code}) - 核心指标")
        
        # 1. KPI Cards
        c1, c2, c3, c4 = st.columns(4)
        mkt_cap = float(val.get('总市值', 0) or 0) / 1e8
        pe = val.get('市盈率(动)', val.get('市盈率', 0))
        pb = val.get('市净率', 0)
        
        c1.metric("总市值", f"{mkt_cap:.2f}亿")
        c2.metric("市盈率 (动态)", f"{pe}", help="当前显示为动态市盈率 (PE-Dynamic)，基于当年预测或动态年化净利润计算。")
        c3.metric("市净率 (PB)", f"{pb}")
        c4.metric("所属行业", val.get('行业', '-'))
        
        st.divider()

    if not df_pl.is_empty():
        # 2. Risk Meter (Z-Score & M-Score)
        st.subheader("🛡️ 风险预警")
        
        # Calculate Scores
        z_df = EnhancedFinancialAnalyzer.calculate_z_score(df_pl)
        m_df = EnhancedFinancialAnalyzer.calculate_m_score(df_pl)
        
        latest_z = z_df.sort("report_date", descending=True).head(1)
        
        # M-Score: Find latest NON-NULL value (Annual Report)
        m_valid = m_df.filter(pl.col("m_score").is_not_null()).sort("report_date", descending=True).head(1)
        
        z_score = latest_z["z_score"][0] if "z_score" in latest_z.columns else 0
        z_rating = latest_z["z_score_rating"][0] if "z_score_rating" in latest_z.columns else "Grey"
        
        if not m_valid.is_empty():
            m_score = m_valid["m_score"][0]
            m_rating = m_valid["m_score_rating"][0]
            m_date = m_valid["report_date"][0].strftime("%Y-%m-%d")
            m_note = f"(基于年报: {m_date})"
        else:
            m_score = 0
            m_rating = "N/A"
            m_note = "(数据不足或非年报期)"
        
        col_risk1, col_risk2 = st.columns(2)
        
        with col_risk1:
            st.markdown("##### 📉 破产风险 (Altman Z-Score)")
            fig_gauge_z = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = z_score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                gauge = {
                    'axis': {'range': [None, 5], 'tickwidth': 1},
                    'bar': {'color': "#00ff00" if z_score > 3 else "#ffff00" if z_score > 1.8 else "#ff0000"},
                    'steps': [
                        {'range': [0, 1.8], 'color': 'rgba(255, 0, 0, 0.2)'},
                        {'range': [1.8, 3], 'color': 'rgba(255, 255, 0, 0.2)'},
                        {'range': [3, 5], 'color': 'rgba(0, 255, 0, 0.2)'}],
                    'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 1.81}
                }
            ))
            fig_gauge_z.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_gauge_z, use_container_width=True)
            st.caption(f"评级: **{z_rating}** (Safe > 2.99, Distress < 1.81)")

        with col_risk2:
            st.markdown("##### 🎭 造假风险 (Beneish M-Score)")
            # M-Score typically: < -2.22 is Safe, > -2.22 is Risk (manipulation likely)
            # Range for gauge: -5 to 0?
            fig_gauge_m = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = m_score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                gauge = {
                    'axis': {'range': [-5, 0], 'tickwidth': 1}, # Typical range
                    'bar': {'color': "#00ff00" if m_score < -2.22 else "#ff0000"},
                    'steps': [
                        {'range': [-5, -2.22], 'color': 'rgba(0, 255, 0, 0.2)'}, # Safe
                        {'range': [-2.22, 0], 'color': 'rgba(255, 0, 0, 0.2)'}   # Risk
                    ],
                    'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': -2.22}
                }
            ))
            fig_gauge_m.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_gauge_m, use_container_width=True)
            st.caption(f"评级: **{m_rating}** (Safe < -2.22) {m_note}")

        # 3. Financial Summary Table
        st.subheader("📊 业绩报表摘要")
        
        # Rename columns for display (English -> Chinese)
        display_map = {
            'report_date': '报告期',
            'total_assets': '资产总计',
            'total_liabilities': '负债合计',
            'total_current_assets': '流动资产合计',
            'total_current_liabilities': '流动负债合计',
            'total_equity': '股东权益合计',
            'retained_earnings': '未分配利润',
            'accounts_receivable': '应收账款',
            'inventory': '存货',
            'fixed_assets': '固定资产',
            'revenue': '营业收入',
            'net_profit': '净利润',
            'total_profit': '利润总额',
            'cogs': '营业成本',
            'sales_fee': '销售费用',
            'manage_fee': '管理费用',
            'cash_flow_op': '经营现金流净额',
            'eps': '每股收益',
            'bps': '每股净资产',
            'roe': '净资产收益率',
            'net_margin': '销售净利率',
            'gross_margin': '销售毛利率',
            'debt_to_assets': '资产负债率',
            'revenue_growth': '营收增长率',
            'net_profit_growth': '净利增长率',
            'm_score': 'M-Score(造假)',
            'm_score_rating': 'M-Score评级',
            'z_score': 'Z-Score(破产)',
            'z_score_rating': 'Z-Score评级'
        }
        
        df_display = df.copy()
        df_display = df_display.rename(columns=display_map)
        
        exclude_cols = ['updated_at', '_data_source', 'z_x1', 'z_x2', 'z_x3', 'z_x4', 'z_x5', 
                        'm_dsri', 'm_gmi', 'm_aqi', 'm_sgi', 'm_depi', 'm_sgai', 'm_lvgi', 'm_tata']
        
        display_cols = [c for c in df_display.columns if c not in exclude_cols]
        st.dataframe(df_display[display_cols].style.format("{:.2f}", subset=df_display[display_cols].select_dtypes(include='number').columns), width=1500)

# --- Tab 2: 深度诊断 ---
with tab_deep:
    if not df_pl.is_empty():
        st.subheader("🧬 杜邦分析 (ROE 拆解)")
        dupont_df = EnhancedFinancialAnalyzer.calculate_dupont(df_pl)
        latest_dup = dupont_df.sort("report_date", descending=True).head(1)
        
        if "dupont_roe_calc" in latest_dup.columns:
            roe = latest_dup["dupont_roe_calc"][0]
            net_margin = latest_dup["dupont_net_margin"][0]
            turnover = latest_dup["dupont_asset_turnover"][0]
            multiplier = latest_dup["dupont_equity_multiplier"][0]
            
            c_d1, c_d2, c_d3, c_d4 = st.columns(4)
            c_d1.metric("ROE (净资产收益率)", f"{roe:.2f}%")
            c_d2.metric("= 销售净利率", f"{net_margin:.2f}%", help="反映产品盈利能力")
            c_d3.metric("× 资产周转率", f"{turnover:.2f}", help="反映管理效率")
            c_d4.metric("× 权益乘数", f"{multiplier:.2f}", help="反映财务杠杆")
            
            # 杜邦趋势图
            fig_dup = make_subplots(specs=[[{"secondary_y": True}]])
            dates = dupont_df["report_date"].to_list()
            fig_dup.add_trace(go.Bar(x=dates, y=dupont_df["dupont_roe_calc"], name="ROE", marker_color='#bc13fe'), secondary_y=False)
            fig_dup.add_trace(go.Scatter(x=dates, y=dupont_df["dupont_net_margin"], name="净利率", line=dict(dash='dot')), secondary_y=True)
            fig_dup.update_layout(title="ROE 杜邦分解趋势", height=400)
            st.plotly_chart(fig_dup, use_container_width=True)

        st.divider()
        
        st.subheader("🕸️ 四维能力雷达")
        scores = EnhancedFinancialAnalyzer.calculate_4d_score(df_pl)
        if scores:
            categories = ['盈利能力', '成长能力', '偿债能力', '营运能力']
            values = [scores.get('profit', 0), scores.get('growth', 0), scores.get('solvency', 0), scores.get('operation', 0)]
            
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name=f_stock_code,
                line_color='#00f3ff'
            ))
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100])
                ),
                showlegend=False,
                title=f"综合评分: {scores.get('total', 0)} 分"
            )
            st.plotly_chart(fig_radar, use_container_width=True)

# --- Tab 3: 行业对标 ---
with tab_peer:
    st.subheader("🆚 行业与龙头对比")
    
    val = data_container["valuation"]
    df_pl = data_container["df_fin_pl"]
    
    if val and val.get('行业'):
        industry = val.get('行业')
        st.info(f"当前行业: **{industry}** | 正在对比同业龙头与行业均值")
        
        if st.button("🚀 生成行业深度对比报告", key="btn_peer_compare"):
            fetcher = FinancialDataFetcher()
            with st.spinner(f"正在进行行业大数据分析 (行业: {industry})..."):
                # Run Async
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                stats = loop.run_until_complete(fetcher.get_industry_stats_async(industry, top_n=10))
                loop.close()
            
            if stats:
                st.success("行业数据分析完成！")
                
                # 1. 核心对比卡片
                leader = stats.get('leader', {})
                avg = stats.get('average', {})
                
                c_p1, c_p2, c_p3 = st.columns(3)
                c_p1.metric("行业龙头", f"{leader.get('name')} ({leader.get('symbol')})")
                
                # Get User's Metrics
                # We need to align metrics. Let's use ROE, NetMargin, AssetTurnover, EquityMultiplier
                # User Data
                if not df_pl.is_empty():
                    user_latest = df_pl.sort("report_date", descending=True).head(1)
                    # Helper to safely get value
                    def get_val(row, keys, default=0):
                        for k in keys:
                            if k in row.columns:
                                return row[k][0]
                        return default
                    
                    user_roe = get_val(user_latest, ['roe', '净资产收益率(ROE)', '加权净资产收益率'])
                    user_nm = get_val(user_latest, ['net_margin', '销售净利率', '净利率'])
                else:
                    user_roe = 0
                    user_nm = 0
                
                # Leader Data
                leader_data = leader.get('data') # Series or Dict or DataFrame
                
                if isinstance(leader_data, pd.DataFrame) and not leader_data.empty:
                     leader_data = leader_data.iloc[0]

                if isinstance(leader_data, pd.Series):
                    # Try multiple keys for ROE
                    leader_roe = leader_data.get('roe', 
                                 leader_data.get('净资产收益率(ROE)', 
                                 leader_data.get('净资产收益率', 
                                 leader_data.get('ROE', 0))))
                    
                    leader_nm = leader_data.get('net_margin', 
                                leader_data.get('销售净利率', 
                                leader_data.get('净利率', 0)))
                else:
                    leader_roe = 0
                    leader_nm = 0
                
                # Avg Data
                avg_roe = avg.get('roe', avg.get('净资产收益率(ROE)', 0))
                avg_nm = avg.get('net_margin', avg.get('销售净利率', 0))
                
                c_p2.metric("我的 ROE", f"{user_roe:.2f}%", delta=f"{user_roe - avg_roe:.2f}% vs 均值")
                c_p3.metric("龙头 ROE", f"{leader_roe:.2f}%", delta=f"{leader_roe - avg_roe:.2f}% vs 均值")
                
                st.divider()
                
                # 2. 行业 PK 雷达图 (Normalized)
                # Dimensions: ROE, NetMargin, GrossMargin, DebtRatio (Inverse), Growth
                # We need to fetch/calculate these for all 3 entities
                # For simplicity, let's use: ROE, 净利率, 毛利率, 负债率, 营收增长率
                
                def extract_metrics(data_source):
                    # data_source can be df_pl(Polars), Series(Leader), Dict(Avg)
                    # Normalize to Dict
                    res = {}
                    keys_map = {
                        'ROE': ['roe', '净资产收益率(ROE)', '加权净资产收益率'],
                        '净利率': ['net_margin', '销售净利率', '净利率'],
                        '毛利率': ['gross_margin', '销售毛利率', '毛利率'],
                        '资产负债率': ['debt_to_assets', '资产负债率'],
                        '营收增长率': ['revenue_growth', '营业收入同比增长率', '营收同比增长']
                    }
                    
                    for name, keys in keys_map.items():
                        val = 0
                        for k in keys:
                            if hasattr(data_source, 'columns') and k in data_source.columns: # Polars/Pandas DataFrame
                                val = data_source[k][0]
                                break
                            elif isinstance(data_source, pd.Series) and k in data_source.index:
                                val = data_source[k]
                                break
                            elif isinstance(data_source, dict) and k in data_source:
                                val = data_source[k]
                                break
                        res[name] = float(val) if val else 0
                    return res

                metrics_user = extract_metrics(user_latest)
                metrics_leader = extract_metrics(leader_data)
                metrics_avg = extract_metrics(avg)
                
                # Plot Radar
                categories = list(metrics_user.keys())
                
                fig_pk = go.Figure()
                my_name = val.get("股票名称") if val.get("股票名称") else f_stock_code
                fig_pk.add_trace(go.Scatterpolar(r=[metrics_user[c] for c in categories], theta=categories, fill='toself', name=f'{my_name} (我)', line_color='#00f3ff'))
                fig_pk.add_trace(go.Scatterpolar(r=[metrics_leader[c] for c in categories], theta=categories, fill='toself', name=f'{leader.get("name")} (龙头)', line_color='#ff00ff'))
                fig_pk.add_trace(go.Scatterpolar(r=[metrics_avg[c] for c in categories], theta=categories, fill='toself', name='行业均值', line_color='#ffff00'))
                
                fig_pk.update_layout(
                    polar=dict(radialaxis=dict(visible=True, gridcolor="gray")),
                    title="行业竞争力雷达 (原始数值)",
                    height=500
                )
                st.plotly_chart(fig_pk, use_container_width=True)
                
                # 3. 详细对比表
                st.subheader("📋 详细数据对比")
                compare_df = pd.DataFrame([metrics_user, metrics_leader, metrics_avg], index=[f'{val.get("股票名称")}', f'{leader.get("name")} (龙头)', '行业均值'])
                st.dataframe(compare_df.style.highlight_max(axis=0, color='darkgreen'), use_container_width=True)
                
            else:
                st.warning("未能获取行业有效数据，请稍后重试。")
    else:
        st.info("请先在侧边栏输入有效代码并点击分析以识别行业。")

# --- Tab 4: 估值建模 ---
with tab_val:
    st.subheader("🧮 智能估值建模")
    
    val = data_container["valuation"]
    df_pl = data_container["df_fin_pl"]
    
    if df_pl is not None and not df_pl.is_empty() and val:
        # Prepare Data
        # Sort by date descending (Newest first) - default from fetcher
        # Verify sort?
        if "report_date" in df_pl.columns:
            df_sorted = df_pl.sort("report_date", descending=True)
        else:
            df_sorted = df_pl
            
        # Get inputs for models
        eps_ttm = val.get('每股收益', 0) 
        price = val.get('最新价', 0)
        pe_ttm = val.get('市盈率(动)', 0)
        
        # Calculate EPS TTM if possible for better accuracy
        if price > 0 and pe_ttm > 0:
            eps_ttm = price / pe_ttm
        
        bps = val.get('每股净资产', 0)
        
        # Calculate Growth Rates (Revenue)
        rev_growth = 0.0
        # Check for 'revenue' or '营业总收入' or 'TOTAL_OPERATE_INCOME'
        # Map likely columns
        rev_col = next((c for c in ['revenue', '营业总收入', 'TOTAL_OPERATE_INCOME'] if c in df_sorted.columns), None)
        
        if rev_col:
            rev_series = df_sorted.select(rev_col).to_pandas()[rev_col]
            rev_growth = ValuationModel.get_growth_rate(rev_series)
            
        col_v1, col_v2 = st.columns([1, 2])
        
        with col_v1:
            st.markdown("### 🛠️ 参数设置")
            
            with st.expander("DCF 模型参数", expanded=True):
                wacc = st.slider("WACC (加权平均资本成本)", 0.05, 0.15, 0.08, 0.005)
                perp_growth = st.slider("永续增长率", 0.0, 0.05, 0.02, 0.005)
                
                # Forecast 3 years growth
                default_growth = float(rev_growth)
                forecast_growth = data_container.get("forecast_growth")
                
                growth_label = "未来3年预测增长率 (%)"
                if forecast_growth is not None:
                    growth_label += f" [研报预测: {forecast_growth*100:.2f}%]"
                    default_growth = forecast_growth * 100
                
                growth_assump = st.number_input(growth_label, value=default_growth, step=1.0) / 100
                
            with st.expander("相对估值参数", expanded=True):
                target_pe = st.number_input("目标 PE", value=float(pe_ttm) if pe_ttm > 0 else 15.0)
                peg_target = st.number_input("目标 PEG", value=1.0)
                
        with col_v2:
            st.markdown("### 🎯 估值结果")
            
            # 1. DCF Calculation
            # Need Free Cash Flow.
            # Approximation: Operating Cash Flow (cash_flow_op) if available, else Net Profit
            fcf_col = next((c for c in ['cash_flow_op', 'MANAGE_NETCASH', '经营现金流量净额'] if c in df_sorted.columns), None)
            
            fcf_base = 0.0
            if fcf_col:
                 fcf_base = df_sorted.select(fcf_col).head(1).to_series()[0]
            elif "net_profit" in df_sorted.columns:
                 fcf_base = df_sorted.select("net_profit").head(1).to_series()[0]
            elif "NETPROFIT" in df_sorted.columns:
                 fcf_base = df_sorted.select("NETPROFIT").head(1).to_series()[0]
                 
            # Project FCF
            fcf_projections = []
            current_fcf = fcf_base
            for _ in range(3):
                current_fcf *= (1 + growth_assump)
                fcf_projections.append(current_fcf)
                
            # Net Debt
            # Total Liabilities - Cash
            # We have 'total_liabilities'? Not explicitly in summary.
            # Assume 0 for simplicity or need to fetch Balance Sheet details.
            # Refinement: Use market cap / enterprise value ratio proxy or just 0
            net_debt = 0 
            
            mcap = val.get('总市值', 0)
            shares = mcap / price if price and mcap else 1
            
            dcf_res = ValuationModel.calculate_dcf(fcf_projections, perp_growth, wacc, net_debt, shares)
            
            # 2. PE & PEG
            pe_val = ValuationModel.calculate_pe_valuation(eps_ttm, target_pe)
            peg_val = ValuationModel.calculate_peg_valuation(eps_ttm, growth_assump * 100, peg_target)
            
            # 3. Graham
            graham_val = ValuationModel.calculate_graham_number(eps_ttm, bps)
            
            # Display
            res_col1, res_col2, res_col3, res_col4 = st.columns(4)
            
            def show_res(title, val, current):
                delta = (val - current) / current * 100 if current > 0 else 0
                st.metric(title, f"{val:.2f}", f"{delta:.1f}%")
                
            with res_col1:
                if "fair_price" in dcf_res:
                    show_res("DCF 估值", dcf_res["fair_price"], price)
                else:
                    st.error("DCF 计算错误")
                    
            with res_col2:
                show_res("PE 估值", pe_val, price)
                
            with res_col3:
                show_res("PEG 估值", peg_val, price)
                
            with res_col4:
                if graham_val > 0:
                    show_res("格雷厄姆估值", graham_val, price)
                else:
                    st.metric("格雷厄姆估值", "N/A", help="因每股收益(EPS)或每股净资产(BPS)为负，无法使用格雷厄姆公式估值")
                
            # Chart
            fig_val = go.Figure()
            
            x_vals = ["现价", "DCF", "PE法", "PEG法"]
            y_vals = [price, dcf_res.get("fair_price", 0), pe_val, peg_val]
            colors = ['gray', '#00f3ff', '#bc13fe', '#00ff00']
            
            if graham_val > 0:
                x_vals.append("格雷厄姆")
                y_vals.append(graham_val)
                colors.append('#ff0000')
            
            fig_val.add_trace(go.Bar(
                x=x_vals,
                y=y_vals,
                marker_color=colors,
                text=[f"{x:.2f}" for x in y_vals],
                textposition='auto'
            ))
            fig_val.update_layout(title="估值模型对比", height=400)
            st.plotly_chart(fig_val, use_container_width=True)
            
            st.caption(f"注：DCF 基于近一期自由现金流/净利润 ({fcf_base/1e8:.2f}亿) 推演；PE法基于目标PE ({target_pe})；PEG基于预期增速 ({growth_assump*100:.1f}%)。")
            
    else:
        st.warning("请先获取数据以进行估值建模 (点击左侧'开始深度分析')")

# --- Tab 5: 数据透视 ---
with tab_data:
    st.header("基本面数据浏览器 (DuckDB)")
    try:
        conn = db_manager.get_connection()
        tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
        
        if tables:
            selected_table = st.selectbox("选择数据表", tables)
            limit = st.slider("展示行数", 10, 1000, 50)
            
            df_db = conn.execute(f"SELECT * FROM {selected_table} LIMIT {limit}").df()
            st.dataframe(df_db, width="stretch")
            st.caption(f"展示前 {limit} 行数据，来源: {selected_table}")
        else:
            st.info("数据库为空，请先运行数据采集任务。")
    except Exception as e:
        st.error(f"数据库连接失败: {e}")
