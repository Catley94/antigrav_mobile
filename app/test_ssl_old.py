import requests
try:
    print("Testing connection to google...")
    requests.get("https://google.com", timeout=5)
    print("Google OK")
    
    print("Testing connection to ntfy.sh...")
    requests.get("https://ntfy.sh", timeout=5)
    print("Ntfy OK")
    
except Exception as e:
    print(f"FAILED: {e}")
