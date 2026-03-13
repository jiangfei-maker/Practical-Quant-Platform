
import requests
import urllib3
import ssl
import socket
import logging

# Disable warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

URL_PUSH2 = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=1&po=1&np=1&ut=b2884a393a59ad64002292a3e90d46a5&fltt=2&invt=2&fid0=f62&fs=m%3A90+t%3A2&stat=1&fields=f12&rt=52975239"
URL_QUOTE = "https://quote.eastmoney.com/"
URL_PUSH2HIS = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?lmt=0&klt=101&secid=1.600000&fields1=f1&fields2=f51&ut=b2884a393a59ad64002292a3e90d46a5"

def test_dns(hostname):
    logger.info(f"Testing DNS for {hostname}...")
    try:
        ip = socket.gethostbyname(hostname)
        logger.info(f"✅ DNS Resolved: {hostname} -> {ip}")
        return True
    except Exception as e:
        logger.error(f"❌ DNS Failed for {hostname}: {e}")
        return False

def test_request(name, url, verify=True, ciphers=None):
    logger.info(f"Testing {name} [verify={verify}, ciphers={ciphers}]...")
    try:
        session = requests.Session()
        session.headers.update({
             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        if ciphers:
            # Create a custom adapter to force ciphers
            class CipherAdapter(requests.adapters.HTTPAdapter):
                def init_poolmanager(self, *args, **kwargs):
                    context = urllib3.util.ssl_.create_urllib3_context(ciphers=ciphers)
                    kwargs['ssl_context'] = context
                    return super(CipherAdapter, self).init_poolmanager(*args, **kwargs)
            
            session.mount('https://', CipherAdapter())

        resp = session.get(url, verify=verify, timeout=5)
        logger.info(f"✅ {name} Success! Status: {resp.status_code}, Length: {len(resp.content)}")
        return True
    except Exception as e:
        logger.error(f"❌ {name} Failed: {e}")
        return False

if __name__ == "__main__":
    print("="*50)
    print("DIAGNOSING SSL/NETWORK LAYER")
    print("="*50)
    
    # 1. DNS Check
    test_dns("push2.eastmoney.com")
    test_dns("quote.eastmoney.com")
    
    # 2. Baseline Test - Main Site (should work)
    test_request("Main Site (quote)", URL_QUOTE)
    
    # 3. Target Test - PUSH2 (Failing)
    test_request("PUSH2 (Standard)", URL_PUSH2)
    
    # 4. Target Test - PUSH2 with verify=False
    test_request("PUSH2 (Insecure)", URL_PUSH2, verify=False)
    
    # 5. Target Test - PUSH2 with Custom Ciphers (Old/Compatible)
    # Using a broad cipher string
    CIPHERS = "ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384"
    test_request("PUSH2 (Custom Ciphers)", URL_PUSH2, ciphers=CIPHERS)
    
    # 6. Sibling Test - PUSH2HIS
    test_request("PUSH2HIS (Sibling)", URL_PUSH2HIS)
