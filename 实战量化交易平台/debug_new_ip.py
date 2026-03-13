
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

IP = "14.103.191.91"
DOMAIN = "push2.eastmoney.com"
API_PATH = "/api/qt/clist/get?pn=1&pz=10&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A90+t%3A2+f%3A%2150&fields=f12,f14"

def test_ip(ip):
    print(f"\nTesting IP: {ip} for {DOMAIN} (HTTP)...")
    url = f"http://{ip}{API_PATH}"
    try:
        resp = requests.get(url, headers={"Host": DOMAIN, "User-Agent": "Mozilla/5.0"}, timeout=5)
        print(f"Status: {resp.status_code}")
        if resp.text.startswith("{") or '"data":' in resp.text:
             print("✅ JSON Response!")
             print(resp.text[:100])
        else:
             print("❌ HTML/Other")
    except Exception as e:
        print(f"Error: {e}")

test_ip(IP)
