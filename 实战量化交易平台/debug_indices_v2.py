
import sys
import os
import logging
from loguru import logger
import pandas as pd

# 配置标准 logging
logging.basicConfig(level=logging.INFO)

# 确保项目根目录在 path 中
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 加载补丁
from core.utils.network_patch import apply_browser_headers_patch
apply_browser_headers_patch()

from core.analysis.market_monitor import MarketMonitor

print("\n" + "="*50)
print("DIAGNOSTIC: Checking Market Index Data Flow")
print("="*50)

try:
    monitor = MarketMonitor()
    print("Calling get_main_indices()...")
    indices = monitor.get_main_indices()
    
    print(f"\nResult: {type(indices)}")
    
    if indices:
        print(f"Keys found: {list(indices.keys())}")
        for name, df in indices.items():
            print(f"\n--- {name} ---")
            if isinstance(df, pd.DataFrame):
                print(f"Type: DataFrame, Shape: {df.shape}")
                if not df.empty:
                    print("Columns:", df.columns.tolist())
                    print("Last Row:")
                    print(df.tail(1))
                else:
                    print("WARNING: DataFrame is empty")
            else:
                print(f"Type: {type(df)} (Expected DataFrame)")
    else:
        print("ERROR: Returned empty dictionary/None")
        
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("DIAGNOSTIC COMPLETE")
print("="*50)
