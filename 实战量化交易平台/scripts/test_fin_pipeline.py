import sys
import os
import duckdb
import pandas as pd
from loguru import logger

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data.financial_fetcher import FinancialDataFetcher
from core.data.db_manager import db_manager

def test_pipeline():
    # 1. Setup Test DB to avoid lock conflicts
    test_db_path = "data/db/test_quant.duckdb"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        
    logger.info(f"Setting up test DB at {test_db_path}")
    db_manager.close()
    db_manager.db_path = test_db_path
    db_manager.conn = None # Force reconnect with new path
    
    # 2. Run Fetcher with save_db=True
    fetcher = FinancialDataFetcher()
    symbol = "600519" # Kweichow Moutai
    logger.info(f"Fetching and saving data for {symbol}...")
    
    df = fetcher.get_financial_summary(symbol, save_db=True)
    
    if df is None:
        logger.error("Failed to fetch data")
        return
        
    logger.info("Fetch completed. Verifying DB content...")
    
    # 3. Verify Data in DB
    conn = duckdb.connect(test_db_path)
    try:
        result = conn.execute("SELECT * FROM financial_statements WHERE stock_code = ?", [symbol]).fetchdf()
        if not result.empty:
            logger.info("✅ Data successfully saved to DB!")
            print(result.head())
            print("Columns:", result.columns.tolist())
            
            # Check core fields
            assert 'revenue' in result.columns
            assert 'net_profit' in result.columns
            assert result.iloc[0]['stock_code'] == symbol
            
            logger.info("Verification Passed.")
        else:
            logger.error("❌ Data not found in DB!")
            
    except Exception as e:
        logger.error(f"Verification failed: {e}")
    finally:
        conn.close()
        # Clean up
        if os.path.exists(test_db_path):
            try:
                os.remove(test_db_path)
                logger.info("Test DB cleaned up.")
            except:
                pass

if __name__ == "__main__":
    test_pipeline()
