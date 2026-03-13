
import pandas as pd
import sys
import os
from datetime import datetime
import shutil
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data.market_crawler import MarketDataCrawler
from core.data.db_manager import db_manager

def test_market_storage():
    print("Testing Market Data Storage Pipeline...")
    
    # Clean up previous test data in DuckDB
    try:
        conn = db_manager.get_connection()
        print(f"DB Connection ID: {id(conn)}")
        conn.execute("DROP TABLE IF EXISTS market_order_book")
        # Verify drop
        try:
            count = conn.execute("SELECT COUNT(*) FROM market_order_book").fetchone()
            print(f"After DROP, count: {count}")
        except:
            print("After DROP, table does not exist (Good).")
            
    except Exception as e:
        print(f"DB Cleanup warning: {e}")

    # Clean up previous Parquet data
    try:
        stock_code = "TEST001"
        timestamp = datetime.now()
        yyyy = timestamp.strftime("%Y")
        mm = timestamp.strftime("%m")
        date_str = timestamp.strftime("%Y%m%d")
        # Note: This path logic matches the crawler's logic
        parquet_path = Path(f"data/market_depth/{yyyy}/{mm}/{stock_code}_{date_str}_ob.parquet")
        print(f"Cleanup Parquet Path: {parquet_path.absolute()}")
        if parquet_path.exists():
            try:
                os.remove(parquet_path)
                print(f"Removed existing parquet file: {parquet_path}")
            except Exception as delete_e:
                print(f"Failed to remove parquet file: {delete_e}")
        else:
            print("Parquet file does not exist during cleanup.")
            
    except Exception as e:
        print(f"Parquet Cleanup warning: {e}")

    crawler = MarketDataCrawler(headless=True)
    
    # Create dummy data
    stock_code = "TEST001"
    timestamp = datetime.now()
    
    # Dummy Order Book
    df_ob = pd.DataFrame([
        {"stock_code": stock_code, "position": "卖1", "price": 100.5, "volume": 100, "captured_at": timestamp},
        {"stock_code": stock_code, "position": "买1", "price": 100.0, "volume": 200, "captured_at": timestamp},
        {"stock_code": stock_code, "position": "买2", "price": -10.0, "volume": 50, "captured_at": timestamp} # Invalid price
    ])
    
    print("\n[Test 1] Saving Order Book (with 1 invalid row)...")
    crawler._save_to_db(df_ob, "market_order_book")
    
    # Verify DuckDB
    print("Verifying DuckDB...")
    df_db = db_manager.conn.execute(f"SELECT * FROM market_order_book WHERE stock_code='{stock_code}'").df()
    print(f"DuckDB Rows: {len(df_db)}")
    if len(df_db) == 2:
        print("PASS: DuckDB has 2 valid rows (invalid one filtered).")
    else:
        print(f"FAIL: DuckDB has {len(df_db)} rows.")
        
    # Verify Parquet
    print("Verifying Parquet...")
    yyyy = timestamp.strftime("%Y")
    mm = timestamp.strftime("%m")
    date_str = timestamp.strftime("%Y%m%d")
    parquet_path = Path(f"data/market_depth/{yyyy}/{mm}/{stock_code}_{date_str}_ob.parquet")
    
    if parquet_path.exists():
        df_pq = pd.read_parquet(parquet_path)
        print(f"Parquet Rows: {len(df_pq)}")
        if len(df_pq) == 2:
            print("PASS: Parquet file created with 2 valid rows.")
        else:
            print(f"FAIL: Parquet has {len(df_pq)} rows.")
    else:
        print(f"FAIL: Parquet file not found at {parquet_path}")

    # Clean up test data
    # db_manager.conn.execute(f"DELETE FROM market_order_book WHERE stock_code='{stock_code}'")
    # if parquet_path.exists():
    #     os.remove(parquet_path)

if __name__ == "__main__":
    test_market_storage()
