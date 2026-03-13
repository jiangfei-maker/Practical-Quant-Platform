
import sys
import os
import pandas as pd
import numpy as np

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

from core.data.db_manager import db_manager
from core.research.factor_lab import FactorLab
from core.data.market_crawler import MarketDataCrawler

def check_industry_data():
    print("\n--- Checking Industry Data ---")
    try:
        conn = db_manager.get_connection()
        df = conn.execute("SELECT code, name, industry FROM stock_basic LIMIT 10").fetch_df()
        print("Sample Data:")
        print(df)
        
        count = conn.execute("SELECT COUNT(*) FROM stock_basic WHERE industry IS NOT NULL").fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM stock_basic").fetchone()[0]
        print(f"\nIndustry Coverage: {count}/{total} ({count/total*100:.1f}%)")
    except Exception as e:
        print(f"Error checking industry data: {e}")

def check_factor_calculation():
    print("\n--- Checking Factor Calculation ---")
    codes = ["600519", "000001"]
    start_date = "20240101"
    end_date = "20240201"
    
    crawler = MarketDataCrawler()
    print(f"Fetching data for {codes} from {start_date} to {end_date}...")
    df_panel = crawler.fetch_batch_daily_data(codes, start_date, end_date)
    
    if df_panel.empty:
        print("No data fetched.")
        return

    print(f"Data fetched: {len(df_panel)} rows.")
    print(df_panel.head())
    
    lab = FactorLab()
    factors = [
        "Momentum", "Volatility", "RSI", "MACD", 
        "SMA", "EMA", "Bollinger", "CCI", 
        "ROC", "KDJ", "ATR", "OBV", "VWAP",
        "MeanReversion",
        "Alpha006", "Alpha012", "Alpha101", "Alpha004", "Alpha009", "Alpha054",
        "MFI", "CMF"
    ]
    
    print("\nCalculating factors...")
    df_factors = lab.calculate_technical_factors(df_panel, factors)
    
    # Check for NaNs
    print("\nFactor Stats (NaN Count / Total):")
    factor_cols = [c for c in df_factors.columns if c.startswith('factor_')]
    for col in factor_cols:
        nan_count = df_factors[col].isna().sum()
        mean_val = df_factors[col].mean()
        std_val = df_factors[col].std()
        print(f"{col}: NaNs={nan_count}/{len(df_factors)}, Mean={mean_val:.4f}, Std={std_val:.4f}")

    # Check Future Returns
    print("\nCalculating Future Returns...")
    df_factors = lab.calculate_future_returns(df_factors, periods=[1, 5])
    print(df_factors[['stock_code', 'trade_date', 'close', 'next_ret_1d', 'next_ret_5d']].head())
    print(df_factors[['stock_code', 'trade_date', 'close', 'next_ret_1d', 'next_ret_5d']].tail())

if __name__ == "__main__":
    check_industry_data()
    check_factor_calculation()
