import sys
import os
import pytest
import pandas as pd
from loguru import logger

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from core.data.financial_fetcher import FinancialDataFetcher

def test_fetch_financial_summary():
    fetcher = FinancialDataFetcher()
    symbol = "600519" # Moutai
    
    print(f"Fetching financial summary for {symbol} (Live & Save)...")
    # 1. Fetch Live and Save to DB
    df = fetcher.get_financial_summary(symbol, save_db=True)
    
    if df is None or df.empty:
        print("Failed to fetch data or data is empty.")
        return

    print("Successfully fetched data (Live).")
    # print(df.head())
    # print("Columns:", df.columns.tolist())
    
    # Check for standardized columns
    required_cols = ['total_assets', 'revenue', 'net_profit', 'inventory']
    for col in required_cols:
        if col in df.columns:
            print(f"✅ {col} found in Live data")
            # Handle duplicate columns (though fetcher should have removed them)
            series = df[col]
            if isinstance(series, pd.DataFrame):
                 print(f"   ⚠️ Duplicate columns found for {col}, taking first.")
                 series = series.iloc[:, 0]
            
            if series.notna().sum() > 0:
                 print(f"   Values present for {col}")
            else:
                 print(f"   ⚠️ All values are NaN for {col}")
        else:
            print(f"❌ {col} NOT found in Live data")

    # 2. Load from DB (Cache)
    print("\nLoading financial summary from DB (Cache)...")
    df_db = fetcher._load_from_db(symbol)
    
    if df_db is None or df_db.empty:
        print("❌ Failed to load from DB.")
    else:
        print("Successfully loaded data from DB.")
        # Check if extended columns are present in DB result
        for col in required_cols:
            if col in df_db.columns:
                print(f"✅ {col} found in DB Cache")
                 # Check values match (rough check on first row)
                if col in df.columns:
                     val_live = df.iloc[0][col]
                     val_db = df_db.iloc[0][col]
                     # Handle NaN
                     if pd.isna(val_live) and pd.isna(val_db):
                         pass
                     elif val_live == val_db:
                         pass # Match
                     else:
                         # Floating point tolerance
                         if abs(val_live - val_db) < 0.01:
                             pass
                         else:
                             print(f"   ⚠️ Value mismatch for {col}: Live={val_live}, DB={val_db}")
            else:
                print(f"❌ {col} NOT found in DB Cache (Schema update failed?)")

if __name__ == "__main__":
    test_fetch_financial_summary()
