
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A90+t%3A2+f%3A%2150"

# Short fields
FIELDS_SHORT = "f12,f14"

# Medium fields
FIELDS_MED = "f12,f14,f2,f3,f62,f184,f66,f69,f72"

# Long fields (Original)
FIELDS_LONG = "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f22,f33,f11,f62,f128,f136,f115,f152,f124,f107,f104,f105,f140,f141,f207,f208,f209,f222"

def test_fields(name, fields):
    print(f"\nTesting: {name}")
    url = f"{BASE_URL}&fields={fields}"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if resp.status_code == 200:
             print("✅ Success!")
        else:
             print(f"❌ Failed status: {resp.status_code}")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    test_fields("Short", FIELDS_SHORT)
    test_fields("Medium", FIELDS_MED)
    test_fields("Long", FIELDS_LONG)
