import requests
import json

url = "http://127.0.0.1:7777/agents/general-assistant/runs"

# Payload for multipart/form-data
# In Agno, 'message' is often a JSON string when sent via multipart
payload = {
    "message": json.dumps({"role": "user", "content": "Ola, quem e voce?"}),
    "stream": "false",
    "monitor": "true"
}

print(f"Sending multipart request to {url}...")
try:
    # Using 'data' in requests with POST and no 'json' or 'files' defaults to form encoding
    # but we need multipart/form-data. requests handles it if we use 'files' even for text fields,
    # or if we just use 'data' it does application/x-www-form-urlencoded.
    # To force multipart/form-data without files, we can just use 'files' with empty or text parts.
    
    files = {
        "message": (None, payload["message"]),
        "stream": (None, payload["stream"]),
        "monitor": (None, payload["monitor"])
    }
    
    response = requests.post(url, files=files, timeout=30)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Success! Agent is responding.")
        # print(response.text)
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
