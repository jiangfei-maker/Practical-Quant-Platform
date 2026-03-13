
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOMAINS = [
    "push2.eastmoney.com",
    "push2his.eastmoney.com",
    "80.push2.eastmoney.com",
    "push1.eastmoney.com",
    "quote.eastmoney.com",
    "f10.eastmoney.com"
]

API_PATH = "/api/qt/clist/get?pn=1&pz=10&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A90+t%3A2+f%3A%2150&fields=f12,f14"

def test_domain(domain):
    print(f"\nTesting {domain}...")
    urls = [f"http://{domain}{API_PATH}", f"https://{domain}{API_PATH}"]
    
    for url in urls:
        print(f"  Testing {url}...")
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, verify=False, timeout=3)
            print(f"  Status: {resp.status_code}")
            if resp.status_code == 200 and ('"data":' in resp.text or resp.text.startswith("{")):
                print(f"  ✅ Success with {url}")
                print(resp.text[:100])
                return True
            else:
                print("  ❌ Failed (Status/Content)")
        except Exception as e:
            print(f"  ❌ Exception: {e}")
    return False

for d in DOMAINS:
    test_domain(d)
