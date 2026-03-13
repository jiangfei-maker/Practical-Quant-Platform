import sys
import os
import time
from loguru import logger
import pandas as pd

# 添加项目根目录到 sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.data.financial_fetcher import FinancialDataFetcher
from core.data.db_manager import db_manager

def test_financial_data():
    """测试财务数据获取与入库"""
    logger.info(">>> 开始测试: 财务数据获取 (FinancialDataFetcher)")
    
    fetcher = FinancialDataFetcher()
    stock_code = "600519" # 贵州茅台
    
    # 1. 测试财务指标
    logger.info(f"1. 测试获取 {stock_code} 财务指标...")
    df_indicators = fetcher.get_financial_indicators(stock_code)
    
    if df_indicators is not None and not df_indicators.empty:
        logger.success(f"✅ 财务指标获取成功: {len(df_indicators)} 行")
        
        # 验证数据库
        conn = db_manager.get_connection()
        try:
            result = conn.execute(f"SELECT count(*) FROM finance_indicators WHERE stock_code='{stock_code}'").fetchone()
            if result[0] > 0:
                logger.success(f"✅ 数据库验证成功: finance_indicators 表中已存在 {result[0]} 条记录")
            else:
                logger.error("❌ 数据库验证失败: 表中无数据")
        except Exception as e:
            logger.error(f"❌ 数据库查询失败: {e}")
    else:
        logger.error("❌ 财务指标获取失败")

    # 2. 测试利润表
    logger.info(f"\n2. 测试获取 {stock_code} 利润表...")
    df_income = fetcher.get_income_statement(stock_code)
    
    if df_income is not None and not df_income.empty:
        logger.success(f"✅ 利润表获取成功: {len(df_income)} 行")
        logger.info(f"   列名示例: {list(df_income.columns[:5])}") # 展示中文列名
    else:
        logger.error("❌ 利润表获取失败 (可能受限于网络或 API)")

    # 3. 测试资产负债表
    logger.info(f"\n3. 测试获取 {stock_code} 资产负债表...")
    df_balance = fetcher.get_balance_sheet(stock_code)
    
    if df_balance is not None and not df_balance.empty:
        logger.success(f"✅ 资产负债表获取成功: {len(df_balance)} 行")
    else:
        logger.error("❌ 资产负债表获取失败")

    # 4. 测试现金流量表
    logger.info(f"\n4. 测试获取 {stock_code} 现金流量表...")
    df_cash = fetcher.get_cash_flow(stock_code)
    
    if df_cash is not None and not df_cash.empty:
        logger.success(f"✅ 现金流量表获取成功: {len(df_cash)} 行")
    else:
        logger.error("❌ 现金流量表获取失败")

    # 5. 测试股票列表
    logger.info(f"\n5. 测试获取股票列表 (stock_basic)...")
    df_stocks = fetcher.get_stock_list()
    
    if df_stocks is not None and not df_stocks.empty:
        logger.success(f"✅ 股票列表获取成功: {len(df_stocks)} 行")
        conn = db_manager.get_connection()
        count = conn.execute("SELECT count(*) FROM stock_basic").fetchone()[0]
        logger.success(f"✅ 数据库验证: stock_basic 表现有 {count} 条记录")
    else:
        logger.error("❌ 股票列表获取失败")


def main():
    logger.info("=== 实战量化交易平台 - 数据源验证脚本 ===")
    
    try:
        test_financial_data()
    except Exception as e:
        logger.exception(f"测试过程发生未捕获异常: {e}")
    finally:
        # 关闭数据库连接
        try:
            db_manager.close()
        except:
            pass
        logger.info("=== 测试结束 ===")

if __name__ == "__main__":
    main()
