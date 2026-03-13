
import requests

URLS = [
    "https://push2.eastmoney.com/api/qt/clist/get",
    "http://push2.eastmoney.com/api/qt/clist/get",
    "https://17.push2.eastmoney.com/api/qt/clist/get"
]

# Params
params = {
    "pn": 1, "pz": 1, "po": 1, "np": 1, 
    "ut": "bd1d9ddb04089700cf9c27f6f7426281", 
    "fltt": 2, "invt": 2, "fid": "f3", "fs": "m:0+t:6,m:0+t:80", 
    "fields": "f1,f2,f3,f4,f12,f13,f14"
}

print("Testing Domains directly...")
for url in URLS:
    print(f"\nTesting {url}...")
    try:
        resp = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, verify=False, timeout=5)
        print(f"Status: {resp.status_code}")
    except Exception as e:
        print(f"Failed: {e}")
