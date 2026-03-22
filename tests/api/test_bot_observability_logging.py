from app.core.logging import log_telegram_bot_event


def test_log_telegram_bot_event_writes_structured_fields(caplog):
    with caplog.at_level("INFO", logger="financial_assistant_admin_bot"):
        log_telegram_bot_event("callback_processed", admin_telegram_id="42", action="approve", user_id=7)

    messages = [record.getMessage() for record in caplog.records if record.name == "financial_assistant_admin_bot"]
    assert any("telegram_bot_event event=callback_processed" in message for message in messages)
    assert any("admin_telegram_id=42" in message for message in messages)
    assert any("action=approve" in message for message in messages)
    assert any("user_id=7" in message for message in messages)
