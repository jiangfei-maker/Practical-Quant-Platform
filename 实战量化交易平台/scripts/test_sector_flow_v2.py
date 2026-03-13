
import akshare as ak
import pandas as pd

def check_alternatives():
    print("1. stock_fund_flow_industry(symbol='即时')")
    try:
        df = ak.stock_fund_flow_industry(symbol="即时")
        print("Success 1")
        print(df.head())
    except Exception as e:
        print(f"Fail 1: {e}")

    print("\n2. stock_sector_fund_flow_rank(indicator='今日', sector_type='行业') - Retry")
    try:
        # Maybe it needs no sector_type?
        df = ak.stock_sector_fund_flow_rank(indicator="今日")
        print("Success 2")
        print(df.head())
    except Exception as e:
        print(f"Fail 2: {e}")
        
    print("\n3. stock_sector_fund_flow_rank with sector_type='概念'")
    try:
        df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="概念")
        print("Success 3")
        print(df.head())
    except Exception as e:
        print(f"Fail 3: {e}")

if __name__ == "__main__":
    check_alternatives()
