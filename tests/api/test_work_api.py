from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import WorkProfile
from app.db.session import get_db
from app.main import app
from app.services import work_service as work_service_module
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


def test_work_profile_schedule_defaults_can_be_updated(client: TestClient):
    default_profile = client.get("/api/v1/work/profile")
    assert default_profile.status_code == 200
    assert {
        key: default_profile.json()[key]
        for key in (
            "workday_start_time",
            "workday_end_time",
            "lunch_start_time",
            "lunch_end_time",
        )
    } == {
        "workday_start_time": "09:00:00",
        "workday_end_time": "18:00:00",
        "lunch_start_time": "13:00:00",
        "lunch_end_time": "14:00:00",
    }

    updated = client.put(
        "/api/v1/work/profile",
        json={
            "company": "Битрикс",
            "position": "Разработчик",
            "standard_hours_per_day": "8.00",
            "workday_start_time": "08:30",
            "workday_end_time": "17:45",
            "lunch_start_time": "12:15",
            "lunch_end_time": "13:00",
            "workweek_days": [0, 1, 2, 3, 4],
            "advance_nominal_day": 20,
            "salary_nominal_day": 5,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["workday_start_time"] == "08:30:00"
    assert updated.json()["workday_end_time"] == "17:45:00"
    assert updated.json()["lunch_start_time"] == "12:15:00"
    assert updated.json()["lunch_end_time"] == "13:00:00"

    refreshed = client.get("/api/v1/work/profile")
    assert refreshed.status_code == 200
    assert refreshed.json()["workday_start_time"] == "08:30:00"
    assert refreshed.json()["lunch_end_time"] == "13:00:00"

    invalid = client.put(
        "/api/v1/work/profile",
        json={
            "workday_start_time": "09:00",
            "workday_end_time": "18:00",
            "lunch_start_time": "14:00",
            "lunch_end_time": "13:00",
        },
    )
    assert invalid.status_code == 422

    too_many_hours = client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workday_start_time": "09:00",
            "workday_end_time": "17:00",
            "lunch_start_time": "13:00",
            "lunch_end_time": "14:00",
        },
    )
    assert too_many_hours.status_code == 422

    shared_plan_id = _create_income_plan(
        client,
        note="Один план для двух ролей",
        scheduled_date="2026-08-20",
        amount="1000.00",
    )
    duplicate_roles = client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "advance_plan_id": shared_plan_id,
            "salary_plan_id": shared_plan_id,
        },
    )
    assert duplicate_roles.status_code == 422


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


def test_today_uses_live_elapsed_hours_until_manual_actual_override(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 8, 10)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = cls(2026, 8, 10, 11, 30)
            return current.replace(tzinfo=tz) if tz else current

    monkeypatch.setattr(work_service_module, "date", FixedDate)
    monkeypatch.setattr(work_service_module, "datetime", FixedDateTime)

    profile = client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workday_start_time": "09:00",
            "workday_end_time": "18:00",
            "lunch_start_time": "13:00",
            "lunch_end_time": "14:00",
            "workweek_days": [0, 1, 2, 3, 4],
        },
    )
    assert profile.status_code == 200

    month = client.get("/api/v1/work/month", params={"year": 2026, "month": 8})
    assert month.status_code == 200
    today = month.json()["days"][9]
    assert today["date"] == "2026-08-10"
    assert today["actual_hours"] == "2.50"
    assert today["credited_hours"] == "2.50"
    assert today["is_live"] is True
    assert today["is_completed"] is False
    assert today["hours_state"] == "live"

    overridden = client.put(
        "/api/v1/work/days/2026-08-10",
        json={
            "status": "workday",
            "planned_hours": "8.00",
            "actual_hours": "6.25",
            "credited_hours": "6.25",
            "note": "Указано вручную",
        },
    )
    assert overridden.status_code == 200
    manual_today = overridden.json()
    assert manual_today["actual_hours"] == "6.25"
    assert manual_today["is_manual"] is True
    assert manual_today["is_live"] is False
    assert manual_today["is_completed"] is True
    assert manual_today["hours_state"] == "actual"


def test_today_before_shift_is_forecast_not_live(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 8, 10)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = cls(2026, 8, 10, 8, 59)
            return current.replace(tzinfo=tz) if tz else current

    monkeypatch.setattr(work_service_module, "date", FixedDate)
    monkeypatch.setattr(work_service_module, "datetime", FixedDateTime)

    today = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()["days"][9]
    assert today["actual_hours"] == "0.00"
    assert today["credited_hours"] == "0.00"
    assert today["is_live"] is False
    assert today["is_completed"] is False
    assert today["hours_state"] == "forecast"


def test_belarus_2026_calendar_and_work_statistics_match_production_hours(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 8, 7)

    monkeypatch.setattr(work_service_module, "date", FixedDate)

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


