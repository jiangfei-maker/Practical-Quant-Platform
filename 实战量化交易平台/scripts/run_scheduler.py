import time
import schedule
from loguru import logger
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data.market_crawler import MarketDataCrawler
from core.data.news_fetcher import NewsFetcher

# Configuration
STOCK_POOL = ["600519", "000001", "300750"] # Demo pool
CRAWL_INTERVAL_SECONDS = 30 # Real-time data interval
NEWS_INTERVAL_MINUTES = 60  # News update interval

def job_market_data():
    """Fetch real-time market data for all stocks in pool"""
    logger.info("Starting market data batch job...")
    crawler = MarketDataCrawler(headless=True)
    
    for code in STOCK_POOL:
        try:
            crawler.fetch_and_save_data(code)
        except Exception as e:
            logger.error(f"Failed to fetch market data for {code}: {e}")
            
    logger.info("Market data batch job completed.")

def job_news_update():
    """Fetch latest news"""
    logger.info("Starting news update job...")
    try:
        fetcher = NewsFetcher()
        # Just fetch to trigger cache update or DB save if implemented
        # Currently NewsFetcher mainly returns DF, so we might want to save it.
        # For now, we just log that we are fetching.
        # In a real system, we would save these to a 'news' table.
        logger.info("Fetching CCTV news...")
        fetcher.get_cctv_news()
        logger.info("Fetching Finance news...")
        fetcher.get_finance_news()
        logger.info("News update job completed.")
    except Exception as e:
        logger.error(f"News job failed: {e}")

def run_scheduler():
    logger.info("🚀 Quant Platform Scheduler Started")
    logger.info(f"Market Data Interval: {CRAWL_INTERVAL_SECONDS}s")
    logger.info(f"News Data Interval: {NEWS_INTERVAL_MINUTES}m")
    
    # Schedule jobs
    schedule.every(CRAWL_INTERVAL_SECONDS).seconds.do(job_market_data)
    schedule.every(NEWS_INTERVAL_MINUTES).minutes.do(job_news_update)
    
    # Run immediately once
    job_market_data()
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user.")
            break
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # Check if schedule is installed
    try:
        import schedule
    except ImportError:
        logger.error("Module 'schedule' not found. Please run: pip install schedule")
        sys.exit(1)
        
    run_scheduler()
