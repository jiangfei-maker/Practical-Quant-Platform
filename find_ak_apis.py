import akshare as ak

def find_apis():
    print("Searching for HSGT/Northbound APIs...")
    for attr in dir(ak):
        if "hsgt" in attr and "north" in attr:
            print(f"Found: {attr}")
            
    print("\nSearching for Sector Fund Flow APIs...")
    for attr in dir(ak):
        if "sector" in attr and "fund" in attr:
            print(f"Found: {attr}")
            
    print("\nSearching for Market Fund Flow APIs...")
    for attr in dir(ak):
        if "market" in attr and "fund" in attr:
            print(f"Found: {attr}")

if __name__ == "__main__":
    find_apis()
