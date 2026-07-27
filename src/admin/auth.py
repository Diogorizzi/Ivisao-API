"""
Autenticação do painel admin: JWT em cookie httponly + bcrypt.
Credenciais lidas de variáveis de ambiente.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Request
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "change-me-in-production-32chars!!")
ALGORITHM = "HS256"
SESSION_TTL = int(os.getenv("ADMIN_SESSION_TTL", "28800"))  # 8h default
COOKIE_NAME = "admin_session"

# Rotas que NÃO precisam de autenticação
_PUBLIC_PATHS = {"/admin/login", "/admin/logout"}


def _admin_username() -> str:
    return os.getenv("ADMIN_USERNAME", "admin")


def _admin_password_hash() -> str:
    return os.getenv("ADMIN_PASSWORD_HASH", "")


def _secret_key() -> str:
    return os.getenv("ADMIN_SECRET_KEY", "change-me-in-production-32chars!!")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(12)).decode()


def check_credentials(username: str, password: str) -> bool:
    stored_hash = _admin_password_hash()
    if not stored_hash:
        return False
    return username == _admin_username() and verify_password(password, stored_hash)


def create_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(seconds=SESSION_TTL)
    return jwt.encode({"sub": _admin_username(), "exp": expire}, _secret_key(), algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def get_current_admin(request: Request) -> str:
    """
    Dependência FastAPI: retorna o username autenticado.
    O redirect já foi tratado pelo middleware — aqui só extrai o user do cookie.
    """
    token = request.cookies.get(COOKIE_NAME)
    return decode_token(token) or _admin_username()


class AdminAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware que protege todas as rotas /admin/* exceto login/logout.
    Intercepta antes do route handler para evitar loops de redirect.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Só processa rotas /admin
        if not path.startswith("/admin"):
            return await call_next(request)

        # Rotas públicas passam direto
        if path in _PUBLIC_PATHS or path.rstrip("/") in _PUBLIC_PATHS:
            return await call_next(request)

        # Verifica cookie
        token = request.cookies.get(COOKIE_NAME)
        user = decode_token(token) if token else None

        if not user:
            # API calls (Bearer token or JSON Accept) get 401, not an HTML redirect
            auth_header = request.headers.get("authorization", "")
            accept_header = request.headers.get("accept", "")
            if auth_header.startswith("Bearer ") or "application/json" in accept_header:
                from starlette.responses import JSONResponse
                return JSONResponse(
                    {"detail": "Unauthorized: valid admin session cookie required for /admin routes"},
                    status_code=401,
                )
            return RedirectResponse(url="/admin/login", status_code=302)

        return await call_next(request)
