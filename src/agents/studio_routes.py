"""
Endpoints do Studio — rotas de suporte ao Studio UI próprio do Dartha.

Expostos em /v1/studio-support/* para não colidir com os endpoints nativos
/v1/studio/* que o AgentOS gera automaticamente.
"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/v1/studio-support", tags=["studio-support"])


class KnowledgeBaseInfo(BaseModel):
    slug: Optional[str]
    display_name: str
    doc_count: int


@router.get("/knowledge-bases", response_model=List[KnowledgeBaseInfo])
def list_knowledge_bases() -> List[KnowledgeBaseInfo]:
    """
    Retorna os departamentos disponíveis para RAG no ChromaDB.
    Inclui contagem de documentos por departamento.
    """
    result: List[KnowledgeBaseInfo] = []

    # Busca departamentos do banco admin
    try:
        from src.admin import db as admin_db
        departments = admin_db.get_all_departments()
    except Exception:
        departments = []

    # Mapeamento fallback se o banco admin não retornar
    from src.knowledge.base import DEPARTMENT_MAPPING
    if not departments:
        fallback = [
            {"slug": slug, "display_name": display or slug.capitalize()}
            for slug, display in DEPARTMENT_MAPPING.items()
        ]
        departments = [type("D", (), d)() for d in fallback]

    # Adiciona opção "Geral (sem filtro)" primeiro
    total_count = _count_docs_for_department(None)
    result.append(KnowledgeBaseInfo(
        slug=None,
        display_name="Geral (sem filtro)",
        doc_count=total_count,
    ))

    # Itera departamentos e conta documentos de cada um
    for dept in departments:
        slug = getattr(dept, "slug", None) or getattr(dept, "name", None)
        display_name = getattr(dept, "display_name", None) or str(slug)
        if not slug:
            continue
        count = _count_docs_for_department(slug)
        result.append(KnowledgeBaseInfo(
            slug=slug,
            display_name=display_name,
            doc_count=count,
        ))

    return result


@router.get("/available-providers")
def list_available_providers():
    """
    Retorna quais providers LLM estão configurados (com credenciais no .env).
    O frontend usa isso para exibir apenas providers disponíveis no ModelSelector.
    """
    from src.config.llm_providers import PROVIDER_REGISTRY
    return [
        {
            "id": name,
            "display_name": provider.display_name,
            "available": provider.is_available(),
        }
        for name, provider in PROVIDER_REGISTRY.items()
    ]


def _count_docs_for_department(department: Optional[str]) -> int:
    """Conta documentos no ChromaDB para um departamento específico."""
    try:
        import chromadb
        import os

        host = os.getenv("CHROMA_HOST", "localhost")
        port = int(os.getenv("CHROMA_PORT", "8000"))
        collection_name = os.getenv("CHROMA_COLLECTION", "dartha_knowledge")

        client = chromadb.HttpClient(host=host, port=port)
        collection = client.get_collection(name=collection_name)

        if department is None:
            return collection.count()

        # Conta com filtro de departamento
        # Resolve slug → display_name (ChromaDB usa display_name como metadado)
        from src.knowledge.base import _resolve_dept_display_name
        display_name = _resolve_dept_display_name(department)

        if display_name:
            results = collection.get(where={"department": display_name})
            return len(results.get("ids", []))
        return 0
    except Exception:
        return 0
