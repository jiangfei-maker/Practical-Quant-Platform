import akshare as ak
import pandas as pd

def test_financial_apis():
    print(f"AkShare Version: {ak.__version__}")
    symbol = "600519"
    
    # 1. Sina
    try:
        print("\n--- Sina Financial Report ---")
        df = ak.stock_financial_report_sina(symbol=symbol, symbol_type="sheet")
        if df is not None:
            print(df.head(3))
        else:
            print("Returned None")
    except Exception as e:
        print(f"Sina Error: {e}")

    # 2. Abstract (NetEase or similar)
    try:
        print("\n--- Financial Abstract ---")
        df = ak.stock_financial_abstract(symbol=symbol)
        if df is not None:
            print(df.head(3))
        else:
            print("Returned None")
    except Exception as e:
        print(f"Abstract Error: {e}")

if __name__ == "__main__":
    test_financial_apis()
