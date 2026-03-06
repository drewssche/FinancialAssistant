from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.operation_repo import OperationRepository
from app.services.debt_service import DebtService


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OperationRepository(db)

    def get_summary(
        self,
        user_id: int,
        period: str = "month",
        date_from: date | None = None,
        date_to: date | None = None,
    ):
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
            resolved_date_from = base_date.replace(day=1)
            next_month_anchor = resolved_date_from.replace(day=28) + timedelta(days=4)
            resolved_date_to = next_month_anchor.replace(day=1) - timedelta(days=1)
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
        return {
            "income_total": income_total,
            "expense_total": expense_total,
            "balance": income_total - expense_total,
            "debt_lend_outstanding": debt_lend_outstanding,
            "debt_borrow_outstanding": debt_borrow_outstanding,
            "debt_net_position": debt_lend_outstanding - debt_borrow_outstanding,
            "active_debt_cards": len(debt_cards),
        }
