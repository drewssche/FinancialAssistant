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
_DASHBOARD_ANALYTICS_PREFIX = "dashanalytics:v1"
_DASHBOARD_ANALYTICS_TTL_SECONDS = 60
_PLANS_PREFIX = "plans:v1"
_PLANS_TTL_SECONDS = 60
_ITEM_TEMPLATES_PREFIX = "itemtpl:v1"
_ITEM_TEMPLATES_TTL_SECONDS = 60
_DEBTS_PREFIX = "debts:v1"
_DEBTS_TTL_SECONDS = 60
_OPERATIONS_PREFIX = "ops:v1"
_OPERATIONS_TTL_SECONDS = 60
_CATEGORIES_PREFIX = "cats:v1"
_CATEGORIES_TTL_SECONDS = 60

_CACHE_NAMESPACE_PREFIXES = {
    "dashboard_summary": _DASHBOARD_SUMMARY_PREFIX,
    "dashboard_analytics": _DASHBOARD_ANALYTICS_PREFIX,
    "plans": _PLANS_PREFIX,
    "item_templates": _ITEM_TEMPLATES_PREFIX,
    "debts": _DEBTS_PREFIX,
    "operations": _OPERATIONS_PREFIX,
    "categories": _CATEGORIES_PREFIX,
}

_CACHE_NAMESPACE_TTLS = {
    "dashboard_summary": _DASHBOARD_SUMMARY_TTL_SECONDS,
    "dashboard_analytics": _DASHBOARD_ANALYTICS_TTL_SECONDS,
    "plans": _PLANS_TTL_SECONDS,
    "item_templates": _ITEM_TEMPLATES_TTL_SECONDS,
    "debts": _DEBTS_TTL_SECONDS,
    "operations": _OPERATIONS_TTL_SECONDS,
    "categories": _CATEGORIES_TTL_SECONDS,
}

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


