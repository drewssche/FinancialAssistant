from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import build_dashboard_summary_cache_key, get_json, set_json
from app.core.metrics import increment_counter, observe_latency_ms
from app.db.models import Category
from app.repositories.operation_repo import OperationRepository
from app.services.debt_service import DebtService


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OperationRepository(db)

    @staticmethod
    def _percent_change(current: Decimal, previous: Decimal) -> float | None:
        if previous == 0:
            if current == 0:
                return 0.0
            return None
        return float(((current - previous) / previous) * Decimal("100"))

    @staticmethod
    def _month_bounds(anchor: date) -> tuple[date, date]:
        month_start = anchor.replace(day=1)
        next_month_anchor = month_start.replace(day=28) + timedelta(days=4)
        month_end = next_month_anchor.replace(day=1) - timedelta(days=1)
        return month_start, month_end

    def _resolve_period_bounds(
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
            resolved_date_from, resolved_date_to = self._month_bounds(base_date)
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

    def get_summary(
        self,
        user_id: int,
        period: str = "month",
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        total_started = perf_counter()
        cache_key = build_dashboard_summary_cache_key(
            user_id=user_id,
            period=period,
            date_from=date_from,
            date_to=date_to,
        )
        cached = get_json(cache_key)
        if cached:
            increment_counter("dashboard_summary_cache_hit_total")
            observe_latency_ms("dashboard_summary_latency_total_ms", (perf_counter() - total_started) * 1000)
            return cached

        increment_counter("dashboard_summary_cache_miss_total")
        miss_compute_started = perf_counter()

        resolved_date_from, resolved_date_to = self._resolve_period_bounds(
            user_id=user_id,
            period=period,
            date_from=date_from,
            date_to=date_to,
        )

        income_total, expense_total = self.repo.summary_for_period(user_id, resolved_date_from, resolved_date_to)
        debt_service = DebtService(self.db)
        debt_cards = debt_service.list_cards(user_id=user_id, include_closed=False)
        debt_lend_outstanding = Decimal("0")
        debt_borrow_outstanding = Decimal("0")
        for card in debt_cards:
            for debt in card.get("debts", []):
                outstanding = Decimal(debt.get("outstanding_total") or 0)
                if outstanding <= 0:
                    continue
                if debt.get("direction") == "lend":
                    debt_lend_outstanding += outstanding
                else:
                    debt_borrow_outstanding += outstanding
        payload = {
            "income_total": income_total,
            "expense_total": expense_total,
            "balance": income_total - expense_total,
            "debt_lend_outstanding": debt_lend_outstanding,
            "debt_borrow_outstanding": debt_borrow_outstanding,
            "debt_net_position": debt_lend_outstanding - debt_borrow_outstanding,
            "active_debt_cards": len(debt_cards),
        }
        set_json(cache_key, payload)
        observe_latency_ms("dashboard_summary_latency_miss_compute_ms", (perf_counter() - miss_compute_started) * 1000)
        observe_latency_ms("dashboard_summary_latency_total_ms", (perf_counter() - total_started) * 1000)
        return payload

    def get_analytics_calendar(
        self,
        *,
        user_id: int,
        month_anchor: date | None = None,
    ) -> dict:
        anchor = month_anchor or date.today()
        month_start, month_end = self._month_bounds(anchor)
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

    def get_analytics_calendar_year(
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
            month_end = self._month_bounds(month_start)[1]
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

    def get_analytics_trend(
        self,
        *,
        user_id: int,
        period: str = "month",
        date_from: date | None = None,
        date_to: date | None = None,
        granularity: str = "day",
    ) -> dict:
        resolved_from, resolved_to = self._resolve_period_bounds(
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
                _, month_end = self._month_bounds(start)
                return month_end
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
        prev_income, prev_expense = self.repo.summary_for_period(user_id=user_id, date_from=prev_from, date_to=prev_to)
        prev_operations = len(self.repo.list_for_period(user_id=user_id, date_from=prev_from, date_to=prev_to))

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
            "income_change_pct": self._percent_change(current_income, Decimal(prev_income or 0)),
            "expense_change_pct": self._percent_change(current_expense, Decimal(prev_expense or 0)),
            "balance_change_pct": self._percent_change(current_balance, prev_balance),
            "operations_change_pct": self._percent_change(Decimal(current_ops), Decimal(prev_operations)),
            "points": points,
        }

    def get_analytics_highlights(
        self,
        *,
        user_id: int,
        period: str = "month",
        date_from: date | None = None,
        date_to: date | None = None,
        month_anchor: date | None = None,
    ) -> dict:
        if period == "month" and month_anchor is not None:
            resolved_from, resolved_to = self._month_bounds(month_anchor)
        else:
            resolved_from, resolved_to = self._resolve_period_bounds(
                user_id=user_id,
                period=period,
                date_from=date_from,
                date_to=date_to,
            )
        month_start, month_end = self._month_bounds(resolved_from)

        span_days = (resolved_to - resolved_from).days + 1
        prev_to = resolved_from - timedelta(days=1)
        prev_from = prev_to - timedelta(days=max(0, span_days - 1))

        operations = self.repo.list_for_period(user_id=user_id, date_from=resolved_from, date_to=resolved_to)
        prev_operations = self.repo.list_for_period(user_id=user_id, date_from=prev_from, date_to=prev_to)

        income_total = Decimal("0")
        expense_total = Decimal("0")
        expense_by_day: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
        for item in operations:
            amount = Decimal(item.amount or 0)
            if item.kind == "income":
                income_total += amount
            else:
                expense_total += amount
                expense_by_day[item.operation_date] += amount

        prev_income_total = Decimal("0")
        prev_expense_total = Decimal("0")
        for item in prev_operations:
            amount = Decimal(item.amount or 0)
            if item.kind == "income":
                prev_income_total += amount
            else:
                prev_expense_total += amount

        max_expense_day_total = Decimal("0")
        max_expense_day_date: date | None = None
        if expense_by_day:
            max_expense_day_date, max_expense_day_total = max(
                expense_by_day.items(),
                key=lambda pair: (pair[1], pair[0]),
            )

        avg_daily_expense = (expense_total / Decimal(span_days)) if span_days > 0 else Decimal("0")

        category_ids = {int(item.category_id) for item in operations if item.category_id is not None}
        category_name_map: dict[int, str] = {}
        if category_ids:
            rows = self.db.execute(
                select(Category.id, Category.name).where(Category.id.in_(category_ids))
            ).all()
            category_name_map = {int(row[0]): str(row[1]) for row in rows}

        heavy_candidates = [item for item in operations if item.kind == "expense"] or operations
        top_operations = sorted(
            heavy_candidates,
            key=lambda item: (Decimal(item.amount or 0), item.operation_date, item.id),
            reverse=True,
        )[:5]

        current_category_totals: dict[int | None, dict] = defaultdict(
            lambda: {
                "total_expense": Decimal("0"),
                "operations_count": 0,
            }
        )
        previous_category_totals: dict[int | None, Decimal] = defaultdict(lambda: Decimal("0"))
        for item in operations:
            if item.kind != "expense":
                continue
            key = int(item.category_id) if item.category_id is not None else None
            bucket = current_category_totals[key]
            bucket["total_expense"] += Decimal(item.amount or 0)
            bucket["operations_count"] += 1
        for item in prev_operations:
            if item.kind != "expense":
                continue
            key = int(item.category_id) if item.category_id is not None else None
            previous_category_totals[key] += Decimal(item.amount or 0)

        top_categories = sorted(
            current_category_totals.items(),
            key=lambda pair: pair[1]["total_expense"],
            reverse=True,
        )[:5]

        expense_values = sorted(Decimal(item.amount or 0) for item in operations if item.kind == "expense")
        median_expense = Decimal("0")
        if expense_values:
            mid = len(expense_values) // 2
            if len(expense_values) % 2 == 0:
                median_expense = (expense_values[mid - 1] + expense_values[mid]) / Decimal("2")
            else:
                median_expense = expense_values[mid]
        anomalies = []
        if median_expense > 0:
            for item in operations:
                if item.kind != "expense":
                    continue
                amount = Decimal(item.amount or 0)
                ratio = float(amount / median_expense) if median_expense > 0 else 0.0
                if ratio < 2.0:
                    continue
                category_name = (
                    category_name_map.get(int(item.category_id), "Без категории")
                    if item.category_id is not None
                    else "Без категории"
                )
                anomalies.append(
                    {
                        "operation_id": int(item.id),
                        "operation_date": item.operation_date.isoformat(),
                        "amount": amount,
                        "note": item.note,
                        "category_name": category_name,
                        "ratio_to_median": ratio,
                    }
                )
        anomalies.sort(key=lambda item: item["amount"], reverse=True)

        current_receipt_items = self.repo.list_receipt_items_for_operations(
            user_id=user_id,
            operation_ids=[int(item.id) for item in operations],
        )
        previous_receipt_items = self.repo.list_receipt_items_for_operations(
            user_id=user_id,
            operation_ids=[int(item.id) for item in prev_operations],
        )

        def build_position_stats(grouped_items: dict[int, list]) -> dict[tuple[str, str | None], dict]:
            stats: dict[tuple[str, str | None], dict] = defaultdict(
                lambda: {
                    "name": "",
                    "shop_name": None,
                    "total_spent": Decimal("0"),
                    "max_unit_price": Decimal("0"),
                    "unit_price_sum": Decimal("0"),
                    "unit_price_count": 0,
                    "purchases_count": 0,
                }
            )
            for rows in grouped_items.values():
                for row in rows:
                    name = str(row.name or "").strip()
                    if not name:
                        continue
                    shop_name = str(row.shop_name).strip() if row.shop_name else None
                    key = (name.casefold(), shop_name.casefold() if shop_name else None)
                    bucket = stats[key]
                    bucket["name"] = name
                    bucket["shop_name"] = shop_name
                    line_total = Decimal(row.line_total or 0)
                    unit_price = Decimal(row.unit_price or 0)
                    bucket["total_spent"] += line_total
                    bucket["max_unit_price"] = max(bucket["max_unit_price"], unit_price)
                    bucket["unit_price_sum"] += unit_price
                    bucket["unit_price_count"] += 1
                    bucket["purchases_count"] += 1
            return stats

        current_position_stats = build_position_stats(current_receipt_items)
        previous_position_stats = build_position_stats(previous_receipt_items)

        top_positions = sorted(
            current_position_stats.values(),
            key=lambda item: (item["max_unit_price"], item["total_spent"], item["purchases_count"]),
            reverse=True,
        )[:10]

        price_increases = []
        for key, current_item in current_position_stats.items():
            previous_item = previous_position_stats.get(key)
            if not previous_item:
                continue
            prev_count = int(previous_item["unit_price_count"] or 0)
            curr_count = int(current_item["unit_price_count"] or 0)
            if prev_count <= 0 or curr_count <= 0:
                continue
            prev_avg = previous_item["unit_price_sum"] / Decimal(prev_count)
            curr_avg = current_item["unit_price_sum"] / Decimal(curr_count)
            change_pct = self._percent_change(curr_avg, prev_avg)
            if change_pct is None or change_pct < 10.0:
                continue
            price_increases.append(
                {
                    "name": current_item["name"],
                    "shop_name": current_item["shop_name"],
                    "previous_avg_unit_price": prev_avg,
                    "current_avg_unit_price": curr_avg,
                    "change_pct": change_pct,
                }
            )

        price_increases.sort(key=lambda item: item["change_pct"], reverse=True)

        balance = income_total - expense_total
        prev_balance = prev_income_total - prev_expense_total
        surplus_total = balance if balance > 0 else Decimal("0")
        deficit_total = abs(balance) if balance < 0 else Decimal("0")
        return {
            "period": period,
            "date_from": resolved_from.isoformat(),
            "date_to": resolved_to.isoformat(),
            "month": month_start.strftime("%Y-%m"),
            "month_start": month_start.isoformat(),
            "month_end": month_end.isoformat(),
            "income_total": income_total,
            "expense_total": expense_total,
            "balance": balance,
            "surplus_total": surplus_total,
            "deficit_total": deficit_total,
            "operations_count": len(operations),
            "avg_daily_expense": avg_daily_expense,
            "max_expense_day_date": max_expense_day_date.isoformat() if max_expense_day_date else None,
            "max_expense_day_total": max_expense_day_total,
            "income_change_pct": self._percent_change(income_total, prev_income_total),
            "expense_change_pct": self._percent_change(expense_total, prev_expense_total),
            "balance_change_pct": self._percent_change(balance, prev_balance),
            "operations_change_pct": self._percent_change(Decimal(len(operations)), Decimal(len(prev_operations))),
            "top_operations": [
                {
                    "operation_id": int(item.id),
                    "operation_date": item.operation_date.isoformat(),
                    "kind": item.kind,
                    "amount": Decimal(item.amount or 0),
                    "note": item.note,
                }
                for item in top_operations
            ],
            "top_categories": [
                {
                    "category_id": category_id,
                    "category_name": (
                        category_name_map.get(category_id, "Без категории")
                        if category_id is not None
                        else "Без категории"
                    ),
                    "total_expense": bucket["total_expense"],
                    "share_pct": (
                        float((bucket["total_expense"] / expense_total) * Decimal("100"))
                        if expense_total > 0
                        else 0.0
                    ),
                    "change_pct": self._percent_change(bucket["total_expense"], previous_category_totals[category_id]),
                    "operations_count": int(bucket["operations_count"]),
                }
                for category_id, bucket in top_categories
            ],
            "anomalies": anomalies[:5],
            "top_positions": [
                {
                    "name": item["name"],
                    "shop_name": item["shop_name"],
                    "total_spent": item["total_spent"],
                    "max_unit_price": item["max_unit_price"],
                    "avg_unit_price": (
                        item["unit_price_sum"] / Decimal(item["unit_price_count"])
                        if int(item["unit_price_count"] or 0) > 0
                        else Decimal("0")
                    ),
                    "purchases_count": int(item["purchases_count"]),
                }
                for item in top_positions
            ],
            "price_increases": price_increases[:5],
        }
