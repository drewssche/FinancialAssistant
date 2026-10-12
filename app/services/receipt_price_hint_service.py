"""Previous comparable purchase for an explicit receipt hint. No writes or defaults."""
from sqlalchemy import and_, or_, select

from app.db.models import CatalogProduct, Operation, OperationItemTemplate, OperationReceiptItem


def shop_key(value):
    return ' '.join((value or '').split()).casefold()


class ReceiptPriceHintService:
    def __init__(self, db):
        self.db = db

    def get(self, *, user_id, product_id, request):
        offer = self.db.scalar(select(OperationItemTemplate.id).join(
            CatalogProduct, CatalogProduct.id == OperationItemTemplate.product_id
        ).where(OperationItemTemplate.id == request.template_id,
                OperationItemTemplate.user_id == user_id,
                CatalogProduct.id == product_id, CatalogProduct.user_id == user_id))
        if offer is None:
            raise LookupError('Product offer not found')
        excluded = request.exclude_operation_id
        if excluded and self.db.scalar(select(Operation.id).where(
            Operation.id == excluded, Operation.user_id == user_id
        )) is None:
            raise LookupError('Operation not found')
        # Unknown package content is not evidence that two packages are identical.
        if not request.sale_unit or (request.sale_unit == 'pack' and not (
            request.package_quantity and request.package_unit
        )) or bool(request.package_quantity) != bool(request.package_unit):
            return {'status': 'unknown_measurements'}
        stmt = select(OperationReceiptItem, Operation.operation_date).join(
            Operation, Operation.id == OperationReceiptItem.operation_id
        ).where(OperationReceiptItem.template_id == request.template_id,
                OperationReceiptItem.user_id == user_id, Operation.user_id == user_id,
                Operation.kind == 'expense', Operation.currency == request.currency,
                Operation.operation_date <= request.as_of,
                OperationReceiptItem.quantity > 0, OperationReceiptItem.line_total >= 0,
                OperationReceiptItem.sale_unit == request.sale_unit,
                OperationReceiptItem.package_quantity == request.package_quantity,
                OperationReceiptItem.package_unit == request.package_unit)
        if excluded:
            # On the same date use entry order; never compare against this receipt
            # or a subsequently entered receipt while editing an older operation.
            stmt = stmt.where(Operation.id != excluded, or_(
                Operation.operation_date < request.as_of,
                and_(Operation.operation_date == request.as_of, Operation.id < excluded),
            ))
        stmt = stmt.order_by(Operation.operation_date.desc(), Operation.id.desc(),
                             OperationReceiptItem.id.desc()).execution_options(yield_per=100)
        for item, recorded_at in self.db.execute(stmt):
            if shop_key(item.shop_name) != shop_key(request.shop_name):
                continue
            # Only compare equal historical variant labels. Missing identity does
            # not silently match a explicitly selected variant (or vice versa).
            if (item.variant_snapshot or {}).get('variant_id') != request.variant_id:
                continue
            return {'status': 'found', 'previous': {
                'operation_id': item.operation_id, 'receipt_item_id': item.id,
                'recorded_at': recorded_at, 'quantity': item.quantity,
                'line_total': item.line_total, 'price': item.line_total / item.quantity,
                'is_discounted': item.is_discounted, 'discount_type': item.discount_type,
            }}
        return {'status': 'no_history'}
