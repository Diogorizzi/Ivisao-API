"""
Processamento assíncrono de documentos via FastAPI BackgroundTasks.
Emite eventos SSE para acompanhamento em tempo real no frontend.
"""
import asyncio
import json
import os
import time
from pathlib import Path
from typing import AsyncGenerator, Dict

import chromadb
from google import genai
from google.genai import types

from src.admin import db as admin_db

# SSE: dict de queues por doc_id
_sse_queues: Dict[str, asyncio.Queue] = {}

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "dartha_knowledge")
EMBEDDING_MODEL = "gemini-embedding-2-preview"

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
IMAGE_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}


def _get_chroma_collection():
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def _generate_embedding(client: genai.Client, text: str) -> list[float]:
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[text],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768,
        ),
    )
    return result.embeddings[0].values


def _generate_image_embedding(client: genai.Client, file_bytes: bytes, mime_type: str) -> list[float]:
    """Generates a 768-dim embedding from image bytes using Gemini inline_data API.
    The resulting vector lives in the same space as text embeddings from _generate_embedding."""
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[types.Content(parts=[types.Part(
            inline_data=types.Blob(mime_type=mime_type, data=file_bytes)
        )])],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768,
        ),
    )
    return result.embeddings[0].values


def _chunk_text(text: str, chunk_size: int = 1600, overlap: int = 320) -> list[str]:
    """
    Chunking recursivo simples com overlap.
    Tenta quebrar em parágrafos → frases → caracteres.
    chunk_size e overlap em caracteres (~400 e 80 tokens respectivamente).
    """
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    separators = ["\n\n", "\n", ". ", " ", ""]

    def split(text: str, sep_idx: int) -> list[str]:
        if sep_idx >= len(separators):
            return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size - overlap)]
        sep = separators[sep_idx]
        parts = text.split(sep) if sep else list(text)
        result = []
        current = ""
        for part in parts:
            candidate = (current + sep + part) if current else part
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    result.append(current)
                    # overlap: carrega o final do chunk anterior
                    overlap_text = current[-overlap:] if len(current) > overlap else current
                    current = overlap_text + (sep if sep else "") + part
                else:
                    result.extend(split(part, sep_idx + 1))
        if current:
            result.append(current)
        return result

    return [c.strip() for c in split(text, 0) if c.strip() and len(c.strip()) > 30]


def _emit(doc_id: str, event: dict) -> None:
    queue = _sse_queues.get(doc_id)
    if queue:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass


def register_sse(doc_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _sse_queues[doc_id] = q
    return q


def unregister_sse(doc_id: str) -> None:
    _sse_queues.pop(doc_id, None)


async def sse_generator(doc_id: str) -> AsyncGenerator[str, None]:
    queue = register_sse(doc_id)
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("step") in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                yield "data: {\"step\": \"ping\"}\n\n"
    finally:
        unregister_sse(doc_id)


def process_document(doc_id: str, loop: asyncio.AbstractEventLoop = None) -> None:
    """
    BackgroundTask: lê, chunka, embeda e armazena no ChromaDB.
    Emite eventos SSE em cada etapa.
    """
    import threading

    def _run():
        google_api_key = os.getenv("GOOGLE_API_KEY", "")
        if not google_api_key:
            admin_db.update_status(doc_id, "error", error_msg="GOOGLE_API_KEY não configurada")
            _emit(doc_id, {"step": "error", "message": "GOOGLE_API_KEY não configurada"})
            return

        doc = admin_db.get_document(doc_id)
        if not doc:
            return

        admin_db.update_status(doc_id, "processing")
        _emit(doc_id, {"step": "reading"})

        # Read raw bytes
        try:
            file_bytes = Path(doc.file_path).read_bytes()
        except Exception as e:
            admin_db.update_status(doc_id, "error", error_msg=f"Leitura: {e}")
            _emit(doc_id, {"step": "error", "message": str(e)})
            return

        try:
            genai_client = genai.Client(api_key=google_api_key)
            collection = _get_chroma_collection()
        except Exception as e:
            admin_db.update_status(doc_id, "error", error_msg=f"Conexão: {e}")
            _emit(doc_id, {"step": "error", "message": str(e)})
            return

        ext = Path(doc.filename).suffix.lstrip(".").lower()
        doc_title = Path(doc.filename).stem.replace("_", " ").replace("-", " ").title()

        if ext in IMAGE_EXTENSIONS:
            # Image branch: single embedding from raw bytes, no chunking
            _emit(doc_id, {"step": "chunking"})
            _emit(doc_id, {"step": "embedding", "done": 0, "total": 1})
            chunk_id = f"{doc.department}_{doc_id}_0"
            try:
                mime_type = IMAGE_MIME.get(ext, "image/jpeg")
                vector = _generate_image_embedding(genai_client, file_bytes, mime_type)
                collection.add(
                    ids=[chunk_id],
                    embeddings=[vector],
                    documents=[doc.filename],
                    metadatas=[{
                        "department": doc.department,
                        "source_file": doc.filename,
                        "doc_title": doc_title,
                        "chunk_index": 0,
                        "file_type": ext,
                    }],
                )
                _emit(doc_id, {"step": "embedding", "done": 1, "total": 1})
            except Exception as e:
                admin_db.update_status(doc_id, "error", error_msg=f"Embedding imagem: {e}")
                _emit(doc_id, {"step": "error", "message": str(e)})
                return

            admin_db.update_status(doc_id, "indexed", chunk_count=1, chroma_ids=[chunk_id])
            _emit(doc_id, {"step": "done", "chunk_count": 1})
            return

        # Text branch: extract → chunk → embed per chunk
        try:
            from src.tools.file_parser import convert_file_to_text
            text = convert_file_to_text(file_bytes, doc.filename)
            if not text or not text.strip():
                raise ValueError("Arquivo vazio ou não pôde ser lido como texto")
        except Exception as e:
            admin_db.update_status(doc_id, "error", error_msg=f"Leitura: {e}")
            _emit(doc_id, {"step": "error", "message": str(e)})
            return

        _emit(doc_id, {"step": "chunking"})
        chunks = _chunk_text(text)
        if not chunks:
            admin_db.update_status(doc_id, "error", error_msg="Nenhum chunk gerado")
            _emit(doc_id, {"step": "error", "message": "Nenhum chunk gerado"})
            return

        total = len(chunks)
        _emit(doc_id, {"step": "embedding", "done": 0, "total": total})

        chroma_ids = []
        for i, chunk in enumerate(chunks):
            try:
                vector = _generate_embedding(genai_client, chunk)
                time.sleep(0.5)
                chunk_id = f"{doc.department}_{doc_id}_{i}"
                collection.add(
                    ids=[chunk_id],
                    embeddings=[vector],
                    documents=[chunk],
                    metadatas=[{
                        "department": doc.department,
                        "source_file": doc.filename,
                        "doc_title": doc_title,
                        "chunk_index": i,
                        "file_type": doc.file_type or "",
                    }],
                )
                chroma_ids.append(chunk_id)
                _emit(doc_id, {"step": "embedding", "done": i + 1, "total": total})
            except Exception as e:
                admin_db.update_status(doc_id, "error", error_msg=f"Chunk {i}: {e}")
                _emit(doc_id, {"step": "error", "message": str(e)})
                return

        admin_db.update_status(
            doc_id,
            "indexed",
            chunk_count=len(chroma_ids),
            chroma_ids=chroma_ids,
        )
        _emit(doc_id, {"step": "done", "chunk_count": len(chroma_ids)})

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
