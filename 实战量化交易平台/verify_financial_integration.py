import duckdb
import pandas as pd
import polars as pl
from core.data.db_manager import db_manager
from core.data.financial_fetcher import FinancialDataFetcher
from core.strategy.financial_analyzer import EnhancedFinancialAnalyzer
from loguru import logger

def verify_integration():
    logger.info(">>> 开始验证: 财务数据集成与 Z-Score 计算")
    
    conn = db_manager.get_connection()
    
    # 1. 检查并获取数据
    stock_code = "600519"
    logger.info(f"检查 {stock_code} 数据...")
    
    tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
    logger.info(f"现有表: {tables}")
    
    required_tables = ["finance_balance_sheet", "finance_income_statement"]
    missing_tables = [t for t in required_tables if t not in tables]
    
    if missing_tables:
        logger.warning(f"缺少表: {missing_tables}，尝试抓取...")
        fetcher = FinancialDataFetcher()
        fetcher.get_balance_sheet(stock_code)
        fetcher.get_income_statement(stock_code)
    else:
        # Check if data exists for stock
        count = conn.execute(f"SELECT count(*) FROM finance_balance_sheet WHERE stock_code = '{stock_code}'").fetchone()[0]
        if count == 0:
            logger.warning(f"表存在但无 {stock_code} 数据，尝试抓取...")
            fetcher = FinancialDataFetcher()
            fetcher.get_balance_sheet(stock_code)
            fetcher.get_income_statement(stock_code)

    # 2. 构建宽表查询 (Join Balance Sheet and Income Statement)
    # 假设列名是中文: 报告期, 资产总计, ...
    # 关联键: stock_code, 报告期
    
    try:
        # 先检查列名以确定 Join 键
        bs_cols = [c[0] for c in conn.execute("DESCRIBE finance_balance_sheet").fetchall()]
        is_cols = [c[0] for c in conn.execute("DESCRIBE finance_income_statement").fetchall()]
        
        logger.info(f"BS Cols Sample: {bs_cols[:10]}")
        retained_cols = [c for c in bs_cols if "SURPLUS" in c or "RESERVE" in c or "UN" in c]
        logger.info(f"Retained Candidate Cols: {retained_cols}")
        
        income_cols = [c for c in is_cols if "INCOME" in c or "REVENUE" in c or "PROFIT" in c]
        logger.info(f"Income Candidate Cols: {income_cols}")
        
        logger.info(f"IS Cols Count: {len(is_cols)}")
        
        join_key = "报告期" if "报告期" in bs_cols else "REPORT_DATE"
        
        # 简单 Join Query
        #以此为基础构建 app/main.py 的查询
        query = f"""
        SELECT 
            t1.*, 
            t2.* EXCLUDE (stock_code, "{join_key}", updated_at) 
        FROM finance_balance_sheet t1
        JOIN finance_income_statement t2 
        ON t1.stock_code = t2.stock_code AND t1."{join_key}" = t2."{join_key}"
        WHERE t1.stock_code = '{stock_code}'
        ORDER BY t1."{join_key}" DESC
        LIMIT 1
        """
        
        logger.info("执行联合查询...")
        df = conn.execute(query).df()
        
        if df.empty:
            logger.error("联合查询结果为空！")
            return
            
        logger.success(f"查询成功，列数: {len(df.columns)}")
        
        # 3. 计算 Z-Score
        # 补充 Mock 市值 (如果 DB 中没有)
        if "总市值" not in df.columns and "market_cap" not in df.columns:
            df["market_cap"] = 2000000000000.0 # Mock 2T
            
        logger.info("转换 Polars 并计算...")
        pl_df = pl.from_pandas(df)
        analyzer = EnhancedFinancialAnalyzer()
        result = analyzer.calculate_z_score(pl_df)
        
        z_score = result["z_score"][0]
        rating = result["z_score_rating"][0]
        
        logger.success(f"Z-Score: {z_score:.4f} ({rating})")
        
        # 验证 app/main.py 的修复方案
        # 之前 app/main.py 用的是 SELECT * FROM financial_data
        # 我需要把 app/main.py 改成这个 Join 查询
        
    except Exception as e:
        logger.error(f"集成测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    verify_integration()
