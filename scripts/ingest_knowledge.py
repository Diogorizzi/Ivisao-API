import os
import uuid
import time
from pathlib import Path

# Rich console output
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table

# Suporte OpenAI Embeddings e Chroma
import chromadb
from dotenv import load_dotenv
from openai import OpenAI

# Extratores locais
from pypdf import PdfReader

# Initialize Rich console
console = Console()

# Configuração Base
load_dotenv()
RAG_DATA_DIR = Path("data/RAG")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.environ.get("CHROMA_COLLECTION", "dartha_knowledge")
CHROMA_PERSIST_PATH = os.environ.get("CHROMA_PERSIST_PATH", "./chroma_data")

def init_collection():
    """
    Tenta o servidor ChromaDB via HTTP (Docker); se indisponível, cai para o
    modo local persistente (mesmo diretório usado por src/knowledge/base.py).
    """
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}  # embeddings da OpenAI são otimizados para Similaridade de Coseno
        )
        console.print(f"[+] Conectado ao ChromaDB via HTTP no Docker ({CHROMA_HOST}:{CHROMA_PORT})", style="green")
        return collection
    except Exception:
        console.print(f"[-] Chroma Server indisponível, usando modo Local persistente ({CHROMA_PERSIST_PATH}).", style="yellow")
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_PATH)
        return client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )

def generate_embedding(content_data: str) -> list[float]:
    """Chama a API de Embeddings da OpenAI para textos"""
    result = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=content_data,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    return result.data[0].embedding

def process_and_chunk_file(file_path: Path):
    """
    Etapa 2 (Chunking) & Etapa 3 (Processamento)
    Trata diferentes tipos de extensões de arquivo com regras delimitadas.
    """
    ext = file_path.suffix.lower()
    chunks = []
    
    if ext == ".txt" or ext == ".md":
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        paragraphs = content.split("\n\n")
        for idx, p in enumerate(paragraphs):
            clean_p = p.strip()
            if len(clean_p) > 20: 
                chunks.append({
                    "data": clean_p,
                    "text_representation": clean_p,
                    "chunk_id": f"{file_path.name}-chunk-{idx}"
                })

    elif ext == ".pdf":
        try:
            reader = PdfReader(file_path)
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text and len(page_text.strip()) > 20:
                    chunks.append({
                        "data": page_text.strip(),
                        "text_representation": f"[PDF Página {i+1}] " + page_text.strip(),
                        "chunk_id": f"{file_path.name}-page-{i+1}"
                    })
        except Exception as err:
            console.print(f"[!] Falha lendo PDF {file_path.name}: {err}", style="red")

    elif ext in [".png", ".jpg", ".jpeg"]:
        # text-embedding-3-small é um modelo de texto — não suporta embeddings
        # multimodais diretos de imagem. Pular por enquanto.
        console.print(f"    [!] Imagem ignorada (embedding de texto não suporta imagens): {file_path.name}", style="yellow")

    return chunks

def run_ingestion():
    if not OPENAI_API_KEY:
         console.print("[ERRO] Variável OPENAI_API_KEY não foi encontrada ou é inválida no ambiente (.env).", style="red bold")
         return

    # Rich header panel
    console.print(Panel.fit(
        "[bold cyan]Ivisao Ingestion Parser - OpenAI text-embedding-3-small[/bold cyan]",
        border_style="cyan"
    ))

    collection = init_collection()
    console.print(f"[+] Conectado à Collection '{CHROMA_COLLECTION}'", style="green")

    if not RAG_DATA_DIR.exists():
        console.print(f"[!] {RAG_DATA_DIR} não existe.", style="red")
        return

    total_chunks_added = 0
    total_files = 0

    for dept_folder in RAG_DATA_DIR.iterdir():
        if dept_folder.is_dir() and not dept_folder.name.startswith("."):
            department_name = dept_folder.name

            for file_path in dept_folder.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith("."):
                    total_files += 1
                    console.print(f"\n[*] Processando [{department_name}] {file_path.name}...", style="cyan")

                    chunks = process_and_chunk_file(file_path)
                    console.print(f"    - Recortado logicamente em {len(chunks)} trechos", style="dim")

                    for chunk in chunks:
                        chunk_id = f"{department_name}_{chunk['chunk_id']}_{uuid.uuid4().hex[:6]}"

                        try:
                            vector = generate_embedding(chunk["data"])
                            time.sleep(1) # Pausa estratégica leve para evitar Rate Limit 429
                        except Exception as embed_err:
                            console.print(f"    [X] Erro de API no arquivo {file_path.name}: {embed_err}", style="red")
                            continue

                        try:
                            collection.add(
                                ids=[chunk_id],
                                embeddings=[vector],
                                documents=[chunk["text_representation"]],
                                metadatas=[{
                                    "department": department_name,
                                    "source_file": file_path.name,
                                    "type": file_path.suffix.replace('.', '').upper()
                                }]
                            )
                            total_chunks_added += 1
                        except Exception as add_err:
                            console.print(f"    [X] Erro no ChromaDB pra salvar {chunk_id}: {add_err}", style="red")

    # Rich summary panel
    summary = f"[bold green]Ingestão Concluída![/bold green]\n{total_files} arquivos e {total_chunks_added} chunks semânticos inseridos no DarthaDB."
    console.print(Panel(summary, border_style="green"))

if __name__ == "__main__":
    run_ingestion()
