# Multimodal Image Embeddings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Suportar embeddings multimodal de imagens (PNG/JPG/JPEG) no pipeline RAG usando `gemini-embedding-2-preview`, gerando vetores diretamente dos bytes da imagem sem necessidade de extração de texto.

**Architecture:** Detectar no `process_document()` se o arquivo é uma imagem e, em vez de tentar extrair texto, gerar o embedding diretamente dos bytes da imagem via `embed_content` com `inline_data`. O vetor resultante (768 dims) vai para o ChromaDB no mesmo espaço vetorial que embeddings de texto, permitindo busca cross-modal. Na busca (query), imagens também podem ser indexadas e recuperadas por consultas de texto.

**Tech Stack:** Python, `google-genai` SDK (já instalado), `google.genai.types.Blob`, ChromaDB HTTP client, FastAPI BackgroundTasks.

---

## File Map

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `src/admin/queue.py` | Modificar | Detectar imagens, branch para `_generate_image_embedding()`, skip chunking |
| `src/tools/file_parser.py` | Sem alteração | Não é chamado para imagens |

Apenas **um arquivo** de código precisa mudar.

---

### Task 1: Adicionar `_generate_image_embedding()` e branch de imagem no `process_document()`

**Files:**
- Modify: `src/admin/queue.py`

O objetivo é:
1. Criar constante `IMAGE_EXTENSIONS` com os tipos suportados.
2. Criar função `_generate_image_embedding(client, file_bytes, mime_type)` que usa `inline_data`.
3. No `process_document._run()`, logo após ler `doc.file_path`, detectar se é imagem e seguir branch separado que pula `convert_file_to_text` e `_chunk_text`, gerando um único vetor do arquivo inteiro.

- [ ] **Step 1: Escrever o teste de `_generate_image_embedding`**

Crie o arquivo `tests/admin/test_queue_image.py`:

