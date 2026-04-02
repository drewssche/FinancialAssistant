from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.currency_repo import CurrencyRepository
from app.repositories.operation_repo import OperationRepository
from app.services.currency_service import CurrencyService
from app.services.debt_service import DebtService


class DashboardAnalyticsTimelineService:
    def __init__(self, db: Session, repo: OperationRepository):
        self.db = db
        self.repo = repo
        self.currency_repo = CurrencyRepository(db)

    @staticmethod
    def _empty_cashflow_bucket() -> dict:
        return {
            "debt_cashflow_total": Decimal("0"),
            "debt_events_count": 0,
            "fx_cashflow_total": Decimal("0"),
            "fx_events_count": 0,
            "cashflow_total": Decimal("0"),
            "cashflow_events_count": 0,
        }

    @staticmethod
    def _money(value: Decimal | int | float | str | None) -> Decimal:
        return Decimal(value or 0).quantize(Decimal("0.01"))

    @staticmethod
    def _coerce_date(value) -> date | None:
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None
        return None

    def _build_cashflow_overlay(
        self,
        *,
        user_id: int,
        date_from: date,
        date_to: date,
    ) -> tuple[dict[date, dict], dict]:
        overlay: dict[date, dict] = defaultdict(self._empty_cashflow_bucket)
        totals = self._empty_cashflow_bucket()
        debt_service = DebtService(self.db)
        debt_cards = debt_service.list_cards(user_id=user_id, include_closed=True, q=None)
        base_currency = debt_service.operation_service._get_user_base_currency(user_id)

        def add_event(
            *,
            event_date: date | None,
            signed_amount: Decimal,
            source: str,
        ) -> None:
            event_date = self._coerce_date(event_date)
            if event_date is None or event_date < date_from or event_date > date_to:
                return
            bucket = overlay[event_date]
            amount = self._money(signed_amount)
            bucket["cashflow_total"] = self._money(bucket["cashflow_total"] + amount)
            bucket["cashflow_events_count"] += 1
            totals["cashflow_total"] = self._money(totals["cashflow_total"] + amount)
            totals["cashflow_events_count"] += 1
            if source == "debt":
                bucket["debt_cashflow_total"] = self._money(bucket["debt_cashflow_total"] + amount)
                bucket["debt_events_count"] += 1
                totals["debt_cashflow_total"] = self._money(totals["debt_cashflow_total"] + amount)
                totals["debt_events_count"] += 1
                return
            bucket["fx_cashflow_total"] = self._money(bucket["fx_cashflow_total"] + amount)
            bucket["fx_events_count"] += 1
            totals["fx_cashflow_total"] = self._money(totals["fx_cashflow_total"] + amount)
            totals["fx_events_count"] += 1

        for card in debt_cards:
            for debt in card.get("debts", []) or []:
                direction = str(debt.get("direction") or "lend")
                for issuance in debt.get("issuances", []) or []:
                    amount = Decimal(issuance.get("current_base_amount") or issuance.get("amount") or 0)
                    signed = -amount if direction == "lend" else amount
                    add_event(
                        event_date=issuance.get("issuance_date"),
                        signed_amount=signed,
                        source="debt",
                    )
                for repayment in debt.get("repayments", []) or []:
                    amount = Decimal(repayment.get("current_base_amount") or repayment.get("amount") or 0)
                    signed = amount if direction == "lend" else -amount
                    add_event(
                        event_date=repayment.get("repayment_date"),
                        signed_amount=signed,
                        source="debt",
                    )

        for trade in self.currency_repo.list_trades_for_period(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        ):
            if not CurrencyService.is_cashflow_trade(trade):
                continue
            quote_currency = str(getattr(trade, "quote_currency", base_currency) or base_currency).upper()
            if quote_currency != base_currency:
                continue
            quantity = Decimal(getattr(trade, "quantity", 0) or 0)
            unit_price = Decimal(getattr(trade, "unit_price", 0) or 0)
            fee = Decimal(getattr(trade, "fee", 0) or 0)
            gross = quantity * unit_price
            signed = -(gross + fee) if trade.side == "buy" else (gross - fee)
            add_event(
                event_date=getattr(trade, "trade_date", None),
                signed_amount=signed,
                source="fx",
            )

        return overlay, totals

    def first_cashflow_date(self, *, user_id: int) -> date | None:
        candidates: list[date] = []
        first_operation = self.repo.first_operation_date(user_id)
        if first_operation:
            candidates.append(first_operation)

        debt_service = DebtService(self.db)
        for card in debt_service.list_cards(user_id=user_id, include_closed=True, q=None):
            for debt in card.get("debts", []) or []:
                for issuance in debt.get("issuances", []) or []:
                    if issuance.get("issuance_date"):
                        candidates.append(issuance["issuance_date"])
                for repayment in debt.get("repayments", []) or []:
                    if repayment.get("repayment_date"):
                        candidates.append(repayment["repayment_date"])

        for trade in self.currency_repo.list_trades_for_period(
            user_id=user_id,
            date_from=date.min,
            date_to=date.max,
        ):
            if not CurrencyService.is_cashflow_trade(trade):
                continue
            if getattr(trade, "trade_date", None):
                candidates.append(trade.trade_date)

        return min(candidates) if candidates else None

    def get_cashflow_totals(
        self,
        *,
        user_id: int,
        date_from: date,
        date_to: date,
    ) -> dict:
        _overlay, totals = self._build_cashflow_overlay(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
        return totals

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
            first_date = self.first_cashflow_date(user_id=user_id)
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
        daily_rows = self.repo.aggregate_daily_for_period(user_id=user_id, date_from=month_start, date_to=month_end)
        cashflow_overlay, cashflow_totals = self._build_cashflow_overlay(
            user_id=user_id,
            date_from=month_start,
            date_to=month_end,
        )
        by_day: dict[date, dict] = defaultdict(
            lambda: {
                "income_total": Decimal("0"),
                "expense_total": Decimal("0"),
                "operations_count": 0,
            }
        )

        for row in daily_rows:
            bucket = by_day[row["operation_date"]]
            bucket["income_total"] = Decimal(row["income_total"] or 0)
            bucket["expense_total"] = Decimal(row["expense_total"] or 0)
            bucket["operations_count"] = int(row["operations_count"] or 0)

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
            week_debt_cashflow = Decimal("0")
            week_debt_events = 0
            week_fx_cashflow = Decimal("0")
            week_fx_events = 0
            week_cashflow_total = Decimal("0")
            week_cashflow_events = 0
            for _ in range(7):
                stats = by_day[cursor]
                cash_stats = cashflow_overlay[cursor]
                in_month = month_start <= cursor <= month_end
                income_total = stats["income_total"] if in_month else Decimal("0")
                expense_total = stats["expense_total"] if in_month else Decimal("0")
                operations_count = int(stats["operations_count"]) if in_month else 0
                debt_cashflow_total = cash_stats["debt_cashflow_total"] if in_month else Decimal("0")
                debt_events_count = int(cash_stats["debt_events_count"]) if in_month else 0
                fx_cashflow_total = cash_stats["fx_cashflow_total"] if in_month else Decimal("0")
                fx_events_count = int(cash_stats["fx_events_count"]) if in_month else 0
                cashflow_total = (income_total - expense_total) + debt_cashflow_total + fx_cashflow_total if in_month else Decimal("0")
                cashflow_events_count = operations_count + debt_events_count + fx_events_count if in_month else 0
                if in_month:
                    week_income += income_total
                    week_expense += expense_total
                    week_ops += operations_count
                    week_debt_cashflow += debt_cashflow_total
                    week_debt_events += debt_events_count
                    week_fx_cashflow += fx_cashflow_total
                    week_fx_events += fx_events_count
                    week_cashflow_total += cashflow_total
                    week_cashflow_events += cashflow_events_count
                week_days.append(
                    {
                        "date": cursor.isoformat(),
                        "in_month": in_month,
                        "income_total": income_total,
                        "expense_total": expense_total,
                        "balance": income_total - expense_total,
                        "operations_count": operations_count,
                        "debt_cashflow_total": debt_cashflow_total,
                        "debt_events_count": debt_events_count,
                        "fx_cashflow_total": fx_cashflow_total,
                        "fx_events_count": fx_events_count,
                        "cashflow_total": cashflow_total,
                        "cashflow_events_count": cashflow_events_count,
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
                    "debt_cashflow_total": week_debt_cashflow,
                    "debt_events_count": week_debt_events,
                    "fx_cashflow_total": week_fx_cashflow,
                    "fx_events_count": week_fx_events,
                    "cashflow_total": week_cashflow_total,
                    "cashflow_events_count": week_cashflow_events,
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
            "debt_cashflow_total": cashflow_totals["debt_cashflow_total"],
            "debt_events_count": cashflow_totals["debt_events_count"],
            "fx_cashflow_total": cashflow_totals["fx_cashflow_total"],
            "fx_events_count": cashflow_totals["fx_events_count"],
            "cashflow_total": (total_income - total_expense) + cashflow_totals["debt_cashflow_total"] + cashflow_totals["fx_cashflow_total"],
            "cashflow_events_count": total_ops + cashflow_totals["debt_events_count"] + cashflow_totals["fx_events_count"],
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
        daily_rows = self.repo.aggregate_daily_for_period(user_id=user_id, date_from=year_start, date_to=year_end)
        cashflow_overlay, _cashflow_totals = self._build_cashflow_overlay(
            user_id=user_id,
            date_from=year_start,
            date_to=year_end,
        )

        by_month: dict[int, dict] = defaultdict(
            lambda: {
                "income_total": Decimal("0"),
                "expense_total": Decimal("0"),
                "operations_count": 0,
                "debt_cashflow_total": Decimal("0"),
                "debt_events_count": 0,
                "fx_cashflow_total": Decimal("0"),
                "fx_events_count": 0,
            }
        )
        for row in daily_rows:
            month_index = int(row["operation_date"].month)
            bucket = by_month[month_index]
            bucket["income_total"] += Decimal(row["income_total"] or 0)
            bucket["expense_total"] += Decimal(row["expense_total"] or 0)
            bucket["operations_count"] += int(row["operations_count"] or 0)
        for event_date, row in cashflow_overlay.items():
            month_index = int(event_date.month)
            bucket = by_month[month_index]
            bucket["debt_cashflow_total"] += Decimal(row["debt_cashflow_total"] or 0)
            bucket["debt_events_count"] += int(row["debt_events_count"] or 0)
            bucket["fx_cashflow_total"] += Decimal(row["fx_cashflow_total"] or 0)
            bucket["fx_events_count"] += int(row["fx_events_count"] or 0)

        months = []
        total_income = Decimal("0")
        total_expense = Decimal("0")
        total_ops = 0
        total_debt_cashflow = Decimal("0")
        total_debt_events = 0
        total_fx_cashflow = Decimal("0")
        total_fx_events = 0
        for month in range(1, 13):
            month_start = date(year, month, 1)
            month_end = self.month_bounds(month_start)[1]
            stats = by_month[month]
            income_total = stats["income_total"]
            expense_total = stats["expense_total"]
            operations_count = int(stats["operations_count"])
            debt_cashflow_total = Decimal(stats["debt_cashflow_total"] or 0)
            debt_events_count = int(stats["debt_events_count"] or 0)
            fx_cashflow_total = Decimal(stats["fx_cashflow_total"] or 0)
            fx_events_count = int(stats["fx_events_count"] or 0)
            total_income += income_total
            total_expense += expense_total
            total_ops += operations_count
            total_debt_cashflow += debt_cashflow_total
            total_debt_events += debt_events_count
            total_fx_cashflow += fx_cashflow_total
            total_fx_events += fx_events_count
            months.append(
                {
                    "month": month_start.strftime("%Y-%m"),
                    "month_start": month_start.isoformat(),
                    "month_end": month_end.isoformat(),
                    "income_total": income_total,
                    "expense_total": expense_total,
                    "balance": income_total - expense_total,
                    "operations_count": operations_count,
                    "debt_cashflow_total": debt_cashflow_total,
                    "debt_events_count": debt_events_count,
                    "fx_cashflow_total": fx_cashflow_total,
                    "fx_events_count": fx_events_count,
                    "cashflow_total": (income_total - expense_total) + debt_cashflow_total + fx_cashflow_total,
                    "cashflow_events_count": operations_count + debt_events_count + fx_events_count,
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
            "debt_cashflow_total": total_debt_cashflow,
            "debt_events_count": total_debt_events,
            "fx_cashflow_total": total_fx_cashflow,
            "fx_events_count": total_fx_events,
            "cashflow_total": (total_income - total_expense) + total_debt_cashflow + total_fx_cashflow,
            "cashflow_events_count": total_ops + total_debt_events + total_fx_events,
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
        daily_rows = self.repo.aggregate_daily_for_period(user_id=user_id, date_from=resolved_from, date_to=resolved_to)
        cashflow_overlay, current_cashflow_totals = self._build_cashflow_overlay(
            user_id=user_id,
            date_from=resolved_from,
            date_to=resolved_to,
        )

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
                "debt_cashflow_total": Decimal("0"),
                "debt_events_count": 0,
                "fx_cashflow_total": Decimal("0"),
                "fx_events_count": 0,
            }
        )
        for row in daily_rows:
            bucket_key = bucket_start_for(row["operation_date"])
            stats = buckets[bucket_key]
            stats["income_total"] += Decimal(row["income_total"] or 0)
            stats["expense_total"] += Decimal(row["expense_total"] or 0)
            stats["operations_count"] += int(row["operations_count"] or 0)
        for event_date, row in cashflow_overlay.items():
            bucket_key = bucket_start_for(event_date)
            stats = buckets[bucket_key]
            stats["debt_cashflow_total"] += Decimal(row["debt_cashflow_total"] or 0)
            stats["debt_events_count"] += int(row["debt_events_count"] or 0)
            stats["fx_cashflow_total"] += Decimal(row["fx_cashflow_total"] or 0)
            stats["fx_events_count"] += int(row["fx_events_count"] or 0)

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
            debt_cashflow_total = Decimal(item["debt_cashflow_total"] or 0)
            debt_events_count = int(item["debt_events_count"] or 0)
            fx_cashflow_total = Decimal(item["fx_cashflow_total"] or 0)
            fx_events_count = int(item["fx_events_count"] or 0)
            cashflow_total = (income_total - expense_total) + debt_cashflow_total + fx_cashflow_total
            cashflow_events_count = operations_count + debt_events_count + fx_events_count
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
                    "debt_cashflow_total": debt_cashflow_total,
                    "debt_events_count": debt_events_count,
                    "fx_cashflow_total": fx_cashflow_total,
                    "fx_events_count": fx_events_count,
                    "cashflow_total": cashflow_total,
                    "cashflow_events_count": cashflow_events_count,
                    "operations_count": operations_count,
                }
            )

        span_days = (resolved_to - resolved_from).days + 1
        prev_to = resolved_from - timedelta(days=1)
        prev_from = prev_to - timedelta(days=max(0, span_days - 1))
        prev_income, prev_expense, prev_operations = self.repo.summary_with_count_for_period(
            user_id=user_id,
            date_from=prev_from,
            date_to=prev_to,
        )
        prev_cashflow_totals = self.get_cashflow_totals(
            user_id=user_id,
            date_from=prev_from,
            date_to=prev_to,
        )

        current_balance = current_income - current_expense
        prev_balance = Decimal(prev_income or 0) - Decimal(prev_expense or 0)
        current_debt_cashflow = Decimal(current_cashflow_totals["debt_cashflow_total"] or 0)
        current_fx_cashflow = Decimal(current_cashflow_totals["fx_cashflow_total"] or 0)
        current_cashflow_total = current_balance + current_debt_cashflow + current_fx_cashflow
        prev_debt_cashflow = Decimal(prev_cashflow_totals["debt_cashflow_total"] or 0)
        prev_fx_cashflow = Decimal(prev_cashflow_totals["fx_cashflow_total"] or 0)
        prev_cashflow_total = prev_balance + prev_debt_cashflow + prev_fx_cashflow
        return {
            "period": period,
            "granularity": granularity,
            "date_from": resolved_from.isoformat(),
            "date_to": resolved_to.isoformat(),
            "income_total": current_income,
            "expense_total": current_expense,
            "balance": current_balance,
            "debt_cashflow_total": current_debt_cashflow,
            "fx_cashflow_total": current_fx_cashflow,
            "cashflow_total": current_cashflow_total,
            "operations_count": current_ops,
            "prev_income_total": Decimal(prev_income or 0),
            "prev_expense_total": Decimal(prev_expense or 0),
            "prev_balance": prev_balance,
            "prev_debt_cashflow_total": prev_debt_cashflow,
            "prev_fx_cashflow_total": prev_fx_cashflow,
            "prev_cashflow_total": prev_cashflow_total,
            "prev_operations_count": int(prev_operations),
            "income_change_pct": self.percent_change(current_income, Decimal(prev_income or 0)),
            "expense_change_pct": self.percent_change(current_expense, Decimal(prev_expense or 0)),
            "balance_change_pct": self.percent_change(current_balance, prev_balance),
            "debt_cashflow_change_pct": self.percent_change(current_debt_cashflow, prev_debt_cashflow),
            "fx_cashflow_change_pct": self.percent_change(current_fx_cashflow, prev_fx_cashflow),
            "cashflow_change_pct": self.percent_change(current_cashflow_total, prev_cashflow_total),
            "operations_change_pct": self.percent_change(Decimal(current_ops), Decimal(prev_operations)),
            "points": points,
        }
