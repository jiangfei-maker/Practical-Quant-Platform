
import akshare as ak
import pandas as pd

def check_sector_flow():
    print("Testing stock_sector_fund_flow_rank...")
    try:
        # Try with different parameters if needed. 
        # Documentation usually says sector_type="行业"
        df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业")
        print("Success!")
        print(df.columns)
        print(df.head())
        return
    except Exception as e:
        print(f"Failed with '行业': {e}")

    try:
        print("Testing stock_industry_daily (alternative)...")
        # Sometimes fund flow is separate
        pass
    except Exception as e:
        print(e)

if __name__ == "__main__":
    check_sector_flow()
