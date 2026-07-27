import sys
import os
from pathlib import Path

# Adiciona a raiz do projeto no PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.knowledge.base import get_knowledge_base

def test_rag_retrieval():
    print("Testing HR department RAG...")
    kb_rh = get_knowledge_base(department="RH")
    docs_rh = kb_rh.search("Quais são os benefícios corporativos de viagens?")
    print(f"Docs found for RH: {len(docs_rh)}")
    for i, doc in enumerate(docs_rh):
        print(f" [{i}] {doc.meta_data.get('name', 'Unknown')} (source: {doc.meta_data.get('source', '')})")

    print("\nTesting Comercial department RAG...")
    kb_comercial = get_knowledge_base(department="Comercial")
    docs_comercial = kb_comercial.search("Qual o script de vendas e o roteiro para abordar clientes?")
    print(f"Docs found for Comercial: {len(docs_comercial)}")
    for i, doc in enumerate(docs_comercial):
        print(f" [{i}] {doc.meta_data.get('name', 'Unknown')} (source: {doc.meta_data.get('source', '')})")

if __name__ == "__main__":
    test_rag_retrieval()
