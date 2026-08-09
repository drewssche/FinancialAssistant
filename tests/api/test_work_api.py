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


def test_belarus_2026_calendar_and_work_statistics_match_production_hours(client: TestClient):
    april = client.get("/api/v1/work/month", params={"year": 2026, "month": 4})
    assert april.status_code == 200
    april_payload = april.json()
    assert april_payload["summary"]["planned_hours"] == "166.00"
    assert april_payload["days"][24]["status"] == "transferred_workday"
    assert april_payload["days"][24]["planned_hours"] == "7.00"

    statistics = client.get(
        "/api/v1/work/statistics",
        params={"period": "month", "anchor": "2026-08-01"},
    )
    assert statistics.status_code == 200
    payload = statistics.json()
    assert payload["date_from"] == "2026-08-01"
    assert payload["date_to"] == "2026-08-31"
    assert payload["planned_days"] == 21
    assert payload["planned_hours"] == "168.00"
    assert payload["actual_hours"] == "40.00"
    assert payload["future_planned_hours"] == "128.00"
    assert len(payload["months"]) == 1


def test_belarus_historical_transfers_are_applied_to_timesheet(client: TestClient):
    may_2024 = client.get("/api/v1/work/month", params={"year": 2024, "month": 5})
    assert may_2024.status_code == 200
    assert may_2024.json()["days"][12]["status"] == "day_off"
    assert may_2024.json()["days"][17]["status"] == "transferred_workday"
    assert may_2024.json()["days"][17]["planned_hours"] == "7.00"

    july_2025 = client.get("/api/v1/work/month", params={"year": 2025, "month": 7})
    assert july_2025.status_code == 200
    assert july_2025.json()["days"][3]["status"] == "day_off"
    assert july_2025.json()["days"][11]["status"] == "transferred_workday"
    assert july_2025.json()["days"][11]["planned_hours"] == "8.00"


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


def test_new_current_job_closes_previous_period_and_keeps_history(client: TestClient):
    first = client.post(
        "/api/v1/work/contracts",
        json={
            "effective_from": "2024-04-12",
            "company": "Инолта",
            "currency": "BYN",
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/work/contracts",
        json={
            "effective_from": "2024-04-29",
            "company": "Битрикс",
            "currency": "BYN",
        },
    )
    assert second.status_code == 201
    history = client.get("/api/v1/work/contracts").json()
    assert [item["company"] for item in history] == ["Битрикс", "Инолта"]
    assert history[1]["effective_to"] == "2024-04-29"
    profile = client.get("/api/v1/work/profile").json()
    assert profile["company"] == "Битрикс"
    assert profile["employment_start_date"] == "2024-04-29"

    updated = client.put(
        f"/api/v1/work/contracts/{second.json()['id']}",
        json={
            "effective_from": "2024-04-29",
            "company": "Битрикс",
            "position": "Разработчик",
            "salary_amount": "3500.00",
            "currency": "BYN",
            "note": "Текущая должность",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["position"] == "Разработчик"
    assert updated.json()["salary_amount"] == "3500.00"
    updated_profile = client.get("/api/v1/work/profile").json()
    assert updated_profile["position"] == "Разработчик"

    salary_category = client.post(
        "/api/v1/categories",
        json={"name": "Зарплата", "kind": "income"},
    )
    assert salary_category.status_code == 200
    category_id = salary_category.json()["id"]
    for operation_date, amount in (
        ("2024-04-20", "200.00"),
        ("2024-04-29", "1500.00"),
        ("2024-05-03", "500.00"),
    ):
        created = client.post(
            "/api/v1/operations",
            json={
                "kind": "income",
                "amount": amount,
                "operation_date": operation_date,
                "category_id": category_id,
            },
        )
        assert created.status_code == 201

    companies = client.get("/api/v1/work/companies")
    assert companies.status_code == 200
    company_map = {item["company"]: item for item in companies.json()}
    assert company_map["Инолта"]["earnings"] == [{"currency": "BYN", "amount": "200.00"}]
    assert company_map["Битрикс"]["earnings"] == [{"currency": "BYN", "amount": "2000.00"}]
    assert company_map["Битрикс"]["salary_operation_count"] == 2
    assert company_map["Битрикс"]["is_current"] is True

    overlap = client.post(
        "/api/v1/work/contracts",
        json={
            "effective_from": "2024-04-15",
            "effective_to": "2024-04-20",
            "company": "Другая компания",
            "currency": "BYN",
        },
    )
    assert overlap.status_code == 400
    assert "пересекается" in overlap.json()["detail"]


def test_raise_can_start_on_previous_period_end_without_resetting_employment_start(client: TestClient):
    first = client.post(
        "/api/v1/work/contracts",
        json={
            "effective_from": "2024-04-29",
            "company": "Битрикс",
            "position": "Специалист",
            "salary_amount": "1500.00",
            "currency": "BYN",
        },
    )
    assert first.status_code == 201
    raised = client.post(
        "/api/v1/work/contracts",
        json={
            "effective_from": "2025-04-29",
            "company": "Битрикс",
            "position": "Ведущий специалист",
            "salary_amount": "1800.00",
            "currency": "BYN",
        },
    )
    assert raised.status_code == 201

    history = client.get("/api/v1/work/contracts").json()
    assert history[1]["effective_to"] == "2025-04-29"
    assert history[0]["effective_from"] == "2025-04-29"
    profile = client.get("/api/v1/work/profile").json()
    assert profile["position"] == "Ведущий специалист"
    assert profile["employment_start_date"] == "2024-04-29"
