
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOMAINS = [
    "push2.eastmoney.com",
    "push2his.eastmoney.com",
    "quote.eastmoney.com",
    "61.129.129.199",
    "101.226.30.206"
]

# A common API path used by AkShare
API_PATH = "/api/qt/clist/get?pn=1&pz=10&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A90+t%3A2+f%3A%2150&fields=f12,f14"

def test_domains_http():
    print("Testing EastMoney Domains (HTTP)...")
    for domain in DOMAINS:
        url = f"http://{domain}{API_PATH}"
        print(f"\nTesting: {url}")
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                if resp.text.startswith("{") or '"data":' in resp.text:
                     print("✅ JSON Response!")
                     print(resp.text[:100])
                else:
                     print("⚠️ HTML/Other Content")
            else:
                print("❌ Non-200 Status")
        except Exception as e:
            print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    test_domains_http()
