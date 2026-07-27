import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict

# Agno imports
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.base import Reader
from agno.knowledge.document import Document
from agno.knowledge.embedder.google import GeminiEmbedder
from agno.db.sqlite.sqlite import SqliteDb

# ChromaDB from Agno (vector db wrapper)
from agno.vectordb.chroma import ChromaDb

# ChromaDB direct client
import chromadb

from src.config.settings import settings
from src.tools.file_parser import convert_file_to_text

# ChromaDB connection config (Docker HTTP)
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "dartha_knowledge")

# Mapeamento de departamentos: agents.yaml -> ChromaDB
DEPARTMENT_MAPPING = {
    "marketing": "Marketing",
    "juridico": "Jurídico",
    "finance": "Financeiro",
    "hr": "RH",
    "sales": "Vendas",
    "operations": "Operações",
    "it": "TI",
    "geral": None,  # Geral não tem filtro
}


class MarkItDownReader(Reader):
    """
    Leitor universal que usa Microsoft MarkItDown para converter diversos
    formatos (.docx, .xlsx, .pptx, .pdf, etc.) em Markdown.
    (Utilizado apenas se for injetar itens online pelo front, mas a Dartha injeta via script).
    """
    def read(self, file_path: Path) -> List[Document]:
        if not file_path.exists():
            return []

        content = convert_file_to_text(file_path.read_bytes(), file_path.name)
        if content:
            return [Document(content=content, meta_data={"source": str(file_path)})]
        return []


def _resolve_dept_display_name(slug: str) -> Optional[str]:
    """
    Converte slug de departamento (ex: 'juridico') para display_name (ex: 'Jurídico').
    Prioridade: DB > DEPARTMENT_MAPPING hardcoded > slug bruto.
    Isso garante que departamentos renomeados pelo admin reflitam nos agentes após restart.
    """
    try:
        from src.admin.db import get_department_by_slug
        dept = get_department_by_slug(slug)
        if dept:
            return dept.display_name
    except Exception:
        pass
    # Fallback para o mapeamento hardcoded (se DB ainda não existir)
    return DEPARTMENT_MAPPING.get(slug, slug)


class DarthaHttpChromaDb(ChromaDb):
    """
    Subclasse do ChromaDb do Agno que força conexão HTTP ao Docker.
    Injeta o HttpClient antes do primeiro uso para evitar usar o Client padrão
    (que tentaria criar uma instância local/persistente).
    """

    def __init__(self, department: str = None, **kwargs):
        # Resolve slug para display_name: DB first, fallback DEPARTMENT_MAPPING
        self._department = _resolve_dept_display_name(department) if department else None
        super().__init__(**kwargs)
        # Pre-injeta o HttpClient para que o property `client` não crie um default
        try:
            self._client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
            self._collection = self._client.get_collection(name=self.collection_name)
            count = self._collection.count()
            dept_info = f" (filtro: {self._department})" if self._department else " (sem filtro)"
            print(f"[DarthaKnowledge] Conectado a '{self.collection_name}' — {count} chunks{dept_info}")
        except Exception as e:
            print(f"[DarthaKnowledge] AVISO: ChromaDB indisponível — RAG desabilitado ({e})")
            self._client = None
            self._collection = None

    def search(self, query: str, limit: int = 5, filters=None) -> List[Document]:
        if self._collection is None:
            return []
        if self._department and filters is None:
            filters = {"department": self._department}
        elif self._department and isinstance(filters, dict):
            filters = {"$and": [{"department": self._department}, filters]}
        return super().search(query=query, limit=limit, filters=filters)

    async def async_search(self, query: str, limit: int = 5, filters=None) -> List[Document]:
        if self._collection is None:
            return []
        if self._department and filters is None:
            filters = {"department": self._department}
        elif self._department and isinstance(filters, dict):
            filters = {"$and": [{"department": self._department}, filters]}
        return await super().async_search(query=query, limit=limit, filters=filters)

    def delete_documents(self, chroma_ids: List[str]) -> None:
        """Remove vetores do ChromaDB pelos IDs. Usado pelo painel admin."""
        if not self._collection:
            raise RuntimeError("ChromaDB collection não disponível")
        if chroma_ids:
            self._collection.delete(ids=chroma_ids)


# Cache de instâncias por departamento (evita recriar embedder/client)
_knowledge_instances: Dict[str, Knowledge] = {}

def get_knowledge_base(department: str = None, num_documents: int = 5) -> Knowledge:
    """
    Retorna a conexão com a Base de Conhecimento Multimodal via ChromaDB (HTTP / Docker).
    Cria uma instância por departamento para garantir isolamento correto.

    Args:
        department:    Filtra documentos por departamento (multitenancy).
        num_documents: Número de documentos retornados por busca semântica.
    """
    # Usa department como chave do cache (None = "global")
    cache_key = department or "global"

    if cache_key in _knowledge_instances:
        return _knowledge_instances[cache_key]

    # Embedder Gemini 2 — 768 dimensões (igual ao script de ingestão)
    embedder = GeminiEmbedder(
        id="gemini-embedding-2-preview",
        api_key=settings.GOOGLE_API_KEY,
        dimensions=768,
    )

    vector_db = DarthaHttpChromaDb(
        id=f"chromadb-{cache_key}",
        collection=CHROMA_COLLECTION,
        embedder=embedder,
        department=department,
        # persistent_client=False por padrão — não cria local
    )

    # Adicionar o contents_db para que o AgentOS frontend descubra esta instância.
    # O contents_db gerencia o mapeamento entre arquivos enviados via UI e vetores.
    contents_db = SqliteDb(
        id=f"contents-db-{cache_key}",
        db_file=os.getenv("SQLITE_DB_PATH", "agno.db")
    )

    instance = Knowledge(
        name=f"dartha_knowledge_{department}" if department else "dartha_knowledge_base",
        readers=[MarkItDownReader()],
        vector_db=vector_db,
        contents_db=contents_db,
        max_results=num_documents,
    )

    _knowledge_instances[cache_key] = instance
    return instance
