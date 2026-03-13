
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

IPS = [
    "61.160.230.232",
    "180.105.204.112",
    "58.216.102.31",
    "114.237.67.68",
    "117.184.38.132",
    "221.231.139.17",
    "121.14.88.203",
    "202.108.23.152"
]

API_PATH = "/api/qt/clist/get?pn=1&pz=10&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A90+t%3A2+f%3A%2150&fields=f12,f14"

def test_ip(ip):
    print(f"CHECKING {ip} ...")
    url = f"https://{ip}{API_PATH}"
    try:
        resp = requests.get(url, headers={"Host": "push2.eastmoney.com", "User-Agent": "Mozilla/5.0"}, verify=False, timeout=2)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("✅ Success!")
            return True
        else:
            print("❌ Failed")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

for ip in IPS:
    if test_ip(ip):
        break
