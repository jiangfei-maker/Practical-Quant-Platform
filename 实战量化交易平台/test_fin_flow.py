
import asyncio
import pandas as pd
import polars as pl
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from core.data.financial_fetcher import FinancialDataFetcher
from core.strategy.financial_analyzer import EnhancedFinancialAnalyzer

async def test_flow():
    print("--- Starting Financial Analysis Test ---")
    fetcher = FinancialDataFetcher()
    symbol = "600519" # Kweichow Moutai

    # 1. Fetch Valuation
    print(f"Fetching valuation for {symbol}...")
    val = await fetcher.get_stock_valuation_async(symbol)
    print(f"Valuation: {val.get('总市值')} (Industry: {val.get('行业')})")

    # 2. Fetch Financial Summary
    print(f"Fetching financial summary for {symbol}...")
    df_pd = await fetcher.get_financial_summary_async(symbol, save_db=False)
    
    # Try fetch_financial_indicators
    # loop = asyncio.get_event_loop()
    # df_pd = await loop.run_in_executor(None, fetcher.get_financial_indicators, symbol)
    
    if df_pd is not None and not df_pd.empty:
        print(f"Got {len(df_pd)} rows of financial data.")
        print(f"Columns: {df_pd.columns.tolist()}")
        
        # Inject Market Cap (Current) for testing Z-Score
        # In production, we might want historical market cap, but for now we use current
        if val and '总市值' in val:
            df_pd['market_cap'] = val['总市值']
        
        # 3. Convert to Polars
        df_pl = pl.from_pandas(df_pd)
        
        # 4. Run Analysis
        print("Calculating Z-Score...")
        z_df = EnhancedFinancialAnalyzer.calculate_z_score(df_pl)
        print(z_df.select(["report_date", "z_score", "z_score_rating"]).head(1))
        
        print("Calculating Dupont...")
        dup_df = EnhancedFinancialAnalyzer.calculate_dupont(df_pl)
        print(dup_df.select(["report_date", "dupont_roe_calc"]).head(1))
        
        print("Calculating 4D Score...")
        scores = EnhancedFinancialAnalyzer.calculate_4d_score(df_pl)
        print(f"4D Scores: {scores}")
        
    else:
        print("Error: No financial data found.")

    # 4. Test Industry Stats
    if val and '行业' in val:
        ind_name = val['行业']
        print(f"\nFetching Industry Stats for {ind_name}...")
        ind_stats = await fetcher.get_industry_stats_async(ind_name, top_n=3)
        print("Industry Stats Keys:", ind_stats.keys())
        if 'average' in ind_stats:
            print("Avg ROE (approx keys):", [k for k in ind_stats['average'].keys() if 'ROE' in k or '收益' in k])
        if 'leader' in ind_stats:
            print("Leader:", ind_stats['leader']['name'], ind_stats['leader']['symbol'])
            
    print("\n--- Test Complete ---")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_flow())
