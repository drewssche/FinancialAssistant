"""Read-only catalog prices for the selected offer, never receipt defaults."""
from sqlalchemy import and_, func, select

from app.db.models import Operation, OperationItemPrice, OperationItemTemplate, OperationReceiptItem


def last_purchase_prices(db, *, user_id, template_ids):
    """Return amount and currency from the same actual purchase at this source."""
    if not template_ids:
        return {}
    line = OperationReceiptItem
    ranked = select(
        line.template_id, line.unit_price, Operation.currency, Operation.operation_date,
        func.row_number().over(
            partition_by=line.template_id,
            order_by=(Operation.operation_date.desc(), Operation.id.desc(), line.id.desc()),
        ).label("rank"),
    ).join(Operation, Operation.id == line.operation_id).where(
        Operation.user_id == user_id, line.user_id == user_id, Operation.kind == "expense",
        line.template_id.in_(template_ids), line.unit_price > 0,
    ).subquery()
    return {
        row.template_id: {"amount": str(row.unit_price), "currency": row.currency,
                          "recorded_at": row.operation_date.isoformat()}
        for row in db.execute(select(ranked).where(ranked.c.rank == 1))
    }


def offer_price_references(db, *, user_id, template_ids):
    if not template_ids:
        return {}
    rows = db.execute(
        select(OperationItemPrice, Operation.currency)
        .join(OperationItemTemplate, OperationItemTemplate.id == OperationItemPrice.template_id)
        .outerjoin(Operation, and_(Operation.id == OperationItemPrice.source_operation_id,
                                   Operation.user_id == user_id))
        .where(OperationItemTemplate.user_id == user_id,
               OperationItemTemplate.id.in_(template_ids))
        .order_by(OperationItemPrice.recorded_at.desc(), OperationItemPrice.id.desc())
    )
    result = {}
    for price, currency in rows:
        if price.template_id in result:
            continue
        result[price.template_id] = {
            'amount': str(price.unit_price),
            'recorded_at': price.recorded_at.isoformat(),
            # Manually entered catalog prices are in the app's base currency.
            'currency': currency if price.source_operation_id else 'BYN',
        }
    return result
