
import socket
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOMAIN = "push2.eastmoney.com"
API_PATH = "/api/qt/clist/get?pn=1&pz=10&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A90+t%3A2+f%3A%2150&fields=f12,f14"

def get_ips(domain):
    print(f"Resolving {domain}...")
    try:
        infos = socket.getaddrinfo(domain, 443, proto=socket.IPPROTO_TCP)
        ips = set()
        for info in infos:
            ip = info[4][0]
            ips.add(ip)
        return list(ips)
    except Exception as e:
        print(f"DNS Resolution failed: {e}")
        return []

def test_ip(ip):
    print(f"\nTesting IP: {ip}...")
    # Handle IPv6 brackets
    if ":" in ip:
        url = f"https://[{ip}]{API_PATH}"
    else:
        url = f"https://{ip}{API_PATH}"
        
    try:
        resp = requests.get(url, headers={"Host": DOMAIN, "User-Agent": "Mozilla/5.0"}, verify=False, timeout=5)
        print(f"Status: {resp.status_code}")
        if resp.text.startswith("{") or '"data":' in resp.text:
             print("✅ JSON Response!")
             print(resp.text[:100])
             return True
        else:
             print("❌ HTML/Other")
             return False
    except Exception as e:
        print(f"Error: {e}")
        return False

ips = get_ips(DOMAIN)
print(f"Found IPs: {ips}")

for ip in ips:
    test_ip(ip)
