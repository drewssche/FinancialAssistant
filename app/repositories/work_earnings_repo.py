from datetime import date

from sqlalchemy import exists, extract, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Operation, WorkPaymentLink


class WorkEarningsRepository:
    """Aggregate live payroll operations once, regardless of how they were matched."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _conditions(*, user_id: int, category_ids: set[int], received_through: date):
        linked = exists(select(WorkPaymentLink.id).where(
            WorkPaymentLink.user_id == user_id,
            or_(
                WorkPaymentLink.operation_id == Operation.id,
                WorkPaymentLink.snapshot_operation_id == Operation.id,
            ),
        ))
        return (
            Operation.user_id == user_id,
            Operation.kind == "income",
            Operation.operation_date <= received_through,
            or_(linked, Operation.category_id.in_(sorted(category_ids))),
        )

    def first_payment_date(self, *, user_id: int, category_ids: set[int], received_through: date):
        return self.db.scalar(select(func.min(Operation.operation_date)).where(
            *self._conditions(user_id=user_id, category_ids=category_ids, received_through=received_through),
        ))

    def monthly_totals(
        self, *, user_id: int, category_ids: set[int],
        date_from: date, date_to: date, received_through: date,
    ):
        year = extract("year", Operation.operation_date)
        month = extract("month", Operation.operation_date)
        currency = func.coalesce(Operation.base_currency, Operation.currency)
        return self.db.execute(select(
            year.label("year"), month.label("month"), currency.label("currency"),
            func.sum(Operation.amount).label("amount"),
            func.count(Operation.id).label("operation_count"),
        ).where(
            *self._conditions(user_id=user_id, category_ids=category_ids, received_through=received_through),
            Operation.operation_date >= date_from,
            Operation.operation_date <= date_to,
        ).group_by(year, month, currency).order_by(year, month, currency)).all()