def _cache_token(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _get_cache_namespace_prefix(namespace: str) -> str:
    try:
        return _CACHE_NAMESPACE_PREFIXES[namespace]
    except KeyError as exc:
        raise ValueError(f"Unknown cache namespace: {namespace}") from exc


def get_namespace_ttl_seconds(namespace: str) -> int:
    try:
        return _CACHE_NAMESPACE_TTLS[namespace]
    except KeyError as exc:
        raise ValueError(f"Unknown cache namespace: {namespace}") from exc


def build_user_scoped_cache_key(
    *,
    namespace: str,
    user_id: int,
    **parts: Any,
) -> str:
    prefix = _get_cache_namespace_prefix(namespace)
    key = f"{prefix}:u:{user_id}"
    for part_name, part_value in parts.items():
        key += f":{part_name}:{_cache_token(part_value)}"
    return key


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
    return build_user_scoped_cache_key(
        namespace="dashboard_summary",
        user_id=user_id,
        p=period,
        from_=date_from,
        to=date_to,
    ).replace(":from_:", ":from:")


def build_dashboard_analytics_cache_key(
    *,
    user_id: int,
    view: str,
    period: str,
    date_from: date | None,
    date_to: date | None,
    month_anchor: date | None = None,
    category_kind: str | None = None,
    category_breakdown_level: str | None = None,
    granularity: str | None = None,
    year_anchor: int | None = None,
) -> str:
    return (
        build_user_scoped_cache_key(
            namespace="dashboard_analytics",
            user_id=user_id,
            view=view,
            period=period,
            from_=date_from,
            to=date_to,
            month=month_anchor,
            category_kind=category_kind,
            category_breakdown_level=category_breakdown_level,
            granularity=granularity,
            year=year_anchor,
        )
        .replace(":from_:", ":from:")
    )


def build_plans_cache_key(
    *,
    user_id: int,
    view: str,
    q: str | None = None,
    kind: str | None = None,
) -> str:
    return build_user_scoped_cache_key(
        namespace="plans",
        user_id=user_id,
        view=view,
        q=q,
        kind=kind,
    )


def build_item_templates_cache_key(
    *,
    user_id: int,
    view: str,
    page: int | None = None,
    page_size: int | None = None,
    q: str | None = None,
    template_id: int | None = None,
    limit: int | None = None,
) -> str:
    return build_user_scoped_cache_key(
        namespace="item_templates",
        user_id=user_id,
        view=view,
        page=page,
        page_size=page_size,
        q=q,
        template_id=template_id,
        limit=limit,
    )


def build_debts_cache_key(
    *,
    user_id: int,
    view: str,
    include_closed: bool | None = None,
    q: str | None = None,
) -> str:
    return build_user_scoped_cache_key(
        namespace="debts",
        user_id=user_id,
        view=view,
        include_closed=include_closed,
        q=q,
    )


def build_operations_cache_key(
    *,
    user_id: int,
    view: str,
    page: int | None = None,
    page_size: int | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    kind: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    category_id: int | None = None,
    q: str | None = None,
    quick_view: str | None = None,
) -> str:
    return build_user_scoped_cache_key(
        namespace="operations",
        user_id=user_id,
        view=view,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
        kind=kind,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        q=q,
        quick_view=quick_view,
    )


def build_categories_cache_key(
    *,
    user_id: int,
    view: str,
    page: int | None = None,
    page_size: int | None = None,
    kind: str | None = None,
    q: str | None = None,
) -> str:
    return build_user_scoped_cache_key(
        namespace="categories",
        user_id=user_id,
        view=view,
        page=page,
        page_size=page_size,
        kind=kind,
        q=q,
    )


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


def invalidate_user_scoped_cache(
    *,
    namespace: str,
    user_id: int,
    metrics_prefix: str | None = None,
) -> None:
    prefix = _get_cache_namespace_prefix(namespace)
    if metrics_prefix:
        increment_counter(f"{metrics_prefix}_invalidate_total")
    client = _get_redis_client()
    pattern = f"{prefix}:u:{user_id}:*"
    if client:
        try:
            keys = list(client.scan_iter(match=pattern, count=100))
            if keys:
                client.delete(*keys)
                if metrics_prefix:
                    increment_counter(f"{metrics_prefix}_invalidated_keys_total", len(keys))
        except RedisError:
            pass
    with _local_cache_lock:
        keys = [key for key in _local_cache if key.startswith(f"{prefix}:u:{user_id}:")]
        if keys:
            for key in keys:
                _local_cache.pop(key, None)
            if metrics_prefix:
                increment_counter(f"{metrics_prefix}_invalidated_keys_total", len(keys))


def invalidate_dashboard_summary_cache(user_id: int) -> None:
    invalidate_user_scoped_cache(
        namespace="dashboard_summary",
        user_id=user_id,
        metrics_prefix="dashboard_summary_cache",
    )


def invalidate_dashboard_analytics_cache(user_id: int) -> None:
    invalidate_user_scoped_cache(
        namespace="dashboard_analytics",
        user_id=user_id,
    )


def invalidate_plans_cache(user_id: int) -> None:
    invalidate_user_scoped_cache(
        namespace="plans",
        user_id=user_id,
    )


def invalidate_item_templates_cache(user_id: int) -> None:
    invalidate_user_scoped_cache(
        namespace="item_templates",
        user_id=user_id,
    )


def invalidate_debts_cache(user_id: int) -> None:
    invalidate_user_scoped_cache(
        namespace="debts",
        user_id=user_id,
    )


def invalidate_operations_cache(user_id: int) -> None:
    invalidate_user_scoped_cache(
        namespace="operations",
        user_id=user_id,
    )


def invalidate_categories_cache(user_id: int) -> None:
    invalidate_user_scoped_cache(
        namespace="categories",
        user_id=user_id,
    )


def reset_cache_for_tests() -> None:
    global _client, _client_initialized
    with _client_lock:
        _client = None
        _client_initialized = False
    with _local_cache_lock:
        _local_cache.clear()
