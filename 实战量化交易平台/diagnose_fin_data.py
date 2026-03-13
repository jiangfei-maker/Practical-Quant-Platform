
import akshare as ak
import pandas as pd

def diagnose():
    symbol = "600519"
    print(f"Fetching data for {symbol}...")
    
    # 1. Abstract
    try:
        df_abs = ak.stock_financial_abstract(symbol=symbol)
        if df_abs is not None and not df_abs.empty:
            print("\n--- Abstract Columns (Row Headers in Transposed) ---")
            print(df_abs['指标'].tolist() if '指标' in df_abs.columns else df_abs.columns.tolist())
            # print first few rows
            # print(df_abs.head())
    except Exception as e:
        print(f"Abstract fetch failed: {e}")

    # 2. Indicator
    try:
        df_ind = ak.stock_financial_analysis_indicator(symbol=symbol)
        if df_ind is not None and not df_ind.empty:
            print("\n--- Indicator Columns ---")
            print(df_ind.columns.tolist())
    except Exception as e:
        print(f"Indicator fetch failed: {e}")

    # 3. Balance Sheet (New - Try 1)
    try:
        # Note: Some EM interfaces require SH/SZ prefix
        df_bal = ak.stock_balance_sheet_by_report_em(symbol="SH" + symbol if symbol.startswith('6') else "SZ" + symbol)
        if df_bal is not None and not df_bal.empty:
            print("\n--- Balance Sheet Columns (EM) ---")
            print(df_bal.columns.tolist())
    except Exception as e:
        print(f"Balance Sheet (EM) fetch failed: {e}")
    
    # 4. Profit Sheet (New - Try 1)
    try:
         df_prof = ak.stock_profit_sheet_by_report_em(symbol="SH" + symbol if symbol.startswith('6') else "SZ" + symbol)
         if df_prof is not None and not df_prof.empty:
            print("\n--- Profit Sheet Columns (EM) ---")
            print(df_prof.columns.tolist())
    except Exception as e:
        print(f"Profit Sheet (EM) fetch failed: {e}")


if __name__ == "__main__":
    diagnose()
