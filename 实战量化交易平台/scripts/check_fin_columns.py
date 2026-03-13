import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.data.financial_fetcher import FinancialDataFetcher
import pandas as pd

def check_columns():
    fetcher = FinancialDataFetcher()
    df = fetcher.get_financial_summary("600519")
    if df is not None:
        print("Columns:", df.columns.tolist())
        
if __name__ == "__main__":
    check_columns()
