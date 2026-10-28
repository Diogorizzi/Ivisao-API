"""Configuração única dos embeddings do RAG (via OpenRouter).

A busca (src/knowledge/base.py), o painel admin (src/admin/queue.py) e os scripts
de ingestão usam este módulo: indexação e busca precisam do MESMO modelo e da
MESMA dimensão, senão os vetores não são comparáveis.
"""
import os
from functools import lru_cache

from openai import OpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
EMBEDDING_MODEL = "voyageai/voyage-multimodal-3.5"
EMBEDDING_DIMENSIONS = 1024


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url=OPENROUTER_BASE_URL)


def embed_text(text: str) -> list[float]:
    result = _client().embeddings.create(model=EMBEDDING_MODEL, input=text)
    return result.data[0].embedding
