
import sys
import os
import asyncio
import logging

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from core.data.market_crawler import MarketDataCrawler
from loguru import logger

# Configure logger to stdout
logger.remove()
logger.add(sys.stdout, level="INFO")

def test_fetch_stock_basic():
    print("Initializing MarketDataCrawler...")
    crawler = MarketDataCrawler()
    
    print("Calling fetch_and_save_stock_basic()...")
    # This method is synchronous but runs an async loop internally
    result = crawler.fetch_and_save_stock_basic()
    
    print(f"Result: {result}")
    
    # Verify DB content
    from core.data.db_manager import db_manager
    conn = db_manager.get_connection()
    try:
        df = conn.execute("SELECT * FROM stock_basic LIMIT 5").fetch_df()
        print("\nFetched 5 rows from stock_basic:")
        print(df)
        
        # Check industry coverage
        count_unknown = conn.execute("SELECT COUNT(*) FROM stock_basic WHERE industry = '未知'").fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM stock_basic").fetchone()[0]
        print(f"\nTotal stocks: {total}")
        print(f"Unknown industry: {count_unknown}")
        print(f"Coverage: {(total - count_unknown) / total * 100:.2f}%")
        
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    test_fetch_stock_basic()
