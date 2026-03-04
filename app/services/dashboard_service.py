from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.repositories.operation_repo import OperationRepository


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OperationRepository(db)

    def get_summary(self, user_id: int, period: str = "30d"):
        date_to = date.today()
        if period == "month":
            date_from = date_to.replace(day=1)
        else:
            date_from = date_to - timedelta(days=30)

        income_total, expense_total = self.repo.summary_for_period(user_id, date_from, date_to)
        return {
            "income_total": income_total,
            "expense_total": expense_total,
            "balance": income_total - expense_total,
        }