```python
"""Testa geração de embeddings de imagem via Gemini."""
from unittest.mock import MagicMock, patch
import pytest

from src.admin.queue import _generate_image_embedding, IMAGE_EXTENSIONS


def _fake_embedding(values):
    emb = MagicMock()
    emb.values = values
    return emb


def test_image_extensions_defined():
    assert "png" in IMAGE_EXTENSIONS
    assert "jpg" in IMAGE_EXTENSIONS
    assert "jpeg" in IMAGE_EXTENSIONS


def test_generate_image_embedding_returns_vector():
    fake_client = MagicMock()
    fake_result = MagicMock()
    fake_result.embeddings = [_fake_embedding([0.1, 0.2, 0.3])]
    fake_client.models.embed_content.return_value = fake_result

    vector = _generate_image_embedding(fake_client, b"fakebytes", "image/png")

    assert vector == [0.1, 0.2, 0.3]
    call_kwargs = fake_client.models.embed_content.call_args
    assert call_kwargs.kwargs["model"] == "gemini-embedding-2-preview"
    # Deve ter passado inline_data, não texto
    contents = call_kwargs.kwargs["contents"]
    assert len(contents) == 1
    part = contents[0].parts[0]
    assert part.inline_data.mime_type == "image/png"
    assert part.inline_data.data == b"fakebytes"
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

```bash
cd d:/Documentos/Projetos/AgnoAgents/Dartha-API-V3
python -m pytest tests/admin/test_queue_image.py -v
```

Esperado: `FAILED` com `ImportError: cannot import name '_generate_image_embedding'` ou `ImportError: cannot import name 'IMAGE_EXTENSIONS'`.

- [ ] **Step 3: Implementar `IMAGE_EXTENSIONS` e `_generate_image_embedding` em `src/admin/queue.py`**

Abrir [src/admin/queue.py](src/admin/queue.py) e adicionar logo após a linha `EMBEDDING_MODEL = "gemini-embedding-2-preview"` (linha 24):

```python
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
IMAGE_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}
```

Adicionar a função logo após `_generate_embedding` (após a linha 44):

```python
def _generate_image_embedding(client: genai.Client, file_bytes: bytes, mime_type: str) -> list:
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
```

- [ ] **Step 4: Rodar o teste de unidade para confirmar que passa**

```bash
python -m pytest tests/admin/test_queue_image.py::test_image_extensions_defined tests/admin/test_queue_image.py::test_generate_image_embedding_returns_vector -v
```

Esperado: `2 passed`.

- [ ] **Step 5: Commit das constantes e função de embedding de imagem**

```bash
git add src/admin/queue.py tests/admin/test_queue_image.py
git commit -m "feat: add _generate_image_embedding and IMAGE_EXTENSIONS to queue"
```

---

### Task 2: Branch de imagem no `process_document._run()`

**Files:**
- Modify: `src/admin/queue.py` — função `process_document._run()`

- [ ] **Step 1: Escrever o teste de integração do branch de imagem**

Adicionar ao final de `tests/admin/test_queue_image.py`:

```python
def test_process_image_branch_skips_text_extraction(tmp_path, monkeypatch):
    """Confirma que imagens não passam por convert_file_to_text nem _chunk_text."""
    import src.admin.queue as q

    # Imagem mínima PNG 1x1 válida
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    # Setup fake doc no DB
    fake_doc = MagicMock()
    fake_doc.file_path = str(tmp_path / "test.png")
    fake_doc.filename = "test.png"
    fake_doc.file_type = "png"
    fake_doc.department = "juridico"
    import pathlib
    pathlib.Path(fake_doc.file_path).write_bytes(png_bytes)

    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
    monkeypatch.setattr("src.admin.db.get_document", lambda doc_id: fake_doc)
    monkeypatch.setattr("src.admin.db.update_status", lambda *a, **kw: None)

    convert_called = []
    chunk_called = []
    monkeypatch.setattr("src.tools.file_parser.convert_file_to_text",
                        lambda *a, **kw: convert_called.append(1) or "")
    monkeypatch.setattr(q, "_chunk_text", lambda *a, **kw: chunk_called.append(1) or [])

    embedded_args = []

    def fake_embed_image(client, file_bytes, mime_type):
        embedded_args.append((file_bytes, mime_type))
        return [0.1] * 768

    monkeypatch.setattr(q, "_generate_image_embedding", fake_embed_image)

    chroma_adds = []

    class FakeCollection:
        def add(self, **kw):
            chroma_adds.append(kw)

    monkeypatch.setattr(q, "_get_chroma_collection", lambda: FakeCollection())

    import google.genai as genai_mod
    monkeypatch.setattr(genai_mod, "Client", lambda api_key: MagicMock())

    # Executa synchronously (sem thread) para facilitar assertions
    import threading
    thread = None

    original_thread = threading.Thread

    def capture_thread(target, **kw):
        nonlocal thread
        thread = original_thread(target=target, **kw)
        return thread

    monkeypatch.setattr(threading, "Thread", capture_thread)

    q.process_document("doc-123")
    if thread:
        thread.join(timeout=5)

    assert len(convert_called) == 0, "convert_file_to_text não deve ser chamada para imagens"
    assert len(chunk_called) == 0, "_chunk_text não deve ser chamada para imagens"
    assert len(embedded_args) == 1, "_generate_image_embedding deve ser chamada uma vez"
    assert embedded_args[0][0] == png_bytes
    assert embedded_args[0][1] == "image/png"
    assert len(chroma_adds) == 1
    assert chroma_adds[0]["metadatas"][0]["file_type"] == "png"
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

```bash
python -m pytest tests/admin/test_queue_image.py::test_process_image_branch_skips_text_extraction -v
```

Esperado: `FAILED` — o branch de imagem ainda não existe em `_run()`.

- [ ] **Step 3: Adicionar o branch de imagem em `process_document._run()`**

Em `src/admin/queue.py`, dentro de `_run()`, substituir o bloco de leitura + chunking + embedding pelo código abaixo. O bloco original vai de `admin_db.update_status(doc_id, "processing")` até o loop de `for i, chunk in enumerate(chunks)`. Substitua toda a lógica após o `update_status("processing")` por:

