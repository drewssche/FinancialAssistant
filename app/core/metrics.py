from __future__ import annotations

from collections import defaultdict, deque
from statistics import mean
from threading import Lock

_COUNTERS: dict[str, int] = defaultdict(int)
_LATENCIES_MS: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=2048))
_HTTP_REQUEST_TOTALS: dict[str, int] = defaultdict(int)
_HTTP_RESPONSE_BYTES: dict[str, deque[int]] = defaultdict(lambda: deque(maxlen=2048))
_LOCK = Lock()


def increment_counter(name: str, value: int = 1) -> None:
    with _LOCK:
        _COUNTERS[name] += value


def get_counter_value(name: str) -> int:
    with _LOCK:
        return int(_COUNTERS.get(name, 0))


def observe_latency_ms(name: str, value_ms: float) -> None:
    with _LOCK:
        _LATENCIES_MS[name].append(max(value_ms, 0.0))


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((len(ordered) - 1) * pct))
    return float(ordered[idx])


def _latency_stats(name: str) -> dict[str, float | int]:
    with _LOCK:
        samples = list(_LATENCIES_MS.get(name, ()))
    if not samples:
        return {"samples": 0, "avg_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0}
    return {
        "samples": len(samples),
        "avg_ms": round(float(mean(samples)), 3),
        "min_ms": round(float(min(samples)), 3),
        "max_ms": round(float(max(samples)), 3),
        "p50_ms": round(_percentile(samples, 0.50), 3),
        "p95_ms": round(_percentile(samples, 0.95), 3),
    }


def get_dashboard_summary_metrics() -> dict:
    with _LOCK:
        hit = _COUNTERS.get("dashboard_summary_cache_hit_total", 0)
        miss = _COUNTERS.get("dashboard_summary_cache_miss_total", 0)
        invalidate = _COUNTERS.get("dashboard_summary_cache_invalidate_total", 0)
        invalidated_keys = _COUNTERS.get("dashboard_summary_cache_invalidated_keys_total", 0)

    return {
        "cache_hit_total": hit,
        "cache_miss_total": miss,
        "cache_invalidate_total": invalidate,
        "cache_invalidated_keys_total": invalidated_keys,
        "cache_hit_ratio": round((hit / (hit + miss)), 4) if (hit + miss) > 0 else 0.0,
        "latency_total": _latency_stats("dashboard_summary_latency_total_ms"),
        "latency_miss_compute": _latency_stats("dashboard_summary_latency_miss_compute_ms"),
        "endpoint_request_totals": get_http_request_totals(),
        "endpoint_response_bytes": get_http_response_size_stats(),
        "database_query_total": get_counter_value("database_query_total"),
        "database_query_error_total": get_counter_value("database_query_error_total"),
        "database_query_latency": _latency_stats("database_query_latency_ms"),
    }


def record_http_request(path: str, method: str) -> None:
    if not path.startswith("/api/v1/"):
        return
    key = f"{method.upper()} {path}"
    with _LOCK:
        _HTTP_REQUEST_TOTALS[key] += 1


def get_http_request_totals() -> dict[str, int]:
    with _LOCK:
        return dict(sorted(_HTTP_REQUEST_TOTALS.items(), key=lambda item: item[0]))


def record_http_response_size(path: str, method: str, size_bytes: int) -> None:
    if not path.startswith("/api/v1/"):
        return
    key = f"{method.upper()} {path}"
    with _LOCK:
        _HTTP_RESPONSE_BYTES[key].append(max(int(size_bytes), 0))


def get_http_response_size_stats() -> dict[str, dict[str, int]]:
    with _LOCK:
        snapshots = {key: list(values) for key, values in _HTTP_RESPONSE_BYTES.items()}
    return {
        key: {
            "samples": len(values),
            "avg_bytes": int(round(sum(values) / len(values))) if values else 0,
            "max_bytes": max(values, default=0),
        }
        for key, values in sorted(snapshots.items(), key=lambda item: item[0])
    }


def reset_metrics_for_tests() -> None:
    with _LOCK:
        _COUNTERS.clear()
        _LATENCIES_MS.clear()
        _HTTP_REQUEST_TOTALS.clear()
        _HTTP_RESPONSE_BYTES.clear()
