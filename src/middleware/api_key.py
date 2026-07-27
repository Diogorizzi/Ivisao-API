"""
FastAPI dependency: validates Authorization: Bearer <token> on protected endpoints.
The token must match API_SECRET_KEY from the environment.
"""
import hmac
import logging
import os
from typing import Optional

from fastapi import Header, HTTPException

_log = logging.getLogger(__name__)


async def require_bearer_token(authorization: Optional[str] = Header(None)) -> None:
    """
    Raises 403 if the Bearer token is missing or wrong.
    Raises 503 if API_SECRET_KEY is not configured on this server.
    """
    secret = os.getenv("API_SECRET_KEY", "")
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Endpoint disabled: API_SECRET_KEY is not configured on this server.",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Missing or malformed Authorization header.")

    token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, secret):
        _log.warning("Rejected request: invalid bearer token")
        raise HTTPException(status_code=403, detail="Invalid bearer token.")
