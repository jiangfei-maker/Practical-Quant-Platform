
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API Path
API_PATH = "/api/qt/clist/get?pn=1&pz=10&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A90+t%3A2+f%3A%2150&fields=f12,f14"

def test_url(url):
    print(f"\nTesting {url}...")
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, verify=False, timeout=3)
        print(f"Status: {resp.status_code}")
        if resp.text.startswith("{") or '"data":' in resp.text:
             print("✅ JSON Response!")
             print(resp.text[:100])
             return True
        else:
             print("❌ HTML/Other")
             return False
    except Exception as e:
        print(f"Error: {e}")
        return False

# 1. HTTP vs HTTPS on push2
test_url("http://push2.eastmoney.com" + API_PATH)
test_url("https://push2.eastmoney.com" + API_PATH)

# 2. Other subdomains
for i in range(1, 10):
    test_url(f"http://push{i}.eastmoney.com" + API_PATH)
    test_url(f"https://push{i}.eastmoney.com" + API_PATH)
