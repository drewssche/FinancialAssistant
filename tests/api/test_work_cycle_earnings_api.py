from decimal import Decimal

import pytest

from app.services.work_service import WorkService
from tests.api.test_operations_api import _client_lifecycle


@pytest.fixture
def client():
    yield from _client_lifecycle()


def test_earnings_norm_uses_salary_month_including_day_overrides(client):
    client.put("/api/v1/work/profile", json={"standard_hours_per_day": "8.00", "workweek_days": [0, 1, 2, 3, 4]})
    client.put("/api/v1/work/days/2026-08-10", json={"status": "sick_paid", "planned_hours": "6.00", "actual_hours": "0.00"})
    client.put("/api/v1/work/days/2026-09-10", json={"status": "workday", "planned_hours": "1.00"})
    payload = client.get("/api/v1/work/month?year=2026&month=9").json()
    norm = payload["salary_cycle"]["earnings_estimate"]
    assert norm["planned_days"] == 21
    assert norm["planned_hours"] == "166.00"
    assert payload["summary"]["planned_days"] == 22
    assert payload["summary"]["planned_hours"] == "169.00"
    assert norm["status"] == "unavailable"
    # Crossing January still uses the complete previous December, not January.
    december = client.get("/api/v1/work/month?year=2026&month=12").json()["summary"]
    january = client.get("/api/v1/work/month?year=2027&month=1").json()["salary_cycle"]
    assert (january["reference_year"], january["reference_month"]) == (2026, 12)
    assert january["earnings_estimate"]["planned_hours"] == december["planned_hours"]
    assert january["earnings_estimate"]["planned_days"] == december["planned_days"]


@pytest.mark.parametrize("case,reason", [
    ("missing", "missing_payment"), ("unknown_forecast", "missing_payment"),
    ("foreign", "unresolved_currency"), ("zero_hours", "missing_work_norm"),
    ("zero_days", "missing_work_norm"), ("actual", None), ("forecast", None),
])
def test_earnings_estimate_never_uses_partial_or_unconverted_salary(case, reason):
    salary = {"role": "salary", "status": "actual", "actual_totals": [{"currency": "BYN", "amount": "2854.78"}]}
    advance = {"role": "advance", "status": "actual", "actual_totals": [{"currency": "BYN", "amount": "1420.00"}]}
    if case == "missing":
        salary["status"] = "missing"
    if case in {"unknown_forecast", "foreign", "forecast"}:
        salary.update(status="forecast", forecast_base_amount=None, forecast_base_currency="BYN",
                      forecast_amount=None if case == "unknown_forecast" else "2854.78",
                      forecast_currency="EUR" if case == "foreign" else "BYN")
    summary = {"planned_days": 0 if case == "zero_days" else 21,
               "planned_hours": Decimal("0" if case == "zero_hours" else "168")}
    estimate = WorkService._salary_cycle_earnings(cycle={"components": [advance, salary], "extras": [{"amount": "9999"}]}, summary=summary)
    assert estimate["reason"] == reason
    if reason:
        assert estimate["status"] == "unavailable"
        assert estimate["daily_amount"] is None
        assert estimate["hourly_amount"] is None
    else:
        assert estimate["status"] == case
        assert estimate["basis_amount"] == Decimal("4274.78")
        assert estimate["daily_amount"] == Decimal("203.56")
        assert estimate["hourly_amount"] == Decimal("25.45")
