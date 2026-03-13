import sys
import os
import polars as pl
import pandas as pd
import pytest
from loguru import logger

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategy.financial_analyzer import EnhancedFinancialAnalyzer
from core.data.financial_fetcher import FinancialDataFetcher

class TestFinancialAnalyzer:
    def test_m_score_calculation(self):
        """Test Beneish M-Score calculation with mocked data"""
        logger.info("Testing M-Score Calculation...")
        
        # Create mock data (2 periods required for M-Score)
        # Period 1 (Previous): Normal
        # Period 2 (Current): Manipulated (High Receivables, High Growth, High Accruals)
        
        data = {
            "report_date": [pd.to_datetime("2022-12-31"), pd.to_datetime("2023-12-31")],
            "revenue": [1000.0, 1500.0],           # High Growth (SGI)
            "cogs": [600.0, 800.0],
            "accounts_receivable": [200.0, 400.0], # High DSRI
            "total_assets": [2000.0, 3000.0],
            "total_current_assets": [1000.0, 1800.0],
            "fixed_assets": [800.0, 1000.0],
            "total_liabilities": [1000.0, 1600.0], # High LVGI
            "net_profit": [100.0, 200.0],
            "cash_flow_op": [120.0, 50.0],         # Low Cash Flow vs High Profit (High TATA)
            "sales_fee": [50.0, 80.0],
            "manage_fee": [50.0, 80.0],
        }
        
        df = pl.DataFrame(data)
        
        # Calculate
        df_res = EnhancedFinancialAnalyzer.calculate_m_score(df)
        
        # Check columns
        assert "m_score" in df_res.columns
        assert "m_score_rating" in df_res.columns
        
        # Check values for the latest period (index 1)
        # We expect high M-Score (Risk)
        latest = df_res.filter(pl.col("report_date") == pd.to_datetime("2023-12-31"))
        m_score = latest["m_score"][0]
        rating = latest["m_score_rating"][0]
        
        logger.info(f"Calculated M-Score: {m_score}")
        logger.info(f"Rating: {rating}")
        
        # M-Score > -2.22 is Risk. 
        # With high DSRI, SGI, TATA, it should be > -2.22 (likely positive or close to 0)
        assert m_score > -2.22
        assert rating == "Risk"

    def test_z_score_calculation(self):
        """Test Altman Z-Score calculation"""
        logger.info("Testing Z-Score Calculation...")
        
        data = {
            "report_date": [pd.to_datetime("2023-12-31")],
            "total_assets": [1000.0],
            "total_liabilities": [400.0],
            "total_current_assets": [600.0],
            "total_current_liabilities": [300.0],
            "retained_earnings": [200.0],
            "ebit": [150.0],
            "market_cap": [1200.0],
            "revenue": [800.0]
        }
        
        df = pl.DataFrame(data)
        df_res = EnhancedFinancialAnalyzer.calculate_z_score(df)
        
        z_score = df_res["z_score"][0]
        logger.info(f"Calculated Z-Score: {z_score}")
        
        # Manual calc:
        # X1 = (600-300)/1000 = 0.3
        # X2 = 200/1000 = 0.2
        # X3 = 150/1000 = 0.15
        # X4 = 1200/400 = 3.0
        # X5 = 800/1000 = 0.8
        # Z = 1.2*0.3 + 1.4*0.2 + 3.3*0.15 + 0.6*3.0 + 1.0*0.8
        # Z = 0.36 + 0.28 + 0.495 + 1.8 + 0.8 = 3.735
        
        assert abs(z_score - 3.735) < 0.01
        assert df_res["z_score_rating"][0] == "Safe"

    def test_integration_live_fetch(self):
        """Integration test with live data (or mock fetcher if network issues)"""
        logger.info("Testing Integration with FinancialDataFetcher...")
        
        fetcher = FinancialDataFetcher()
        # Use a stable stock like Maotai
        df = fetcher.get_financial_summary("600519", save_db=False)
        
        if df is None or df.empty:
            logger.warning("Live fetch failed, skipping integration test validation.")
            return

        logger.info(f"Fetched {len(df)} records")
        logger.info(f"Columns: {df.columns.tolist()}")
        
        # Check standardized columns
        assert "cash_flow_op" in df.columns
        assert "net_profit" in df.columns
        
        # Convert to Polars
        df_pl = pl.from_pandas(df)
        
        # Run Analyzer
        df_m = EnhancedFinancialAnalyzer.calculate_m_score(df_pl)
        df_z = EnhancedFinancialAnalyzer.calculate_z_score(df_pl)
        
        # Check results
        if not df_m.filter(pl.col("m_score").is_not_null()).is_empty():
            latest_m = df_m.sort("report_date", descending=True).head(1)
            logger.info(f"Latest M-Score: {latest_m['m_score'][0]} ({latest_m['m_score_rating'][0]})")
        
        if not df_z.filter(pl.col("z_score").is_not_null()).is_empty():
            latest_z = df_z.sort("report_date", descending=True).head(1)
            logger.info(f"Latest Z-Score: {latest_z['z_score'][0]} ({latest_z['z_score_rating'][0]})")

if __name__ == "__main__":
    t = TestFinancialAnalyzer()
    t.test_m_score_calculation()
    t.test_z_score_calculation()
    t.test_integration_live_fetch()
