
import requests

IPS_TO_TEST = [
    "117.184.33.102", # 82.push2
    "43.144.251.121", # 92.push2
    "61.129.129.196", # 79.push2
    "14.103.191.91", # New from nslookup
    "140.207.67.156", # New from nslookup (push2his)
    "117.184.38.132", "61.129.129.199", # Previous
    "221.232.203.245", "202.103.24.166", # Previous failed
    "222.73.203.19", "222.73.203.21", # Shanghai Telecom
    "183.136.162.246", # Guangdong
    "180.163.22.189",
    "180.163.22.190",
    "101.227.163.22",
    "124.71.214.232", # Huawei Cloud?
    "14.17.75.14" 
]

PATH = "/api/qt/clist/get"
HOST = "push2.eastmoney.com"

print("Scanning for working Eastmoney IPs...")
working_ip = None

for ip in IPS_TO_TEST:
    for proto in ["http", "https"]:
        # Test with Host header
        url = f"{proto}://{ip}{PATH}"
        try:
            # print(f"Testing {url} with Host header...")
            resp = requests.get(url, headers={"Host": HOST, "User-Agent": "Mozilla/5.0"}, verify=False, timeout=3)
            if resp.status_code == 200:
                 print(f"✅ Found Working IP ({proto}, with Host): {ip} (Status: 200)")
                 print(resp.text[:100])
                 working_ip = ip
            # else:
            #      print(f"⚠️ Reachable IP ({proto}, with Host): {ip} (Status: {resp.status_code})")
        except:
            pass
            
        # Test WITHOUT Host header (Direct IP access)
        try:
            # print(f"Testing {url} without Host header...")
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, verify=False, timeout=3)
            if resp.status_code == 200:
                 print(f"✅ Found Working IP ({proto}, NO Host): {ip} (Status: 200)")
                 print(resp.text[:100])
                 working_ip = ip
            # else:
            #      print(f"⚠️ Reachable IP ({proto}, NO Host): {ip} (Status: {resp.status_code})")
        except:
            pass

if not working_ip:
    print("❌ No working IP found in list.")
