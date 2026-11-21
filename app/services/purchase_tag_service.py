from decimal import ROUND_HALF_UP

from sqlalchemy import String, case, cast, func, literal, select

from app.core.receipt_pricing import CENT
from app.core.tags import normalize_tags
from app.db.models import Category, Operation, OperationReceiptItem, PlanOperation, PlanReceiptItem

ENTRY_LIMIT = 30


def purchase_tag_summary(db, user_id: int, tag: str) -> dict:
    """A tag on the operation takes precedence over tags on its individual lines."""
    names = normalize_tags([tag])
    if not names:
        raise ValueError("Укажите тег")
    tag = names[0]

    def matches(column):
        return cast(column, String).concat(literal(",")).contains(f"#{tag},", autoescape=True)

    def collect(parent, line, parent_key, day, item_currency, *, planned=False):
        line_sums = (
            select(parent_key.label("entry_id"), func.sum(line.line_total).label("amount"),
                   func.count().label("item_count"), func.min(line.name).label("item_name"))
            .where(line.user_id == user_id, matches(line.tags))
            .group_by(parent_key).subquery()
        )
        whole = matches(parent.tags)
        original = case(
            ((parent.original_amount == 0) & (parent.currency == parent.base_currency), parent.amount),
            else_=parent.original_amount,
        )
        amount = case((whole, original), else_=line_sums.c.amount)
        currency = case((whole, parent.currency), else_=item_currency)
        receipt_label = (
            select(func.coalesce(func.nullif(line.shop_name, ""), line.name))
            .where(parent_key == parent.id, line.user_id == user_id)
            .order_by(line.id).limit(1).correlate(parent).scalar_subquery()
        )
        tagged_label = case(
            (line_sums.c.item_count == 1, line_sums.c.item_name),
            else_=literal("Позиций по тегу · ").concat(cast(line_sums.c.item_count, String)),
        )
        description = func.coalesce(func.nullif(func.trim(parent.note), ""), case((~whole, tagged_label)),
                                    Category.name, receipt_label)
        stmt = (
            select(parent.id, day.label("date"), parent.kind, parent.note, description.label("description"),
                   currency.label("currency"), amount.label("amount"))
            .outerjoin(line_sums, line_sums.c.entry_id == parent.id)
            .outerjoin(Category, (Category.id == parent.category_id)
                       & ((Category.user_id == user_id) | Category.user_id.is_(None)))
            .where(parent.user_id == user_id, parent.kind.in_(("income", "expense")),
                   whole | line_sums.c.entry_id.is_not(None))
        )
        if planned:
            stmt = stmt.where(parent.status == "active")
        else:
            stmt = stmt.add_columns(whole.label("whole"), parent.base_currency, parent.amount.label("base_amount"),
                                    Operation.receipt_fx_rate.label("item_rate"))
        groups = {kind: {"entries": [], "count": 0, "totals": {}} for kind in ("income", "expense")}
        base_totals = {}
        for row in db.execute(stmt.order_by(day.asc() if planned else day.desc(), parent.id)):
            group = groups[row.kind]
            group["count"] += 1
            totals = group["totals"]
            totals[row.currency] = totals.get(row.currency, 0) + row.amount
            if len(group["entries"]) < ENTRY_LIMIT:
                group["entries"].append(dict(id=row.id, date=row.date, note=row.note, description=row.description,
                                             currency=row.currency, amount=row.amount))
            if not planned:
                base_amount = row.base_amount if row.whole else (
                    row.amount * row.item_rate
                ).quantize(CENT, rounding=ROUND_HALF_UP)
                base = base_totals.setdefault(row.base_currency, {"income": 0, "expense": 0})
                base[row.kind] += base_amount
        return groups, base_totals

    posted, historical = collect(Operation, OperationReceiptItem, OperationReceiptItem.operation_id,
                                 Operation.operation_date, Operation.item_currency)
    future, _ = collect(PlanOperation, PlanReceiptItem, PlanReceiptItem.plan_id,
                        PlanOperation.scheduled_date, PlanOperation.currency, planned=True)

    income, expense = posted["income"]["totals"], posted["expense"]["totals"]
    currencies = sorted(income.keys() | expense.keys())
    # A common historical base makes amounts in different currencies comparable.
    converted = len(currencies) > 1 and len(historical) == 1
    balances = historical if converted else {
        currency: {"income": income.get(currency, 0), "expense": expense.get(currency, 0)} for currency in currencies
    }
    for amounts in balances.values():
        amounts["net"] = amounts["income"] - amounts["expense"]
    return dict(tag=tag, balances=balances, converted=converted, paid=posted["expense"], received=posted["income"],
                planned=future["expense"], planned_income=future["income"])
