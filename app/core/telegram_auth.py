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


def verify_and_extract_telegram_login_widget_user(
    auth_data: dict,
    bot_token: str,
    max_age_seconds: int,
) -> dict:
    if not auth_data:
        raise ValueError("Invalid Telegram login payload: empty body")

    provided_hash = str(auth_data.get("hash") or "").strip()
    if not provided_hash:
        raise ValueError("Invalid Telegram login payload: missing hash")

    auth_date_raw = auth_data.get("auth_date")
    if auth_date_raw in (None, ""):
        raise ValueError("Invalid Telegram login payload: missing auth_date")

    try:
        auth_date = int(auth_date_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid Telegram login payload: bad auth_date") from exc

    now_ts = int(time.time())
    if auth_date > now_ts + 30:
        raise ValueError("Invalid Telegram login payload: auth_date is in the future")
    if now_ts - auth_date > max_age_seconds:
        raise ValueError("Invalid Telegram login payload: auth_date expired")

    telegram_id = auth_data.get("id")
    if telegram_id in (None, ""):
        raise ValueError("Invalid Telegram login payload: missing user id")

    pairs = []
    for key, value in auth_data.items():
        if key == "hash" or value in (None, ""):
            continue
        pairs.append((str(key), str(value)))

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs))
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, provided_hash):
        raise ValueError("Invalid Telegram login payload: hash mismatch")

    first_name = str(auth_data.get("first_name") or "").strip()
    last_name = str(auth_data.get("last_name") or "").strip()
    display_name = " ".join(part for part in [first_name, last_name] if part).strip() or first_name or None

    return {
        "telegram_id": str(telegram_id),
        "display_name": display_name,
        "username": auth_data.get("username"),
        "avatar_url": auth_data.get("photo_url"),
    }
