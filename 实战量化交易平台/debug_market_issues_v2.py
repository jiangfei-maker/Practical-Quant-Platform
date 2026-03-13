
import akshare as ak
import pandas as pd
from core.utils.network_patch import apply_browser_headers_patch
from core.analysis.market_monitor import MarketMonitor

# Apply patch
apply_browser_headers_patch()

monitor = MarketMonitor()

print("="*50)
print("DEBUGGING MARKET ISSUES")
print("="*50)

# 1. Test Sector Fund Flow
print("\n[Test 1] Sector Fund Flow")
try:
    print("Trying ak.stock_sector_fund_flow_rank(indicator='今日')...")
    df_flow = ak.stock_sector_fund_flow_rank(indicator="今日")
    print(f"Result Shape: {df_flow.shape}")
    print("Columns:", df_flow.columns.tolist())
    if not df_flow.empty:
        print(df_flow[['名称', '今日主力净流入-净额']].head())
        # Check values
        val = df_flow['今日主力净流入-净额'].iloc[0]
        print(f"Sample '今日主力净流入-净额' value: {val} (Type: {type(val)})")
except Exception as e:
    print(f"Primary API Failed: {e}")
    try:
        print("Trying Fallback ak.stock_fund_flow_industry(symbol='即时')...")
        df_fallback = ak.stock_fund_flow_industry(symbol="即时")
        print(f"Fallback Result Shape: {df_fallback.shape}")
        print("Columns:", df_fallback.columns.tolist())
        if not df_fallback.empty:
            print(df_fallback.head())
    except Exception as e2:
        print(f"Fallback API Failed: {e2}")

# 2. Test Sector Data (Heatmap)
print("\n[Test 2] Sector Data (Heatmap)")
try:
    print("Trying ak.stock_board_industry_name_em()...")
    df_sector = ak.stock_board_industry_name_em()
    print(f"Result Shape: {df_sector.shape}")
    print("Columns:", df_sector.columns.tolist())
    if not df_sector.empty:
        print(df_sector.head())
        # Check for rising/falling counts
        if '上涨家数' in df_sector.columns:
            print("Found '上涨家数' column.")
        else:
            print("MISSING '上涨家数' column!")
except Exception as e:
    print(f"API Failed: {e}")

# 3. Test Sector Constituents
print("\n[Test 3] Sector Constituents")
test_sector = "半导体" # Try a common sector
try:
    print(f"Trying ak.stock_board_industry_cons_em(symbol='{test_sector}')...")
    df_cons = ak.stock_board_industry_cons_em(symbol=test_sector)
    print(f"Result Shape: {df_cons.shape}")
    if not df_cons.empty:
        print(df_cons.head())
    else:
        print("Result is empty.")
except Exception as e:
    print(f"API Failed: {e}")
