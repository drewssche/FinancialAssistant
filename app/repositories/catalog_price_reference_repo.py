"""Read-only catalog prices for the selected offer, never receipt defaults."""
from sqlalchemy import and_, select

from app.db.models import Operation, OperationItemPrice, OperationItemTemplate


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
