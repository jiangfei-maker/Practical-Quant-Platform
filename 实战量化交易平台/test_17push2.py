
import requests

ip = "117.184.38.132"
host = "push2.eastmoney.com" # Pretend we are accessing push2
url = f"https://{ip}/api/qt/clist/get"

print(f"Testing {host} -> {ip}...")
try:
    resp = requests.get(url, headers={"Host": host, "User-Agent": "Mozilla/5.0"}, verify=False, timeout=5)
    print(f"Status: {resp.status_code}")
    print(resp.text[:200])
except Exception as e:
    print(f"Failed: {e}")
