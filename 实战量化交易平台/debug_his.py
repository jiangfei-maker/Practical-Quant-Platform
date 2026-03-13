
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API Path for Sector Data
API_PATH = "/api/qt/clist/get?pn=1&pz=100&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A90+t%3A2+f%3A%2150&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f22,f33,f11,f62,f128,f136,f115,f152,f124,f107,f104,f105,f140,f141,f207,f208,f209,f222"

def test_url(base_url):
    url = f"{base_url}{API_PATH}"
    print(f"\nTesting {base_url}...")
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, verify=False, timeout=3)
        print(f"Status: {resp.status_code}")
        if resp.text.startswith("{") or '"data":' in resp.text:
             print("✅ JSON Response!")
             print(resp.text[:200])
        else:
             print("❌ HTML/Other")
             print(resp.text[:200])
    except Exception as e:
        print(f"Error: {e}")

test_url("https://push2his.eastmoney.com")
