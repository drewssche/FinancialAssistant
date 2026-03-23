import asyncio
from datetime import datetime, timezone

from app.core.config import get_settings
from scripts import run_telegram_admin_bot as bot_script


class _RecordingBotClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def call(self, method: str, payload: dict | None = None) -> dict:
        self.calls.append((method, payload or {}))
        return {"ok": True}


def test_build_redis_fallback_advisory_text_includes_runtime_state(monkeypatch):
    monkeypatch.setattr(
        bot_script,
        "get_cache_runtime_status",
        lambda: {
            "backend": "local_fallback",
            "redis_available": False,
            "redis_host": "redis",
            "redis_port": 6379,
            "local_entry_count": 3,
            "namespace_ttls": {"dashboard_summary": 60},
        },
    )

    text = bot_script._build_redis_fallback_advisory_text()

    assert text is not None
    assert "local fallback" in text
    assert "redis=redis:6379" in text
    assert "bot_local_cache_entries=3" in text
    assert "p95 <= 250ms" in text


def test_maybe_send_redis_fallback_advisory_sends_once_per_cooldown(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "1001,1002")
    get_settings.cache_clear()
    monkeypatch.setattr(
        bot_script,
        "get_cache_runtime_status",
        lambda: {
            "backend": "local_fallback",
            "redis_available": False,
            "redis_host": "redis",
            "redis_port": 6379,
            "local_entry_count": 0,
            "namespace_ttls": {},
        },
    )
    monkeypatch.setattr(bot_script, "_REDIS_ADVISORY_STAMP_FILE", tmp_path / "redis_advisory.json")
    client = _RecordingBotClient()

    with caplog.at_level("INFO", logger="financial_assistant_admin_bot"):
        asyncio.run(bot_script.maybe_send_redis_fallback_advisory(client))
        asyncio.run(bot_script.maybe_send_redis_fallback_advisory(client))

    send_calls = [call for call in client.calls if call[0] == "sendMessage"]
    assert len(send_calls) == 2
    assert "telegram_bot_event event=redis_advisory_sent" in caplog.text
    assert "telegram_bot_event event=redis_advisory_skipped reason=cooldown_active" in caplog.text
    get_settings.cache_clear()


def test_redis_advisory_stamp_respects_cooldown(tmp_path, monkeypatch):
    stamp_file = tmp_path / "redis_advisory.json"
    monkeypatch.setattr(bot_script, "_REDIS_ADVISORY_STAMP_FILE", stamp_file)
    now_utc = datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc)

    bot_script._store_redis_advisory_stamp(now_utc)

    assert bot_script._load_redis_advisory_stamp(now_utc) is True
    later_utc = datetime.fromtimestamp(
        now_utc.timestamp() + bot_script._REDIS_ADVISORY_COOLDOWN_SECONDS + 1,
        tz=timezone.utc,
    )
    assert bot_script._load_redis_advisory_stamp(later_utc) is False
