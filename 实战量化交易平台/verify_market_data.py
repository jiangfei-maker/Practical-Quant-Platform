import sys
import os
from loguru import logger
from core.data.market_crawler import MarketDataCrawler

# 配置 logger
logger.remove()
logger.add(sys.stderr, level="INFO")

def test_market_crawler():
    logger.info(">>> 开始测试: 市场数据抓取 (MarketDataCrawler)")
    
    stock_code = "600519" # 贵州茅台
    crawler = MarketDataCrawler(headless=True)
    
    try:
        logger.info(f"正在抓取 {stock_code} 的实时盘口与成交明细...")
        crawler.fetch_and_save_data(stock_code)
        logger.success(f"抓取流程完成")
        
        # 验证数据库中的数据
        from core.data.db_manager import db_manager
        conn = db_manager.get_connection()
        
        # 1. 验证 Order Book
        try:
            res = conn.execute("SELECT COUNT(*) FROM market_order_book WHERE stock_code = ?", [stock_code]).fetchone()
            count = res[0]
            if count > 0:
                logger.success(f"✅ market_order_book 验证成功: {count} 条记录")
                # 展示前几条
                df = conn.execute("SELECT * FROM market_order_book WHERE stock_code = ? LIMIT 5", [stock_code]).df()
                logger.info(f"   Order Book 示例:\n{df}")
            else:
                logger.warning("⚠️ market_order_book 为空")
        except Exception as e:
            logger.warning(f"验证 market_order_book 失败 (可能表未创建): {e}")

        # 2. 验证 Transactions
        try:
            res = conn.execute("SELECT COUNT(*) FROM market_transactions WHERE stock_code = ?", [stock_code]).fetchone()
            count = res[0]
            if count > 0:
                logger.success(f"✅ market_transactions 验证成功: {count} 条记录")
                df = conn.execute("SELECT * FROM market_transactions WHERE stock_code = ? LIMIT 5", [stock_code]).df()
                logger.info(f"   Transactions 示例:\n{df}")
            else:
                logger.warning("⚠️ market_transactions 为空")
        except Exception as e:
            logger.warning(f"验证 market_transactions 失败 (可能表未创建): {e}")

    except Exception as e:
        logger.error(f"测试失败: {e}")

if __name__ == "__main__":
    test_market_crawler()
