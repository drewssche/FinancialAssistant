from datetime import date
from decimal import Decimal
from time import perf_counter

from sqlalchemy.orm import Session

from app.core.cache import build_dashboard_summary_cache_key, get_json, set_json
from app.core.metrics import increment_counter, observe_latency_ms
from app.repositories.operation_repo import OperationRepository
from app.services.dashboard_analytics import DashboardAnalyticsService
from app.services.debt_service import DebtService


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OperationRepository(db)
        self.analytics = DashboardAnalyticsService(db, self.repo)

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

        resolved_date_from, resolved_date_to = self.analytics.resolve_period_bounds(
            user_id=user_id,
            period=period,
            date_from=date_from,
            date_to=date_to,
        )

        operations = self.repo.list_for_period(user_id=user_id, date_from=resolved_date_from, date_to=resolved_date_to)
        income_total = Decimal("0.00")
        expense_total = Decimal("0.00")
        for item in operations:
            amount = Decimal(item.amount or 0)
            if item.kind == "income":
                income_total += amount
            else:
                expense_total += amount
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
            "date_from": resolved_date_from.isoformat(),
            "date_to": resolved_date_to.isoformat(),
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
        return self.analytics.get_calendar(user_id=user_id, month_anchor=month_anchor)

    def get_analytics_calendar_year(
        self,
        *,
        user_id: int,
        year_anchor: int | None = None,
    ) -> dict:
        return self.analytics.get_calendar_year(user_id=user_id, year_anchor=year_anchor)

    def get_analytics_trend(
        self,
        *,
        user_id: int,
        period: str = "month",
        date_from: date | None = None,
        date_to: date | None = None,
        granularity: str = "day",
    ) -> dict:
        return self.analytics.get_trend(
            user_id=user_id,
            period=period,
            date_from=date_from,
            date_to=date_to,
            granularity=granularity,
        )

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
        return self.analytics.get_highlights(
            user_id=user_id,
            period=period,
            category_kind=category_kind,
            category_breakdown_level=category_breakdown_level,
            date_from=date_from,
            date_to=date_to,
            month_anchor=month_anchor,
        )
