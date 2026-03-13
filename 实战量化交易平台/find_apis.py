
import akshare as ak

print("Searching for constituent APIs...")
for attr in dir(ak):
    if "cons" in attr and "stock" in attr:
        print(attr)
