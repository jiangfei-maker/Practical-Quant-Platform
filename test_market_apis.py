import akshare as ak
import pandas as pd

def test_market_data():
    print("Testing Market Data Interfaces...")
    
    # 1. Sector Fund Flow
    try:
        print("\nFetching Sector Fund Flow...")
        # stock_sector_fund_flow_rank: 东方财富-板块资金流向
        df_sector = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
        if df_sector is not None and not df_sector.empty:
            print("Sector Fund Flow (Top 5):")
            print(df_sector[['名称', '今日增仓占比', '今日净流入_净额']].head())
        else:
            print("Sector Fund Flow returned empty.")
    except Exception as e:
        print(f"Sector Fund Flow Error: {e}")

    # 2. Northbound Fund Flow (HSGT)
    try:
        print("\nFetching Northbound Fund Flow...")
        # stock_hsgt_north_net_flow_in_em: 东方财富-沪深港通-北向资金-净流入
        df_north = ak.stock_hsgt_north_net_flow_in_em(symbol="北上")
        if df_north is not None and not df_north.empty:
            print("Northbound Fund Flow (Last 5):")
            print(df_north.tail())
        else:
            print("Northbound Fund Flow returned empty.")
    except Exception as e:
        print(f"Northbound Fund Flow Error: {e}")

if __name__ == "__main__":
    test_market_data()
