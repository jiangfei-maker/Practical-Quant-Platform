
import sys
import os
import pandas as pd
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from core.data.market_crawler import MarketDataCrawler
from core.data.financial_fetcher import FinancialDataFetcher
from core.research.factor_lab import FactorLab
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")

def test_factor_pipeline():
    logger.info("=== Starting Factor Pipeline Test ===")
    
    # 1. Setup
    stock_codes = ['600519', '000858']
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    s_date_str = start_date.strftime("%Y%m%d")
    e_date_str = end_date.strftime("%Y%m%d")
    
    crawler = MarketDataCrawler()
    fetcher = FinancialDataFetcher()
    lab = FactorLab()
    
    # 2. Fetch Market Data
    logger.info("Fetching market data...")
    df_panel = crawler.fetch_batch_daily_data(stock_codes, s_date_str, e_date_str)
    if df_panel.empty:
        logger.error("Failed to fetch market data")
        return
    logger.info(f"Market data fetched: {len(df_panel)} rows")
    
    # 3. Calculate Technical Factors
    logger.info("Calculating technical factors...")
    factors_to_calc = ["Momentum", "RSI", "MACD"]
    df_tech = lab.calculate_technical_factors(
        df_panel, 
        factors_to_calc,
        mom_window=5,
        rsi_window=14
    )
    logger.info(f"Technical factors calculated. Columns: {df_tech.columns.tolist()}")
    
    # 4. Fetch Financial Data
    logger.info("Fetching financial data...")
    fin_data_list = []
    for code in stock_codes:
        try:
            logger.info(f"Fetching financial data for {code}...")
            # Use get_financial_summary instead of get_financial_data
            if hasattr(fetcher, 'get_financial_summary'):
                df_fin = fetcher.get_financial_summary(code)
            else:
                logger.error("FinancialDataFetcher missing get_financial_summary")
                df_fin = None
                
            if df_fin is not None and not df_fin.empty:
                df_fin['stock_code'] = code
                fin_data_list.append(df_fin)
                logger.info(f"Fetched {len(df_fin)} records for {code}")
        except Exception as e:
            logger.error(f"Error fetching {code}: {e}")
            
    if not fin_data_list:
        logger.error("No financial data fetched")
        return

    df_fin_all = pd.concat(fin_data_list)
    if 'report_date' not in df_fin_all.columns and df_fin_all.index.name == 'report_date':
        df_fin_all = df_fin_all.reset_index()
        
    logger.info(f"Financial data merged: {len(df_fin_all)} rows. Columns: {df_fin_all.columns.tolist()}")
    
    # 5. Calculate Fundamental Factors
    logger.info("Calculating fundamental factors...")
    df_final = lab.calculate_fundamental_factors(df_tech, df_fin_all)
    
    # 6. Validation
    expected_factors = ['factor_pe', 'factor_pb', 'factor_roe', 'factor_net_margin']
    found_factors = [f for f in expected_factors if f in df_final.columns]
    
    logger.info(f"Final DataFrame Shape: {df_final.shape}")
    logger.info(f"Fundamental Factors Found: {found_factors}")
    
    if len(found_factors) > 0:
        logger.success("Test Passed: Fundamental factors calculated successfully")
        # Print sample
        print(df_final[['trade_date', 'stock_code', 'close', 'factor_pe', 'factor_roe']].tail(10))
    else:
        logger.error("Test Failed: No fundamental factors found in result")

if __name__ == "__main__":
    test_factor_pipeline()
