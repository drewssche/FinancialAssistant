import pytest
from fastapi.testclient import TestClient

from tests.api.test_operations_api import _client_lifecycle


@pytest.fixture
def client():
    yield from _client_lifecycle()


def _create_income_plan(client: TestClient, *, note: str, scheduled_date: str, amount: str) -> int:
    response = client.post(
        "/api/v1/plans",
        json={
            "kind": "income",
            "amount": amount,
            "scheduled_date": scheduled_date,
            "note": note,
            "recurrence_enabled": True,
            "recurrence_frequency": "monthly",
        },
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def test_work_month_is_generated_automatically_and_manual_override_wins(client: TestClient):
    month = client.get("/api/v1/work/month", params={"year": 2026, "month": 8})
    assert month.status_code == 200
    payload = month.json()
    assert payload["summary"]["planned_days"] == 21
    assert payload["summary"]["planned_hours"] == "168.00"
    assert payload["summary"]["override_days"] == 0
    assert payload["days"][0]["status"] == "weekend"
    assert payload["days"][2]["status"] == "workday"

    changed = client.put(
        "/api/v1/work/days/2026-08-10",
        json={"status": "sick_paid", "note": "Сикдей"},
    )
    assert changed.status_code == 200
    day = changed.json()
    assert day["planned_hours"] == "8.00"
    assert day["actual_hours"] == "0.00"
    assert day["credited_hours"] == "8.00"
    assert day["is_manual"] is True

    refreshed = client.get("/api/v1/work/month", params={"year": 2026, "month": 8}).json()
    assert refreshed["summary"]["override_days"] == 1
    assert refreshed["summary"]["sick_days"] == 1

    vacation = client.put(
        "/api/v1/work/days",
        json={
            "date_from": "2026-08-17",
            "date_to": "2026-08-21",
            "status": "vacation",
        },
    )
    assert vacation.status_code == 200
    assert vacation.json()["updated"] == 5
    with_vacation = client.get("/api/v1/work/month", params={"year": 2026, "month": 8}).json()
    assert with_vacation["summary"]["vacation_days"] == 5
    assert with_vacation["days"][16]["credited_hours"] == "8.00"

    reset = client.delete("/api/v1/work/days/2026-08-10")
    assert reset.status_code == 204
    restored = client.get("/api/v1/work/month", params={"year": 2026, "month": 8}).json()["days"][9]
    assert restored["status"] == "workday"
    assert restored["is_manual"] is False


def test_payroll_plans_keep_nominal_days_and_shift_only_backward(client: TestClient):
    salary_plan_id = _create_income_plan(
        client,
        note="Основная часть",
        scheduled_date="2026-09-05",
        amount="1176.00",
    )
    advance_plan_id = _create_income_plan(
        client,
        note="Аванс",
        scheduled_date="2026-08-20",
        amount="1050.00",
    )

    profile = client.put(
        "/api/v1/work/profile",
        json={
            "company": "Битрикс",
            "position": "Разработчик",
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "salary_plan_id": salary_plan_id,
            "advance_plan_id": advance_plan_id,
            "salary_nominal_day": 5,
            "advance_nominal_day": 20,
        },
    )
    assert profile.status_code == 200
    assert profile.json()["payment_shift_rule"] == "previous_workday"

    september = client.get("/api/v1/work/month", params={"year": 2026, "month": 9}).json()
    salary = next(item for item in september["payments"] if item["role"] == "salary")
    assert salary["nominal_date"] == "2026-09-05"
    assert salary["effective_date"] == "2026-09-04"
    assert salary["shifted"] is True

    linked_salary = client.get(f"/api/v1/plans/{salary_plan_id}").json()
    assert linked_salary["scheduled_date"] == "2026-09-04"

    confirmed = client.post(f"/api/v1/plans/{salary_plan_id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["plan"]["scheduled_date"] == "2026-10-05"


def test_work_contract_periods_cannot_overlap(client: TestClient):
    first = client.post(
        "/api/v1/work/contracts",
        json={
            "effective_from": "2026-04-29",
            "company": "Битрикс",
            "position": "Разработчик",
            "salary_amount": "3000.00",
            "currency": "BYN",
        },
    )
    assert first.status_code == 201

    overlap = client.post(
        "/api/v1/work/contracts",
        json={
            "effective_from": "2026-05-01",
            "salary_amount": "3200.00",
            "currency": "BYN",
        },
    )
    assert overlap.status_code == 400
    assert "пересекается" in overlap.json()["detail"]
