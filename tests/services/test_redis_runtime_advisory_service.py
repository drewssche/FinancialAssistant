from app.services.redis_runtime_advisory_service import (
    RedisRuntimeAdvisoryService,
    reset_redis_runtime_advisory_state_for_tests,
)


def setup_function():
    reset_redis_runtime_advisory_state_for_tests()


def test_build_advisory_returns_none_within_safe_baseline(monkeypatch):
    monkeypatch.setattr(
        "app.services.redis_runtime_advisory_service.get_cache_backend_mode",
        lambda: "local_fallback",
    )
    monkeypatch.setattr(
        "app.services.redis_runtime_advisory_service.get_local_cache_entry_count",
        lambda: 5,
    )
    monkeypatch.setattr(
        "app.services.redis_runtime_advisory_service.get_counter_value",
        lambda name: 10,
    )
    monkeypatch.setattr(
        "app.services.redis_runtime_advisory_service.get_dashboard_summary_metrics",
        lambda: {"latency_total": {"samples": 2, "p95_ms": 120.0}},
    )

    advisory = RedisRuntimeAdvisoryService().build_advisory()

    assert advisory is None


def test_build_advisory_returns_threshold_based_message(monkeypatch):
    monkeypatch.setattr(
        "app.services.redis_runtime_advisory_service.get_cache_backend_mode",
        lambda: "local_fallback",
    )
    monkeypatch.setattr(
        "app.services.redis_runtime_advisory_service.get_local_cache_entry_count",
        lambda: 40,
    )

    def _counter(name: str) -> int:
        if name == "backend_cache_local_fallback_read_total":
            return 70
        if name == "backend_cache_local_fallback_write_total":
            return 30
        return 0

    monkeypatch.setattr("app.services.redis_runtime_advisory_service.get_counter_value", _counter)
    monkeypatch.setattr(
        "app.services.redis_runtime_advisory_service.get_dashboard_summary_metrics",
        lambda: {"latency_total": {"samples": 8, "p95_ms": 310.0}},
    )

    advisory = RedisRuntimeAdvisoryService().build_advisory()

    assert advisory is not None
    assert advisory.local_cache_entries == 40
    assert advisory.local_fallback_reads == 70
    assert advisory.local_fallback_writes == 30
    assert "пора подключить Redis" in advisory.text
    assert "docker compose --profile cache up --build -d" in advisory.text
    assert "safe <= 25" in advisory.text
    assert "current=40" in advisory.text
    assert "current=70" in advisory.text
    assert "current=30" in advisory.text
    assert "current=310.0ms" in advisory.text


def test_build_advisory_ignores_counter_only_breaches_for_small_install(monkeypatch):
    monkeypatch.setattr(
        "app.services.redis_runtime_advisory_service.get_cache_backend_mode",
        lambda: "local_fallback",
    )
    monkeypatch.setattr(
        "app.services.redis_runtime_advisory_service.get_local_cache_entry_count",
        lambda: 11,
    )

    def _counter(name: str) -> int:
        if name == "backend_cache_local_fallback_read_total":
            return 446
        if name == "backend_cache_local_fallback_write_total":
            return 280
        return 0

    monkeypatch.setattr("app.services.redis_runtime_advisory_service.get_counter_value", _counter)
    monkeypatch.setattr(
        "app.services.redis_runtime_advisory_service.get_dashboard_summary_metrics",
        lambda: {"latency_total": {"samples": 12, "p95_ms": 82.5}},
    )

    advisory = RedisRuntimeAdvisoryService().build_advisory()

    assert advisory is None


def test_maybe_send_advisory_respects_cooldown(monkeypatch):
    monkeypatch.setattr(
        "app.services.redis_runtime_advisory_service.get_cache_backend_mode",
        lambda: "local_fallback",
    )
    monkeypatch.setattr(
        "app.services.redis_runtime_advisory_service.get_local_cache_entry_count",
        lambda: 40,
    )

    def _counter(name: str) -> int:
        if name == "backend_cache_local_fallback_read_total":
            return 70
        if name == "backend_cache_local_fallback_write_total":
            return 30
        return 0

    monkeypatch.setattr("app.services.redis_runtime_advisory_service.get_counter_value", _counter)
    monkeypatch.setattr(
        "app.services.redis_runtime_advisory_service.get_dashboard_summary_metrics",
        lambda: {"latency_total": {"samples": 8, "p95_ms": 310.0}},
    )
    sent_payloads: list[dict] = []
    monkeypatch.setattr(
        "app.services.redis_runtime_advisory_service.notify_redis_fallback_advisory",
        lambda **kwargs: sent_payloads.append(kwargs),
    )

    service = RedisRuntimeAdvisoryService()

    assert service.maybe_send_advisory() is True
    assert service.maybe_send_advisory() is False
    assert len(sent_payloads) == 1
