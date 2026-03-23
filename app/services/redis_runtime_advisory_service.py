from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import monotonic

from app.core.cache import get_cache_backend_mode, get_local_cache_entry_count
from app.core.metrics import get_counter_value, get_dashboard_summary_metrics
from app.services.telegram_admin_notifier import notify_redis_fallback_advisory

_SAFE_LOCAL_CACHE_ENTRIES = 25
_SAFE_LOCAL_FALLBACK_READS = 50
_SAFE_LOCAL_FALLBACK_WRITES = 25
_SAFE_DASHBOARD_SUMMARY_P95_MS = 250.0
_P95_MIN_SAMPLES = 5
_ADVISORY_COOLDOWN_SECONDS = 6 * 60 * 60
_ADVISORY_LOCK = Lock()
_LAST_ADVISORY_SENT_AT = 0.0


@dataclass(frozen=True)
class RedisFallbackAdvisory:
    text: str
    local_cache_entries: int
    local_fallback_reads: int
    local_fallback_writes: int
    dashboard_summary_p95_ms: float


class RedisRuntimeAdvisoryService:
    def build_advisory(self) -> RedisFallbackAdvisory | None:
        if get_cache_backend_mode() != "local_fallback":
            return None

        local_cache_entries = get_local_cache_entry_count()
        local_fallback_reads = get_counter_value("backend_cache_local_fallback_read_total")
        local_fallback_writes = get_counter_value("backend_cache_local_fallback_write_total")
        dashboard_metrics = get_dashboard_summary_metrics()
        latency_total = dashboard_metrics.get("latency_total") or {}
        dashboard_summary_p95_ms = float(latency_total.get("p95_ms") or 0.0)
        dashboard_summary_samples = int(latency_total.get("samples") or 0)

        breaches: list[str] = []
        if local_cache_entries >= _SAFE_LOCAL_CACHE_ENTRIES:
            breaches.append(
                f"local cache entries: safe <= {_SAFE_LOCAL_CACHE_ENTRIES}, current={local_cache_entries}"
            )
        if local_fallback_reads >= _SAFE_LOCAL_FALLBACK_READS:
            breaches.append(
                f"local fallback reads: safe <= {_SAFE_LOCAL_FALLBACK_READS}, current={local_fallback_reads}"
            )
        if local_fallback_writes >= _SAFE_LOCAL_FALLBACK_WRITES:
            breaches.append(
                f"local fallback writes: safe <= {_SAFE_LOCAL_FALLBACK_WRITES}, current={local_fallback_writes}"
            )
        if (
            dashboard_summary_samples >= _P95_MIN_SAMPLES
            and dashboard_summary_p95_ms > _SAFE_DASHBOARD_SUMMARY_P95_MS
        ):
            breaches.append(
                "dashboard summary p95: "
                f"safe <= {_SAFE_DASHBOARD_SUMMARY_P95_MS:.0f}ms, current={dashboard_summary_p95_ms:.1f}ms"
            )

        if not breaches:
            return None

        text = (
            "Админ-совет: приложение сейчас работает без Redis и уже вышло за безопасный local-fallback baseline.\n\n"
            "Нормально без Redis для маленькой установки:\n"
            f"- local cache entries <= {_SAFE_LOCAL_CACHE_ENTRIES}\n"
            f"- local fallback reads <= {_SAFE_LOCAL_FALLBACK_READS}\n"
            f"- local fallback writes <= {_SAFE_LOCAL_FALLBACK_WRITES}\n"
            f"- dashboard summary p95 <= {_SAFE_DASHBOARD_SUMMARY_P95_MS:.0f} ms\n\n"
            "Текущие значения:\n"
            f"- local cache entries: {local_cache_entries}\n"
            f"- local fallback reads: {local_fallback_reads}\n"
            f"- local fallback writes: {local_fallback_writes}\n"
            f"- dashboard summary p95: {dashboard_summary_p95_ms:.1f} ms\n\n"
            "Превышения:\n"
            + "\n".join(f"- {item}" for item in breaches)
            + "\n\nРекомендация: подключить Redis для backend cache."
        )
        return RedisFallbackAdvisory(
            text=text,
            local_cache_entries=local_cache_entries,
            local_fallback_reads=local_fallback_reads,
            local_fallback_writes=local_fallback_writes,
            dashboard_summary_p95_ms=dashboard_summary_p95_ms,
        )

    def maybe_send_advisory(self) -> bool:
        advisory = self.build_advisory()
        if advisory is None:
            return False

        now_mono = monotonic()
        global _LAST_ADVISORY_SENT_AT
        with _ADVISORY_LOCK:
            if now_mono - _LAST_ADVISORY_SENT_AT < _ADVISORY_COOLDOWN_SECONDS:
                return False
            notify_redis_fallback_advisory(
                text=advisory.text,
                local_cache_entries=advisory.local_cache_entries,
                local_fallback_reads=advisory.local_fallback_reads,
                local_fallback_writes=advisory.local_fallback_writes,
                dashboard_summary_p95_ms=advisory.dashboard_summary_p95_ms,
            )
            _LAST_ADVISORY_SENT_AT = now_mono
        return True


def reset_redis_runtime_advisory_state_for_tests() -> None:
    global _LAST_ADVISORY_SENT_AT
    with _ADVISORY_LOCK:
        _LAST_ADVISORY_SENT_AT = 0.0
