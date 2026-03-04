import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.core.telegram_auth import verify_and_extract_telegram_user


TEST_BOT_TOKEN = "123456:ABCDEF_TEST_TOKEN"


def build_init_data(user: dict, auth_date: int | None = None) -> str:
    auth_date = auth_date or int(time.time())
    payload = {
        "auth_date": str(auth_date),
        "query_id": "AAHtestQuery",
        "user": json.dumps(user, separators=(",", ":"), ensure_ascii=False),
    }

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", TEST_BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


def test_verify_and_extract_valid_init_data():
    init_data = build_init_data(
        {
            "id": 42,
            "first_name": "Alex",
            "username": "alex_fin",
            "photo_url": "https://example.com/avatar.png",
        }
    )

    result = verify_and_extract_telegram_user(init_data, TEST_BOT_TOKEN, max_age_seconds=3600)

    assert result["telegram_id"] == "42"
    assert result["display_name"] == "Alex"
    assert result["username"] == "alex_fin"


def test_verify_and_extract_rejects_invalid_hash():
    init_data = build_init_data({"id": 42, "first_name": "Alex"}) + "x"

    with pytest.raises(ValueError, match="hash mismatch"):
        verify_and_extract_telegram_user(init_data, TEST_BOT_TOKEN, max_age_seconds=3600)


def test_verify_and_extract_rejects_expired_auth_date():
    expired = int(time.time()) - 7200
    init_data = build_init_data({"id": 42, "first_name": "Alex"}, auth_date=expired)

    with pytest.raises(ValueError, match="expired"):
        verify_and_extract_telegram_user(init_data, TEST_BOT_TOKEN, max_age_seconds=300)
