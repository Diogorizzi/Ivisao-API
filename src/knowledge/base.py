import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict

# Agno imports
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.base import Reader
from agno.knowledge.document import Document
from agno.knowledge.embedder.openai import OpenAIEmbedder
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
# Fallback local (sem Docker) — mesmo diretório usado por scripts/ingest_knowledge.py
CHROMA_PERSIST_PATH = os.getenv("CHROMA_PERSIST_PATH", "./chroma_data")

# Mapeamento de departamentos: agents.yaml -> ChromaDB
# IMPORTANTE: a chave e o valor são o mesmo texto (identidade), pois esse é
# também o nome exato da pasta em data/RAG/{departamento}/ e o valor gravado
# no metadata "department" pelo scripts/ingest_knowledge.py. Se algum dia
# quiser exibir um nome "bonito" diferente do slug, primeiro garanta que
# ingest_knowledge.py grave esse mesmo nome no metadata — senão a busca por
# departamento para de encontrar documentos.
DEPARTMENT_MAPPING = {
    "recepcao": "recepcao",
    "consultorios": "consultorios",
    "sala-exames": "sala-exames",
    "orientacao-cirurgica": "orientacao-cirurgica",
    "administrativo": "administrativo",
    "faturamento": "faturamento",
    "financeiro": "financeiro",
    "central-guias": "central-guias",
    "farmacia": "farmacia",
    "centro-cirurgico": "centro-cirurgico",
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
    Subclasse do ChromaDb do Agno.
    Tenta conectar ao servidor ChromaDB via HTTP (Docker); se indisponível,
    cai automaticamente para o modo local persistente (mesmo diretório usado
    por scripts/ingest_knowledge.py), evitando exigir Docker em desenvolvimento.
    """

    def __init__(self, department: str = None, **kwargs):
        # Resolve slug para display_name: DB first, fallback DEPARTMENT_MAPPING
        self._department = _resolve_dept_display_name(department) if department else None
        super().__init__(**kwargs)
        self._client = None
        self._collection = None
        mode = None

        # 1. Tenta o servidor ChromaDB via HTTP (Docker)
        try:
            client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
            collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._client, self._collection = client, collection
            mode = f"HTTP (Docker {CHROMA_HOST}:{CHROMA_PORT})"
        except Exception:
            # 2. Fallback: modo local persistente (sem Docker)
            try:
                client = chromadb.PersistentClient(path=CHROMA_PERSIST_PATH)
                collection = client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                self._client, self._collection = client, collection
                mode = f"local persistente ({CHROMA_PERSIST_PATH})"
            except Exception as e:
                print(f"[DarthaKnowledge] AVISO: ChromaDB indisponível — RAG desabilitado ({e})")
                return

        count = self._collection.count()
        dept_info = f" (filtro: {self._department})" if self._department else " (sem filtro)"
        print(f"[DarthaKnowledge] Conectado a '{self.collection_name}' via {mode} — {count} chunks{dept_info}")

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

    # Embedder OpenAI text-embedding-3-small — 1536 dimensões (igual ao script de ingestão)
    embedder = OpenAIEmbedder(
        id="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY,
        dimensions=1536,
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
