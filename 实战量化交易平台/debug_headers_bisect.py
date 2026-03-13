
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A90+t%3A2+f%3A%2150&fields=f12,f14"

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def test_case(name, headers):
    print(f"\nTesting: {name}")
    try:
        resp = requests.get(URL, headers=headers, timeout=5)
        if resp.status_code == 200:
             print("✅ Success!")
        else:
             print(f"❌ Failed status: {resp.status_code}")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

def run():
    # Case 1: Just UA (Baseline)
    test_case("Just UA", BASE_HEADERS)
    
    # Case 2: + Referer
    h2 = BASE_HEADERS.copy()
    h2["Referer"] = "https://quote.eastmoney.com/"
    test_case("+ Referer", h2)

    # Case 3: + Origin
    h3 = BASE_HEADERS.copy()
    h3["Origin"] = "https://quote.eastmoney.com"
    test_case("+ Origin", h3)

    # Case 4: + Accept
    h4 = BASE_HEADERS.copy()
    h4["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    test_case("+ Accept", h4)
    
    # Case 5: + Accept-Language
    h5 = BASE_HEADERS.copy()
    h5["Accept-Language"] = "zh-CN,zh;q=0.9,en;q=0.8"
    test_case("+ Accept-Language", h5)

if __name__ == "__main__":
    run()
