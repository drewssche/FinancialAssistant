from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import jwt

from app.core.config import get_settings


ALGORITHM = "HS256"


def create_access_token(payload: Dict[str, Any]) -> str:
    settings = get_settings()
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=settings.app_access_token_expire_minutes)
    token_payload = {**payload, "exp": expire_at}
    return jwt.encode(token_payload, settings.app_secret_key, algorithm=ALGORITHM)