def test_salary_cycle_combines_previous_month_advance_current_salary_and_extras(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 8, 1)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = cls(2026, 8, 1, 12, 0)
            return current.replace(tzinfo=tz) if tz else current

    monkeypatch.setattr(work_service_module, "date", FixedDate)
    monkeypatch.setattr(work_service_module, "datetime", FixedDateTime)

    payroll_category = client.post(
        "/api/v1/categories",
        json={"name": "Зарплата", "kind": "income"},
    ).json()
    salary_plan_id = _create_income_plan(
        client,
        note="Основная часть",
        scheduled_date="2026-08-05",
        amount="1200.00",
    )
    advance_plan_id = _create_income_plan(
        client,
        note="Аванс",
        scheduled_date="2026-07-20",
        amount="1000.00",
    )
    for plan_id in (salary_plan_id, advance_plan_id):
        assert client.patch(
            f"/api/v1/plans/{plan_id}",
            json={"category_id": payroll_category["id"]},
        ).status_code == 200
    assert client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "salary_plan_id": salary_plan_id,
            "advance_plan_id": advance_plan_id,
            "salary_nominal_day": 5,
            "advance_nominal_day": 20,
        },
    ).status_code == 200
    advance_operation = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "1050.00",
            "operation_date": "2026-07-20",
            "category_id": payroll_category["id"],
            "note": "Фактический аванс",
        },
    ).json()
    assert client.post(
        "/api/v1/work/payments/links",
        json={"operation_id": advance_operation["id"], "role": "advance"},
    ).status_code == 201
    vacation_pay = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "300.00",
            "operation_date": "2026-07-25",
            "category_id": payroll_category["id"],
            "note": "Отпускные",
        },
    ).json()

    response = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    )
    assert response.status_code == 200
    cycle = response.json()["salary_cycle"]
    assert cycle["reference_year"] == 2026
    assert cycle["reference_month"] == 7
    assert cycle["label"] == "Зарплата за июль 2026 г."
    # July 5 was Sunday and July 3 is a Belarus holiday, so it moved to July 2.
    assert cycle["window_from_exclusive"] == "2026-07-02"
    assert cycle["window_to_inclusive"] == "2026-08-05"
    assert cycle["status"] == "mixed"

    advance = next(item for item in cycle["components"] if item["role"] == "advance")
    salary = next(item for item in cycle["components"] if item["role"] == "salary")
    assert advance["effective_date"] == "2026-07-20"
    assert advance["status"] == "actual"
    assert advance["actual_totals"] == [{"currency": "BYN", "amount": "1050.00"}]
    assert [item["operation_id"] for item in advance["actual_operations"]] == [
        advance_operation["id"]
    ]
    assert salary["effective_date"] == "2026-08-05"
    assert salary["status"] == "forecast"
    assert salary["forecast_amount"] == "1200.00"
    assert salary["forecast_currency"] == "BYN"
    assert [item["operation_id"] for item in cycle["extras"]] == [vacation_pay["id"]]
    assert cycle["totals"] == [
        {
            "currency": "BYN",
            "actual_amount": "1350.00",
            "forecast_amount": "1200.00",
            "expected_amount": "2550.00",
            "extras_amount": "300.00",
        }
    ]


def test_salary_cycle_exact_date_category_fallback_and_shifted_boundaries(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 9, 10)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = cls(2026, 9, 10, 12, 0)
            return current.replace(tzinfo=tz) if tz else current

    monkeypatch.setattr(work_service_module, "date", FixedDate)
    monkeypatch.setattr(work_service_module, "datetime", FixedDateTime)

    payroll_category = client.post(
        "/api/v1/categories",
        json={"name": "ЗП и премии", "kind": "income"},
    ).json()
    salary_plan_id = _create_income_plan(
        client,
        note="Основная часть",
        scheduled_date="2026-09-04",
        amount="1500.00",
    )
    advance_plan_id = _create_income_plan(
        client,
        note="Аванс",
        scheduled_date="2026-08-20",
        amount="900.00",
    )
    for plan_id in (salary_plan_id, advance_plan_id):
        assert client.patch(
            f"/api/v1/plans/{plan_id}",
            json={"category_id": payroll_category["id"]},
        ).status_code == 200
    assert client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "salary_plan_id": salary_plan_id,
            "advance_plan_id": advance_plan_id,
            "salary_nominal_day": 5,
            "advance_nominal_day": 20,
        },
    ).status_code == 200

    extra = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "125.00",
            "operation_date": "2026-08-10",
            "category_id": payroll_category["id"],
            "note": "Премия",
        },
    ).json()
    advance = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "925.00",
            "operation_date": "2026-08-20",
            "category_id": payroll_category["id"],
            "note": "Аванс",
        },
    ).json()
    salary = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "1575.00",
            "operation_date": "2026-09-04",
            "category_id": payroll_category["id"],
            "note": "Зарплата",
        },
    ).json()

    cycle = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 9},
    ).json()["salary_cycle"]
    assert cycle["reference_month"] == 8
    assert cycle["window_from_exclusive"] == "2026-08-05"
    # September 5 was Saturday, so both the component and inclusive boundary use Sep 4.
    assert cycle["window_to_inclusive"] == "2026-09-04"
    assert cycle["status"] == "actual"
    by_role = {item["role"]: item for item in cycle["components"]}
    assert by_role["advance"]["status"] == "actual"
    assert by_role["advance"]["actual_operations"][0]["source"] == "category_match"
    assert by_role["advance"]["actual_operations"][0]["operation_id"] == advance["id"]
    assert by_role["salary"]["effective_date"] == "2026-09-04"
    assert by_role["salary"]["shifted"] is True
    assert by_role["salary"]["actual_operations"][0]["operation_id"] == salary["id"]
    assert [item["operation_id"] for item in cycle["extras"]] == [extra["id"]]
    assert cycle["totals"] == [
        {
            "currency": "BYN",
            "actual_amount": "2625.00",
            "forecast_amount": "0.00",
            "expected_amount": "2625.00",
            "extras_amount": "125.00",
        }
    ]

    # Removing the salary plan must not let that role consume another role's
    # category merely because an operation happens on the salary due date.
    assert client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "advance_plan_id": advance_plan_id,
            "salary_nominal_day": 5,
            "advance_nominal_day": 20,
        },
    ).status_code == 200
    without_salary_plan = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 9},
    ).json()["salary_cycle"]
    by_role = {item["role"]: item for item in without_salary_plan["components"]}
    assert by_role["salary"]["status"] == "missing"
    assert by_role["salary"]["actual_operations"] == []
    assert [item["operation_id"] for item in without_salary_plan["extras"]] == [
        extra["id"],
        salary["id"],
    ]


