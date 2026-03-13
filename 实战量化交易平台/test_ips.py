
import requests
import time

IPS = [
    "117.184.38.132",
    "61.129.129.199",
    "221.232.203.245",
    "202.103.24.166"
]
HOST = "push2.eastmoney.com"
PATH = "/api/qt/clist/get"

# Params that are typically used
params = {
    "pn": 1, "pz": 1, "po": 1, "np": 1, 
    "ut": "bd1d9ddb04089700cf9c27f6f7426281", 
    "fltt": 2, "invt": 2, "fid": "f3", "fs": "m:0+t:6,m:0+t:80", 
    "fields": "f1,f2,f3,f4,f12,f13,f14"
}

print(f"Testing IPs for Host: {HOST}...")

for ip in IPS:
    url = f"http://{ip}{PATH}"
    print(f"\nTesting {ip}...")
    try:
        resp = requests.get(url, params=params, headers={"Host": HOST, "User-Agent": "Mozilla/5.0"}, verify=False, timeout=3)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("SUCCESS!")
            print(resp.text[:100])
            break
    except Exception as e:
        print(f"Failed: {e}")
