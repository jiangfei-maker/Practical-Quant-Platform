
import os
import requests

print("Env vars:")
for k, v in os.environ.items():
    if "PROXY" in k.upper():
        print(f"{k}: {v}")

print("\nTesting Baidu...")
try:
    resp = requests.get("https://www.baidu.com", timeout=5)
    print(f"Baidu Status: {resp.status_code}")
except Exception as e:
    print(f"Baidu Failed: {e}")
