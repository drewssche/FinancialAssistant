from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.repositories.currency_repo import CurrencyRepository
from app.repositories.debt_repo import DebtRepository
from app.repositories.operation_repo import OperationRepository


class DashboardAnalyticsTimelineService:
    MONEY_Q = Decimal("0.01")

    def __init__(
        self,
        repo: OperationRepository,
        currency_repo: CurrencyRepository | None = None,
        debt_repo: DebtRepository | None = None,
    ):
        self.repo = repo
        self.currency_repo = currency_repo
        self.debt_repo = debt_repo

    @classmethod
    def _money(cls, value) -> Decimal:
        return Decimal(value or 0).quantize(cls.MONEY_Q)

    def _build_operation_balance_map(
        self,
        *,
        user_id: int,
        range_start: date,
        range_end: date,
    ) -> dict[date, Decimal]:
        first_date = self.repo.first_operation_date(user_id)
        if not first_date or first_date > range_end:
            return {}
        daily_rows = self.repo.aggregate_daily_for_period(user_id=user_id, date_from=first_date, date_to=range_end)
        delta_by_day = {
            row["operation_date"]: Decimal(row["income_total"] or 0) - Decimal(row["expense_total"] or 0)
            for row in daily_rows
        }
        balances: dict[date, Decimal] = {}
        cursor = first_date
        running = Decimal("0")
        while cursor <= range_end:
            running += delta_by_day.get(cursor, Decimal("0"))
            if cursor >= range_start:
                balances[cursor] = self._money(running)
            cursor += timedelta(days=1)
        return balances

    def _build_currency_value_map(
        self,
        *,
        user_id: int,
        range_start: date,
        range_end: date,
    ) -> dict[date, Decimal]:
        if not self.currency_repo:
            return {}
        all_trades = [row for row in self.currency_repo.list_all_trades(user_id=user_id) if row.trade_date <= range_end]
        if not all_trades:
            return {}
        currencies = sorted({str(row.asset_currency or "").upper() for row in all_trades if row.asset_currency})
        trades_by_date: dict[date, list] = defaultdict(list)
        rate_rows_by_date: dict[date, list[tuple[str, Decimal]]] = defaultdict(list)
        start_candidates = [range_start]

        for trade in all_trades:
            trades_by_date[trade.trade_date].append(trade)
            start_candidates.append(trade.trade_date)

        for currency in currencies:
            history = self.currency_repo.list_rate_history(
                user_id=user_id,
                currency=currency,
                limit=5000,
                date_to=range_end,
            )
            for row in history:
                rate_rows_by_date[row.rate_date].append((currency, Decimal(row.rate or 0)))
                start_candidates.append(row.rate_date)

        positions: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        latest_rates: dict[str, Decimal] = {}
        values: dict[date, Decimal] = {}
        cursor = min(start_candidates)

        while cursor <= range_end:
            for trade in trades_by_date.get(cursor, []):
                currency = str(trade.asset_currency or "").upper()
                quantity = Decimal(trade.quantity or 0)
                if trade.side == "buy":
                    positions[currency] += quantity
                else:
                    positions[currency] -= quantity
                    if positions[currency] < 0:
                        positions[currency] = Decimal("0")
            for currency, rate in rate_rows_by_date.get(cursor, []):
                latest_rates[currency] = rate
            if cursor >= range_start:
                total_value = Decimal("0")
                has_value = False
                for currency, quantity in positions.items():
                    if quantity <= 0:
                        continue
                    rate = latest_rates.get(currency)
                    if rate is None:
                        continue
                    total_value += quantity * rate
                    has_value = True
                if has_value:
                    values[cursor] = self._money(total_value)
            cursor += timedelta(days=1)
        return values

    def _build_debt_value_map(
        self,
        *,
        user_id: int,
        range_start: date,
        range_end: date,
    ) -> dict[date, Decimal]:
        if not self.debt_repo:
            return {}
        debts = [row for row in self.debt_repo.list_all_debts_for_user(user_id=user_id) if row.start_date <= range_end]
        if not debts:
            return {}
        debt_ids = [int(row.id) for row in debts]
        issuances = self.debt_repo.list_all_issuances_for_debts(debt_ids)
        repayments = self.debt_repo.list_all_repayments_for_debts(debt_ids)
        forgivenesses = self.debt_repo.list_all_forgivenesses_for_debts(debt_ids)

        currencies = sorted(
            {
                str(getattr(debt, "currency", "") or "").upper()
                for debt in debts
                if str(getattr(debt, "currency", "") or "").upper()
                != str(getattr(debt, "base_currency", "BYN") or "BYN").upper()
            }
        )
        rate_rows_by_date: dict[date, list[tuple[str, Decimal]]] = defaultdict(list)
        start_candidates = [range_start]
        for debt in debts:
            start_candidates.append(debt.start_date)
        for issuance in issuances:
            start_candidates.append(issuance.issuance_date)
        for repayment in repayments:
            start_candidates.append(repayment.repayment_date)
        for forgiveness in forgivenesses:
            start_candidates.append(forgiveness.forgiven_date)

        for currency in currencies:
            history = self.currency_repo.list_rate_history(
                user_id=user_id,
                currency=currency,
                limit=5000,
                date_to=range_end,
            )
            for row in history:
                rate_rows_by_date[row.rate_date].append((currency, Decimal(row.rate or 0)))
                start_candidates.append(row.rate_date)

        issuances_by_date: dict[date, list] = defaultdict(list)
        repayments_by_date: dict[date, list] = defaultdict(list)
        forgivenesses_by_date: dict[date, list] = defaultdict(list)
        for issuance in issuances:
            issuances_by_date[issuance.issuance_date].append(issuance)
        for repayment in repayments:
            repayments_by_date[repayment.repayment_date].append(repayment)
        for forgiveness in forgivenesses:
            forgivenesses_by_date[forgiveness.forgiven_date].append(forgiveness)

        debt_meta = {
            int(debt.id): {
                "direction": str(getattr(debt, "direction", "lend") or "lend"),
                "currency": str(getattr(debt, "currency", "BYN") or "BYN").upper(),
                "base_currency": str(getattr(debt, "base_currency", "BYN") or "BYN").upper(),
            }
            for debt in debts
        }
        outstanding_by_debt: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
        latest_rates: dict[str, Decimal] = {}
        values: dict[date, Decimal] = {}
        cursor = min(start_candidates)

        while cursor <= range_end:
            for currency, rate in rate_rows_by_date.get(cursor, []):
                latest_rates[currency] = rate
            for issuance in issuances_by_date.get(cursor, []):
                outstanding_by_debt[int(issuance.debt_id)] += Decimal(issuance.amount or 0)
            for repayment in repayments_by_date.get(cursor, []):
                debt_id = int(repayment.debt_id)
                outstanding_by_debt[debt_id] -= Decimal(repayment.amount or 0)
                if outstanding_by_debt[debt_id] < 0:
                    outstanding_by_debt[debt_id] = Decimal("0")
            for forgiveness in forgivenesses_by_date.get(cursor, []):
                debt_id = int(forgiveness.debt_id)
                outstanding_by_debt[debt_id] -= Decimal(forgiveness.amount or 0)
                if outstanding_by_debt[debt_id] < 0:
                    outstanding_by_debt[debt_id] = Decimal("0")
            if cursor >= range_start:
                total_value = Decimal("0")
                has_value = False
                for debt_id, outstanding in outstanding_by_debt.items():
                    if outstanding <= 0:
                        continue
                    meta = debt_meta.get(debt_id)
                    if not meta:
                        continue
                    direction_sign = Decimal("1") if meta["direction"] == "lend" else Decimal("-1")
                    if meta["currency"] == meta["base_currency"]:
                        total_value += direction_sign * outstanding
                        has_value = True
                        continue
                    rate = latest_rates.get(meta["currency"])
                    if rate is None:
                        continue
                    total_value += direction_sign * (outstanding * rate)
                    has_value = True
                if has_value:
                    values[cursor] = self._money(total_value)
            cursor += timedelta(days=1)
        return values

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
        daily_rows = self.repo.aggregate_daily_for_period(user_id=user_id, date_from=month_start, date_to=month_end)
        grid_start = month_start - timedelta(days=month_start.weekday())
        operation_balance_map = self._build_operation_balance_map(user_id=user_id, range_start=grid_start, range_end=month_end)
        currency_value_map = self._build_currency_value_map(user_id=user_id, range_start=grid_start, range_end=month_end)
        debt_value_map = self._build_debt_value_map(user_id=user_id, range_start=grid_start, range_end=month_end)
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
            week_balance_date: date | None = None
            for _ in range(7):
                stats = by_day[cursor]
                in_month = month_start <= cursor <= month_end
                income_total = stats["income_total"] if in_month else Decimal("0")
                expense_total = stats["expense_total"] if in_month else Decimal("0")
                operations_count = int(stats["operations_count"]) if in_month else 0
                flow_balance = income_total - expense_total
                operation_balance = operation_balance_map.get(cursor, Decimal("0")) if in_month else Decimal("0")
                currency_value = currency_value_map.get(cursor) if in_month else None
                debt_value = debt_value_map.get(cursor) if in_month else None
                total_balance = self._money(operation_balance + (currency_value or Decimal("0")) + (debt_value or Decimal("0"))) if in_month else Decimal("0")
                if in_month:
                    week_income += income_total
                    week_expense += expense_total
                    week_ops += operations_count
                    week_balance_date = cursor
                week_days.append(
                    {
                        "date": cursor.isoformat(),
                        "in_month": in_month,
                        "income_total": income_total,
                        "expense_total": expense_total,
                        "flow_balance": flow_balance,
                        "operation_balance": operation_balance,
                        "currency_value": currency_value,
                        "debt_value": debt_value,
                        "balance": total_balance,
                        "operations_count": operations_count,
                    }
                )
                cursor += timedelta(days=1)
            total_income += week_income
            total_expense += week_expense
            total_ops += week_ops
            week_operation_balance = operation_balance_map.get(week_balance_date, Decimal("0")) if week_balance_date else Decimal("0")
            week_currency_value = currency_value_map.get(week_balance_date) if week_balance_date else None
            week_debt_value = debt_value_map.get(week_balance_date) if week_balance_date else None
            weeks.append(
                {
                    "week_start": week_days[0]["date"],
                    "week_end": week_days[-1]["date"],
                    "income_total": week_income,
                    "expense_total": week_expense,
                    "flow_balance": week_income - week_expense,
                    "operation_balance": week_operation_balance,
                    "currency_value": week_currency_value,
                    "debt_value": week_debt_value,
                    "balance_date": week_balance_date.isoformat() if week_balance_date else None,
                    "balance": self._money(week_operation_balance + (week_currency_value or Decimal("0")) + (week_debt_value or Decimal("0"))),
                    "operations_count": week_ops,
                    "days": week_days,
                }
            )

        month_operation_balance = operation_balance_map.get(month_end, Decimal("0"))
        month_currency_value = currency_value_map.get(month_end)
        month_debt_value = debt_value_map.get(month_end)
        return {
            "month": month_start.strftime("%Y-%m"),
            "month_start": month_start.isoformat(),
            "month_end": month_end.isoformat(),
            "income_total": total_income,
            "expense_total": total_expense,
            "flow_balance": total_income - total_expense,
            "operation_balance": month_operation_balance,
            "currency_value": month_currency_value,
            "debt_value": month_debt_value,
            "balance": self._money(month_operation_balance + (month_currency_value or Decimal("0")) + (month_debt_value or Decimal("0"))),
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
        daily_rows = self.repo.aggregate_daily_for_period(user_id=user_id, date_from=year_start, date_to=year_end)
        operation_balance_map = self._build_operation_balance_map(user_id=user_id, range_start=year_start, range_end=year_end)
        currency_value_map = self._build_currency_value_map(user_id=user_id, range_start=year_start, range_end=year_end)
        debt_value_map = self._build_debt_value_map(user_id=user_id, range_start=year_start, range_end=year_end)

        by_month: dict[int, dict] = defaultdict(
            lambda: {
                "income_total": Decimal("0"),
                "expense_total": Decimal("0"),
                "operations_count": 0,
            }
        )
        for row in daily_rows:
            month_index = int(row["operation_date"].month)
            bucket = by_month[month_index]
            bucket["income_total"] += Decimal(row["income_total"] or 0)
            bucket["expense_total"] += Decimal(row["expense_total"] or 0)
            bucket["operations_count"] += int(row["operations_count"] or 0)

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
            operation_balance = operation_balance_map.get(month_end, Decimal("0"))
            currency_value = currency_value_map.get(month_end)
            debt_value = debt_value_map.get(month_end)
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
                    "flow_balance": income_total - expense_total,
                    "operation_balance": operation_balance,
                    "currency_value": currency_value,
                    "debt_value": debt_value,
                    "balance": self._money(operation_balance + (currency_value or Decimal("0")) + (debt_value or Decimal("0"))),
                    "operations_count": operations_count,
                }
            )

        year_operation_balance = operation_balance_map.get(year_end, Decimal("0"))
        year_currency_value = currency_value_map.get(year_end)
        year_debt_value = debt_value_map.get(year_end)
        return {
            "year": year,
            "year_start": year_start.isoformat(),
            "year_end": year_end.isoformat(),
            "income_total": total_income,
            "expense_total": total_expense,
            "flow_balance": total_income - total_expense,
            "operation_balance": year_operation_balance,
            "currency_value": year_currency_value,
            "debt_value": year_debt_value,
            "balance": self._money(year_operation_balance + (year_currency_value or Decimal("0")) + (year_debt_value or Decimal("0"))),
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
        daily_rows = self.repo.aggregate_daily_for_period(user_id=user_id, date_from=resolved_from, date_to=resolved_to)

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
        for row in daily_rows:
            bucket_key = bucket_start_for(row["operation_date"])
            stats = buckets[bucket_key]
            stats["income_total"] += Decimal(row["income_total"] or 0)
            stats["expense_total"] += Decimal(row["expense_total"] or 0)
            stats["operations_count"] += int(row["operations_count"] or 0)

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
        prev_income, prev_expense, prev_operations = self.repo.summary_with_count_for_period(
            user_id=user_id,
            date_from=prev_from,
            date_to=prev_to,
        )

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
