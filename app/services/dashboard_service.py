from datetime import date
from decimal import Decimal
from time import perf_counter

from sqlalchemy.orm import Session

from app.core.cache import (
    build_dashboard_analytics_cache_key,
    build_dashboard_summary_cache_key,
    get_json,
    get_namespace_ttl_seconds,
    set_json,
)
from app.core.metrics import increment_counter, observe_latency_ms
from app.repositories.debt_repo import DebtRepository
from app.repositories.operation_repo import OperationRepository
from app.services.currency_service import CurrencyService
from app.services.dashboard_analytics import DashboardAnalyticsService
from app.services.redis_runtime_advisory_service import RedisRuntimeAdvisoryService

MONEY_Q = Decimal("0.01")


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OperationRepository(db)
        self.analytics = DashboardAnalyticsService(db, self.repo)
        self.redis_runtime_advisory = RedisRuntimeAdvisoryService()

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
            self.redis_runtime_advisory.maybe_send_advisory()
            return cached

        increment_counter("dashboard_summary_cache_miss_total")
        miss_compute_started = perf_counter()

        resolved_date_from, resolved_date_to = self.analytics.resolve_period_bounds(
            user_id=user_id,
            period=period,
            date_from=date_from,
            date_to=date_to,
        )

        income_total_raw, expense_total_raw = self.repo.summary_for_period(
            user_id=user_id,
            date_from=resolved_date_from,
            date_to=resolved_date_to,
        )
        income_total = self._money(income_total_raw)
        expense_total = self._money(expense_total_raw)
        debt_repo = DebtRepository(self.db)
        debt_lend_outstanding, debt_borrow_outstanding, active_debt_cards = debt_repo.summary_active_totals(
            user_id=user_id,
        )
        debt_lend_outstanding = self._money(debt_lend_outstanding)
        debt_borrow_outstanding = self._money(debt_borrow_outstanding)
        currency_service = CurrencyService(self.db)
        currency_summary = currency_service.compute_positions(user_id=user_id)
        tracked_codes = currency_summary["tracked_currencies"]
        tracked_positions = [
            {
                "currency": item["currency"],
                "quantity": item["quantity"],
                "average_buy_rate": item["average_buy_rate"],
                "current_rate": item["current_rate"],
                "current_rate_date": item["current_rate_date"],
                "current_value": item["current_value"],
                "result_value": item["result_value"],
            }
            for item in currency_summary["positions"]
            if item["currency"] in tracked_codes
        ]
        payload = {
            "date_from": resolved_date_from.isoformat(),
            "date_to": resolved_date_to.isoformat(),
            "income_total": income_total,
            "expense_total": expense_total,
            "balance": income_total - expense_total,
            "debt_lend_outstanding": debt_lend_outstanding,
            "debt_borrow_outstanding": debt_borrow_outstanding,
            "debt_net_position": debt_lend_outstanding - debt_borrow_outstanding,
            "active_debt_cards": active_debt_cards,
            "currency_book_value": currency_summary["total_book_value"],
            "currency_current_value": currency_summary["total_current_value"],
            "currency_result_value": currency_summary["total_result_value"],
            "active_currency_positions": currency_summary["active_positions"],
            "tracked_currency_positions": tracked_positions,
        }
        set_json(cache_key, payload)
        observe_latency_ms("dashboard_summary_latency_miss_compute_ms", (perf_counter() - miss_compute_started) * 1000)
        observe_latency_ms("dashboard_summary_latency_total_ms", (perf_counter() - total_started) * 1000)
        self.redis_runtime_advisory.maybe_send_advisory()
        return payload

    @staticmethod
    def _money(value) -> Decimal:
        return Decimal(value or 0).quantize(MONEY_Q)

    def get_analytics_calendar(
        self,
        *,
        user_id: int,
        month_anchor: date | None = None,
    ) -> dict:
        resolved_month_anchor = month_anchor or date.today().replace(day=1)
        cache_key = build_dashboard_analytics_cache_key(
            user_id=user_id,
            view="calendar",
            period="month",
            date_from=None,
            date_to=None,
            month_anchor=resolved_month_anchor,
        )
        cached = get_json(cache_key)
        if cached:
            return cached

        payload = self.analytics.get_calendar(user_id=user_id, month_anchor=resolved_month_anchor)
        set_json(
            cache_key,
            payload,
            ttl_seconds=get_namespace_ttl_seconds("dashboard_analytics"),
        )
        return payload

    def get_analytics_calendar_year(
        self,
        *,
        user_id: int,
        year_anchor: int | None = None,
    ) -> dict:
        resolved_year_anchor = int(year_anchor or date.today().year)
        cache_key = build_dashboard_analytics_cache_key(
            user_id=user_id,
            view="calendar_year",
            period="year",
            date_from=None,
            date_to=None,
            year_anchor=resolved_year_anchor,
        )
        cached = get_json(cache_key)
        if cached:
            return cached

        payload = self.analytics.get_calendar_year(user_id=user_id, year_anchor=resolved_year_anchor)
        set_json(
            cache_key,
            payload,
            ttl_seconds=get_namespace_ttl_seconds("dashboard_analytics"),
        )
        return payload

    def get_analytics_trend(
        self,
        *,
        user_id: int,
        period: str = "month",
        date_from: date | None = None,
        date_to: date | None = None,
        granularity: str = "day",
    ) -> dict:
        cache_key = build_dashboard_analytics_cache_key(
            user_id=user_id,
            view="trend",
            period=period,
            date_from=date_from,
            date_to=date_to,
            granularity=granularity,
        )
        cached = get_json(cache_key)
        if cached:
            return cached

        payload = self.analytics.get_trend(
            user_id=user_id,
            period=period,
            date_from=date_from,
            date_to=date_to,
            granularity=granularity,
        )
        set_json(
            cache_key,
            payload,
            ttl_seconds=get_namespace_ttl_seconds("dashboard_analytics"),
        )
        return payload

    def get_analytics_highlights(
        self,
        *,
        user_id: int,
        period: str = "month",
        category_kind: str = "expense",
        category_breakdown_level: str = "category",
        date_from: date | None = None,
        date_to: date | None = None,
        month_anchor: date | None = None,
    ) -> dict:
        cache_key = build_dashboard_analytics_cache_key(
            user_id=user_id,
            view="highlights",
            period=period,
            date_from=date_from,
            date_to=date_to,
            month_anchor=month_anchor,
            category_kind=category_kind,
            category_breakdown_level=category_breakdown_level,
        )
        cached = get_json(cache_key)
        if cached:
            return cached

        payload = self.analytics.get_highlights(
            user_id=user_id,
            period=period,
            category_kind=category_kind,
            category_breakdown_level=category_breakdown_level,
            date_from=date_from,
            date_to=date_to,
            month_anchor=month_anchor,
        )
        set_json(
            cache_key,
            payload,
            ttl_seconds=get_namespace_ttl_seconds("dashboard_analytics"),
        )
        return payload

    def get_debt_preview(self, *, user_id: int, limit_cards: int = 6) -> list[dict]:
        debt_repo = DebtRepository(self.db)
        rows = debt_repo.list_active_dashboard_preview_rows(user_id=user_id)
        grouped: dict[int, dict] = {}
        ordered_counterparty_ids: list[int] = []
        for row in rows:
            counterparty_id = int(row[1])
            if counterparty_id not in grouped:
                grouped[counterparty_id] = {
                    "counterparty_id": counterparty_id,
                    "counterparty": str(row[2]),
                    "principal_total": self._money(0),
                    "principal_lend_total": self._money(0),
                    "principal_borrow_total": self._money(0),
                    "repaid_total": self._money(0),
                    "outstanding_total": self._money(0),
                    "status": "active",
                    "nearest_due_date": None,
                    "debts": [],
                }
                ordered_counterparty_ids.append(counterparty_id)
            debt = {
                "id": int(row[0]),
                "direction": str(row[3]),
                "principal": self._money(row[4]),
                "repaid_total": self._money(row[5]),
                "outstanding_total": self._money(row[6]),
                "start_date": row[7].isoformat(),
                "due_date": row[8].isoformat() if row[8] is not None else None,
                "note": row[9],
                "created_at": row[10].isoformat(),
            }
            card = grouped[counterparty_id]
            card["debts"].append(debt)
            card["principal_total"] += debt["principal"]
            card["repaid_total"] += debt["repaid_total"]
            card["outstanding_total"] += debt["outstanding_total"]
            if debt["direction"] == "lend":
                card["principal_lend_total"] += debt["principal"]
            else:
                card["principal_borrow_total"] += debt["principal"]
            due_date = debt["due_date"]
            if due_date and (card["nearest_due_date"] is None or due_date < card["nearest_due_date"]):
                card["nearest_due_date"] = due_date
        return [grouped[counterparty_id] for counterparty_id in ordered_counterparty_ids[:limit_cards]]
