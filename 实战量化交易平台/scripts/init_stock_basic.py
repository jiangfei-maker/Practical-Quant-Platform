import sys
import os
import asyncio
from loguru import logger

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data.market_crawler import MarketDataCrawler

def main():
    crawler = MarketDataCrawler()
    logger.info("Starting stock_basic initialization...")
    result = crawler.fetch_and_save_stock_basic()
    logger.info(result)

if __name__ == "__main__":
    main()
