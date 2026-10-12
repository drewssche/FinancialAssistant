"""Catalog-wide comparisons from receipts; a single streaming read, no writes."""
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select

from app.core.search import matches_search
from app.db.models import CatalogProduct, Operation, OperationItemTemplate, OperationReceiptItem
from app.services.product_price_history_service import content, percent


def money(value):
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class CatalogPriceChangesService:
    def __init__(self, db):
        self.db = db

    def get(self, *, user_id, basis='unit', price_kind='paid', comparison='period',
            direction='all', q=None, date_from=None, date_to=None, page=1, page_size=20):
        stmt = select(OperationReceiptItem, Operation.operation_date, Operation.currency,
                      CatalogProduct.id, CatalogProduct.name, OperationItemTemplate.name).join(
            Operation, Operation.id == OperationReceiptItem.operation_id).join(
            OperationItemTemplate, OperationItemTemplate.id == OperationReceiptItem.template_id).join(
            CatalogProduct, CatalogProduct.id == OperationItemTemplate.product_id).where(
                OperationReceiptItem.user_id == user_id, Operation.user_id == user_id,
                OperationItemTemplate.user_id == user_id, CatalogProduct.user_id == user_id,
                Operation.kind == 'expense', CatalogProduct.is_archived.is_(False),
                OperationItemTemplate.is_archived.is_(False))
        if date_from:
            stmt = stmt.where(Operation.operation_date >= date_from)
        if date_to:
            stmt = stmt.where(Operation.operation_date <= date_to)
        stmt = stmt.order_by(Operation.operation_date, Operation.id, OperationReceiptItem.id)
        groups = {}
        excluded = 0
        for item, day, currency, product_id, product_name, offer_name in self.db.execute(stmt.execution_options(yield_per=500)):
            shop = ' '.join((item.shop_name or '').split())
            # Filter stable series metadata, never individual historical line names/prices.
            if q and not matches_search(' '.join([product_name, offer_name, shop]), q):
                continue
            if item.quantity <= 0 or item.line_total < 0:
                excluded += 1
                continue
            price = item.line_total / item.quantity if price_kind == 'paid' else item.regular_unit_price
            unit, divisor = content(item)
            if price is None or (basis == 'normalized' and divisor is None):
                excluded += 1
                continue
            package = (item.sale_unit, item.package_quantity, item.package_unit)
            if basis == 'normalized':
                price /= divisor
                grouping = unit
                volume = item.quantity * divisor
            else:
                grouping, unit, volume = package, item.sale_unit, item.quantity
            key = (product_id, item.template_id, currency, shop.casefold(), grouping)
            row = dict(receipt_item_id=item.id, operation_id=item.operation_id, recorded_at=day,
                       price=price, volume=volume, package=package, is_discounted=item.is_discounted)
            if key not in groups:
                groups[key] = dict(product_id=product_id, product_name=product_name,
                    template_id=item.template_id, offer_name=offer_name, shop_name=shop or None,
                    currency=currency, unit=unit, sale_unit=item.sale_unit if basis == 'unit' else None,
                    package_quantity=item.package_quantity if basis == 'unit' else None,
                    package_unit=item.package_unit if basis == 'unit' else None,
                    first=row, last=row, previous=None, observations_count=0,
                    increases=0, decreases=0, package_changed=False)
            group = groups[key]
            if group['observations_count']:
                previous = group['last']
                group['previous'] = previous
                group['increases'] += price > previous['price']
                group['decreases'] += price < previous['price']
                group['package_changed'] |= package != previous['package']
            group['last'] = row
            group['observations_count'] += 1
        items = []
        insufficient = 0
        for group in groups.values():
            if group['observations_count'] < 2:
                insufficient += 1
                continue
            first, last, previous = group.pop('first'), group.pop('last'), group.pop('previous')
            reference = first if comparison == 'period' else previous
            change_direction = (last['price'] > reference['price']) - (last['price'] < reference['price'])
            if direction != 'all' and change_direction != {'up': 1, 'down': -1, 'same': 0}[direction]:
                continue
            baseline_cost, latest_cost = money(reference['price'] * last['volume']), money(last['price'] * last['volume'])
            items.append({**group, 'reference_price': reference['price'], 'latest_price': last['price'],
                'reference_date': reference['recorded_at'], 'latest_date': last['recorded_at'],
                'latest_operation_id': last['operation_id'], 'latest_receipt_item_id': last['receipt_item_id'],
                'direction': change_direction, 'change_percent': percent(reference['price'], last['price']),
                'period_change_percent': percent(first['price'], last['price']),
                'last_change_percent': percent(previous['price'], last['price']),
                'baseline_cost': baseline_cost, 'latest_cost': latest_cost, 'cost_difference': latest_cost - baseline_cost,
                'latest_is_discounted': last['is_discounted'], 'reference_is_discounted': reference['is_discounted']})
        items.sort(key=lambda row: (row['latest_date'], row['latest_operation_id'], row['latest_receipt_item_id']), reverse=True)
        start = (page - 1) * page_size
        return dict(items=items[start:start + page_size], total=len(items), page=page, page_size=page_size,
                    excluded_count=excluded, insufficient_series_count=insufficient,
                    basis=basis, price_kind=price_kind, comparison=comparison)
