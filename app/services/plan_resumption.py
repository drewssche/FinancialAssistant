import calendar
from datetime import date, timedelta


def next_resumption_date(*, plan, requested_date: date | None, end_date: date | None, today: date, advance, month_end: bool = False) -> date:
    """Resume a completed schedule without reusing its completed occurrence."""
    if plan.status not in {"confirmed", "skipped"}:
        raise ValueError("План уже активен. Откройте его заново, чтобы изменить расписание.")
    earliest = max(today, plan.scheduled_date + timedelta(days=1))
    if plan.last_confirmed_at:
        earliest = max(earliest, plan.last_confirmed_at.date() + timedelta(days=1))
    if requested_date is not None:
        candidate = requested_date
        if month_end and candidate.day != calendar.monthrange(candidate.year, candidate.month)[1]:
            raise ValueError("Для повторения в последний день месяца выберите последний день нужного месяца.")
        if candidate < earliest:
            raise ValueError(f"Следующий платёж должен быть не раньше {earliest:%d.%m.%Y}.")
    else:
        candidate = plan.scheduled_date
        try:
            while candidate < earliest:
                next_date = advance(candidate)
                if next_date <= candidate:
                    raise ValueError("Не удалось рассчитать следующую дату плана.")
                candidate = next_date
        except (OverflowError, ValueError) as exc:
            raise ValueError("Не удалось рассчитать следующую дату. Проверьте интервал повторения.") from exc
    if end_date and candidate > end_date:
        raise ValueError("Дата окончания повторения раньше следующего платежа. Измените или уберите её.")
    return candidate
