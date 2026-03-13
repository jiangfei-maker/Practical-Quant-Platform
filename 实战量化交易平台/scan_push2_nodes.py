
import requests
import urllib3
import concurrent.futures

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_PATH = "/api/qt/clist/get?pn=1&pz=10&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A90+t%3A2+f%3A%2150&fields=f12,f14"

def check_node(i):
    domain = f"{i}.push2.eastmoney.com"
    url = f"http://{domain}{API_PATH}"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=2)
        if resp.status_code == 200 and (resp.text.startswith("{") or '"data":' in resp.text):
            return i, True, resp.elapsed.total_seconds()
    except:
        pass
    return i, False, 0

def scan():
    print("Scanning push2 nodes (1-100)...")
    working_nodes = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(check_node, i) for i in range(1, 101)]
        for future in concurrent.futures.as_completed(futures):
            i, success, latency = future.result()
            if success:
                print(f"✅ Node {i} works! Latency: {latency:.2f}s")
                working_nodes.append((i, latency))
            else:
                # print(f"❌ Node {i} failed")
                pass
                
    print(f"\nFound {len(working_nodes)} working nodes.")
    if working_nodes:
        best_node = sorted(working_nodes, key=lambda x: x[1])[0]
        print(f"Best Node: {best_node[0]}.push2.eastmoney.com")

if __name__ == "__main__":
    scan()
