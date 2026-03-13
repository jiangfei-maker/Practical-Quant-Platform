import akshare as ak
import pandas as pd

def check_financial_data_v2():
    symbol = "600519" # MaoTai
    print(f"Checking financial data (v2) for {symbol}...")

    try:
        print("\n--- Balance Sheet (Report) ---")
        df = ak.stock_balance_sheet_by_report_em(symbol=symbol)
        print(df.head(3))
        print(f"Columns: {df.columns.tolist()[:5]} ...")
    except Exception as e:
        print(f"Balance Sheet Error: {e}")

    try:
        print("\n--- Profit Sheet (Report) ---")
        df = ak.stock_profit_sheet_by_report_em(symbol=symbol)
        print(df.head(3))
        print(f"Columns: {df.columns.tolist()[:5]} ...")
    except Exception as e:
        print(f"Profit Sheet Error: {e}")

    try:
        print("\n--- Cash Flow Sheet (Report) ---")
        df = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)
        print(df.head(3))
        print(f"Columns: {df.columns.tolist()[:5]} ...")
    except Exception as e:
        print(f"Cash Flow Sheet Error: {e}")
    
    try:
        print("\n--- Financial Indicators (Main) ---")
        df = ak.stock_financial_analysis_indicator_em(symbol=symbol)
        print(df.head(3))
        print(f"Columns: {df.columns.tolist()[:5]} ...")
    except Exception as e:
        print(f"Indicator Error: {e}")

if __name__ == "__main__":
    check_financial_data_v2()
