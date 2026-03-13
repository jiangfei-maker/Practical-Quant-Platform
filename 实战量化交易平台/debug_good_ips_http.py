
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GOOD_IPS = {
    "push2.eastmoney.com": "117.184.38.132",
    "push2his.eastmoney.com": "61.129.129.199" 
}

API_PATH = "/api/qt/clist/get?pn=1&pz=10&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A90+t%3A2+f%3A%2150&fields=f12,f14"

def test_manual_ip_http(domain, ip):
    print(f"Testing HTTP {domain} -> {ip}...")
    url = f"http://{ip}{API_PATH}"
    try:
        resp = requests.get(url, headers={"Host": domain, "User-Agent": "Mozilla/5.0"}, timeout=5)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200 and ('"data":' in resp.text or resp.text.startswith("{")):
            print("✅ Success!")
            print(resp.text[:100])
            return True
        else:
            print("❌ Failed (Status/Content)")
            print(resp.text[:100])
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

for domain, ip in GOOD_IPS.items():
    test_manual_ip_http(domain, ip)
