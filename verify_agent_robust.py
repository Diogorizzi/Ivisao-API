import requests
import json

base_url = "http://127.0.0.1:7777"
agent_id = "general-assistant"

endpoints = [
    f"{base_url}/agents/{agent_id}/run",
    f"{base_url}/agent/run",
    f"{base_url}/v1/agents/{agent_id}/run",
]

payload = {
    "message": "Ola, quem e voce?",
    "stream": False
}

for url in endpoints:
    print(f"Testing {url}...")
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response success!")
            break
        else:
            print(f"Response: {response.text[:100]}")
    except Exception as e:
        print(f"Error: {e}")

print("Verification complete.")
