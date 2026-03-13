
import requests
import socket
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PATH = "/api/qt/clist/get?pn=1&pz=1&fs=m:0+t:6&fields=f12"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    None, # No UA
    "EASTMONEY_APP", # Fake app?
]

print("Scanning subdomains...")

for i in range(1, 100):
    host = f"{i}.push2.eastmoney.com"
    try:
        ip = socket.gethostbyname(host)
        print(f"Found {host} -> {ip}")
        
        # Test connection
        url = f"http://{host}{PATH}"
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                print(f"✅ WORKING: {host} (HTTP)")
                print(resp.text[:100])
                break
        except:
            pass
            
        url = f"https://{host}{PATH}"
        try:
            resp = requests.get(url, verify=False, timeout=2)
            if resp.status_code == 200:
                print(f"✅ WORKING: {host} (HTTPS)")
                print(resp.text[:100])
                break
        except:
            pass
            
    except socket.gaierror:
        pass
    except Exception as e:
        print(f"Error {host}: {e}")