def test_salary_cycle_assigns_late_explicit_salary_to_nearest_occurrence(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 8, 10)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = cls(2026, 8, 10, 12, 0)
            return current.replace(tzinfo=tz) if tz else current

    monkeypatch.setattr(work_service_module, "date", FixedDate)
    monkeypatch.setattr(work_service_module, "datetime", FixedDateTime)

    category = client.post(
        "/api/v1/categories",
        json={"name": "Зарплата", "kind": "income"},
    ).json()
    salary_plan_id = _create_income_plan(
        client,
        note="Основная часть",
        scheduled_date="2026-08-05",
        amount="1500.00",
    )
    assert client.patch(
        f"/api/v1/plans/{salary_plan_id}",
        json={"category_id": category["id"]},
    ).status_code == 200
    assert client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "salary_plan_id": salary_plan_id,
            "salary_nominal_day": 5,
            "advance_nominal_day": 20,
        },
    ).status_code == 200
    assert client.put(
        "/api/v1/work/days/2026-08-05",
        json={"status": "company_day_off", "note": "Перенос выплаты назад"},
    ).status_code == 200
    late_salary = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "1245.68",
            "operation_date": "2026-07-06",
            "category_id": category["id"],
            "note": "Корректировка основной части",
        },
    ).json()
    assert client.post(
        "/api/v1/work/payments/links",
        json={"operation_id": late_salary["id"], "role": "salary"},
    ).status_code == 201
    exact_salary = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "1245.68",
            "operation_date": "2026-07-02",
            "category_id": category["id"],
            "note": "Основная часть тем же размером",
        },
    ).json()
    assert client.post(
        "/api/v1/work/payments/links",
        json={"operation_id": exact_salary["id"], "role": "salary"},
    ).status_code == 201
    next_occurrence_salary = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "100.00",
            "operation_date": "2026-07-19",
            "category_id": category["id"],
            "note": "Ближе к следующей основной части",
        },
    ).json()
    assert client.post(
        "/api/v1/work/payments/links",
        json={"operation_id": next_occurrence_salary["id"], "role": "salary"},
    ).status_code == 201

    july_cycle = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 7},
    ).json()["salary_cycle"]
    july_salary = next(
        item for item in july_cycle["components"] if item["role"] == "salary"
    )
    assert july_salary["effective_date"] == "2026-07-02"
    assert [item["operation_id"] for item in july_salary["actual_operations"]] == [
        late_salary["id"],
        exact_salary["id"],
    ]
    assert july_salary["actual_totals"] == [
        {"currency": "BYN", "amount": "2491.36"}
    ]

    august_cycle = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()["salary_cycle"]
    august_salary = next(
        item for item in august_cycle["components"] if item["role"] == "salary"
    )
    assert august_salary["effective_date"] == "2026-08-04"
    assert [item["operation_id"] for item in august_salary["actual_operations"]] == [
        next_occurrence_salary["id"]
    ]
    assert late_salary["id"] not in {
        item["operation_id"] for item in august_salary["actual_operations"]
    }
    assert late_salary["id"] not in {
        item["operation_id"] for item in august_cycle["extras"]
    }
    assert exact_salary["id"] not in {
        item["operation_id"] for item in august_salary["actual_operations"]
    }


def test_salary_cycle_january_reference_and_payment_shift_cross_year(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 12, 20)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = cls(2026, 12, 20, 12, 0)
            return current.replace(tzinfo=tz) if tz else current

    monkeypatch.setattr(work_service_module, "date", FixedDate)
    monkeypatch.setattr(work_service_module, "datetime", FixedDateTime)
    assert client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "salary_nominal_day": 1,
            "advance_nominal_day": 20,
        },
    ).status_code == 200

    cycle = client.get(
        "/api/v1/work/month",
        params={"year": 2027, "month": 1},
    ).json()["salary_cycle"]
    assert (cycle["reference_year"], cycle["reference_month"]) == (2026, 12)
    assert cycle["label"] == "Зарплата за декабрь 2026 г."
    salary = next(item for item in cycle["components"] if item["role"] == "salary")
    assert salary["nominal_date"] == "2027-01-01"
    assert salary["effective_date"] == "2026-12-31"
    assert salary["shifted"] is True
    assert cycle["window_to_inclusive"] == "2026-12-31"


def test_salary_cycle_ambiguous_shared_effective_date_stays_in_extras(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 8, 10)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = cls(2026, 8, 10, 12, 0)
            return current.replace(tzinfo=tz) if tz else current

    monkeypatch.setattr(work_service_module, "date", FixedDate)
    monkeypatch.setattr(work_service_module, "datetime", FixedDateTime)
    category = client.post(
        "/api/v1/categories",
        json={"name": "Зарплата", "kind": "income"},
    ).json()
    salary_plan_id = _create_income_plan(
        client,
        note="Основная часть",
        scheduled_date="2026-07-31",
        amount="1500.00",
    )
    advance_plan_id = _create_income_plan(
        client,
        note="Аванс",
        scheduled_date="2026-07-31",
        amount="900.00",
    )
    for plan_id in (salary_plan_id, advance_plan_id):
        assert client.patch(
            f"/api/v1/plans/{plan_id}",
            json={"category_id": category["id"]},
        ).status_code == 200
    assert client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "salary_plan_id": salary_plan_id,
            "advance_plan_id": advance_plan_id,
            "salary_nominal_day": 1,
            "advance_nominal_day": 31,
        },
    ).status_code == 200
    ambiguous = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "500.00",
            "operation_date": "2026-07-31",
            "category_id": category["id"],
            "note": "Нельзя определить роль только по дате",
        },
    ).json()

    cycle = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()["salary_cycle"]
    assert {
        item["effective_date"] for item in cycle["components"]
    } == {"2026-07-31"}
    assert all(item["status"] == "missing" for item in cycle["components"])
    assert [item["operation_id"] for item in cycle["extras"]] == [ambiguous["id"]]


