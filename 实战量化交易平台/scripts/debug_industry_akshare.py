
import akshare as ak
import pandas as pd
import time

def test_industry_apis():
    print("Testing ak.stock_board_industry_name_em()...")
    try:
        df_ind = ak.stock_board_industry_name_em()
        print(f"Successfully fetched {len(df_ind)} industries.")
        print(df_ind.head())
        
        if not df_ind.empty:
            first_ind = df_ind.iloc[0]['板块名称']
            print(f"\nTesting ak.stock_board_industry_cons_em(symbol='{first_ind}')...")
            df_cons = ak.stock_board_industry_cons_em(symbol=first_ind)
            print(f"Successfully fetched {len(df_cons)} stocks for {first_ind}.")
            print(df_cons.head())
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_industry_apis()
