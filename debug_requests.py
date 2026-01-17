import requests
import logging

# Enable debug logging for requests
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

url = "http://127.0.0.1:8080/antigrav_sam_notifications"
print(f"POSTing to: {url}")

try:
    headers = {
        "Title": "Debug Test",
        "Priority": "default"
    }
    resp = requests.post(url, data="test local with headers", headers=headers, timeout=5)
    print(f"Status: {resp.status_code}")
    print(f"Headers: {resp.headers}")
    print(f"Content: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
