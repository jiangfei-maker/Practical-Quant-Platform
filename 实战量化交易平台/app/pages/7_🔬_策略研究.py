import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os
import importlib
import asyncio

# 添加根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from core.data.db_manager import db_manager
import core.data.market_crawler
from core.data.financial_fetcher import FinancialDataFetcher
# Force reload to ensure new methods are picked up
import core.research.factor_lab
importlib.reload(core.research.factor_lab)
from core.research.factor_lab import FactorLab
from core.research.model_trainer import ModelTrainer
from core.research.quant_tools import QuantTools

# 页面配置
st.set_page_config(
    page_title="策略研究实验室 Pro",
    page_icon="🔬",
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

# 初始化 Session State
if 'factor_lab' not in st.session_state:
    st.session_state.factor_lab = FactorLab()
if 'model_trainer' not in st.session_state:
    st.session_state.model_trainer = ModelTrainer()
if 'panel_data' not in st.session_state:
    st.session_state.panel_data = pd.DataFrame()

# 初始化 Crawler
crawler = core.data.market_crawler.MarketDataCrawler()

st.title("🔬 量化策略研究实验室 (Institutional Grade)")
st.markdown("---")

# --- Sidebar: 股票池配置 ---
st.sidebar.header("1. 投资域配置 (Universe)")

pool_type = st.sidebar.selectbox(
    "选择股票池",
    ["沪深300 (Top 50 演示)", "中证500 (成长)", "全市场 (A股)", "自选股", "自定义代码"]
)

stock_codes = []
if "沪深300" in pool_type:
    # 演示用 Top 50 权重股
    stock_codes = [
        "600519", "300750", "601318", "600036", "002594", 
        "601888", "000858", "600900", "600809", "600276",
        "000333", "601166", "002415", "603288", "601012",
        "000568", "002714", "600030", "300015", "002352",
        "601328", "601398", "601288", "601939", "601988",
        "600000", "600016", "601628", "601601", "601668",
        "601138", "601390", "601998", "601857", "601088",
        "601800", "601728", "601186", "601989", "601688",
        "000001", "000002", "000776", "000725", "000651",
        "000786", "000895", "000538", "000963", "002001"
    ]
    st.sidebar.caption(f"已选择 {len(stock_codes)} 只权重股")
    
elif "自选股" in pool_type:
    stock_codes = ["600519", "000858", "600887"]
    st.sidebar.caption("模拟自选股列表")

elif "自定义" in pool_type:
    input_codes = st.sidebar.text_area("输入股票代码 (逗号分隔)", "600519, 000001, 000858")
    stock_codes = [c.strip() for c in input_codes.split(",") if c.strip()]

elif "全市场" in pool_type:
    try:
        # 从数据库获取全市场代码
        conn = db_manager.get_connection()
        # 检查表是否存在
        check = conn.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'stock_basic'").fetchone()[0]
        if check > 0:
            df_basic = conn.execute("SELECT code FROM stock_basic").fetch_df()
            stock_codes = df_basic['code'].tolist()
            st.sidebar.success(f"已加载全市场 {len(stock_codes)} 只股票")
        else:
            st.sidebar.error("基础数据表不存在，请先点击下方的'更新基础数据'")
            stock_codes = []
    except Exception as e:
        st.sidebar.error(f"读取全市场数据失败: {e}")
        stock_codes = []
    
else:
    # 模拟其他指数，暂用 Top 50 代替
    stock_codes = ["600519", "000858"]
    st.sidebar.warning("全市场数据量过大，演示模式下仅加载部分股票")

st.sidebar.markdown("---")
st.sidebar.header("2. 回测时间范围")
start_date = st.sidebar.date_input("开始日期", datetime(2022, 1, 1))
end_date = st.sidebar.date_input("结束日期", datetime.now())

# --- Main Tabs ---
# 预先计算因子列列表，供各 Tab 使用
factor_cols = []
if not st.session_state.panel_data.empty:
    factor_cols = [c for c in st.session_state.panel_data.columns if c.startswith('factor_')]

tab1, tab2, tab3, tab4 = st.tabs([
    "⛏️ 因子挖掘 (Data & Factors)", 
    "📊 因子实验室 (Alpha Testing)", 
    "🧠 机器学习建模 (AI Models)",
    "📦 组合管理与实盘 (Portfolio)"
])

# === Tab 1: 因子挖掘 ===
with tab1:
    st.subheader("数据准备与特征工程")
    
    col_a, col_b = st.columns([1, 3])
    
    with col_a:
        st.info("步骤 1: 构建因子库")
        
        all_factors = [
            "Momentum", "Volatility", "RSI", "MACD", 
            "SMA", "EMA", "Bollinger", "CCI", 
            "ROC", "KDJ", "ATR", "OBV", "VWAP",
            "MeanReversion",
            "Alpha006", "Alpha012", "Alpha101",
            "MFI", "CMF"
        ]
        
        # 全选/反选
        if 'select_all_factors' not in st.session_state:
            st.session_state.select_all_factors = False
            
        # Initialize default selection in session state if not present
        # This prevents the "widget created with default value" warning when using session state
        if "factors_multiselect" not in st.session_state:
            st.session_state.factors_multiselect = ["Momentum", "Volatility", "RSI", "MACD", "Alpha101"]

        def toggle_all():
            """Callback to handle 'Select All' checkbox"""
            if st.session_state.get("select_all_factors", False):
                st.session_state.factors_multiselect = all_factors
            else:
                st.session_state.factors_multiselect = ["Momentum", "Volatility", "RSI", "MACD", "Alpha101"]
                
        st.checkbox("全选所有因子", key="select_all_factors", on_change=toggle_all)
        
        # Create widget without 'default' param since it's managed by session_state
        factors_to_calc = st.multiselect(
            "选择技术/量价因子",
            all_factors,
            key="factors_multiselect"
        )
        
        calc_fundamental = st.checkbox("包含基本面因子 (财务估值/成长)", value=True)
        
        if st.button("🚀 生成因子面板数据", type="primary"):
            # Initialize progress components
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.text(f"正在从数据库/API获取 {len(stock_codes)} 只股票数据...")
                s_date_str = start_date.strftime("%Y%m%d")
                e_date_str = end_date.strftime("%Y%m%d")
                
                # 1. 获取行情
                df_panel = crawler.fetch_batch_daily_data(stock_codes, s_date_str, e_date_str)
                progress_bar.progress(20)
                
                if not df_panel.empty:
                    # 模拟行业数据 (如果数据库没有)
                    if 'industry' not in df_panel.columns:
                        # 简单随机模拟几个行业用于演示中性化
                        import numpy as np
                        inds = ['Finance', 'Tech', 'Consumer', 'Energy', 'Healthcare']
                        code_ind_map = {c: np.random.choice(inds) for c in stock_codes}
                        df_panel['industry'] = df_panel['stock_code'].map(code_ind_map)
                    
                    # 2. 计算技术因子
                    status_text.text("正在计算量价技术因子...")
                    df_factors = st.session_state.factor_lab.calculate_technical_factors(
                        df_panel, factors_to_calc
                    )
                    progress_bar.progress(40)
                        
                    # 3. 基本面因子
                    if calc_fundamental:
                        status_text.text("正在匹配财务报表数据...")
                        fetcher = FinancialDataFetcher()
                        fin_data_list = []
                        
                        total_stocks = len(stock_codes)
                        for i, code in enumerate(stock_codes):
                            # Update progress for each stock (mapping 40% -> 80%)
                            # Use max(..., 80) to ensure we don't go backwards or exceed range
                            current_prog = 40 + int((i / total_stocks) * 40)
                            progress_bar.progress(min(current_prog, 80))
                            status_text.text(f"正在匹配财务数据: {code} ({i+1}/{total_stocks})")
                            
                            try:
                                res = fetcher.get_financial_summary(code)
                                if not res.empty:
                                    res['stock_code'] = code
                                    fin_data_list.append(res)
                            except:
                                pass
                        
                        if fin_data_list:
                            status_text.text("正在合并并计算基本面因子...")
                            df_fin = pd.concat(fin_data_list)
                            if 'report_date' not in df_fin.columns and df_fin.index.name == 'report_date':
                                df_fin = df_fin.reset_index()
                            
                            df_factors = st.session_state.factor_lab.calculate_fundamental_factors(
                                df_factors, df_fin
                            )
                    
                    progress_bar.progress(90)
                    
                    # 4. 计算 Target (未来收益)
                    status_text.text("正在计算未来收益 (Target)...")
                    df_factors = st.session_state.factor_lab.calculate_future_returns(
                        df_factors, periods=[1, 5, 10, 20]
                    )
                    
                    st.session_state.panel_data = df_factors
                    progress_bar.progress(100)
                    status_text.success(f"因子库构建完成! Shape: {df_factors.shape}")
                    
                else:
                    progress_bar.empty()
                    status_text.error("未获取到行情数据")
                    
            except Exception as e:
                progress_bar.empty()
                status_text.error(f"发生错误: {str(e)}")

    with col_b:
        if not st.session_state.panel_data.empty:
            st.markdown("##### 因子数据概览")
            st.dataframe(st.session_state.panel_data.head(50), use_container_width=True)
            
            st.markdown("##### 数据完整度检查")
            missing = st.session_state.panel_data.isnull().sum()
            missing = missing[missing > 0]
            if not missing.empty:
                st.bar_chart(missing)
            else:
                st.success("数据完整，无缺失值")

# === Tab 2: 因子分析 (Professional) ===
with tab2:
    st.subheader("因子有效性检验 (Alphalens Framework)")
    
    if st.session_state.panel_data.empty:
        st.warning("请先在 Tab 1 生成数据")
    else:
        df_analysis = st.session_state.panel_data.copy()
        # factor_cols 已在全局计算
        
        # --- 配置区域 ---
        with st.container():
            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                selected_factor = st.selectbox("选择分析因子", factor_cols)
            with c2:
                target_period = st.selectbox("预测周期", [1, 5, 10, 20], index=1, format_func=lambda x: f"{x}日收益 (Lag {x})")
            with c3:
                st.markdown("**预处理设置**")
                do_winsorize = st.checkbox("去极值 (Winsorization)", value=True, help="MAD法，剔除 3倍中位数偏差的异常值")
                do_standardize = st.checkbox("标准化 (Z-Score)", value=True, help="使因子服从标准正态分布，便于比较")
                do_neutralize = st.checkbox("行业中性化 (Ind. Neutral)", value=True, help="剔除行业涨跌幅影响，提取纯 Alpha")

        if st.button("开始专业分析 (Run Alphalens Analysis)", type="primary"):
            with st.spinner("正在进行因子清洗、IC计算与分层回测..."):
                # 1. 预处理
                processed_df = st.session_state.factor_lab.process_factors_pipeline(
                    df_analysis, [selected_factor],
                    do_winsorize=do_winsorize,
                    do_standardize=do_standardize,
                    do_neutralize=do_neutralize,
                    industry_col='industry'
                )
                
                target_col = f'next_ret_{target_period}d'
                
                # 2. 运行 QuantTools 分析
                res = QuantTools.get_factor_performance(
                    processed_df, selected_factor, target_col, groups=5
                )
                
                # --- 展示结果 ---
                
                # A. 核心指标卡片
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Rank IC 均值", f"{res['ic_stats']['mean']:.4f}")
                m2.metric("ICIR (稳定性)", f"{res['ic_stats']['icir']:.2f}", help="IC均值/IC标准差，通常 > 0.5 为优秀")
                m3.metric("多空年化收益", f"{(res['long_short_cum'].iloc[-1]**(252/len(res['long_short_cum'])) - 1)*100:.2f}%")
                m4.metric("多空最大回撤", "计算中...") # 暂略
                
                # B. 分层累积收益图 (最核心图表)
                st.markdown("### 1. 分组累积收益 (Layered Cumulative Returns)")
                st.caption("优秀的因子应该呈现清晰的'喇叭口'发散形态，且具有单调性 (Group 5 > Group 4 > ... > Group 1)")
                
                cum_ret_df = res['cum_returns']
                fig_layer = px.line(cum_ret_df, x=cum_ret_df.index, y=cum_ret_df.columns, 
                                  title=f"{selected_factor} - 5分组累积收益曲线",
                                  labels={"value": "Cumulative Return", "index": "Date", "group": "Quantile"})
                st.plotly_chart(fig_layer, use_container_width=True)
                
                # C. IC 衰减与时序图
                c_left, c_right = st.columns(2)
                with c_left:
                    st.markdown("### 2. IC 时序分布")
                    fig_ic = px.bar(res['ic_series'], x='trade_date', y='ic', title="每日 Rank IC (信息系数)")
                    fig_ic.add_hline(y=res['ic_stats']['mean'], line_dash="dash", line_color="red", annotation_text="Mean IC")
                    st.plotly_chart(fig_ic, use_container_width=True)
                
                with c_right:
                    st.markdown("### 3. 多空对冲净值 (Long-Short)")
                    ls_series = res['long_short_cum']
                    fig_ls = px.line(ls_series, title="多空对冲策略净值 (Top - Bottom)")
                    st.plotly_chart(fig_ls, use_container_width=True)

# === Tab 3: 机器学习建模 (保留原有并优化) ===
with tab3:
    st.subheader("AI 策略建模")
    
    if st.session_state.panel_data.empty:
        st.warning("请先在 Tab 1 准备数据")
    else:
        # 简单配置
        model_type = st.selectbox("选择模型算法", ["RandomForest (随机森林)", "LightGBM (梯度提升)", "Linear (线性回归)"])
        
        features = st.multiselect("选择入模特征 (X)", factor_cols, default=factor_cols[:5] if factor_cols else None)
        label = st.selectbox("选择预测目标 (Y)", [c for c in df_analysis.columns if 'next_ret' in c], index=1)
        
        if st.button("开始训练模型", key="train_btn"):
            with st.spinner("模型训练中..."):
                # 简单清洗
                train_df = st.session_state.panel_data.dropna(subset=features + [label])
                
                # 训练
                # st.session_state.model_trainer.train(train_df, features, label, model_type=model_type.split()[0])
                
                # 1. 准备数据
                dataset = st.session_state.model_trainer.prepare_dataset(train_df, features, label)
                if dataset:
                    # 2. 训练
                    st.session_state.model_trainer.train_model(
                        dataset['X_train'], dataset['y_train'], 
                        model_name=model_type.split()[0]
                    )
                    
                    # 3. 评估
                    eval_res = st.session_state.model_trainer.evaluate_model(dataset['X_test'], dataset['y_test'])
                    if eval_res['status'] == 'success':
                        st.success("训练完成！测试集评估结果：")
                        st.json(eval_res['metrics'])
                        if 'ic' in eval_res:
                            st.metric("测试集 IC", f"{eval_res['ic']:.4f}")
                else:
                    st.error("数据准备失败")
                
                # 特征重要性
                if st.session_state.model_trainer.feature_importance:
                    fi_df = pd.DataFrame(list(st.session_state.model_trainer.feature_importance.items()), columns=['Feature', 'Importance'])
                    fi_df = fi_df.sort_values('Importance', ascending=False)
                    st.bar_chart(fi_df.set_index('Feature'))
                
                # 保存模型选项
                if st.button("保存当前模型"):
                    st.session_state.model_trainer.save_model("models/latest_strategy_model.pkl")
                    st.success("模型已保存至 models/latest_strategy_model.pkl")

# === Tab 4: 组合构建与实盘 (Portfolio) ===
with tab4:
    st.subheader("组合构建与交易计划生成")
    
    st.info("基于已训练的模型或单因子，生成下一交易日的具体买卖计划。")
    
    c1, c2 = st.columns(2)
    with c1:
        strategy_mode = st.radio("策略模式", ["基于单因子排序", "基于AI模型预测"])
        
        if strategy_mode == "基于单因子排序":
            if not factor_cols:
                st.warning("暂无可用因子，请先在 Tab 1 生成数据")
                sel_factor = None
            else:
                sel_factor = st.selectbox("选择排序因子", factor_cols, key="port_factor")
                ascending = st.checkbox("从小到大排序 (如低估值)", value=False)
        else:
            st.write("使用 Tab 3 训练的最新模型进行预测")
            
    with c2:
        top_n = st.number_input("持仓股票数量", 5, 100, 10)
        weight_method = st.selectbox("权重分配方式", ["Equal Weight (等权)", "Risk Parity (波动率倒数)", "Market Cap (市值加权)"])
        capital = st.number_input("计划投入资金 (元)", 100000, 100000000, 1000000)
        
    if st.button("生成调仓计划", type="primary"):
        # 0. 前置检查
        if strategy_mode == "基于单因子排序" and not sel_factor:
            st.error("请先选择排序因子")
            st.stop()

        # 1. 获取最新一天的截面数据
        latest_date = st.session_state.panel_data['trade_date'].max()
        current_pool = st.session_state.panel_data[st.session_state.panel_data['trade_date'] == latest_date].copy()
        
        if current_pool.empty:
            st.error("数据为空")
        else:
            st.write(f"基准日期: {latest_date.date()}")
            
            # 2. 打分/预测
            if strategy_mode == "基于单因子排序":
                current_pool['score'] = current_pool[sel_factor]
                if ascending:
                    current_pool['score'] = -current_pool['score'] # 统一为越大越好
            else:
                # AI 模型预测
                if st.session_state.model_trainer.trained_model:
                    # 确保特征存在
                    feats = st.session_state.model_trainer.feature_names
                    # 填充缺失值以免报错
                    X = current_pool[feats].fillna(0)
                    current_pool['score'] = st.session_state.model_trainer.predict(X)
                else:
                    st.error("请先在 Tab 3 训练模型")
                    st.stop()
            
            # 3. 选股 (Top N)
            target_stocks = current_pool.sort_values('score', ascending=False).head(top_n).copy()
            
            # 4. 优化权重
            # 构造收益率矩阵用于计算波动率 (取过去 60 天)
            # 这里简化：仅使用 close 价格倒推波动率
            # 实际应从数据库取历史序列
            
            if weight_method == "Risk Parity":
                # 简单估算波动率: 使用 factor_volatility_20d (如果存在)
                if 'factor_volatility_20d' in target_stocks.columns:
                    vols = target_stocks['factor_volatility_20d']
                elif 'factor_Volatility' in target_stocks.columns: # 之前计算的通用名
                    vols = target_stocks['factor_Volatility']
                else:
                    st.warning("未找到波动率因子，退化为等权")
                    vols = pd.Series(1, index=target_stocks.index)
                
                inv_vols = 1 / (vols + 1e-6)
                weights = inv_vols / inv_vols.sum()
                target_stocks['weight'] = weights
                
            else:
                # 等权
                target_stocks['weight'] = 1.0 / top_n
                
            # 5. 计算目标仓位
            target_stocks['target_value'] = capital * target_stocks['weight']
            target_stocks['target_shares'] = (target_stocks['target_value'] / target_stocks['close'] / 100).astype(int) * 100
            
            # 6. 展示计划
            st.markdown("### 📋 交易执行计划 (Trade Plan)")
            
            plan_df = target_stocks[['stock_code', 'close', 'score', 'weight', 'target_shares', 'target_value']]
            plan_df['weight'] = plan_df['weight'].apply(lambda x: f"{x*100:.2f}%")
            plan_df['target_value'] = plan_df['target_value'].apply(lambda x: f"¥{x:,.0f}")
            
            # 建议成交算法
            plan_df['execution_algo'] = 'VWAP' # 默认建议
            
            st.dataframe(plan_df, use_container_width=True)
            
            st.info("💡 建议执行算法: 大额订单建议使用 VWAP (成交量加权平均价) 或 TWAP (时间加权) 算法拆单执行，以减少市场冲击。")
            
            # 下载
            csv = plan_df.to_csv().encode('utf-8')
            st.download_button("📥 下载交易清单 (CSV)", csv, "trade_plan.csv", "text/csv")
