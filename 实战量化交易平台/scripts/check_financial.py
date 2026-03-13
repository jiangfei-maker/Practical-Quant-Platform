import akshare as ak
import pandas as pd

def check_financial_data():
    symbol = "600519" # MaoTai
    print(f"Checking financial data for {symbol}...")

    try:
        print("\n--- Balance Sheet (EM) ---")
        df_balance = ak.stock_balance_sheet_em(symbol=symbol)
        print(df_balance.head(3))
        print(df_balance.columns.tolist())
    except Exception as e:
        print(f"Balance Sheet Error: {e}")

    try:
        print("\n--- Profit Sheet (EM) ---")
        df_profit = ak.stock_profit_sheet_em(symbol=symbol)
        print(df_profit.head(3))
        print(df_profit.columns.tolist())
    except Exception as e:
        print(f"Profit Sheet Error: {e}")

    try:
        print("\n--- Cash Flow Sheet (EM) ---")
        df_cash = ak.stock_cash_flow_sheet_em(symbol=symbol)
        print(df_cash.head(3))
        print(df_cash.columns.tolist())
    except Exception as e:
        print(f"Cash Flow Sheet Error: {e}")

if __name__ == "__main__":
    check_financial_data()
