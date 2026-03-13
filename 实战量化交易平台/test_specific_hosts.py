
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TESTS = [
    # IP, Host, Description
    ("117.184.33.102", "82.push2.eastmoney.com", "82.push2"),
    ("43.144.251.121", "92.push2.eastmoney.com", "92.push2"),
    ("61.129.129.196", "79.push2.eastmoney.com", "79.push2"),
    ("14.103.191.91", "push2.eastmoney.com", "push2 (Direct)"),
]

PATH = "/api/qt/clist/get?pn=1&pz=1&fs=m:0+t:6&fields=f12"

print("Testing specific Host headers...")

for ip, host, desc in TESTS:
    for proto in ["http", "https"]:
        url = f"{proto}://{ip}{PATH}"
        try:
            print(f"Testing {desc} ({proto}): {url} with Host: {host}")
            resp = requests.get(url, headers={"Host": host, "User-Agent": "Mozilla/5.0"}, verify=False, timeout=5)
            if resp.status_code == 200:
                print(f"✅ SUCCESS {desc} ({proto}): {resp.text[:100]}")
            else:
                print(f"⚠️ FAILED {desc} ({proto}): Status {resp.status_code}")
        except Exception as e:
            print(f"❌ ERROR {desc} ({proto}): {e}")
