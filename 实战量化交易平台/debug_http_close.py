
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A90+t%3A2+f%3A%2150&fields=f12,f14"

def test_close():
    print(f"\nTesting URL: {URL} with Connection: close")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Connection": "close"
    }
    try:
        resp = requests.get(URL, headers=headers, timeout=5)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
             print("✅ Success!")
        else:
             print("❌ Failed status")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    test_close()
