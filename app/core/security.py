from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import jwt

from app.core.config import get_settings


ALGORITHM = "HS256"


def create_access_token(payload: Dict[str, Any]) -> str:
    settings = get_settings()
    issued_at = datetime.now(timezone.utc)
    expire_at = issued_at + timedelta(minutes=settings.app_access_token_expire_minutes)
    session_started_at = int(payload.get("session_started_at") or issued_at.timestamp())
    token_payload = {
        **payload,
        "iat": int(issued_at.timestamp()),
        "exp": expire_at,
        "session_started_at": session_started_at,
    }
    return jwt.encode(token_payload, settings.app_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])


def get_access_token_expiration(token: str) -> datetime:
    payload = decode_access_token(token)
    return datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc)
