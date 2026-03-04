from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.operation_repo import OperationRepository


class OperationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OperationRepository(db)

    def create_operation(
        self,
        user_id: int,
        kind: str,
        amount: Decimal,
        operation_date: date,
        category_id: int | None,
        note: str | None,
    ):
        item = self.repo.create(user_id, kind, amount, operation_date, category_id, note)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_operations(self, user_id: int, period_days: int = 30):
        date_to = date.today()
        date_from = date_to - timedelta(days=period_days)
        return self.repo.list_for_period(user_id, date_from, date_to)
