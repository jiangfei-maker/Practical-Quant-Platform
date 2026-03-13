
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

IP = "117.184.38.248" # push2ex IP
HOST = "push2.eastmoney.com"
PATH = "/api/qt/clist/get?pn=1&pz=1&fs=m:0+t:6&fields=f12"

url = f"http://{IP}{PATH}"
print(f"Testing http://{IP} with Host: {HOST}")

try:
    resp = requests.get(url, headers={"Host": HOST, "User-Agent": "Mozilla/5.0"}, verify=False, timeout=5)
    print(f"Status: {resp.status_code}")
    print(resp.text[:100])
except Exception as e:
    print(f"Error: {e}")

url = f"https://{IP}{PATH}"
print(f"Testing https://{IP} with Host: {HOST}")

try:
    resp = requests.get(url, headers={"Host": HOST, "User-Agent": "Mozilla/5.0"}, verify=False, timeout=5)
    print(f"Status: {resp.status_code}")
    print(resp.text[:100])
except Exception as e:
    print(f"Error: {e}")
