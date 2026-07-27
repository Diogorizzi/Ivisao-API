import requests
import json

url = "http://127.0.0.1:7777/agents/general-assistant/runs"
payload = {
    "message": "Ola, quem e voce?"
}

print(f"Sending request to {url}...")
try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Success!")
        # print(json.dumps(response.json(), indent=2))
        print("Response content received.")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
