import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


def verify_and_extract_telegram_user(
    init_data: str,
    bot_token: str,
    max_age_seconds: int,
) -> dict:
    pairs = parse_qsl(init_data, keep_blank_values=True)
    if not pairs:
        raise ValueError("Invalid Telegram payload: empty init_data")

    payload = dict(pairs)
    provided_hash = payload.get("hash")
    if not provided_hash:
        raise ValueError("Invalid Telegram payload: missing hash")

    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted((k, v) for k, v in pairs if k != "hash")
    )

    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, provided_hash):
        raise ValueError("Invalid Telegram payload: hash mismatch")

    auth_date_raw = payload.get("auth_date")
    if not auth_date_raw:
        raise ValueError("Invalid Telegram payload: missing auth_date")

    try:
        auth_date = int(auth_date_raw)
    except ValueError as exc:
        raise ValueError("Invalid Telegram payload: bad auth_date") from exc

    now_ts = int(time.time())
    if auth_date > now_ts + 30:
        raise ValueError("Invalid Telegram payload: auth_date is in the future")
    if now_ts - auth_date > max_age_seconds:
        raise ValueError("Invalid Telegram payload: auth_date expired")

    user_json = payload.get("user")
    if not user_json:
        raise ValueError("Invalid Telegram payload: missing user")

    try:
        user = json.loads(user_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid Telegram payload: malformed user") from exc

    telegram_id = user.get("id")
    if telegram_id is None:
        raise ValueError("Invalid Telegram payload: missing user id")

    return {
        "telegram_id": str(telegram_id),
        "display_name": user.get("first_name"),
        "username": user.get("username"),
        "avatar_url": user.get("photo_url"),
    }
