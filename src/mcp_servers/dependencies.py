from fastapi import Header, HTTPException


def get_user_id(x_user_id: str = Header(None)) -> str:
    """
    Extracts user identity from the X-User-Id header.
    The Next.js proxy layer injects this header after validating the session.
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id
