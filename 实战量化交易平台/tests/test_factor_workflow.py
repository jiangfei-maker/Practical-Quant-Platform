
import sys
import os
import pandas as pd
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from core.data.market_crawler import MarketDataCrawler
from core.research.factor_lab import FactorLab

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_factor_workflow():
    print("Testing Factor Analysis Workflow...")
    
    # 1. Fetch Data
    crawler = MarketDataCrawler()
    # Use a few reliable stocks
    codes = ["600519", "000858", "601318"] 
    print(f"Fetching data for {codes}...")
    
    # Fetch short history to be fast
    df = crawler.fetch_batch_daily_data(codes, start_date="20230101", end_date="20230601")
    
    if df.empty:
        print("❌ Data fetch failed! df is empty.")
        return
        
    print(f"✅ Data fetched: {len(df)} rows")
    print(df.head())
    
    # 2. Calculate Factors
    lab = FactorLab()
    factors = ["Momentum", "RSI", "MACD"]
    print(f"Calculating factors: {factors}...")
    
    df_factors = lab.calculate_technical_factors(df, factors)
    
    # Check if factors exist
    factor_cols = [c for c in df_factors.columns if c.startswith('factor_')]
    if not factor_cols:
         print("❌ Factor calculation failed! No factor columns found.")
         return
         
    print(f"✅ Factors calculated: {factor_cols}")
    
    # 3. Calculate Future Returns
    print("Calculating future returns...")
    df_factors = lab.calculate_future_returns(df_factors, periods=[1, 5])
    
    if 'next_ret_5d' not in df_factors.columns:
        print("❌ Future return calculation failed!")
        return
        
    # 4. Evaluate Factors
    print("Evaluating factors...")
    res = lab.evaluate_batch_factors(df_factors, factor_cols, 'next_ret_5d')
    
    if res.empty:
        print("❌ Factor evaluation returned empty result.")
        # Check why
        # Maybe not enough cross-section? 3 stocks might be too few for correlation if dates don't overlap perfectly?
        # But they should.
    else:
        print("✅ Factor evaluation success!")
        print(res)

if __name__ == "__main__":
    test_factor_workflow()
