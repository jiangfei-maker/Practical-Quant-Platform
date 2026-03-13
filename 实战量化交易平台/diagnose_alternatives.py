
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# The path that fails on push2
API_PATH = "/api/qt/clist/get?pn=1&pz=1&po=1&np=1&ut=b2884a393a59ad64002292a3e90d46a5&fltt=2&invt=2&fid0=f62&fs=m%3A90+t%3A2&stat=1&fields=f12&rt=52975239"

DOMAINS = [
    "push2.eastmoney.com", # Known bad
    "push1.eastmoney.com",
    "push3.eastmoney.com",
    "push.eastmoney.com",
    "f10.eastmoney.com",   # Sometimes used for other things
    "dcfm.eastmoney.com",
    "19.push2.eastmoney.com" # Sometimes IPs are exposed as subdomains
]

def test_domain(domain):
    url = f"https://{domain}{API_PATH}"
    logger.info(f"Testing {domain}...")
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        if resp.status_code == 200:
            logger.info(f"✅ SUCCESS: {domain} is working! Length: {len(resp.content)}")
            return True
        else:
            logger.warning(f"⚠️ {domain} returned status {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ {domain} failed: {e}")
        return False

if __name__ == "__main__":
    print("="*50)
    print("SEARCHING FOR ALTERNATIVE DOMAINS")
    print("="*50)
    
    working_domains = []
    for d in DOMAINS:
        if test_domain(d):
            working_domains.append(d)
            
    print("\n" + "="*50)
    if working_domains:
        print(f"🎉 FOUND WORKING DOMAINS: {working_domains}")
    else:
        print("😭 NO WORKING ALTERNATIVES FOUND.")