def test_salary_cycle_totals_use_base_currency_for_fx_actual_and_forecast(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 8, 1)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = cls(2026, 8, 1, 12, 0)
            return current.replace(tzinfo=tz) if tz else current

    monkeypatch.setattr(work_service_module, "date", FixedDate)
    monkeypatch.setattr(work_service_module, "datetime", FixedDateTime)
    assert client.put(
        "/api/v1/currency/rates/current",
        json={
            "currency": "USD",
            "rate": "3.25",
            "rate_date": "2026-08-01",
            "source": "nbrb_auto_unit",
        },
    ).status_code == 200
    category = client.post(
        "/api/v1/categories",
        json={"name": "Зарплата", "kind": "income"},
    ).json()
    salary_plan = client.post(
        "/api/v1/plans",
        json={
            "kind": "income",
            "amount": "1000.00",
            "currency": "USD",
            "scheduled_date": "2026-08-05",
            "category_id": category["id"],
            "note": "Основная часть",
            "recurrence_enabled": True,
            "recurrence_frequency": "monthly",
        },
    )
    assert salary_plan.status_code == 201
    assert client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "salary_plan_id": salary_plan.json()["id"],
            "salary_nominal_day": 5,
            "advance_nominal_day": 20,
        },
    ).status_code == 200
    advance_operation = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "300.00",
            "currency": "USD",
            "fx_rate": "3.25",
            "operation_date": "2026-07-20",
            "category_id": category["id"],
            "note": "Валютный аванс",
        },
    )
    assert advance_operation.status_code == 201, advance_operation.text
    advance_operation_id = advance_operation.json()["id"]
    assert client.post(
        "/api/v1/work/payments/links",
        json={"operation_id": advance_operation_id, "role": "advance"},
    ).status_code == 201

    cycle = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()["salary_cycle"]
    advance = next(item for item in cycle["components"] if item["role"] == "advance")
    salary = next(item for item in cycle["components"] if item["role"] == "salary")
    assert advance["actual_operations"][0]["amount"] == "300.00"
    assert advance["actual_operations"][0]["currency"] == "USD"
    assert advance["actual_operations"][0]["base_amount"] == "975.00"
    assert advance["actual_totals"] == [{"currency": "BYN", "amount": "975.00"}]
    assert salary["forecast_amount"] == "1000.00"
    assert salary["forecast_currency"] == "USD"
    assert salary["forecast_base_amount"] == "3250.00"
    assert cycle["totals"] == [
        {
            "currency": "BYN",
            "actual_amount": "975.00",
            "forecast_amount": "3250.00",
            "expected_amount": "4225.00",
            "extras_amount": "0.00",
        }
    ]


def test_salary_cycle_rejects_invalid_order_and_legacy_data_does_not_double_count(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 8, 10)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = cls(2026, 8, 10, 12, 0)
            return current.replace(tzinfo=tz) if tz else current

    monkeypatch.setattr(work_service_module, "date", FixedDate)
    monkeypatch.setattr(work_service_module, "datetime", FixedDateTime)
    category = client.post(
        "/api/v1/categories",
        json={"name": "Зарплата", "kind": "income"},
    ).json()
    salary_plan_id = _create_income_plan(
        client,
        note="Основная часть",
        scheduled_date="2026-08-05",
        amount="1500.00",
    )
    advance_plan_id = _create_income_plan(
        client,
        note="Аванс",
        scheduled_date="2026-07-31",
        amount="900.00",
    )
    for plan_id in (salary_plan_id, advance_plan_id):
        assert client.patch(
            f"/api/v1/plans/{plan_id}",
            json={"category_id": category["id"]},
        ).status_code == 200
    invalid = client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "salary_plan_id": salary_plan_id,
            "advance_plan_id": advance_plan_id,
            "salary_nominal_day": 5,
            "advance_nominal_day": 1,
        },
    )
    assert invalid.status_code == 422
    assert "День аванса должен быть позже" in invalid.text
    assert client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "salary_plan_id": salary_plan_id,
            "advance_plan_id": advance_plan_id,
            "salary_nominal_day": 5,
            "advance_nominal_day": 20,
        },
    ).status_code == 200

    # Simulate a pre-validation profile already stored by an older release.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        profile = db.scalar(select(WorkProfile).where(WorkProfile.user_id == 1))
        assert profile is not None
        profile.advance_nominal_day = 1
        db.commit()
    finally:
        db_generator.close()

    actual_advance = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "925.00",
            "operation_date": "2026-07-01",
            "category_id": category["id"],
            "note": "Аванс за июль",
        },
    ).json()

    july_cycle = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 7},
    ).json()["salary_cycle"]
    august_cycle = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()["salary_cycle"]
    advance = next(
        item for item in august_cycle["components"] if item["role"] == "advance"
    )
    assert advance["nominal_date"] == "2026-07-01"
    assert advance["effective_date"] == "2026-07-01"
    assert advance["status"] == "missing"
    assert advance["actual_operations"] == []
    july_ids = {
        item["operation_id"]
        for item in july_cycle["extras"]
    } | {
        item["operation_id"]
        for component in july_cycle["components"]
        for item in component["actual_operations"]
    }
    august_ids = {
        item["operation_id"]
        for item in august_cycle["extras"]
    } | {
        item["operation_id"]
        for component in august_cycle["components"]
        for item in component["actual_operations"]
    }
    assert actual_advance["id"] in july_ids
    assert actual_advance["id"] not in august_ids


def test_salary_cycle_keeps_unresolved_fx_forecast_in_original_currency(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 8, 1)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = cls(2026, 8, 1, 12, 0)
            return current.replace(tzinfo=tz) if tz else current

    monkeypatch.setattr(work_service_module, "date", FixedDate)
    monkeypatch.setattr(work_service_module, "datetime", FixedDateTime)
    plan = client.post(
        "/api/v1/plans",
        json={
            "kind": "income",
            "amount": "1000.00",
            "currency": "CHF",
            "scheduled_date": "2026-08-05",
            "note": "Основная часть без доступного курса",
            "recurrence_enabled": True,
            "recurrence_frequency": "monthly",
        },
    )
    assert plan.status_code == 201
    assert client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "salary_plan_id": plan.json()["id"],
            "salary_nominal_day": 5,
            "advance_nominal_day": 20,
        },
    ).status_code == 200

    cycle = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()["salary_cycle"]
    salary = next(item for item in cycle["components"] if item["role"] == "salary")
    assert salary["status"] == "forecast"
    assert salary["forecast_amount"] == "1000.00"
    assert salary["forecast_currency"] == "CHF"
    assert salary["forecast_base_amount"] is None
    assert cycle["totals"] == [
        {
            "currency": "CHF",
            "actual_amount": "0.00",
            "forecast_amount": "1000.00",
            "expected_amount": "1000.00",
            "extras_amount": "0.00",
        }
    ]


