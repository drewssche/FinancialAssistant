from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.repositories.operation_repo import OperationRepository


class DashboardAnalyticsTimelineService:
    def __init__(self, repo: OperationRepository):
        self.repo = repo

    @staticmethod
    def percent_change(current: Decimal, previous: Decimal) -> float | None:
        if previous == 0:
            if current == 0:
                return 0.0
            return None
        return float(((current - previous) / previous) * Decimal("100"))

    @staticmethod
    def month_bounds(anchor: date) -> tuple[date, date]:
        month_start = anchor.replace(day=1)
        next_month_anchor = month_start.replace(day=28) + timedelta(days=4)
        month_end = next_month_anchor.replace(day=1) - timedelta(days=1)
        return month_start, month_end

    def resolve_period_bounds(
        self,
        *,
        user_id: int,
        period: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[date, date]:
        base_date = date_to or date.today()
        resolved_date_to = base_date

        if date_from:
            resolved_date_from = date_from
        elif period == "day":
            resolved_date_from = base_date
            resolved_date_to = base_date
        elif period == "week":
            resolved_date_from = base_date - timedelta(days=base_date.weekday())
            resolved_date_to = resolved_date_from + timedelta(days=6)
        elif period == "month":
            resolved_date_from, resolved_date_to = self.month_bounds(base_date)
        elif period == "year":
            resolved_date_from = base_date.replace(month=1, day=1)
            resolved_date_to = base_date.replace(month=12, day=31)
        elif period == "all_time":
            first_date = self.repo.first_operation_date(user_id)
            resolved_date_from = first_date or base_date
            resolved_date_to = base_date
        elif period == "custom":
            raise ValueError("date_from is required for custom period")
        else:
            raise ValueError("Invalid period")

        if resolved_date_from > resolved_date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        return resolved_date_from, resolved_date_to

    def get_calendar(
        self,
        *,
        user_id: int,
        month_anchor: date | None = None,
    ) -> dict:
        anchor = month_anchor or date.today()
        month_start, month_end = self.month_bounds(anchor)
        operations = self.repo.list_for_period(user_id=user_id, date_from=month_start, date_to=month_end)
        by_day: dict[date, dict] = defaultdict(
            lambda: {
                "income_total": Decimal("0"),
                "expense_total": Decimal("0"),
                "operations_count": 0,
            }
        )

        for item in operations:
            bucket = by_day[item.operation_date]
            amount = Decimal(item.amount or 0)
            if item.kind == "income":
                bucket["income_total"] += amount
            else:
                bucket["expense_total"] += amount
            bucket["operations_count"] += 1

        grid_start = month_start - timedelta(days=month_start.weekday())
        grid_end = month_end + timedelta(days=(6 - month_end.weekday()))

        weeks = []
        cursor = grid_start
        total_income = Decimal("0")
        total_expense = Decimal("0")
        total_ops = 0

        while cursor <= grid_end:
            week_days = []
            week_income = Decimal("0")
            week_expense = Decimal("0")
            week_ops = 0
            for _ in range(7):
                stats = by_day[cursor]
                in_month = month_start <= cursor <= month_end
                income_total = stats["income_total"] if in_month else Decimal("0")
                expense_total = stats["expense_total"] if in_month else Decimal("0")
                operations_count = int(stats["operations_count"]) if in_month else 0
                if in_month:
                    week_income += income_total
                    week_expense += expense_total
                    week_ops += operations_count
                week_days.append(
                    {
                        "date": cursor.isoformat(),
                        "in_month": in_month,
                        "income_total": income_total,
                        "expense_total": expense_total,
                        "balance": income_total - expense_total,
                        "operations_count": operations_count,
                    }
                )
                cursor += timedelta(days=1)
            total_income += week_income
            total_expense += week_expense
            total_ops += week_ops
            weeks.append(
                {
                    "week_start": week_days[0]["date"],
                    "week_end": week_days[-1]["date"],
                    "income_total": week_income,
                    "expense_total": week_expense,
                    "balance": week_income - week_expense,
                    "operations_count": week_ops,
                    "days": week_days,
                }
            )

        return {
            "month": month_start.strftime("%Y-%m"),
            "month_start": month_start.isoformat(),
            "month_end": month_end.isoformat(),
            "income_total": total_income,
            "expense_total": total_expense,
            "balance": total_income - total_expense,
            "operations_count": total_ops,
            "weeks": weeks,
        }

    def get_calendar_year(
        self,
        *,
        user_id: int,
        year_anchor: int | None = None,
    ) -> dict:
        year = int(year_anchor or date.today().year)
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        operations = self.repo.list_for_period(user_id=user_id, date_from=year_start, date_to=year_end)

        by_month: dict[int, dict] = defaultdict(
            lambda: {
                "income_total": Decimal("0"),
                "expense_total": Decimal("0"),
                "operations_count": 0,
            }
        )
        for item in operations:
            month_index = int(item.operation_date.month)
            bucket = by_month[month_index]
            amount = Decimal(item.amount or 0)
            if item.kind == "income":
                bucket["income_total"] += amount
            else:
                bucket["expense_total"] += amount
            bucket["operations_count"] += 1

        months = []
        total_income = Decimal("0")
        total_expense = Decimal("0")
        total_ops = 0
        for month in range(1, 13):
            month_start = date(year, month, 1)
            month_end = self.month_bounds(month_start)[1]
            stats = by_month[month]
            income_total = stats["income_total"]
            expense_total = stats["expense_total"]
            operations_count = int(stats["operations_count"])
            total_income += income_total
            total_expense += expense_total
            total_ops += operations_count
            months.append(
                {
                    "month": month_start.strftime("%Y-%m"),
                    "month_start": month_start.isoformat(),
                    "month_end": month_end.isoformat(),
                    "income_total": income_total,
                    "expense_total": expense_total,
                    "balance": income_total - expense_total,
                    "operations_count": operations_count,
                }
            )

        return {
            "year": year,
            "year_start": year_start.isoformat(),
            "year_end": year_end.isoformat(),
            "income_total": total_income,
            "expense_total": total_expense,
            "balance": total_income - total_expense,
            "operations_count": total_ops,
            "months": months,
        }

    def get_trend(
        self,
        *,
        user_id: int,
        period: str = "month",
        date_from: date | None = None,
        date_to: date | None = None,
        granularity: str = "day",
    ) -> dict:
        resolved_from, resolved_to = self.resolve_period_bounds(
            user_id=user_id,
            period=period,
            date_from=date_from,
            date_to=date_to,
        )
        if granularity not in {"day", "week", "month", "year"}:
            raise ValueError("Invalid granularity")
        operations = self.repo.list_for_period(user_id=user_id, date_from=resolved_from, date_to=resolved_to)

        def bucket_start_for(day_value: date) -> date:
            if granularity == "day":
                return day_value
            if granularity == "week":
                return day_value - timedelta(days=day_value.weekday())
            if granularity == "month":
                return day_value.replace(day=1)
            return day_value.replace(month=1, day=1)

        def bucket_end_for(start: date) -> date:
            if granularity == "day":
                return start
            if granularity == "week":
                return start + timedelta(days=6)
            if granularity == "month":
                return self.month_bounds(start)[1]
            return start.replace(month=12, day=31)

        buckets: dict[date, dict] = defaultdict(
            lambda: {
                "income_total": Decimal("0"),
                "expense_total": Decimal("0"),
                "operations_count": 0,
            }
        )
        for item in operations:
            bucket_key = bucket_start_for(item.operation_date)
            stats = buckets[bucket_key]
            amount = Decimal(item.amount or 0)
            if item.kind == "income":
                stats["income_total"] += amount
            else:
                stats["expense_total"] += amount
            stats["operations_count"] += 1

        sorted_keys = sorted(buckets.keys())
        points = []
        current_income = Decimal("0")
        current_expense = Decimal("0")
        current_ops = 0
        for key in sorted_keys:
            item = buckets[key]
            income_total = item["income_total"]
            expense_total = item["expense_total"]
            operations_count = int(item["operations_count"])
            start = max(key, resolved_from)
            end = min(bucket_end_for(key), resolved_to)
            current_income += income_total
            current_expense += expense_total
            current_ops += operations_count
            points.append(
                {
                    "bucket_start": start.isoformat(),
                    "bucket_end": end.isoformat(),
                    "label": start.strftime("%d.%m.%Y") if granularity in {"day", "week"} else start.strftime("%m.%Y") if granularity == "month" else start.strftime("%Y"),
                    "income_total": income_total,
                    "expense_total": expense_total,
                    "balance": income_total - expense_total,
                    "operations_count": operations_count,
                }
            )

        span_days = (resolved_to - resolved_from).days + 1
        prev_to = resolved_from - timedelta(days=1)
        prev_from = prev_to - timedelta(days=max(0, span_days - 1))
        previous_ops = self.repo.list_for_period(user_id=user_id, date_from=prev_from, date_to=prev_to)
        prev_income = Decimal("0")
        prev_expense = Decimal("0")
        for item in previous_ops:
            amount = Decimal(item.amount or 0)
            if item.kind == "income":
                prev_income += amount
            else:
                prev_expense += amount
        prev_operations = len(previous_ops)

        current_balance = current_income - current_expense
        prev_balance = Decimal(prev_income or 0) - Decimal(prev_expense or 0)
        return {
            "period": period,
            "granularity": granularity,
            "date_from": resolved_from.isoformat(),
            "date_to": resolved_to.isoformat(),
            "income_total": current_income,
            "expense_total": current_expense,
            "balance": current_balance,
            "operations_count": current_ops,
            "prev_income_total": Decimal(prev_income or 0),
            "prev_expense_total": Decimal(prev_expense or 0),
            "prev_balance": prev_balance,
            "prev_operations_count": int(prev_operations),
            "income_change_pct": self.percent_change(current_income, Decimal(prev_income or 0)),
            "expense_change_pct": self.percent_change(current_expense, Decimal(prev_expense or 0)),
            "balance_change_pct": self.percent_change(current_balance, prev_balance),
            "operations_change_pct": self.percent_change(Decimal(current_ops), Decimal(prev_operations)),
            "points": points,
        }
