
import subprocess
import sys

# Target URL (push2)
URL = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=100&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A90+t%3A2+f%3A%2150&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f22,f33,f11,f62,f128,f136,f115,f152,f124,f107,f104,f105,f140,f141,f207,f208,f209,f222"

def run_curl(name, cmd_args):
    print(f"\n--- Testing {name} ---")
    cmd = ["curl", "-v", "-k"] + cmd_args + [URL]
    try:
        # Run curl
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(f"Exit Code: {result.returncode}")
        
        # Check stderr for connection info
        stderr = result.stderr
        if "SSL certificate problem" in stderr:
            print("SSL Error detected")
        if "Recv failure" in stderr or "Connection reset" in stderr:
            print("Connection Reset detected")
            
        # Check stdout for content
        stdout = result.stdout
        if stdout.startswith("{") or '"data":' in stdout:
            print("✅ JSON Content received!")
            print(stdout[:200])
        else:
            print(f"❌ Content doesn't look like JSON. Length: {len(stdout)}")
            print(stdout[:200])
            
    except Exception as e:
        print(f"Execution Failed: {e}")

# 1. Simple Curl
run_curl("Simple Curl", [])

# 2. Mimic Chrome Windows
run_curl("Mimic Chrome", [
    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "-H", "Referer: https://quote.eastmoney.com/",
    "-H", "Origin: https://quote.eastmoney.com"
])