def test_work_month_uses_past_payroll_operations_and_current_future_plan_amount(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 8, 19)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = cls(2026, 8, 19, 12, 0)
            return current.replace(tzinfo=tz) if tz else current

    monkeypatch.setattr(work_service_module, "date", FixedDate)
    monkeypatch.setattr(work_service_module, "datetime", FixedDateTime)

    payroll_category = client.post(
        "/api/v1/categories",
        json={"name": "Зарплата", "kind": "income"},
    ).json()
    other_category = client.post(
        "/api/v1/categories",
        json={"name": "Прочие доходы", "kind": "income"},
    ).json()
    salary_plan_id = _create_income_plan(
        client,
        note="Основная часть",
        scheduled_date="2026-08-05",
        amount="1176.00",
    )
    advance_plan_id = _create_income_plan(
        client,
        note="Аванс",
        scheduled_date="2026-08-20",
        amount="1050.00",
    )
    for plan_id in (salary_plan_id, advance_plan_id):
        assert client.patch(
            f"/api/v1/plans/{plan_id}",
            json={"category_id": payroll_category["id"]},
        ).status_code == 200

    skipped = client.post(f"/api/v1/plans/{salary_plan_id}/skip")
    assert skipped.status_code == 200
    assert skipped.json()["scheduled_date"] == "2026-09-05"
    assert client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "salary_plan_id": salary_plan_id,
            "advance_plan_id": advance_plan_id,
            "salary_nominal_day": 5,
            "advance_nominal_day": 20,
        },
    ).status_code == 200

    first_salary = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "1973.56",
            "operation_date": "2026-08-05",
            "category_id": payroll_category["id"],
            "note": "Зарплата за июль",
        },
    ).json()
    second_salary = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "348.00",
            "operation_date": "2026-08-05",
            "category_id": payroll_category["id"],
            "note": "Корректировка",
        },
    ).json()
    vacation_pay = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "450.00",
            "operation_date": "2026-08-15",
            "category_id": payroll_category["id"],
            "note": "Отпускные",
        },
    ).json()
    future_income = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "999.00",
            "operation_date": "2026-08-25",
            "category_id": payroll_category["id"],
            "note": "Будущая корректировка",
        },
    ).json()
    unrelated_income = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "75.00",
            "operation_date": "2026-08-05",
            "category_id": other_category["id"],
            "note": "Кэшбэк",
        },
    ).json()
    payroll_expense = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "20.00",
            "operation_date": "2026-08-05",
            "category_id": payroll_category["id"],
            "note": "Не является выплатой",
        },
    ).json()

    august = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    )
    assert august.status_code == 200
    payload = august.json()
    salary = next(item for item in payload["payments"] if item["role"] == "salary")
    advance = next(item for item in payload["payments"] if item["role"] == "advance")
    assert salary["forecast_visible"] is False
    assert salary["forecast_amount"] is None
    assert salary["forecast_currency"] is None
    assert salary["actual_operations"] == []
    assert advance["forecast_visible"] is True
    assert advance["forecast_amount"] == "1050.00"

    detected = payload["payroll_operations"]
    assert [item["operation_id"] for item in detected] == [
        first_salary["id"],
        second_salary["id"],
        vacation_pay["id"],
    ]
    assert all(item["source"] == "category_match" for item in detected)
    assert all(item["link_id"] is None for item in detected)
    assert all(item["label"] == "Зарплата" for item in detected)
    assert all(item["category_name"] == "Зарплата" for item in detected)
    assert all("role" not in item for item in detected)
    assert future_income["id"] not in {item["operation_id"] for item in detected}
    assert unrelated_income["id"] not in {item["operation_id"] for item in detected}
    assert payroll_expense["id"] not in {item["operation_id"] for item in detected}
    assert client.get(
        "/api/v1/work/payments/history",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    ).json() == {"items": [], "total": 0}

    assert client.patch(
        f"/api/v1/plans/{advance_plan_id}",
        json={"amount": "1100.00"},
    ).status_code == 200
    changed_month = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()
    changed_advance = next(
        item for item in changed_month["payments"] if item["role"] == "advance"
    )
    assert changed_advance["forecast_visible"] is True
    assert changed_advance["forecast_amount"] == "1100.00"

    assert client.patch(
        f"/api/v1/plans/{advance_plan_id}",
        json={"kind": "expense"},
    ).status_code == 200
    expense_plan_month = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()
    expense_advance = next(
        item for item in expense_plan_month["payments"] if item["role"] == "advance"
    )
    assert expense_advance["forecast_visible"] is False
    assert expense_advance["forecast_amount"] is None
    assert client.patch(
        f"/api/v1/plans/{advance_plan_id}",
        json={"kind": "income"},
    ).status_code == 200

    linked = client.post(
        "/api/v1/work/payments/links",
        json={"operation_id": first_salary["id"], "role": "salary"},
    )
    assert linked.status_code == 201
    after_link = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()
    assert first_salary["id"] not in {
        item["operation_id"] for item in after_link["payroll_operations"]
    }
    linked_salary = next(
        item for item in after_link["payments"] if item["role"] == "salary"
    )
    assert [item["operation_id"] for item in linked_salary["actual_operations"]] == [
        first_salary["id"]
    ]


