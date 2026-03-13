
import akshare as ak
from core.utils.network_patch import apply_browser_headers_patch

apply_browser_headers_patch()

print("Testing THS Constituents Fallback...")
try:
    # Check if this API exists and works
    # Note: AKShare names might be different. Let's try to find a THS sector constituent API.
    # common one: stock_board_industry_cons_ths
    df = ak.stock_board_industry_cons_ths(symbol="半导体及元件") 
    # Note: THS sector names might be different from EM. "半导体" might be "半导体及元件"
    print("Success!")
    print(df.head())
except Exception as e:
    print(f"Failed: {e}")
