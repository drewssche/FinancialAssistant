from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.operation import Operation


def _period_bounds(selected: date, period: str) -> tuple[date, date]:
    if period == "day":
        return selected, selected
    week_start = selected - timedelta(days=selected.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def create_operation(
    db: Session,
    *,
    kind: str,
    subcategory: str,
    amount: Decimal,
    occurred_on: date,
    account: str,
    comment: str,
) -> Operation:
    op = Operation(
        kind=kind,
        subcategory=subcategory,
        amount=amount,
        occurred_on=occurred_on,
        account=account,
        comment=comment,
    )
    db.add(op)
    db.commit()
    db.refresh(op)
    return op


def update_operation(
    db: Session,
    op: Operation,
    *,
    kind: str,
    subcategory: str,
    amount: Decimal,
    occurred_on: date,
    account: str,
    comment: str,
) -> Operation:
    op.kind = kind
    op.subcategory = subcategory
    op.amount = amount
    op.occurred_on = occurred_on
    op.account = account
    op.comment = comment
    db.commit()
    db.refresh(op)
    return op


def delete_operation(db: Session, op: Operation) -> None:
    db.delete(op)
    db.commit()


def recent_operations(db: Session, limit: int = 20) -> list[Operation]:
    stmt = select(Operation).order_by(desc(Operation.occurred_on), desc(Operation.created_at)).limit(limit)
    return list(db.scalars(stmt).all())


def build_summary(db: Session, selected: date, period: str) -> dict:
    start_date, end_date = _period_bounds(selected, period)

    totals = {"income": Decimal("0"), "expense": Decimal("0")}
    totals_stmt = (
        select(Operation.kind, func.coalesce(func.sum(Operation.amount), 0))
        .where(Operation.occurred_on >= start_date, Operation.occurred_on <= end_date)
        .group_by(Operation.kind)
    )
    for kind, amount in db.execute(totals_stmt).all():
        totals[kind] = Decimal(amount)

    def _grouped(kind: str) -> list[dict]:
        stmt = (
            select(Operation.subcategory, func.coalesce(func.sum(Operation.amount), 0).label("total"))
            .where(
                Operation.kind == kind,
                Operation.occurred_on >= start_date,
                Operation.occurred_on <= end_date,
            )
            .group_by(Operation.subcategory)
            .order_by(desc("total"))
        )
        rows = db.execute(stmt).all()
        return [{"name": name, "amount": round(float(total), 2)} for name, total in rows]

    return {
        "selected_date": selected.isoformat(),
        "period": period,
        "totals": {
            "income": round(float(totals["income"]), 2),
            "expense": round(float(totals["expense"]), 2),
            "balance": round(float(totals["income"] - totals["expense"]), 2),
        },
        "income_rows": _grouped("income"),
        "expense_rows": _grouped("expense"),
    }


def serialize_operation(item: Operation) -> dict:
    return {
        "id": str(item.id),
        "kind": item.kind,
        "subcategory": item.subcategory,
        "amount": round(float(item.amount), 2),
        "occurred_on": item.occurred_on.isoformat(),
        "account": item.account,
        "comment": item.comment or "",
        "created_at": item.created_at.isoformat(timespec="seconds"),
    }


def get_operation(db: Session, operation_id: UUID) -> Operation | None:
    return db.get(Operation, operation_id)