def test_today_neutral_payroll_operation_does_not_hide_a_role_forecast(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 8, 20)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = cls(2026, 8, 20, 12, 0)
            return current.replace(tzinfo=tz) if tz else current

    monkeypatch.setattr(work_service_module, "date", FixedDate)
    monkeypatch.setattr(work_service_module, "datetime", FixedDateTime)
    category = client.post(
        "/api/v1/categories",
        json={"name": "Зарплата", "kind": "income"},
    ).json()
    plan_id = _create_income_plan(
        client,
        note="Аванс",
        scheduled_date="2026-08-20",
        amount="1050.00",
    )
    assert client.patch(
        f"/api/v1/plans/{plan_id}",
        json={"category_id": category["id"]},
    ).status_code == 200
    assert client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "advance_plan_id": plan_id,
            "salary_nominal_day": 5,
            "advance_nominal_day": 20,
        },
    ).status_code == 200

    before = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()
    advance_before = next(item for item in before["payments"] if item["role"] == "advance")
    assert advance_before["forecast_visible"] is True
    assert advance_before["forecast_amount"] == "1050.00"

    operation = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "1075.00",
            "operation_date": "2026-08-20",
            "category_id": category["id"],
            "note": "Фактический аванс",
        },
    ).json()
    after = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()
    advance_after = next(item for item in after["payments"] if item["role"] == "advance")
    assert advance_after["forecast_visible"] is True
    assert advance_after["forecast_amount"] == "1050.00"
    assert [item["operation_id"] for item in after["payroll_operations"]] == [operation["id"]]


def test_payroll_forecast_and_history_follow_linked_plan_and_current_operation(client: TestClient):
    rate = client.put(
        "/api/v1/currency/rates/current",
        json={
            "currency": "USD",
            "rate": "3.25",
            "rate_date": "2026-08-01",
            "source": "nbrb_auto_unit",
        },
    )
    assert rate.status_code == 200
    salary_category = client.post(
        "/api/v1/categories",
        json={"name": "Зарплата", "kind": "income"},
    )
    assert salary_category.status_code == 200

    plan = client.post(
        "/api/v1/plans",
        json={
            "kind": "income",
            "amount": "1000.00",
            "currency": "USD",
            "scheduled_date": "2026-08-05",
            "category_id": salary_category.json()["id"],
            "note": "Основная часть",
            "recurrence_enabled": True,
            "recurrence_frequency": "monthly",
        },
    )
    assert plan.status_code == 201
    plan_id = int(plan.json()["id"])

    linked = client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "salary_plan_id": plan_id,
            "salary_nominal_day": 5,
            "advance_nominal_day": 20,
        },
    )
    assert linked.status_code == 200

    august_before_payment = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    )
    assert august_before_payment.status_code == 200
    salary_forecast = next(
        item for item in august_before_payment.json()["payments"] if item["role"] == "salary"
    )
    assert salary_forecast["forecast_visible"] is False
    assert salary_forecast["forecast_amount"] is None
    assert salary_forecast["forecast_currency"] is None
    assert salary_forecast["actual_operations"] == []

    confirmed = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert confirmed.status_code == 200
    operation_id = int(confirmed.json()["operation"]["id"])
    corrected = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={
            "amount": "1250.00",
            "operation_date": "2026-08-07",
            "note": "Скорректированная фактическая зарплата",
        },
    )
    assert corrected.status_code == 200
    assert corrected.json()["original_amount"] == "1250.00"
    assert corrected.json()["amount"] == "4062.50"

    history = client.get(
        "/api/v1/work/payments/history",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    )
    assert history.status_code == 200
    assert history.json()["total"] == 1
    history_item = history.json()["items"][0]
    link_id = int(history_item["link_id"])
    assert history_item == {
        "link_id": link_id,
        "source": "plan_confirmation",
        "role": "salary",
        "label": "Основная часть",
        "plan_id": plan_id,
        "operation_id": operation_id,
        "source_operation_id": operation_id,
        "operation_date": "2026-08-07",
        "amount": "1250.00",
        "currency": "USD",
        "base_amount": "4062.50",
        "base_currency": "BYN",
        "note": "Скорректированная фактическая зарплата",
        "category_name": "Зарплата",
        "is_deleted": False,
    }

    august_after_payment = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    )
    assert august_after_payment.status_code == 200
    salary_payment = next(
        item for item in august_after_payment.json()["payments"] if item["role"] == "salary"
    )
    assert salary_payment["forecast_visible"] is False
    assert salary_payment["forecast_amount"] is None
    assert salary_payment["forecast_currency"] is None
    assert salary_payment["actual_operations"] == [
        {
                key: value
                for key, value in history_item.items()
                if key not in {"role", "plan_id"}
            }
    ]

    moved = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={"operation_date": "2026-09-01"},
    )
    assert moved.status_code == 200

    august_history = client.get(
        "/api/v1/work/payments/history",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    )
    assert august_history.status_code == 200
    assert august_history.json()["items"] == []

    september_history = client.get(
        "/api/v1/work/payments/history",
        params={"date_from": "2026-09-01", "date_to": "2026-09-30"},
    )
    assert september_history.status_code == 200
    assert september_history.json()["items"][0]["operation_date"] == "2026-09-01"

    august_after_move = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()
    august_salary = next(item for item in august_after_move["payments"] if item["role"] == "salary")
    assert august_salary["actual_operations"] == []

    september_after_move = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 9},
    ).json()
    september_salary = next(item for item in september_after_move["payments"] if item["role"] == "salary")
    assert september_salary["actual_operations"][0]["operation_date"] == "2026-09-01"


