from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from app.api.deps import get_current_user_id
from app.db.models import PlanReminderJob
from app.db.session import get_db
from app.main import app
from tests.api.test_operations_api import _client_lifecycle


@pytest.fixture
def client():
    yield from _client_lifecycle()


@pytest.fixture
def clock(monkeypatch):
    import app.services.plan_service as module

    class FrozenDate(date):
        current = date(2026, 8, 28)

        @classmethod
        def today(cls):
            return cls.current

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.combine(FrozenDate.current, datetime.min.time(), tzinfo=tz or timezone.utc)

    monkeypatch.setattr(module, "date", FrozenDate)
    monkeypatch.setattr(module, "datetime", FrozenDatetime)
    return FrozenDate


def completed_plan(client, *, recurring=False):
    created = client.post("/api/v1/plans", json={
        "kind": "expense", "amount": "2.99", "scheduled_date": "2026-08-28",
        "note": "Подписка", "recurrence_enabled": recurring,
        **({"recurrence_frequency": "monthly", "recurrence_end_date": "2026-08-28"} if recurring else {}),
    })
    assert created.status_code == 201, created.text
    plan_id = created.json()["id"]
    confirmed = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["plan"]["status"] == "confirmed"
    return plan_id, confirmed.json()["operation"]


def test_resume_same_plan_preserves_payment_history_and_schedules_reminder(client, clock):
    plan_id, operation = completed_plan(client)
    clock.current = date(2026, 9, 10)
    preview = client.post(f"/api/v1/plans/{plan_id}/resume-preview", json={"recurrence_frequency": "monthly"})
    assert preview.status_code == 200
    assert preview.json()["scheduled_date"] == "2026-09-28"
    assert client.get(f"/api/v1/plans/{plan_id}").json()["status"] == "confirmed"
    data = {"resume": True, "recurrence_enabled": True, "recurrence_frequency": "monthly",
            "scheduled_date": preview.json()["scheduled_date"], "amount": "3.99"}
    resumed = client.patch(f"/api/v1/plans/{plan_id}", json=data)
    assert resumed.status_code == 200, resumed.text
    plan = resumed.json()
    assert (plan["id"], plan["status"], plan["scheduled_date"]) == (plan_id, "upcoming", "2026-09-28")
    assert plan["confirm_count"] == 1
    assert plan["confirmed_operation_id"] == operation["id"]
    assert client.get(f"/api/v1/operations/{operation['id']}").json() == operation
    assert client.get("/api/v1/operations").json()["total"] == 1
    history = client.get("/api/v1/plans/history").json()
    assert history["total"] == 1
    assert history["items"][0]["amount"] == "2.99"
    assert client.get("/api/v1/plans").json()["items"][0]["status"] == "upcoming"
    events = client.get("/api/v1/activity", params={"entity_type": "plan", "entity_id": plan_id}).json()["items"]
    assert events[0]["title"] == "План возобновлён"
    # A second save from an obsolete completed-plan form cannot reactivate it again.
    assert client.patch(f"/api/v1/plans/{plan_id}", json=data).status_code == 400
    assert client.get("/api/v1/operations").json()["total"] == 1
    session = app.dependency_overrides[get_db]()
    db = next(session)
    try:
        jobs = db.scalars(select(PlanReminderJob).where(PlanReminderJob.plan_id == plan_id, PlanReminderJob.status == "pending")).all()
        assert len(jobs) == 1
    finally:
        session.close()
    clock.current = date(2026, 9, 28)
    next_payment = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert next_payment.status_code == 200, next_payment.text
    assert next_payment.json()["operation"]["amount"] == "3.99"
    assert next_payment.json()["plan"]["scheduled_date"] == "2026-10-28"
    assert client.get("/api/v1/operations").json()["total"] == 2
    assert client.get(f"/api/v1/operations/{operation['id']}").json() == operation



def test_edit_completed_plan_without_resume_keeps_it_completed(client, clock):
    plan_id, operation = completed_plan(client)
    response = client.patch(f"/api/v1/plans/{plan_id}", json={"note": "Новое название", "amount": "4.99"})
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
    assert client.get(f"/api/v1/operations/{operation['id']}").json() == operation
    events = client.get("/api/v1/activity", params={"entity_type": "plan", "entity_id": plan_id}).json()["items"]
    assert "edit" in events[0]["available_actions"]


