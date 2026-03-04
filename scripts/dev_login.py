#!/usr/bin/env python3
"""Generate Telegram-like initData and get a local access token for development."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def build_init_data(bot_token: str, telegram_id: int, first_name: str, username: str, photo_url: str | None) -> str:
    payload = {
        "auth_date": str(int(time.time())),
        "query_id": "dev_query_001",
        "user": json.dumps(
            {
                "id": telegram_id,
                "first_name": first_name,
                "username": username,
                **({"photo_url": photo_url} if photo_url else {}),
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    }

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


def request_access_token(api_url: str, init_data: str) -> tuple[int, str]:
    endpoint = f"{api_url.rstrip('/')}/api/v1/auth/telegram"
    body = json.dumps({"init_data": init_data}).encode("utf-8")
    req = Request(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urlopen(req, timeout=10) as response:
            return response.getcode(), response.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local dev login for Telegram auth flow")
    parser.add_argument("--api-url", default="http://localhost:8001", help="Base URL of backend API")
    parser.add_argument("--telegram-id", type=int, default=100001)
    parser.add_argument("--first-name", default="Dev")
    parser.add_argument("--username", default="dev_user")
    parser.add_argument("--photo-url", default=None)
    parser.add_argument("--bot-token", default=None, help="Overrides TELEGRAM_BOT_TOKEN from env/.env")

    args = parser.parse_args()

    env_file_values = parse_env_file(Path(".env"))
    bot_token = args.bot_token or os.getenv("TELEGRAM_BOT_TOKEN") or env_file_values.get("TELEGRAM_BOT_TOKEN")

    if not bot_token:
        print("ERROR: TELEGRAM_BOT_TOKEN is required (set .env or pass --bot-token).")
        return 1

    init_data = build_init_data(
        bot_token=bot_token,
        telegram_id=args.telegram_id,
        first_name=args.first_name,
        username=args.username,
        photo_url=args.photo_url,
    )

    status_code, response_text = request_access_token(args.api_url, init_data)
    if status_code != 200:
        print("Auth request failed")
        print(f"Status: {status_code}")
        print(f"Response/Error: {response_text}")
        return 1

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        print("Auth response is not JSON")
        print(response_text)
        return 1

    token = data.get("access_token")
    if not token:
        print("No access_token in response")
        print(response_text)
        return 1

    print("Access token received:")
    print(token)
    print("\nQuick test command:")
    print(
        "curl -H \"Authorization: Bearer "
        + token
        + "\" "
        + f"{args.api_url.rstrip('/')}/api/v1/users/me"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
