import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import scripts.run_telegram_admin_bot as bot


@pytest.mark.parametrize("payload", [
    {}, {"text": ""}, {"text": " \n\t "}, {"text": None}, {"text": 123},
    {"photo": [{}]}, {"sticker": {}}, {"write_access_allowed": {}},
    {"web_app_data": {"data": "private payload"}},
])
def test_non_command_messages_do_not_crash_or_reply(payload, caplog):
    client = SimpleNamespace(call=AsyncMock())
    caplog.set_level("INFO")
    assert asyncio.run(bot.process_update(client, {
        "update_id": 1, "message": {"chat": {"id": 42, "type": "private"}, **payload},
    }))
    client.call.assert_not_called()
    assert "update_failed" not in caplog.text
    assert "private payload" not in caplog.text


def test_start_still_works_after_ignored_message(monkeypatch):
    monkeypatch.setattr(bot, "get_settings", lambda: SimpleNamespace(admin_telegram_id_set={"42"}))
    client = SimpleNamespace(call=AsyncMock())

    async def run():
        for update_id, payload in enumerate([{"photo": []}, {"text": "/start parameter"}]):
            assert await bot.process_update(client, {
                "update_id": update_id, "message": {"chat": {"id": 42}, **payload},
            })

    asyncio.run(run())
    client.call.assert_awaited_once_with("sendMessage", {
        "chat_id": 42, "text": "Уведомления о новых заявках включены.",
    })


def test_failure_is_bounded_and_next_event_is_processed(monkeypatch, caplog):
    handler = AsyncMock(side_effect=[ValueError("secret payload")] * 3 + [None])
    monkeypatch.setattr(bot, "handle_message", handler)
    caplog.set_level("INFO")

    async def run():
        client = SimpleNamespace(call=AsyncMock())
        assert not await bot.process_update(client, {"update_id": 1, "message": {}}, retry_delay_seconds=0)
        assert await bot.process_update(client, {"update_id": 2, "message": {}})

    asyncio.run(run())
    assert handler.await_count == 4
    assert "retries exhausted: update_id=1" in caplog.text
    assert "secret payload" not in caplog.text


def test_failed_callback_notifies_user_and_malformed_envelope_is_isolated(monkeypatch):
    monkeypatch.setattr(bot, "handle_callback_query", AsyncMock(side_effect=ValueError("bad callback")))
    client = SimpleNamespace(call=AsyncMock())
    assert not asyncio.run(bot.process_update(client, {
        "update_id": 1, "callback_query": {"id": "cb1", "message": "invalid"},
    }, retry_delay_seconds=0))
    assert client.call.call_args.args[0] == "answerCallbackQuery"
    assert "Проверьте состояние" in client.call.call_args.args[1]["text"]


def test_cancellation_is_not_swallowed(monkeypatch):
    monkeypatch.setattr(bot, "handle_message", AsyncMock(side_effect=asyncio.CancelledError))
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(bot.process_update(None, {"update_id": 1, "message": {}}))
