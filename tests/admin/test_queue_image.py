"""Testa geração de embeddings de imagem via Gemini."""
from unittest.mock import MagicMock
import pytest

from src.admin.queue import _generate_image_embedding, IMAGE_EXTENSIONS, IMAGE_MIME


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


def test_image_mime_keys_match_extensions():
    assert IMAGE_MIME.keys() == IMAGE_EXTENSIONS
    assert IMAGE_MIME["png"] == "image/png"
    assert IMAGE_MIME["jpg"] == "image/jpeg"
    assert IMAGE_MIME["jpeg"] == "image/jpeg"


def test_process_image_branch_skips_text_extraction(tmp_path, monkeypatch):
    """Confirms that images don't go through convert_file_to_text or _chunk_text."""
    import src.admin.queue as q

    # Minimal valid 1x1 PNG
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    # Setup fake doc
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

    assert len(convert_called) == 0, "convert_file_to_text should not be called for images"
    assert len(chunk_called) == 0, "_chunk_text should not be called for images"
    assert len(embedded_args) == 1, "_generate_image_embedding should be called once"
    assert embedded_args[0][0] == png_bytes
    assert embedded_args[0][1] == "image/png"
    assert len(chroma_adds) == 1
    assert chroma_adds[0]["metadatas"][0]["file_type"] == "png"
