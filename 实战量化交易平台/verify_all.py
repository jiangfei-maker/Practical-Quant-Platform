
import sys
import os
import pandas as pd
import akshare as ak
from loguru import logger

sys.path.append(os.getcwd())
from core.analysis.market_monitor import MarketMonitor
from core.utils.network_patch import apply_browser_headers_patch

apply_browser_headers_patch()

def verify():
    print("="*50)
    print("VERIFYING ALL MODULES")
    print("="*50)
    
    monitor = MarketMonitor()
    
    # 1. Main Indices
    print("\n[Test 1] Main Indices...")
    try:
        indices = monitor.get_main_indices()
        if indices:
            print(f"✅ Success! Got {len(indices)} indices.")
            for name, df in indices.items():
                print(f"  - {name}: {len(df)} rows. Last close: {df.iloc[-1]['close']}")
        else:
            print("❌ Failed: Empty result")
    except Exception as e:
        print(f"❌ Failed: {e}")

    # 2. Market Breadth (Spot EM)
    print("\n[Test 2] Market Breadth (stock_zh_a_spot_em)...")
    try:
        breadth = monitor.get_market_breadth()
        if breadth:
            print(f"✅ Success! Stats: {breadth.get('stats')}")
        else:
            print("❌ Failed: None result")
    except Exception as e:
        print(f"❌ Failed: {e}")

    # 3. Sector Fund Flow
    print("\n[Test 3] Sector Fund Flow...")
    try:
        flow = monitor.get_sector_fund_flow()
        if not flow.empty:
            print(f"✅ Success! Shape: {flow.shape}")
            print(flow.head(2))
        else:
            print("❌ Failed: Empty DataFrame")
    except Exception as e:
        print(f"❌ Failed: {e}")

    # 4. Sector Stocks (e.g. 银行)
    print("\n[Test 4] Sector Stocks (stock_board_industry_cons_em)...")
    try:
        # Get a sector name first
        sectors = monitor.get_sector_data()
        if not sectors.empty:
            first_sector = sectors.iloc[0]['板块名称']
            print(f"  Testing sector: {first_sector}")
            stocks = monitor.get_sector_stocks(first_sector)
            if not stocks.empty:
                print(f"✅ Success! Shape: {stocks.shape}")
                print(stocks.head(2))
            else:
                print("❌ Failed: Empty Stocks DataFrame")
        else:
            print("❌ Failed: Could not get sectors to test stocks")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    verify()
