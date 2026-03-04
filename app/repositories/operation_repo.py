from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db.models import Operation


class OperationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: int,
        kind: str,
        amount: Decimal,
        operation_date: date,
        category_id: int | None,
        note: str | None,
    ) -> Operation:
        operation = Operation(
            user_id=user_id,
            kind=kind,
            amount=amount,
            operation_date=operation_date,
            category_id=category_id,
            note=note,
        )
        self.db.add(operation)
        self.db.flush()
        return operation

    def list_for_period(self, user_id: int, date_from: date, date_to: date):
        stmt = (
            select(Operation)
            .where(and_(Operation.user_id == user_id, Operation.operation_date >= date_from, Operation.operation_date <= date_to))
            .order_by(Operation.operation_date.desc(), Operation.id.desc())
        )
        return list(self.db.scalars(stmt))

    def summary_for_period(self, user_id: int, date_from: date, date_to: date):
        income_stmt = select(func.coalesce(func.sum(Operation.amount), 0)).where(
            and_(
                Operation.user_id == user_id,
                Operation.kind == "income",
                Operation.operation_date >= date_from,
                Operation.operation_date <= date_to,
            )
        )
        expense_stmt = select(func.coalesce(func.sum(Operation.amount), 0)).where(
            and_(
                Operation.user_id == user_id,
                Operation.kind == "expense",
                Operation.operation_date >= date_from,
                Operation.operation_date <= date_to,
            )
        )
        income_total = self.db.scalar(income_stmt)
        expense_total = self.db.scalar(expense_stmt)
        return income_total, expense_total
