"""
Utilitário para converter documentos para texto.
Suporta: .pdf (pypdf), .docx, .xlsx, .pptx, .csv, .txt, .md e mais (markitdown).
"""

import io
import os
import re
import tempfile
from pathlib import Path
from typing import Optional


def _extract_pdf(file_bytes: bytes, filename: str) -> Optional[str]:
    """
    Extrai texto de PDF usando pypdf (já instalado como dependência direta).
    Retorna None se o PDF for apenas imagens/escaneado (sem camada de texto).
    """
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text.strip())
        result = "\n\n".join(pages)
        if not result.strip():
            print(f"[pypdf] '{filename}': PDF sem camada de texto (escaneado/imagem).")
            return None
        return result
    except Exception as e:
        print(f"[pypdf] Erro ao converter '{filename}': {e}")
        return None


def convert_file_to_text(file_bytes: bytes, filename: str) -> Optional[str]:
    """
    Converte um arquivo (bytes) para texto.
    - PDFs: usa pypdf diretamente (sem depender de pdfminer.six).
    - Outros formatos: usa markitdown (docx, xlsx, pptx, csv, html, etc.).
    Retorna o conteúdo como string, ou None em caso de falha.
    """
    suffix = Path(filename).suffix.lower()

    # PDFs são tratados diretamente via pypdf
    if suffix == ".pdf":
        return _extract_pdf(file_bytes, filename)

    # Demais formatos: markitdown
    try:
        from markitdown import MarkItDown

        md = MarkItDown()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            result = md.convert(tmp_path)
            # imagens embutidas viram "![](data:image/...base64...)": ruído sem valor para busca
            return re.sub(r"!\[[^\]]*\]\(data:image[^)]*\)", "", result.text_content)
        finally:
            os.unlink(tmp_path)

    except ImportError:
        try:
            return file_bytes.decode("utf-8")
        except Exception:
            return None
    except Exception as e:
        print(f"[markitdown] Erro ao converter '{filename}': {e}")
        return None


# Extensões que a OpenAI API aceita nativamente (apenas PDF)
OPENAI_NATIVE_EXTENSIONS = {".pdf"}

# Extensões que precisam ser convertidas via markitdown
MARKITDOWN_EXTENSIONS = {
    ".docx", ".xlsx", ".pptx", ".doc", ".xls",
    ".csv", ".html", ".htm", ".json", ".xml",
    ".txt", ".md", ".rst"
}


def should_convert_with_markitdown(filename: str) -> bool:
    """
    Verifica se o arquivo precisa ser convertido via markitdown antes de enviar para a LLM.
    """
    suffix = Path(filename).suffix.lower()
    return suffix in MARKITDOWN_EXTENSIONS
