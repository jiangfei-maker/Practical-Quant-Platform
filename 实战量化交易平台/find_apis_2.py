
import akshare as ak

print("Searching for industry APIs...")
for attr in dir(ak):
    if "industry" in attr and "stock" in attr:
        print(attr)
