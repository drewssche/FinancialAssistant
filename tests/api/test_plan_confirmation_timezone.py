import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.orm import sessionmaker

from app.db.models import AuthIdentity
from app.db.session import get_db
from app.main import app
from scripts import run_telegram_admin_bot as bot
from tests.api.test_operations_api import _client_lifecycle


@pytest.fixture
def client():
    yield from _client_lifecycle()


@pytest.fixture
def set_clock(monkeypatch):
    clock = Mock(wraps=datetime)
    monkeypatch.setattr("app.services.plan_service.datetime", clock)

    def set_time(instant):
        clock.now.return_value = datetime.fromisoformat(instant)

    return set_time


def create_plan(client, ui, **options):
    prefs = client.put("/api/v1/preferences", json={"data": {"ui": ui}})
    assert prefs.status_code == 200
    response = client.post("/api/v1/plans", json={
        "scheduled_date": "2026-11-20", "kind": "expense", "amount": "10.00", **options,
    })
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.parametrize(("ui", "instant", "expected"), [
    ({"timezone": "auto", "browser_timezone": "Europe/Minsk"}, "2026-11-14T21:00:01Z", "2026-11-15"),
    ({"timezone": "America/New_York", "browser_timezone": "Europe/Minsk"}, "2026-11-15T04:59:59Z", "2026-11-14"),
    ({"timezone": "America/New_York"}, "2026-07-01T04:00:00Z", "2026-07-01"),
    ({"timezone": "auto", "browser_timezone": "Invalid/Zone"}, "2026-11-14T21:00:01Z", "2026-11-14"),
    ({}, "2026-11-14T21:00:01Z", "2026-11-14"),
])
def test_web_confirmation_uses_account_day(client, set_clock, ui, instant, expected):
    plan_id = create_plan(client, ui)
    set_clock(instant)
    result = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert result.status_code == 200, result.text
    operation = result.json()["operation"]
    assert client.get(f"/api/v1/operations/{operation['id']}").json()["operation_date"] == expected
    assert client.get("/api/v1/plans/history").json()["items"][0]["effective_date"] == expected


def test_telegram_confirms_new_local_day_and_web_rejects_repeat(client, set_clock, monkeypatch):
    plan_id = create_plan(client, {"timezone": "Europe/Minsk"}, recurrence_enabled=True, recurrence_frequency="daily")
    path = f"/api/v1/plans/{plan_id}/confirm"
    set_clock("2026-11-14T20:59:59Z")
    assert client.post(path).json()["operation"]["operation_date"] == "2026-11-14"

    session = app.dependency_overrides[get_db]()
    db = next(session)
    try:
        db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="100500"))
        db.commit()
        monkeypatch.setattr(bot, "SessionLocal", sessionmaker(db.get_bind()))
    finally:
        session.close()

    set_clock("2026-11-14T21:00:01Z")
    transport = SimpleNamespace(call=AsyncMock(return_value={"ok": True}))
    update = {"update_id": 1, "callback_query": {
        "id": "cb", "data": f"planc:{plan_id}", "from": {"id": 100500},
        "message": {"message_id": 1, "chat": {"id": 100500, "type": "private"}},
    }}
    assert asyncio.run(bot.process_update(transport, update))
    edit, answer = transport.call.await_args_list
    assert edit.args[0] == "editMessageText" and "2026-11-15" in edit.args[1]["text"]
    assert answer.args[1]["text"] == "Подтверждено"

    set_clock("2026-11-15T00:00:01Z")
    repeated = client.post(path)
    assert repeated.status_code == 400
    assert "already confirmed today" in repeated.json()["detail"]
    operations = client.get("/api/v1/operations").json()["items"]
    history = client.get("/api/v1/plans/history").json()["items"]
    assert sorted(op["operation_date"] for op in operations) == ["2026-11-14", "2026-11-15"]
    assert sorted(item["effective_date"] for item in history) == ["2026-11-14", "2026-11-15"]


def test_confirmed_exchange_rate_is_effective_on_local_day(client, set_clock):
    for day, rate in [("2026-11-14", "3.10"), ("2026-11-15", "3.20"), ("2026-11-16", "3.30")]:
        result = client.put("/api/v1/currency/rates/current", json={
            "currency": "USD", "rate_date": day, "rate": rate, "source": "nbrb_auto_unit",
        })
        assert result.status_code == 200
    plan_id = create_plan(client, {"timezone": "Europe/Minsk"}, currency="USD")
    set_clock("2026-11-14T21:00:01Z")
    operation = client.post(f"/api/v1/plans/{plan_id}/confirm").json()["operation"]
    assert operation["operation_date"] == operation["fx_rate_date"] == "2026-11-15"
    assert operation["amount"] == "32.00"
