
import akshare as ak
import pandas as pd
import time

try:
    print("Fetching tick data for 600519...")
    df = ak.stock_zh_a_tick_tx_js(symbol="sh600519")
    print("Columns:", df.columns.tolist())
    print("Last 5 rows:")
    print(df.tail(5))
    
    if '性质' in df.columns:
        print("Nature column exists.")
        print(df['性质'].unique())
    else:
        print("Nature column MISSING.")

    print("\nFetching bid/ask data for 600519...")
    df_ba = ak.stock_bid_ask_em(symbol="600519")
    print("Bid/Ask Columns:", df_ba.columns.tolist())
    print(df_ba)

except Exception as e:
    print(f"Error: {e}")
