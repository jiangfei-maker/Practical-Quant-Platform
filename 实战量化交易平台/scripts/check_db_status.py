
import duckdb
import os
import pandas as pd

def check_db():
    db_path = r"c:\Users\34657\Desktop\第二版 - 副本\实战量化交易平台\data\db\quant_core.duckdb"
    print(f"Checking DB at {db_path}...")
    
    try:
        # Try read-only connection
        con = duckdb.connect(db_path, read_only=True)
        print("Connected successfully (read-only).")
        
        # Check stock_basic
        try:
            df = con.execute("SELECT * FROM stock_basic LIMIT 5").fetch_df()
            print("\nFetched 5 rows from stock_basic:")
            print(df)
            
            # Check industry stats
            total = con.execute("SELECT COUNT(*) FROM stock_basic").fetchone()[0]
            unknown = con.execute("SELECT COUNT(*) FROM stock_basic WHERE industry = '未知' OR industry IS NULL").fetchone()[0]
            print(f"\nTotal stocks: {total}")
            print(f"Unknown industry: {unknown}")
            print(f"Coverage: {(total - unknown) / total * 100:.2f}%")
            
        except Exception as e:
            print(f"Query Error: {e}")
            
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    check_db()
