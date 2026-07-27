import os
from dotenv import load_dotenv
load_dotenv()
from agno.knowledge.embedder.google import GeminiEmbedder

e = GeminiEmbedder(id="gemini-embedding-2-preview", api_key=os.environ["GOOGLE_API_KEY"], dimensions=768)
res = e.get_embedding("test")
if len(res) > 0:
    print("SUCCESS", len(res))
else:
    print("FAILED")
