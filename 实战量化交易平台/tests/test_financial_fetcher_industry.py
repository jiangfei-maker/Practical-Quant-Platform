import unittest
import asyncio
from loguru import logger
import pandas as pd
import sys
import os

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

from core.data.financial_fetcher import FinancialDataFetcher

class TestFinancialFetcherIndustry(unittest.TestCase):
    def setUp(self):
        self.fetcher = FinancialDataFetcher()

    def test_get_industry_stats_live(self):
        """Test fetching industry stats for a known industry (e.g. '白酒')"""
        logger.info("Testing Industry Stats Fetching...")
        
        industry = "白酒"
        
        # Use asyncio to run the async method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            stats = loop.run_until_complete(self.fetcher.get_industry_stats_async(industry, top_n=5))
            
            if not stats:
                logger.warning(f"No stats returned for {industry}. API might be unstable.")
                return

            logger.info(f"Industry Stats Keys: {stats.keys()}")
            
            self.assertIn("industry_name", stats)
            self.assertEqual(stats["industry_name"], industry)
            
            self.assertIn("leader", stats)
            leader = stats["leader"]
            logger.info(f"Leader: {leader.get('name')} ({leader.get('symbol')})")
            self.assertTrue(leader.get('symbol'))
            
            self.assertIn("average", stats)
            avg = stats["average"]
            logger.info(f"Average Metrics: {avg}")
            
            # Check if we have key metrics
            # Note: keys depend on standardization. 
            # We expect 'roe', 'net_margin', etc. if standardization worked on the fetched data
            # The fetched data comes from get_financial_summary_async which standardizes columns.
            
            expected_metrics = ['roe', 'net_margin', 'gross_margin', 'revenue_growth']
            found_any = False
            for k in expected_metrics:
                if k in avg:
                    found_any = True
                    break
            
            if not found_any:
                 # It might be using Chinese keys if standardization failed or raw data used?
                 # get_financial_summary_async returns standardized DF.
                 # avg is calculated from that DF.
                 # So it SHOULD be English keys.
                 logger.warning(f"Expected metrics {expected_metrics} not found in average. Keys: {avg.keys()}")
            
            self.assertTrue(found_any, "Should have at least one key financial metric in average")

        finally:
            loop.close()

if __name__ == '__main__':
    unittest.main()
