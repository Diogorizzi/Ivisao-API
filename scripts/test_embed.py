import os
from dotenv import load_dotenv
load_dotenv()
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agno.knowledge.embedder.openai import OpenAIEmbedder
from src.knowledge.embeddings import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, OPENROUTER_BASE_URL, embed_text

direct = embed_text("teste")
print("SDK direto (sem dimensions):", len(direct), "dimensões")

# Mesmo caminho usado pela busca dos agentes (agno + base_url + dimensions)
e = OpenAIEmbedder(id=EMBEDDING_MODEL, api_key=os.environ["OPENROUTER_API_KEY"], base_url=OPENROUTER_BASE_URL, dimensions=EMBEDDING_DIMENSIONS)
res = e.get_embedding("teste")
print("Embedder do agno:", len(res), "dimensões (esperado:", EMBEDDING_DIMENSIONS, ")")
print("OK" if len(res) == len(direct) == EMBEDDING_DIMENSIONS else "INCONSISTENTE — ajustar EMBEDDING_DIMENSIONS")
