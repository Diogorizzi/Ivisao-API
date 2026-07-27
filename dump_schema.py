import requests
import json

r = requests.get('http://127.0.0.1:7777/openapi.json')
data = r.json()

path_data = data['paths'].get('/agents/{agent_id}/runs', {}).get('post', {})
if not path_data:
    print("Path /agents/{agent_id}/runs not found in paths.")
    # Try singular run
    path_data = data['paths'].get('/agents/{agent_id}/run', {}).get('post', {})
    if path_data:
        print("Using /agents/{agent_id}/run instead.")

content = path_data.get('requestBody', {}).get('content', {})
print("--- Content Types ---")
print(list(content.keys()))

for ct in content:
    print(f"\n--- Schema for {ct} ---")
    schema = content[ct]['schema']
    if '$ref' in schema:
        ref_name = schema['$ref'].split('/')[-1]
        print(f"Ref: {ref_name}")
        print(json.dumps(data['components']['schemas'].get(ref_name, {}), indent=2))
    else:
        print(json.dumps(schema, indent=2))
