from sqlalchemy import String, case, cast, func, literal, select

from app.core.tags import normalize_tags
from app.db.models import Operation, OperationReceiptItem, PlanOperation, PlanReceiptItem


def purchase_tag_summary(db, user_id: int, tag: str) -> dict:
    """A tagged receipt counts in full, otherwise count just the tagged lines."""
    names = normalize_tags([tag])
    if not names:
        raise ValueError("Укажите тег")
    tag = names[0]

    def matches(column):
        return cast(column, String).concat(literal(",")).contains(f"#{tag},", autoescape=True)

    def expenses(parent, line, parent_key, day, *, planned=False):
        line_sums = (
            select(parent_key.label("entry_id"), func.sum(line.line_total).label("amount"))
            .where(line.user_id == user_id, matches(line.tags))
            .group_by(parent_key).subquery()
        )
        amount = case((matches(parent.tags), parent.original_amount), else_=line_sums.c.amount)
        stmt = (select(parent.id, day, parent.note, parent.currency, amount.label("amount"))
                .outerjoin(line_sums, line_sums.c.entry_id == parent.id)
                .where(parent.user_id == user_id, parent.kind == "expense",
                       matches(parent.tags) | line_sums.c.entry_id.is_not(None)))
        if planned:
            stmt = stmt.where(parent.status == "active")
        totals = {}
        entries = []
        count = 0
        for row in db.execute(stmt.order_by(day.asc() if planned else day.desc(), parent.id)):
            totals[row.currency] = totals.get(row.currency, 0) + row.amount
            count += 1
            if len(entries) < 30:
                entries.append(dict(id=row.id, date=row[1], note=row.note, currency=row.currency, amount=row.amount))
        return dict(entries=entries, count=count, totals=totals)

    return dict(tag=tag,
                paid=expenses(Operation, OperationReceiptItem, OperationReceiptItem.operation_id, Operation.operation_date),
                planned=expenses(PlanOperation, PlanReceiptItem, PlanReceiptItem.plan_id, PlanOperation.scheduled_date, planned=True))
