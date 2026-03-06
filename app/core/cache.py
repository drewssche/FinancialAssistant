from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from threading import Lock
from time import time
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.metrics import increment_counter

_DASHBOARD_SUMMARY_PREFIX = "dashsum:v1"
_DASHBOARD_SUMMARY_TTL_SECONDS = 60

_client: Redis | None = None
_client_initialized = False
_client_lock = Lock()
_local_cache: dict[str, tuple[float, str]] = {}
_local_cache_lock = Lock()


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _get_redis_client() -> Redis | None:
    global _client, _client_initialized

    if _client_initialized:
        return _client

    with _client_lock:
        if _client_initialized:
            return _client
        settings = get_settings()
        try:
            _client = Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                decode_responses=True,
                socket_connect_timeout=0.1,
                socket_timeout=0.1,
            )
            _client.ping()
        except RedisError:
            _client = None
        _client_initialized = True
        return _client


def build_dashboard_summary_cache_key(
    *,
    user_id: int,
    period: str,
    date_from: date | None,
    date_to: date | None,
) -> str:
    from_token = date_from.isoformat() if date_from else "-"
    to_token = date_to.isoformat() if date_to else "-"
    return f"{_DASHBOARD_SUMMARY_PREFIX}:u:{user_id}:p:{period}:from:{from_token}:to:{to_token}"


def get_json(cache_key: str) -> dict[str, Any] | None:
    client = _get_redis_client()
    if client:
        try:
            raw = client.get(cache_key)
        except RedisError:
            raw = None
    else:
        with _local_cache_lock:
            record = _local_cache.get(cache_key)
            if not record:
                raw = None
            else:
                expires_at, raw_value = record
                if expires_at <= time():
                    _local_cache.pop(cache_key, None)
                    raw = None
                else:
                    raw = raw_value
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def set_json(cache_key: str, payload: dict[str, Any], ttl_seconds: int = _DASHBOARD_SUMMARY_TTL_SECONDS) -> None:
    client = _get_redis_client()
    encoded = json.dumps(payload, default=_json_default, ensure_ascii=False)
    if client:
        try:
            client.setex(cache_key, ttl_seconds, encoded)
            return
        except RedisError:
            pass
    with _local_cache_lock:
        _local_cache[cache_key] = (time() + ttl_seconds, encoded)


def invalidate_dashboard_summary_cache(user_id: int) -> None:
    increment_counter("dashboard_summary_cache_invalidate_total")
    client = _get_redis_client()
    pattern = f"{_DASHBOARD_SUMMARY_PREFIX}:u:{user_id}:*"
    if client:
        try:
            keys = list(client.scan_iter(match=pattern, count=100))
            if keys:
                client.delete(*keys)
                increment_counter("dashboard_summary_cache_invalidated_keys_total", len(keys))
        except RedisError:
            pass
    with _local_cache_lock:
        keys = [key for key in _local_cache if key.startswith(f"{_DASHBOARD_SUMMARY_PREFIX}:u:{user_id}:")]
        if keys:
            for key in keys:
                _local_cache.pop(key, None)
            increment_counter("dashboard_summary_cache_invalidated_keys_total", len(keys))


def reset_cache_for_tests() -> None:
    global _client, _client_initialized
    with _client_lock:
        _client = None
        _client_initialized = False
    with _local_cache_lock:
        _local_cache.clear()