@pytest.mark.parametrize("extra", [
    {"scheduled_date": "2026-08-28"},
    {"scheduled_date": "2026-09-09"},
    {"recurrence_end_date": "2026-09-20"},
    {"scheduled_date": "2026-10-05", "recurrence_month_end": True},
])
def test_resume_rejects_completed_past_or_expired_dates_atomically(client, clock, extra):
    plan_id, _ = completed_plan(client)
    clock.current = date(2026, 9, 10)
    options = {"recurrence_frequency": "monthly", **extra}
    assert client.post(f"/api/v1/plans/{plan_id}/resume-preview", json=options).status_code == 400
    assert client.patch(f"/api/v1/plans/{plan_id}", json={"resume": True, "recurrence_enabled": True, "amount": "9.99", **options}).status_code == 400
    plan = client.get(f"/api/v1/plans/{plan_id}").json()
    assert plan["status"] == "confirmed"
    assert plan["original_amount"] == "2.99"
    assert not plan["recurrence_enabled"]


def test_expired_recurring_plan_can_be_resumed_with_new_end_date(client, clock):
    plan_id, _ = completed_plan(client, recurring=True)
    clock.current = date(2026, 9, 10)
    assert client.post(f"/api/v1/plans/{plan_id}/confirm").status_code == 400
    assert client.post(f"/api/v1/plans/{plan_id}/skip").status_code == 400
    edit = client.patch(f"/api/v1/plans/{plan_id}", json={"note": "Новая подпись"})
    assert edit.json()["status"] == "confirmed"
    resumed = client.patch(f"/api/v1/plans/{plan_id}", json={"resume": True, "recurrence_end_date": None})
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["scheduled_date"] == "2026-09-28"


def test_resume_accepts_explicit_next_date_and_checks_user_scope(client, clock):
    plan_id, _ = completed_plan(client)
    clock.current = date(2026, 9, 10)
    options = {"scheduled_date": "2026-10-05", "recurrence_frequency": "monthly"}
    assert client.post(f"/api/v1/plans/{plan_id}/resume-preview", json=options).json()["scheduled_date"] == "2026-10-05"
    original_auth = app.dependency_overrides[get_current_user_id]
    app.dependency_overrides[get_current_user_id] = lambda: 999
    try:
        assert client.post(f"/api/v1/plans/{plan_id}/resume-preview", json=options).status_code == 404
        assert client.patch(f"/api/v1/plans/{plan_id}", json={**options, "resume": True, "recurrence_enabled": True}).status_code == 404
    finally:
        app.dependency_overrides[get_current_user_id] = original_auth
    resumed = client.patch(f"/api/v1/plans/{plan_id}", json={**options, "resume": True, "recurrence_enabled": True})
    assert resumed.status_code == 200
    assert resumed.json()["scheduled_date"] == "2026-10-05"


@pytest.mark.parametrize(("options", "expected"), [
    ({"recurrence_frequency": "monthly", "recurrence_month_end": True}, "2026-09-30"),
    ({"recurrence_frequency": "monthly", "recurrence_interval": 2}, "2026-10-28"),
    ({"recurrence_frequency": "yearly"}, "2027-08-28"),
    ({"recurrence_frequency": "monthly", "recurrence_month_end": True, "scheduled_date": "2026-10-31"}, "2026-10-31"),
    ({"recurrence_frequency": "weekly", "recurrence_weekdays": [0, 4]}, "2026-09-14"),
    ({"recurrence_frequency": "daily", "recurrence_workdays_only": True}, "2026-09-14"),
])
def test_resume_preview_uses_existing_recurrence_rules(client, clock, options, expected):
    plan_id, _ = completed_plan(client)
    clock.current = date(2026, 9, 12)
    preview = client.post(f"/api/v1/plans/{plan_id}/resume-preview", json=options)
    assert preview.status_code == 200, preview.text
    assert preview.json()["scheduled_date"] == expected


def test_skipped_plan_can_resume_without_creating_operation(client, clock):
    response = client.post("/api/v1/plans", json={
        "kind": "expense", "amount": "2.99", "scheduled_date": "2026-08-28",
    })
    plan_id = response.json()["id"]
    assert client.post(f"/api/v1/plans/{plan_id}/skip").status_code == 200
    clock.current = date(2026, 9, 10)
    response = client.patch(f"/api/v1/plans/{plan_id}", json={
        "resume": True, "recurrence_enabled": True, "recurrence_frequency": "monthly",
    })
    assert response.status_code == 200
    assert response.json()["status"] == "upcoming"
    assert response.json()["skip_count"] == 1
    assert client.get("/api/v1/operations").json()["total"] == 0
