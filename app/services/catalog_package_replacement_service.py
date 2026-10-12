from collections import defaultdict
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.db.models import CatalogPackageReplacement as Replacement, Operation, OperationReceiptItem, OperationItemTemplate
from app.services.catalog_identity_service import CatalogIdentityService
from app.services.catalog_product_service import CatalogProductService
from app.services.activity_service import ActivityService
from app.services.product_price_history_service import content, percent


def dimensions(snapshot):
    return (snapshot.get('sale_unit'), Decimal(str(snapshot['package_quantity'])) if snapshot.get('package_quantity') else None, snapshot.get('package_unit'))


def package_content(snapshot):
    sale, qty, unit = dimensions(snapshot)
    if sale not in {'piece', 'pack'} or not qty or not unit:
        raise ValueError('Для обеих фасовок укажите содержимое упаковки и его единицу')
    return content(SimpleNamespace(sale_unit=sale, package_quantity=qty, package_unit=unit))


def pct(old, new):
    value = percent(old, new)
    return str(value) if value is not None else None


class CatalogPackageReplacementService:
    def __init__(self, db):
        self.db = db
        self.identity = CatalogIdentityService(db)

    def rows(self, user_id, product_id):
        return list(self.db.scalars(select(Replacement).where(Replacement.user_id == user_id,
            Replacement.product_id == product_id).order_by(Replacement.effective_date, Replacement.id)))

    def get(self, *, user_id, product_id):
        registry = self.identity.get(user_id=user_id, product_id=product_id)
        rows = self.rows(user_id, product_id)
        candidates = defaultdict(list)
        for row in rows:
            candidates[row.old_variant_id].append((row, 'old', row.old_snapshot))
            candidates[row.new_variant_id].append((row, 'new', row.new_snapshot))
        pairs = defaultdict(dict)
        if rows:
            stmt = select(OperationReceiptItem, Operation.operation_date, Operation.currency).join(
                Operation, Operation.id == OperationReceiptItem.operation_id).join(
                OperationItemTemplate, OperationItemTemplate.id == OperationReceiptItem.template_id).where(
                OperationReceiptItem.user_id == user_id, Operation.user_id == user_id,
                OperationItemTemplate.user_id == user_id, OperationItemTemplate.product_id == product_id,
                Operation.kind == 'expense', OperationReceiptItem.quantity > 0,
                OperationReceiptItem.line_total >= 0,
                OperationReceiptItem.variant_snapshot['variant_id'].as_integer().in_(list(candidates))
            ).order_by(Operation.operation_date, Operation.id, OperationReceiptItem.id).execution_options(yield_per=100)
            for item, day, currency in self.db.execute(stmt):
                for row, side, snapshot in candidates[(item.variant_snapshot or {}).get('variant_id')]:
                    if dimensions(snapshot) != (item.sale_unit, item.package_quantity, item.package_unit):
                        continue
                    if (side == 'old' and day > row.effective_date) or (side == 'new' and day < row.effective_date):
                        continue
                    shop = ' '.join((item.shop_name or '').split())
                    pair = pairs[row.id].setdefault((currency, shop.casefold()), {'currency': currency, 'shop_name': shop or None})
                    # Ascending observations: keep last old and first new purchase.
                    if side == 'new' and side in pair:
                        continue
                    _, volume = package_content(snapshot)
                    pair[side] = dict(operation_id=item.operation_id, receipt_item_id=item.id,
                        recorded_at=day, price=item.line_total / item.quantity,
                        normalized_price=item.line_total / item.quantity / volume,
                        regular_normalized_price=item.regular_unit_price / volume if item.regular_unit_price is not None else None,
                        is_discounted=item.is_discounted)
        items = []
        for row in rows:
            unit, old_volume = package_content(row.old_snapshot)
            _, new_volume = package_content(row.new_snapshot)
            comparisons = []
            for pair in pairs[row.id].values():
                if 'old' not in pair or 'new' not in pair:
                    continue
                before, after = pair['old'], pair['new']
                comparisons.append(dict(currency=pair['currency'], shop_name=pair['shop_name'],
                    old={k:str(v) if isinstance(v, Decimal) else v for k,v in before.items()},
                    new={k:str(v) if isinstance(v, Decimal) else v for k,v in after.items()},
                    package_price_change_percent=pct(before['price'], after['price']),
                    normalized_price_change_percent=pct(before['normalized_price'], after['normalized_price']),
                    regular_normalized_change_percent=pct(before['regular_normalized_price'], after['regular_normalized_price'])
                        if before['regular_normalized_price'] is not None and after['regular_normalized_price'] is not None else None))
            items.append(dict(id=row.id, old_variant_id=row.old_variant_id, new_variant_id=row.new_variant_id,
                effective_date=row.effective_date, old_snapshot=row.old_snapshot, new_snapshot=row.new_snapshot,
                note=row.note, unit=unit, old_volume=str(old_volume), new_volume=str(new_volume),
                volume_change_percent=pct(old_volume,new_volume),
                constant_package_price_change_percent=pct(new_volume,old_volume), comparisons=comparisons))
        return dict(variants=registry['variants'], items=items)

    def create(self, *, user_id, product_id, data):
        product = self.identity.product(user_id, product_id, lock=True)
        if product.is_archived:
            raise ValueError('Сначала восстановите товар из архива')
        old_id, new_id = data['old_variant_id'], data['new_variant_id']
        if old_id == new_id:
            raise ValueError('Выберите две разные фасовки')
        variants = {v['id']:v for v in self.identity.get(user_id=user_id, product_id=product_id)['variants']}
        if old_id not in variants or new_id not in variants:
            raise ValueError('Обе фасовки должны принадлежать этому товару')
        old, new = variants[old_id], variants[new_id]
        for expected, actual in ((data['expected_old'], old), (data['expected_new'], new)):
            if dimensions(expected) != dimensions(actual) or expected['name'] != actual['name'] or expected['codes'] != actual['codes']:
                raise ValueError('Фасовка изменилась после загрузки. Обновите варианты и проверьте подтверждение.')
        if package_content(old)[0] != package_content(new)[0]:
            raise ValueError('Нельзя сопоставить массу, объём и количество штук друг с другом')
        rows = self.rows(user_id, product_id)
        successors = {r.old_variant_id:r.new_variant_id for r in rows}
        current = new_id
        seen = {old_id}
        while current in successors:
            if current in seen:
                raise ValueError('Замена образует цикл')
            seen.add(current); current = successors[current]
        if current == old_id:
            raise ValueError('Замена образует цикл')
        for r in rows:
            if r.old_variant_id == old_id or r.new_variant_id == new_id:
                raise ValueError('У фасовки уже есть подтверждённая замена; сначала отмените прежнюю связь')
            if (r.new_variant_id == old_id and r.effective_date > data['effective_date']) or (r.old_variant_id == new_id and r.effective_date < data['effective_date']):
                raise ValueError('Даты замен должны следовать порядку фасовок')
            if (r.new_variant_id == old_id and dimensions(r.new_snapshot) != dimensions(old)) or (r.old_variant_id == new_id and dimensions(r.old_snapshot) != dimensions(new)):
                raise ValueError('Размер связанной фасовки изменён: создайте отдельный вариант для нового размера')
        snapshot = lambda value: {key:value[key] for key in ('id','name','sale_unit','package_quantity','package_unit','codes')}
        row = Replacement(user_id=user_id, product_id=product_id, old_variant_id=old_id, new_variant_id=new_id,
            effective_date=data['effective_date'], old_snapshot=snapshot(old), new_snapshot=snapshot(new),
            note=(data.get('note') or '').strip() or None)
        self.db.add(row)
        try:
            self.db.flush()
            ActivityService(self.db).record(user_id=user_id, actor_user_id=user_id, entity_type='catalog_product',
                entity_id=product_id,event_type='updated',title='Замена фасовки подтверждена',
                metadata={'replacement_id':row.id,'old':row.old_snapshot,'new':row.new_snapshot,'effective_date':str(row.effective_date)})
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError('Связь уже изменилась. Обновите карточку.') from exc
        CatalogProductService(self.db)._invalidate(user_id)
        return self.get(user_id=user_id, product_id=product_id)

    def remove(self, *, user_id, product_id, replacement_id):
        self.identity.product(user_id, product_id, lock=True)
        row = self.db.scalar(select(Replacement).where(Replacement.id == replacement_id,
            Replacement.user_id == user_id, Replacement.product_id == product_id))
        if row is None:
            raise LookupError('Подтверждение не найдено')
        ActivityService(self.db).record(user_id=user_id,actor_user_id=user_id,entity_type='catalog_product',
            entity_id=product_id,event_type='updated',title='Подтверждение замены фасовки отменено',
            metadata={'replacement_id':row.id,'old':row.old_snapshot,'new':row.new_snapshot,'effective_date':str(row.effective_date)})
        self.db.delete(row); self.db.commit()
        CatalogProductService(self.db)._invalidate(user_id)
        return self.get(user_id=user_id, product_id=product_id)