def test_payroll_link_survives_plan_relink_and_deletions_without_past_forecast(
    client: TestClient,
):
    category = client.post(
        "/api/v1/categories",
        json={"name": "Зарплата", "kind": "income"},
    ).json()
    plan_id = _create_income_plan(
        client,
        note="Основная часть",
        scheduled_date="2026-08-05",
        amount="1000.00",
    )
    assert client.patch(
        f"/api/v1/plans/{plan_id}",
        json={"category_id": category["id"]},
    ).status_code == 200
    assert client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "salary_plan_id": plan_id,
            "salary_nominal_day": 5,
            "advance_nominal_day": 20,
        },
    ).status_code == 200

    confirmed = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert confirmed.status_code == 200
    operation_id = int(confirmed.json()["operation"]["id"])
    assert client.patch(
        f"/api/v1/operations/{operation_id}",
        json={"operation_date": "2026-08-05"},
    ).status_code == 200
    assert client.patch(f"/api/v1/plans/{plan_id}", json={"amount": "2000.00"}).status_code == 200

    august = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()
    salary = next(item for item in august["payments"] if item["role"] == "salary")
    assert salary["forecast_visible"] is False
    assert salary["forecast_amount"] is None
    assert salary["actual_operations"][0]["operation_id"] == operation_id

    corrected_category = client.post(
        "/api/v1/categories",
        json={"name": "Зарплата после сверки", "kind": "income"},
    ).json()
    corrected = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={
            "amount": "1250.00",
            "operation_date": "2026-08-08",
            "category_id": corrected_category["id"],
            "note": "Фактическая выплата после сверки",
        },
    )
    assert corrected.status_code == 200
    current_history = client.get(
        "/api/v1/work/payments/history",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    ).json()["items"][0]
    assert current_history["amount"] == "1250.00"
    assert current_history["operation_date"] == "2026-08-08"
    assert current_history["category_name"] == "Зарплата после сверки"
    assert current_history["note"] == "Фактическая выплата после сверки"
    durable_extra = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "100.00",
            "operation_date": "2026-07-25",
            "category_id": corrected_category["id"],
            "note": "Премия старого зарплатного плана",
        },
    ).json()

    replacement_plan_id = _create_income_plan(
        client,
        note="Новая основная часть",
        scheduled_date="2026-09-05",
        amount="2500.00",
    )
    assert client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "salary_plan_id": replacement_plan_id,
            "salary_nominal_day": 5,
            "advance_nominal_day": 20,
        },
    ).status_code == 200
    assert client.delete(f"/api/v1/plans/{plan_id}").status_code == 204

    durable_history = client.get(
        "/api/v1/work/payments/history",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    ).json()
    assert durable_history["total"] == 1
    item = durable_history["items"][0]
    assert item["role"] == "salary"
    assert item["plan_id"] == plan_id
    assert item["operation_id"] == operation_id
    durable_cycle = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()["salary_cycle"]
    durable_salary = next(
        item for item in durable_cycle["components"] if item["role"] == "salary"
    )
    assert [item["operation_id"] for item in durable_salary["actual_operations"]] == [
        operation_id
    ]
    assert durable_salary["actual_totals"] == [
        {"currency": "BYN", "amount": "1250.00"}
    ]
    assert [item["operation_id"] for item in durable_cycle["extras"]] == [
        durable_extra["id"]
    ]
    assert durable_cycle["totals"] == [
        {
            "currency": "BYN",
            "actual_amount": "1350.00",
            "forecast_amount": "0.00",
            "expected_amount": "1350.00",
            "extras_amount": "100.00",
        }
    ]

    assert client.delete(f"/api/v1/operations/{operation_id}").status_code == 204
    after_operation_delete = client.get(
        "/api/v1/work/payments/history",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    ).json()["items"][0]
    assert after_operation_delete["operation_id"] is None
    assert after_operation_delete["source_operation_id"] == operation_id
    assert after_operation_delete["operation_date"] == "2026-08-08"
    assert after_operation_delete["amount"] == "1250.00"
    assert after_operation_delete["base_amount"] == "1250.00"
    assert after_operation_delete["category_name"] == "Зарплата после сверки"
    assert after_operation_delete["note"] == "Фактическая выплата после сверки"
    assert after_operation_delete["is_deleted"] is True
    deleted_cycle = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()["salary_cycle"]
    deleted_salary = next(
        item for item in deleted_cycle["components"] if item["role"] == "salary"
    )
    assert deleted_salary["status"] == "missing"
    assert deleted_salary["actual_operations"] == []
    assert deleted_salary["actual_totals"] == []
    assert [item["operation_id"] for item in deleted_cycle["extras"]] == [
        durable_extra["id"]
    ]
    assert deleted_cycle["totals"] == [
        {
            "currency": "BYN",
            "actual_amount": "100.00",
            "forecast_amount": "0.00",
            "expected_amount": "100.00",
            "extras_amount": "100.00",
        }
    ]

    restored = client.post(f"/api/v1/operations/{operation_id}/restore")
    assert restored.status_code == 200
    after_restore = client.get(
        "/api/v1/work/payments/history",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    ).json()["items"][0]
    assert after_restore["operation_id"] == operation_id
    assert after_restore["source_operation_id"] == operation_id
    assert after_restore["amount"] == "1250.00"
    assert after_restore["operation_date"] == "2026-08-08"
    assert after_restore["category_name"] == "Зарплата после сверки"
    assert after_restore["note"] == "Фактическая выплата после сверки"
    assert after_restore["is_deleted"] is False
    restored_cycle = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()["salary_cycle"]
    restored_salary = next(
        item for item in restored_cycle["components"] if item["role"] == "salary"
    )
    assert [item["operation_id"] for item in restored_salary["actual_operations"]] == [
        operation_id
    ]
    assert restored_salary["actual_totals"] == [
        {"currency": "BYN", "amount": "1250.00"}
    ]
    assert restored_cycle["totals"] == [
        {
            "currency": "BYN",
            "actual_amount": "1350.00",
            "forecast_amount": "0.00",
            "expected_amount": "1350.00",
            "extras_amount": "100.00",
        }
    ]


