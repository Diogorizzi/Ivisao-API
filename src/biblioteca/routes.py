"""
Router FastAPI para operações da Biblioteca do usuário.
Prefixo: /biblioteca  —  montado em src/app.py
"""
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl

from src.middleware.api_key import require_bearer_token
from src.tools.file_parser import convert_file_to_text

router = APIRouter(prefix="/biblioteca", tags=["Biblioteca"])

ALLOWED_EXTENSIONS = {
    "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt",
    "csv", "txt", "md",
}

MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024  # 64 MB


class ProcessarUrlRequest(BaseModel):
    url: str
    filename: str


class ProcessarUrlResponse(BaseModel):
    texto: str
    tamanho_chars: int


@router.post(
    "/processar_url",
    response_model=ProcessarUrlResponse,
    dependencies=[Depends(require_bearer_token)],
)
async def processar_url(body: ProcessarUrlRequest):
    ext = Path(body.filename).suffix.lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de arquivo não suportado: .{ext}",
        )

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            response = await client.get(body.url, headers={"User-Agent": "Dartha/1.0"})
            response.raise_for_status()

            content_length = int(response.headers.get("content-length", 0))
            if content_length > MAX_DOWNLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"Arquivo muito grande. Limite: {MAX_DOWNLOAD_BYTES // (1024*1024)} MB.",
                )

            file_bytes = response.content
            if len(file_bytes) > MAX_DOWNLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"Arquivo muito grande. Limite: {MAX_DOWNLOAD_BYTES // (1024*1024)} MB.",
                )

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao baixar arquivo: HTTP {e.response.status_code}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro de rede ao baixar arquivo: {e}",
        )

    texto = convert_file_to_text(file_bytes, body.filename)
    if not texto or not texto.strip():
        raise HTTPException(
            status_code=422,
            detail="Não foi possível extrair texto do arquivo. Pode ser escaneado ou corrompido.",
        )

    return ProcessarUrlResponse(texto=texto, tamanho_chars=len(texto))
