
import sys
import os
import pandas as pd
from loguru import logger

# Add project root to path
sys.path.append(os.getcwd())

from core.analysis.market_monitor import market_monitor

def test_market_monitor():
    logger.info("Testing Market Monitor...")
    
    # 1. Limit Pool
    logger.info("Fetching Limit Pool...")
    df_limit = market_monitor.get_limit_pool()
    if not df_limit.empty:
        logger.info(f"Limit Pool fetched: {len(df_limit)} records")
        logger.info(f"Columns: {df_limit.columns.tolist()}")
    else:
        logger.warning("Limit Pool is empty (could be non-trading hours or API issue)")

    # 2. Sector Data
    logger.info("Fetching Sector Data...")
    df_sector = market_monitor.get_sector_data()
    if not df_sector.empty:
        logger.info(f"Sector Data fetched: {len(df_sector)} records")
    else:
        logger.error("Sector Data fetch failed")

    # 3. Fund Flow
    logger.info("Fetching Fund Flow...")
    df_flow = market_monitor.get_sector_fund_flow()
    if not df_flow.empty:
        logger.info(f"Fund Flow fetched: {len(df_flow)} records")
    else:
        logger.error("Fund Flow fetch failed")

if __name__ == "__main__":
    test_market_monitor()
