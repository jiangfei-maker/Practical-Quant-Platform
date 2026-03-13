
import akshare as ak
import requests
from core.utils.network_patch import apply_browser_headers_patch

# Monkeypatch requests to print URLs
original_request = requests.Session.request

def debug_request(self, method, url, *args, **kwargs):
    print(f"DEBUG REQUEST: {method} {url}")
    try:
        return original_request(self, method, url, *args, **kwargs)
    except Exception as e:
        print(f"REQUEST FAILED: {e}")
        raise e

requests.Session.request = debug_request

# Apply our existing patch (which might override our debug patch if we are not careful, 
# but apply_browser_headers_patch usually patches Session.request too. 
# Let's apply the system patch first, then our debug wrapper.)

# Actually, let's just run the system patch first, then wrap it.
apply_browser_headers_patch()

# Re-wrap to see what's happening AFTER the patch
patched_request = requests.Session.request
def debug_wrapper(self, method, url, *args, **kwargs):
    print(f"DEBUG REQUEST: {method} {url}")
    return patched_request(self, method, url, *args, **kwargs)

requests.Session.request = debug_wrapper

print("="*50)
print("DEBUGGING URLS")
print("="*50)

try:
    print("\n1. Testing stock_board_industry_name_em...")
    ak.stock_board_industry_name_em()
except:
    pass

try:
    print("\n3. Testing stock_fund_flow_industry...")
    ak.stock_fund_flow_industry(symbol="即时")
except:
    pass
