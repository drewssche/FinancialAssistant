from datetime import date
from decimal import Decimal

from sqlalchemy import Select, and_, asc, desc, func, select
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

    def get_by_id(self, user_id: int, operation_id: int) -> Operation | None:
        stmt = select(Operation).where(Operation.user_id == user_id, Operation.id == operation_id)
        return self.db.scalar(stmt)

    def list_filtered(
        self,
        user_id: int,
        page: int,
        page_size: int,
        sort_by: str,
        sort_dir: str,
        kind: str | None,
        date_from: date | None,
        date_to: date | None,
        category_id: int | None,
        q: str | None,
    ) -> tuple[list[Operation], int]:
        conditions = [Operation.user_id == user_id]

        if kind:
            conditions.append(Operation.kind == kind)
        if date_from:
            conditions.append(Operation.operation_date >= date_from)
        if date_to:
            conditions.append(Operation.operation_date <= date_to)
        if category_id is not None:
            conditions.append(Operation.category_id == category_id)
        if q:
            conditions.append(Operation.note.ilike(f"%{q}%"))

        base_stmt: Select[tuple[Operation]] = select(Operation).where(and_(*conditions))
        count_stmt = select(func.count()).select_from(Operation).where(and_(*conditions))

        sort_column = {
            "operation_date": Operation.operation_date,
            "amount": Operation.amount,
            "created_at": Operation.created_at,
        }[sort_by]
        order_expr = asc(sort_column) if sort_dir == "asc" else desc(sort_column)

        stmt = (
            base_stmt.order_by(order_expr, Operation.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.scalars(stmt))
        total = int(self.db.scalar(count_stmt) or 0)
        return items, total

    def update(self, operation: Operation, updates: dict) -> Operation:
        for key, value in updates.items():
            setattr(operation, key, value)
        self.db.flush()
        return operation

    def delete(self, operation: Operation) -> None:
        self.db.delete(operation)
        self.db.flush()

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

    def first_operation_date(self, user_id: int) -> date | None:
        stmt = select(func.min(Operation.operation_date)).where(Operation.user_id == user_id)
        return self.db.scalar(stmt)
