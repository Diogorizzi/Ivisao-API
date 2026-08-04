import os
from dotenv import load_dotenv
load_dotenv()
from agno.knowledge.embedder.openai import OpenAIEmbedder

e = OpenAIEmbedder(id="text-embedding-3-small", api_key=os.environ["OPENAI_API_KEY"], dimensions=1536)
res = e.get_embedding("test")
if len(res) > 0:
    print("SUCCESS", len(res))
else:
    print("FAILED")
