import calendar
from datetime import date, timedelta
from decimal import Decimal


FIXED_BY_HOLIDAYS = {
    (1, 1): "Новый год",
    (1, 2): "Новый год",
    (1, 7): "Рождество Христово (православное)",
    (3, 8): "Международный женский день",
    (5, 1): "Праздник труда",
    (5, 9): "День Победы",
    (7, 3): "День Независимости Республики Беларусь",
    (11, 7): "День Октябрьской революции",
    (12, 25): "Рождество Христово (католическое)",
}

# Nationwide five-day-calendar transfer established for 2026. Organizations may
# choose another Saturday; a user override always has priority over these defaults.
TRANSFERRED_DAYS = {
    date(2026, 4, 20): (False, "Перенос рабочего дня на 25 апреля"),
    date(2026, 4, 25): (True, "Перенесённый рабочий день с 20 апреля"),
}

NON_WORKING_OVERRIDE_STATUSES = {
    "holiday",
    "weekend",
    "vacation",
    "sick_paid",
    "sick_unpaid",
    "company_day_off",
    "day_off",
    "unpaid_leave",
}
WORKING_OVERRIDE_STATUSES = {"workday", "transferred_workday", "overtime"}
PAYROLL_CALENDAR_OVERRIDE_STATUSES = {
    "holiday",
    "weekend",
    "company_day_off",
    "workday",
    "transferred_workday",
}


def parse_workweek_mask(value: str | None) -> set[int]:
    result: set[int] = set()
    for raw in str(value or "0,1,2,3,4").split(","):
        try:
            weekday = int(raw.strip())
        except ValueError:
            continue
        if 0 <= weekday <= 6:
            result.add(weekday)
    return result or {0, 1, 2, 3, 4}


def holiday_name(day: date, *, country_code: str = "BY") -> str | None:
    if country_code != "BY":
        return None
    fixed = FIXED_BY_HOLIDAYS.get((day.month, day.day))
    if fixed:
        return fixed
    if orthodox_easter(day.year) + timedelta(days=9) == day:
        return "Радуница"
    return None


def orthodox_easter(year: int) -> date:
    """Gregorian date of Orthodox Easter using the Meeus Julian algorithm."""
    a = year % 4
    b = year % 7
    c = year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    julian_month = 3 + (d + e + 114) // 31
    julian_day = ((d + e + 114) % 31) + 1
    # Difference is 13 days for the supported product range (2000-2099).
    return date(year, julian_month, julian_day) + timedelta(days=13)


def baseline_day(day: date, *, workweek_mask: str = "0,1,2,3,4", country_code: str = "BY") -> dict:
    transfer = TRANSFERRED_DAYS.get(day) if country_code == "BY" else None
    holiday = holiday_name(day, country_code=country_code)
    if transfer:
        is_workday, name = transfer
        return {"is_workday": is_workday, "status": "transferred_workday" if is_workday else "day_off", "label": name}
    if holiday:
        return {"is_workday": False, "status": "holiday", "label": holiday}
    if day.weekday() not in parse_workweek_mask(workweek_mask):
        return {"is_workday": False, "status": "weekend", "label": "Выходной"}
    return {"is_workday": True, "status": "workday", "label": "Рабочий день"}


def effective_is_workday(
    day: date,
    *,
    workweek_mask: str = "0,1,2,3,4",
    country_code: str = "BY",
    override_status: str | None = None,
) -> bool:
    if override_status in WORKING_OVERRIDE_STATUSES:
        return True
    if override_status in NON_WORKING_OVERRIDE_STATUSES:
        return False
    return bool(baseline_day(day, workweek_mask=workweek_mask, country_code=country_code)["is_workday"])


def previous_workday(
    nominal_date: date,
    *,
    workweek_mask: str = "0,1,2,3,4",
    country_code: str = "BY",
    override_statuses: dict[date, str] | None = None,
) -> date:
    current = nominal_date
    statuses = override_statuses or {}
    for _ in range(31):
        if effective_is_workday(
            current,
            workweek_mask=workweek_mask,
            country_code=country_code,
            override_status=statuses.get(current),
        ):
            return current
        current -= timedelta(days=1)
    raise ValueError("Could not resolve a previous workday")


def nominal_date_for_month(year: int, month: int, nominal_day: int) -> date:
    return date(year, month, min(max(1, int(nominal_day)), calendar.monthrange(year, month)[1]))


def next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def resolve_payment_date(
    year: int,
    month: int,
    nominal_day: int,
    *,
    workweek_mask: str = "0,1,2,3,4",
    country_code: str = "BY",
    override_statuses: dict[date, str] | None = None,
) -> tuple[date, date]:
    nominal = nominal_date_for_month(year, month, nominal_day)
    effective = previous_workday(
        nominal,
        workweek_mask=workweek_mask,
        country_code=country_code,
        override_statuses=override_statuses,
    )
    return nominal, effective


def next_linked_payment_date(
    current_effective: date,
    nominal_day: int,
    *,
    workweek_mask: str = "0,1,2,3,4",
    country_code: str = "BY",
    override_statuses: dict[date, str] | None = None,
) -> date:
    year, month = current_effective.year, current_effective.month
    candidates: list[tuple[int, int, date]] = []
    for _ in range(4):
        _, effective = resolve_payment_date(
            year,
            month,
            nominal_day,
            workweek_mask=workweek_mask,
            country_code=country_code,
            override_statuses=override_statuses,
        )
        candidates.append((year, month, effective))
        year, month = next_month(year, month)
    matched_index = next((idx for idx, (_, _, value) in enumerate(candidates) if value == current_effective), None)
    if matched_index is not None:
        if matched_index + 1 < len(candidates):
            return candidates[matched_index + 1][2]
    for _, _, value in candidates:
        if value > current_effective:
            return value
    raise ValueError("Could not resolve the next payroll payment date")


def money_hours(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))
