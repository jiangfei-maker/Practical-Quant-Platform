import polars as pl
from loguru import logger

class EnhancedFinancialAnalyzer:
    """
    增强型财务分析器
    包含 Altman Z-Score (破产风险) 和 Beneish M-Score (造假识别)
    """
    
    @staticmethod
    def calculate_z_score(df: pl.DataFrame) -> pl.DataFrame:
        """
        Z = 1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5
        X1 = (流动资产 - 流动负债) / 总资产
        X2 = 留存收益 / 总资产
        X3 = 息税前利润 / 总资产
        X4 = 股东权益市值 / 总负债
        X5 = 营业收入 / 总资产
        """
        # 0. 确保列名标准化 (FinancialFetcher 已做处理，这里做防御性检查)
        # 核心列: total_assets, total_liabilities, total_current_assets, total_current_liabilities, 
        # retained_earnings, ebit(total_profit), market_cap, revenue
        
        # 映射 EBIT: total_profit -> ebit
        if "ebit" not in df.columns and "total_profit" in df.columns:
            df = df.with_columns(pl.col("total_profit").alias("ebit"))
            
        required_cols = [
            "total_assets", "total_liabilities", "total_current_assets", 
            "total_current_liabilities", "retained_earnings", "ebit", 
            "market_cap", "revenue"
        ]
        
        # 检查列是否存在
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            logger.warning(f"Z-Score 计算缺少列: {missing}")
            # 尝试填充 0 以避免报错，但结果可能不准确
            for c in missing:
                df = df.with_columns(pl.lit(0).alias(c))

        try:
            df = df.with_columns([
                ((pl.col("total_current_assets") - pl.col("total_current_liabilities")) / pl.col("total_assets")).fill_nan(0).alias("z_x1"),
                (pl.col("retained_earnings") / pl.col("total_assets")).fill_nan(0).alias("z_x2"),
                (pl.col("ebit") / pl.col("total_assets")).fill_nan(0).alias("z_x3"),
                (pl.col("market_cap") / pl.col("total_liabilities")).fill_nan(0).alias("z_x4"),
                (pl.col("revenue") / pl.col("total_assets")).fill_nan(0).alias("z_x5")
            ])
            
            df = df.with_columns(
                (1.2 * pl.col("z_x1") + 1.4 * pl.col("z_x2") + 3.3 * pl.col("z_x3") + 0.6 * pl.col("z_x4") + 1.0 * pl.col("z_x5")).alias("z_score")
            )
            
            # 风险评级
            df = df.with_columns(
                pl.when(pl.col("z_score") > 2.99).then(pl.lit("Safe"))
                .when(pl.col("z_score") < 1.81).then(pl.lit("Distress"))
                .otherwise(pl.lit("Grey")).alias("z_score_rating")
            )
            
            logger.success("Z-Score 计算完成")
            return df
        except Exception as e:
            logger.error(f"Z-Score 计算错误: {e}")
            return df

    @staticmethod
    def calculate_dupont(df: pl.DataFrame) -> pl.DataFrame:
        """
        杜邦分析 (Dupont Analysis)
        ROE = 销售净利率 x 资产周转率 x 权益乘数
        """
        # 标准列名: net_profit, revenue, total_assets, total_equity
        
        # 计算核心指标
        try:
            # 1. 销售净利率 (Net Profit Margin) = 净利润 / 营业收入
            if "net_profit" in df.columns and "revenue" in df.columns:
                df = df.with_columns((pl.col("net_profit") / pl.col("revenue") * 100).fill_nan(0).alias("dupont_net_margin"))
            
            # 2. 资产周转率 (Asset Turnover) = 营业收入 / 总资产
            if "revenue" in df.columns and "total_assets" in df.columns:
                df = df.with_columns((pl.col("revenue") / pl.col("total_assets")).fill_nan(0).alias("dupont_asset_turnover"))
            
            # 3. 权益乘数 (Equity Multiplier) = 总资产 / 股东权益
            if "total_assets" in df.columns and "total_equity" in df.columns:
                df = df.with_columns((pl.col("total_assets") / pl.col("total_equity")).fill_nan(0).alias("dupont_equity_multiplier"))

            # 4. ROE (计算值)
            # 注意: dupont_net_margin 是百分比 (e.g. 15.0), 其他是比率
            # 结果保持为百分比 (e.g. 15.0)
            if "dupont_net_margin" in df.columns and "dupont_asset_turnover" in df.columns and "dupont_equity_multiplier" in df.columns:
                df = df.with_columns(
                    (pl.col("dupont_net_margin") * pl.col("dupont_asset_turnover") * pl.col("dupont_equity_multiplier")).alias("dupont_roe_calc")
                )
            
            logger.success("杜邦分析指标计算完成")
            return df
        except Exception as e:
            logger.error(f"杜邦分析计算错误: {e}")
            return df

    @staticmethod
    def calculate_4d_score(df: pl.DataFrame) -> dict:
        """
        计算四维能力评分 (0-100)
        返回: {"profit": 80, "growth": 60, "operation": 70, "solvency": 90, "total": 75}
        """
        # 仅取最近一期数据进行评分
        if df.is_empty():
            return {}
        
        latest = df.sort("report_date", descending=True).head(1)
        
        scores = {}
        
        # Helper to safely get value
        def get_val(col, default=0):
            return latest.get_column(col)[0] if col in latest.columns and latest.get_column(col)[0] is not None else default

        # 1. 盈利能力 (Profitability)
        roe = get_val("roe")
        gpm = get_val("gross_margin") # Using standardized name
        if gpm == 0: gpm = get_val("gross_profit_margin") # Fallback
        
        s_roe = min(max(roe * 5, 0), 100) # 20% ROE -> 100分
        s_gpm = min(max(gpm * 2, 0), 100) # 50% GPM -> 100分
        scores["profit"] = (s_roe * 0.7 + s_gpm * 0.3)

        # 2. 成长能力 (Growth)
        # 需计算 YoY
        # 这里假设 df 包含多期数据，我们需要先计算 YoY
        # 但 calculate_4d_score 只接收了 DataFrame，我们无法确定它是否计算了 YoY
        # 尝试使用 fetcher 返回的 'revenue_growth' 字段如果存在 (AkShare 摘要有)
        # 或者 financial_fetcher 并没有自动计算 YoY for detail columns
        # 这里简化使用 'revenue_growth' (营业收入同比增长) 和 'net_profit_growth'
        # 标准化后: 'revenue_growth' might not be standard in our list, check fetcher
        # Fetcher mapping didn't explicitly map growth columns from 'stock_financial_analysis_indicator'
        # But 'stock_financial_analysis_indicator' has '主营业务收入增长率(%)', '净利润增长率(%)'
        # Let's try to access likely keys or default to 0
        
        rev_yoy = get_val("revenue_growth", get_val("主营业务收入增长率(%)"))
        np_yoy = get_val("net_profit_growth", get_val("净利润增长率(%)"))
        
        s_rev = min(max((rev_yoy + 10) * 2, 0), 100) # -10% -> 0分, 40% -> 100分
        s_np = min(max((np_yoy + 10) * 2, 0), 100)
        scores["growth"] = (s_rev * 0.5 + s_np * 0.5)

        # 3. 偿债能力 (Solvency)
        lev = get_val("debt_to_assets")
        if 40 <= lev <= 60:
            s_lev = 100
        elif lev < 40:
            s_lev = 80
        else:
            s_lev = max(100 - (lev - 60) * 2.5, 0)
        scores["solvency"] = s_lev

        # 4. 营运能力 (Operation)
        # 应收账款周转率 = 营业收入 / 应收账款
        # 存货周转率 = 营业成本 / 存货
        revenue = get_val("revenue")
        receivables = get_val("accounts_receivable")
        cogs = get_val("cogs")
        inventory = get_val("inventory")
        
        turnover_receiv = 0
        if receivables > 0:
            turnover_receiv = revenue / receivables
            
        turnover_inv = 0
        if inventory > 0:
            turnover_inv = cogs / inventory
            
        # 评分标准 (行业差异大，这里用通用标准)
        # 应收周转率 > 6 (2个月) -> 100
        # 存货周转率 > 4 (3个月) -> 100
        s_tr = min(max(turnover_receiv * 15, 0), 100)
        s_ti = min(max(turnover_inv * 25, 0), 100)
        
        # 如果没有数据，给默认分
        if receivables == 0 and inventory == 0:
            scores["operation"] = 60
        elif receivables == 0:
            scores["operation"] = s_ti
        elif inventory == 0:
            scores["operation"] = s_tr
        else:
            scores["operation"] = (s_tr * 0.5 + s_ti * 0.5)

        # 总分
        scores["total"] = (scores["profit"] + scores["growth"] + scores["solvency"] + scores["operation"]) / 4
        
        return {k: round(v, 1) for k, v in scores.items()}

    @staticmethod
    def calculate_m_score(df: pl.DataFrame) -> pl.DataFrame:
        """
        计算 Beneish M-Score (造假风险)
        M = -4.84 + 0.92*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI
        需两期数据 (t, t-1)
        """
        # 1. 确保数据按日期升序排列以便 shift
        df = df.sort("report_date")
        
        # 修正: M-Score 仅适用于年度报告 (Month=12)
        # 季度报告是累积值，直接 shift(1) 会导致 (Q3/Q2) 的 SGI 虚高 (e.g. 1.5)，从而误判造假
        # 因此我们提取年报数据进行计算，再合并回主表
        
        # 检查是否为日期类型，如果不是则转换
        if df["report_date"].dtype == pl.Utf8:
            df = df.with_columns(pl.col("report_date").str.to_datetime())

        # 筛选年报
        is_annual = pl.col("report_date").dt.month() == 12
        df_annual = df.filter(is_annual).sort("report_date")
        
        if df_annual.height < 2:
            logger.warning("年报数据不足 2 期，无法计算 M-Score")
            # 返回空列以保持 Schema 一致
            empty_cols = ["m_score", "m_score_rating", "m_dsri", "m_gmi", "m_aqi", "m_sgi", "m_depi", "m_sgai", "m_lvgi", "m_tata"]
            for c in empty_cols:
                df = df.with_columns(pl.lit(None).cast(pl.Float64).alias(c))
            return df

        # 2. 定义计算所需列 (基于 df_annual)
        # revenue, cogs, accounts_receivable, total_assets, total_current_assets, fixed_assets(PPE proxy),
        # total_liabilities, net_profit, cash_flow_op, sales_fee, manage_fee
        
        # 检查关键列
        required = ["revenue", "total_assets"]
        if any(c not in df_annual.columns for c in required):
            logger.warning("M-Score 缺少关键列，跳过计算")
            return df
            
        # 填充缺失列为 0
        cols_needed = [
            "cogs", "accounts_receivable", "total_current_assets", "fixed_assets",
            "total_liabilities", "net_profit", "cash_flow_op", "sales_fee", "manage_fee"
        ]
        for c in cols_needed:
            if c not in df_annual.columns:
                df_annual = df_annual.with_columns(pl.lit(0.0).alias(c))
                
        # 3. 计算中间指标 (Shift 获取上期 - 年报对年报)
        # Helper expressions
        prev = lambda c: pl.col(c).shift(1)
        
        # DSRI: (Rec_t / Rev_t) / (Rec_t-1 / Rev_t-1)
        dsri_expr = (pl.col("accounts_receivable") / pl.col("revenue")) / (prev("accounts_receivable") / prev("revenue"))
        
        # GMI: ((Rev_t-1 - COGS_t-1)/Rev_t-1) / ((Rev_t - COGS_t)/Rev_t)
        # Gross Margin t = (Rev - COGS) / Rev
        gm_t = (pl.col("revenue") - pl.col("cogs")) / pl.col("revenue")
        gm_prev = (prev("revenue") - prev("cogs")) / prev("revenue")
        gmi_expr = gm_prev / gm_t
        
        # AQI: (1 - (CurrAsset_t + PPE_t)/TotalAsset_t) / ...
        # Asset Quality = 1 - (CA + PPE)/TA
        aq_t = 1 - (pl.col("total_current_assets") + pl.col("fixed_assets")) / pl.col("total_assets")
        aq_prev = 1 - (prev("total_current_assets") + prev("fixed_assets")) / prev("total_assets")
        aqi_expr = aq_t / aq_prev
        
        # SGI: Rev_t / Rev_t-1
        sgi_expr = pl.col("revenue") / prev("revenue")
        
        # DEPI: (Dep_t-1 / (Dep_t-1 + PPE_t-1)) / (Dep_t / (Dep_t + PPE_t))
        # 缺少折旧数据，暂设为 1
        depi_expr = pl.lit(1.0)
        
        # SGAI: (SGA_t / Rev_t) / (SGA_t-1 / Rev_t-1)
        sga_t = pl.col("sales_fee") + pl.col("manage_fee")
        sga_prev = prev("sales_fee") + prev("manage_fee")
        sgai_expr = (sga_t / pl.col("revenue")) / (sga_prev / prev("revenue"))
        
        # LVGI: Lev_t / Lev_t-1
        # Lev = Total Liab / Total Assets
        lev_t = pl.col("total_liabilities") / pl.col("total_assets")
        lev_prev = prev("total_liabilities") / prev("total_assets")
        lvgi_expr = lev_t / lev_prev
        
        # TATA: (NetProfit_t - CashFlowOp_t) / TotalAssets_t
        tata_expr = (pl.col("net_profit") - pl.col("cash_flow_op")) / pl.col("total_assets")
        
        # 4. 计算 M-Score
        # M = -4.84 + 0.92*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI
        
        # Handle division by zero or nulls
        # We wrap calculations to fill nulls/infs with 1 (neutral) or 0
        def safe(expr, default=1.0):
            return expr.fill_nan(default).fill_null(default)

        df_annual = df_annual.with_columns([
            safe(dsri_expr).alias("m_dsri"),
            safe(gmi_expr).alias("m_gmi"),
            safe(aqi_expr).alias("m_aqi"),
            safe(sgi_expr).alias("m_sgi"),
            safe(depi_expr).alias("m_depi"),
            safe(sgai_expr).alias("m_sgai"),
            safe(lvgi_expr).alias("m_lvgi"),
            safe(tata_expr, 0.0).alias("m_tata") # TATA default 0
        ])
        
        df_annual = df_annual.with_columns(
            (-4.84 + 
             0.92 * pl.col("m_dsri") + 
             0.528 * pl.col("m_gmi") + 
             0.404 * pl.col("m_aqi") + 
             0.892 * pl.col("m_sgi") + 
             0.115 * pl.col("m_depi") - 
             0.172 * pl.col("m_sgai") + 
             4.679 * pl.col("m_tata") - 
             0.327 * pl.col("m_lvgi")
            ).alias("m_score")
        )
        
        # Rating
        # M > -2.22 suggests possible manipulation (less negative is worse)
        # e.g. -1.0 is High Risk, -3.0 is Low Risk
        df_annual = df_annual.with_columns(
            pl.when(pl.col("m_score") > -2.22).then(pl.lit("Risk"))

            .otherwise(pl.lit("Safe")).alias("m_score_rating")
        )

        # 5. 合并回主表
        # 选择结果列
        res_cols = ["report_date", "m_score", "m_score_rating", "m_dsri", "m_gmi", "m_aqi", "m_sgi", "m_depi", "m_sgai", "m_lvgi", "m_tata"]
        df_res = df_annual.select(res_cols)
        
        # Join back
        # 注意: join 后原来的列可能会有 null (如果非年报)
        df = df.join(df_res, on="report_date", how="left")
        
        logger.success("M-Score 计算完成 (仅年报)")
        return df
