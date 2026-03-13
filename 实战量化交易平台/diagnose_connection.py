
import requests
import akshare as ak
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Target AKShare function that was failing
def test_func():
    return ak.stock_sector_fund_flow_rank(indicator="今日")

def test_default_connection():
    logger.info("Testing default connection...")
    try:
        df = test_func()
        logger.info(f"Default connection success! Shape: {df.shape}")
        return True
    except Exception as e:
        logger.error(f"Default connection failed: {e}")
        return False

def test_patched_connection_simple():
    logger.info("Testing simple patched connection (Headers only)...")
    
    # Simple patch
    original_request = requests.Session.request
    def patched_request(self, method, url, *args, **kwargs):
        headers = kwargs.get('headers', {})
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        kwargs['headers'] = headers
        return original_request(self, method, url, *args, **kwargs)
    
    requests.Session.request = patched_request
    
    try:
        df = test_func()
        logger.info(f"Simple patched connection success! Shape: {df.shape}")
        requests.Session.request = original_request # Restore
        return True
    except Exception as e:
        logger.error(f"Simple patched connection failed: {e}")
        requests.Session.request = original_request # Restore
        return False

def test_patched_connection_advanced():
    logger.info("Testing advanced patched connection (Session + Retries + Headers)...")
    
    # Advanced patch logic
    original_init = requests.Session.__init__
    
    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        
        # Retry strategy
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.mount("http://", adapter)
        self.mount("https://", adapter)
        
        # Default Headers
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        })

    requests.Session.__init__ = patched_init
    
    try:
        df = test_func()
        logger.info(f"Advanced patched connection success! Shape: {df.shape}")
        return True
    except Exception as e:
        logger.error(f"Advanced patched connection failed: {e}")
        return False

if __name__ == "__main__":
    print("="*50)
    print("DIAGNOSING EASTMONEY CONNECTION ISSUES")
    print("="*50)
    
    # 1. Test Default
    if not test_default_connection():
        print("\nDefault connection failed as expected.")
        
        # 2. Test Simple Patch
        if not test_patched_connection_simple():
            print("\nSimple headers patch failed.")
            
            # 3. Test Advanced Patch
            if test_patched_connection_advanced():
                print("\n✅ SUCCESS: Advanced patch with Session/Retries works!")
            else:
                print("\n❌ ALL METHODS FAILED. Network environment might be blocking EastMoney.")
        else:
            print("\n✅ SUCCESS: Simple headers patch works!")
    else:
        print("\n✅ SUCCESS: Default connection works (Intermittent issue?)")