```python
        admin_db.update_status(doc_id, "processing")
        _emit(doc_id, {"step": "reading"})

        # Leitura do arquivo
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
            # Branch de imagem: um único embedding do arquivo inteiro
            _emit(doc_id, {"step": "embedding", "done": 0, "total": 1})
            try:
                mime_type = IMAGE_MIME.get(ext, "image/jpeg")
                vector = _generate_image_embedding(genai_client, file_bytes, mime_type)
                chunk_id = f"{doc.department}_{doc_id}_0"
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

        # Branch de texto: extração → chunking → embedding por chunk
        try:
            from src.tools.file_parser import convert_file_to_text
            text = convert_file_to_text(file_bytes, doc.filename)
            if not text or not text.strip():
                raise ValueError("Arquivo vazio ou não pôde ser lido como texto")
        except Exception as e:
            admin_db.update_status(doc_id, "error", error_msg=f"Leitura: {e}")
            _emit(doc_id, {"step": "error", "message": str(e)})
            return

        # Chunking
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
```

> **Atenção:** Remova as linhas originais do bloco de leitura (que importava `convert_file_to_text`) e do loop de chunks. O novo código os substitui completamente.

- [ ] **Step 4: Rodar todos os testes de imagem**

```bash
python -m pytest tests/admin/test_queue_image.py -v
```

Esperado: `3 passed`.

- [ ] **Step 5: Commit do branch de imagem no pipeline**

```bash
git add src/admin/queue.py tests/admin/test_queue_image.py
git commit -m "feat: process images with multimodal embedding, skip text extraction"
```

---

### Task 3: Verificação visual no admin

**Files:**
- Nenhum arquivo novo — confirmar que o upload de imagem já funciona end-to-end.

- [ ] **Step 1: Iniciar o servidor**

```bash
cd d:/Documentos/Projetos/AgnoAgents/Dartha-API-V3
uvicorn src.app:app --reload --port 8001
```

- [ ] **Step 2: Acessar o admin e fazer upload de uma imagem**

Abrir `http://localhost:8001/admin`, escolher um departamento, clicar em "Enviar arquivos" e arrastar um `.png` ou `.jpg`. Verificar:
- O arquivo aparece na fila com status `pending`
- A barra de progresso avança até `Gerando embeddings (0/1)` → `(1/1)`
- O arquivo termina com status `✓ indexado` e `1 chunk`
- Nenhum erro no console do servidor

- [ ] **Step 3: Verificar que documentos de texto ainda funcionam**

Fazer upload de um `.pdf` ou `.txt` no mesmo departamento e confirmar que o fluxo normal de chunking e embedding continua funcionando.

- [ ] **Step 4: Commit final de confirmação (se houver ajustes)**

```bash
git add -p  # só se houver mudanças
git commit -m "fix: adjust image embedding pipeline after manual testing"
```

---

## Self-Review

**Cobertura do spec:**
- [x] Detectar arquivo de imagem no `process_document` → Task 2
- [x] Usar `_generate_image_embedding` com `inline_data` → Task 1 + 2
- [x] Pular `convert_file_to_text` e `_chunk_text` para imagens → Task 2
- [x] Armazenar no ChromaDB com metadado `file_type` correto → Task 2
- [x] Progresso SSE funciona para imagens (emit `done:0/total:1` → `done:1/total:1`) → Task 2
- [x] Docs de texto continuam funcionando sem regressão → Task 3

**Placeholder scan:** Nenhum TBD ou TODO.

**Type consistency:**
- `_generate_image_embedding(client, file_bytes, mime_type)` → definida na Task 1, usada na Task 2 ✓
- `IMAGE_EXTENSIONS` e `IMAGE_MIME` → definidas na Task 1, usadas na Task 2 ✓
- `chunk_id` → mesma convenção `{department}_{doc_id}_{index}` usada no branch de texto ✓
