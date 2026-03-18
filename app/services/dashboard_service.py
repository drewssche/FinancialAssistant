from datetime import date
from decimal import Decimal
from time import perf_counter

from sqlalchemy.orm import Session

from app.core.cache import build_dashboard_summary_cache_key, get_json, set_json
from app.core.metrics import increment_counter, observe_latency_ms
from app.repositories.debt_repo import DebtRepository
from app.repositories.operation_repo import OperationRepository
from app.services.dashboard_analytics import DashboardAnalyticsService

MONEY_Q = Decimal("0.01")


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
        }
        set_json(cache_key, payload)
        observe_latency_ms("dashboard_summary_latency_miss_compute_ms", (perf_counter() - miss_compute_started) * 1000)
        observe_latency_ms("dashboard_summary_latency_total_ms", (perf_counter() - total_started) * 1000)
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