def test_manual_payroll_links_candidates_validation_and_audit(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 8, 19)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = cls(2026, 8, 19, 12, 0)
            return current.replace(tzinfo=tz) if tz else current

    monkeypatch.setattr(work_service_module, "date", FixedDate)
    monkeypatch.setattr(work_service_module, "datetime", FixedDateTime)
    current_advance_plan_id = _create_income_plan(
        client,
        note="Текущий аванс",
        scheduled_date="2026-08-20",
        amount="9999.00",
    )
    assert client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "advance_plan_id": current_advance_plan_id,
            "salary_nominal_day": 5,
            "advance_nominal_day": 20,
        },
    ).status_code == 200
    income_category = client.post(
        "/api/v1/categories",
        json={"name": "Премия", "kind": "income"},
    ).json()
    income = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "350.00",
            "operation_date": "2026-08-15",
            "category_id": income_category["id"],
            "note": "Разовая премия",
        },
    )
    assert income.status_code == 201
    operation_id = int(income.json()["id"])
    expense = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "10.00",
            "operation_date": "2026-08-15",
            "note": "Не выплата",
        },
    ).json()
    future_income = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "500.00",
            "operation_date": "2026-08-25",
            "note": "Будущая выплата",
        },
    ).json()

    candidates = client.get(
        "/api/v1/work/payments/candidates",
        params={
            "date_from": "2026-08-01",
            "date_to": "2026-08-31",
            "q": "премия",
            "limit": 20,
        },
    )
    assert candidates.status_code == 200
    assert candidates.json() == {
        "items": [
            {
                "operation_id": operation_id,
                "operation_date": "2026-08-15",
                "amount": "350.00",
                "currency": "BYN",
                "base_amount": "350.00",
                "base_currency": "BYN",
                "note": "Разовая премия",
                "category_name": "Премия",
                "is_linked": False,
                "link_id": None,
                "linked_role": None,
            }
        ],
        "total": 1,
    }

    created = client.post(
        "/api/v1/work/payments/links",
        json={"operation_id": operation_id, "role": "advance"},
    )
    assert created.status_code == 201
    link = created.json()
    assert link["source"] == "manual"
    assert link["role"] == "advance"
    assert link["label"] == "Аванс"
    assert link["plan_id"] is None
    assert link["operation_id"] == operation_id
    assert link["source_operation_id"] == operation_id

    august = client.get(
        "/api/v1/work/month",
        params={"year": 2026, "month": 8},
    ).json()
    advance = next(item for item in august["payments"] if item["role"] == "advance")
    assert advance["plan_id"] == current_advance_plan_id
    assert advance["forecast_visible"] is True
    assert advance["forecast_amount"] == "9999.00"
    assert advance["actual_operations"][0]["operation_id"] == operation_id

    linked_candidates = client.get(
        "/api/v1/work/payments/candidates",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    ).json()
    linked_candidate = next(
        item for item in linked_candidates["items"] if item["operation_id"] == operation_id
    )
    assert all(item["operation_id"] != future_income["id"] for item in linked_candidates["items"])
    assert linked_candidate["is_linked"] is True
    assert linked_candidate["link_id"] == link["link_id"]
    assert linked_candidate["linked_role"] == "advance"

    corrected_category = client.post(
        "/api/v1/categories",
        json={"name": "Зарплата / бонус", "kind": "income"},
    ).json()
    assert client.patch(
        f"/api/v1/operations/{operation_id}",
        json={"category_id": corrected_category["id"]},
    ).status_code == 200
    current_history = client.get(
        "/api/v1/work/payments/history",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    ).json()["items"]
    assert current_history[0]["category_name"] == "Зарплата / бонус"

    blocked_kind_change = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={"kind": "expense"},
    )
    assert blocked_kind_change.status_code == 400
    assert "Сначала отвяжите" in blocked_kind_change.json()["detail"]

    duplicate = client.post(
        "/api/v1/work/payments/links",
        json={"operation_id": operation_id, "role": "salary"},
    )
    assert duplicate.status_code == 400
    assert client.post(
        "/api/v1/work/payments/links",
        json={"operation_id": expense["id"], "role": "salary"},
    ).status_code == 400
    assert client.post(
        "/api/v1/work/payments/links",
        json={"operation_id": future_income["id"], "role": "salary"},
    ).status_code == 400
    assert client.post(
        "/api/v1/work/payments/links",
        json={"operation_id": 999999, "role": "salary"},
    ).status_code == 404
    assert client.get(
        "/api/v1/work/payments/candidates",
        params={"date_from": "2026-09-01", "date_to": "2026-08-01"},
    ).status_code == 400

    removed = client.delete(f"/api/v1/work/payments/links/{link['link_id']}")
    assert removed.status_code == 204
    history = client.get(
        "/api/v1/work/payments/history",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    ).json()
    assert history == {"items": [], "total": 0}

    activity = client.get("/api/v1/activity", params={"page_size": 100}).json()["items"]
    payroll_events = [item for item in activity if item["entity_type"] == "work_payment_link"]
    assert [item["title"] for item in payroll_events] == [
        "Связь выплаты удалена",
        "Выплата связана с операцией",
    ]


def test_manual_payment_uses_operation_forecast_and_cannot_duplicate_after_restore(
    client: TestClient,
):
    plan_id = _create_income_plan(
        client,
        note="Плановая зарплата",
        scheduled_date="2026-08-05",
        amount="2000.00",
    )
    assert client.put(
        "/api/v1/work/profile",
        json={
            "standard_hours_per_day": "8.00",
            "workweek_days": [0, 1, 2, 3, 4],
            "salary_plan_id": plan_id,
            "salary_nominal_day": 5,
            "advance_nominal_day": 20,
        },
    ).status_code == 200
    operation = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "375.00",
            "operation_date": "2026-08-12",
            "note": "Ручная часть выплаты",
        },
    ).json()
    operation_id = int(operation["id"])

    linked = client.post(
        "/api/v1/work/payments/links",
        json={"operation_id": operation_id, "role": "salary"},
    )
    assert linked.status_code == 201
    assert linked.json()["plan_id"] is None
    salary = next(
        item
        for item in client.get(
            "/api/v1/work/month",
            params={"year": 2026, "month": 8},
        ).json()["payments"]
        if item["role"] == "salary"
    )
    assert salary["forecast_visible"] is False
    assert salary["forecast_amount"] is None
    assert salary["actual_operations"][0]["source"] == "manual"

    assert client.delete(f"/api/v1/operations/{operation_id}").status_code == 204
    assert client.post(f"/api/v1/operations/{operation_id}/restore").status_code == 200
    history = client.get(
        "/api/v1/work/payments/history",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    ).json()["items"]
    assert len(history) == 1
    assert history[0]["link_id"] == linked.json()["link_id"]
    assert history[0]["operation_id"] == operation_id
    assert history[0]["is_deleted"] is False

    duplicate = client.post(
        "/api/v1/work/payments/links",
        json={"operation_id": operation_id, "role": "advance"},
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Операция уже связана с выплатой"


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
