import boto3 
import json  

client = boto3.client("bedrock-runtime", region_name="us-east-2")  

response = client.invoke_model( 
    modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0", 
    body=json.dumps({ 
        "anthropic_version": "bedrock-2023-05-31", 
        "max_tokens": 1024, 
        "messages": [{ 
            "role": "user", 
            "content": "Tell me a short story about a robot." 
        }] 
    }) 
)  

result = json.loads(response["body"].read()) 
print(result["content"][0]["text"])


Erros e processos: 
inference.py#L1
 

Estou instalando o env da bedrock para usar claude e eles passaram o seguinte

Install the SDK
To use the quickstart sample code below, install the SDK for your chosen language.
pip install boto3

Run the following code to make your inference request

import boto3 
import json  

client = boto3.client("bedrock-runtime", region_name="us-east-2")  

response = client.invoke_model( 
    modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0", 
    body=json.dumps({ 
        "anthropic_version": "bedrock-2023-05-31", 
        "max_tokens": 1024, 
        "messages": [{ 
            "role": "user", 
            "content": "Tell me a short story about a robot." 
        }] 
    }) 
)  

result = json.loads(response["body"].read()) 
print(result["content"][0]["text"])