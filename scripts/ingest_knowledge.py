import os
import uuid
import time
from pathlib import Path

# Rich console output
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table

# Suporte GenAI e Embeddings (Google e Chroma)
import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Extratores locais
from pypdf import PdfReader

# Initialize Rich console
console = Console()

# Configuração Base
load_dotenv()
RAG_DATA_DIR = Path("data/RAG")
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Inicializa o Client Oficial do Gemini (Multimodal Native)
if GEMINI_API_KEY:
    genai_client = genai.Client(api_key=GEMINI_API_KEY)
EMBEDDING_MODEL = "gemini-embedding-2-preview"

# Inicializa ChromaDB apontando para o Docker Client/Server configurado
try:
    chroma_client = chromadb.HttpClient(host="localhost", port=8000)
    console.print("[+] Conectado ao ChromaDB via HTTP no Docker (localhost:8000)", style="green")
except Exception as e:
    console.print("[-] Falhou em conectar ao Chroma Server, usando modo Local persistente.", style="yellow")
    chroma_client = chromadb.PersistentClient(path="./chroma_data")

def init_collection():
    """Garante a inicialização segura da coleção e reseta se necessário."""
    try:
        collection = chroma_client.get_or_create_collection(
            name="dartha_knowledge",
            metadata={"hnsw:space": "cosine"} # O Gemini model gera embeddings otimizados para Similaridade de Coseno
        )
        return collection
    except Exception as e:
        console.print(f"[!] Erro de coleção: {e}", style="red")
        return chroma_client.create_collection("dartha_knowledge")

def generate_embedding(content_data) -> list[float]:
    """Chama a API do Gemini Embeddings 2 para textos ou multimídia"""
    result = genai_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[content_data],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768 # Reduz para 768 ajudando na performance do banco Dartha
        )
    )
    return result.embeddings[0].values

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
        with open(file_path, "rb") as bf:
            image_bytes = bf.read()
            mime = f"image/{ext.replace('.', '')}"
            if ext == ".jpg": mime = "image/jpeg"
            
            chunks.append({
                 "data": types.Part.from_bytes(data=image_bytes, mime_type=mime),
                 "text_representation": f"[IMAGEM MULTIMODAL: {file_path.name}]",
                 "chunk_id": f"{file_path.name}-image"
            })
            
    return chunks

def run_ingestion():
    if not GEMINI_API_KEY:
         console.print("[ERRO] Variável GOOGLE_API_KEY não foi encontrada ou é inválida no ambiente (.env).", style="red bold")
         return

    # Rich header panel
    console.print(Panel.fit(
        "[bold cyan]Dartha Ingestion Parser - Gemini 2 (Multimodal)[/bold cyan]",
        border_style="cyan"
    ))

    collection = init_collection()
    console.print("[+] Conectado à Collection 'dartha_knowledge'", style="green")

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
                        except Exception as gemini_err:
                            console.print(f"    [X] Erro de API no arquivo {file_path.name}: {gemini_err}", style="red")
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
