import re
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from app.core.measurement import normalize_measurement, measurement_snapshot
from app.db.models import CatalogProduct, CatalogVariant, CatalogVariantCode, CatalogOfferIdentity, OperationItemTemplate
from app.services.activity_service import ActivityService
from app.services.catalog_product_service import CatalogProductService


def normalize_codes(codes):
    result = {}
    for raw in codes:
        code = raw.strip()
        if not re.fullmatch(r'(?:[0-9]{8}|[0-9]{12,14})', code):
            raise ValueError('GTIN/EAN: нужны 8, 12, 13 или 14 цифр. Артикул магазина укажите в предложении.')
        total = sum(int(digit) * (3 if i % 2 == 0 else 1) for i, digit in enumerate(reversed(code[:-1])))
        if (10 - total % 10) % 10 != int(code[-1]) or not int(code):
            raise ValueError('Неверная контрольная цифра GTIN/EAN')
        result.setdefault(code.zfill(14), code)
    return result


class CatalogIdentityService:
    def __init__(self, db):
        self.db = db

    def product(self, user_id, product_id, *, lock=False):
        stmt = select(CatalogProduct).where(CatalogProduct.id == product_id, CatalogProduct.user_id == user_id)
        product = self.db.scalar(stmt.with_for_update() if lock else stmt)
        if product is None:
            raise LookupError('Товар не найден')
        return product

    def get(self, *, user_id, product_id):
        self.product(user_id, product_id)
        variants = list(self.db.scalars(select(CatalogVariant).where(CatalogVariant.product_id == product_id, CatalogVariant.user_id == user_id).order_by(CatalogVariant.is_archived, CatalogVariant.id)))
        codes = {}
        if variants:
            for row in self.db.scalars(select(CatalogVariantCode).where(CatalogVariantCode.user_id == user_id, CatalogVariantCode.variant_id.in_([v.id for v in variants])).order_by(CatalogVariantCode.id)):
                codes.setdefault(row.variant_id, []).append(row.code)
        mappings = self.db.scalars(select(CatalogOfferIdentity).join(OperationItemTemplate, OperationItemTemplate.id == CatalogOfferIdentity.template_id).where(CatalogOfferIdentity.user_id == user_id, OperationItemTemplate.user_id == user_id, OperationItemTemplate.product_id == product_id))
        return {'variants': [dict(id=v.id, name=v.name, is_archived=v.is_archived, **measurement_snapshot(v, json_safe=True), codes=codes.get(v.id, [])) for v in variants],
                'offers': [dict(template_id=m.template_id, variant_id=m.variant_id, retailer_code=m.retailer_code, external_name=m.external_name, product_url=m.product_url) for m in mappings]}

    def save_variant(self, *, user_id, product_id, data, variant_id=None):
        product = self.product(user_id, product_id, lock=True)
        if product.is_archived:
            raise ValueError('Сначала восстановите товар из архива')
        measurement = normalize_measurement(data)
        name = ' '.join(data['name'].split())
        if not name:
            raise ValueError('Укажите название фасовки')
        codes = normalize_codes(data['codes'])
        row = None
        if variant_id:
            row = self.db.scalar(select(CatalogVariant).where(CatalogVariant.id == variant_id, CatalogVariant.user_id == user_id, CatalogVariant.product_id == product_id))
            if row is None:
                raise LookupError('Фасовка не найдена')
        if codes:
            conflict = self.db.scalar(select(CatalogVariantCode.id).where(CatalogVariantCode.user_id == user_id, CatalogVariantCode.gtin14.in_(codes), CatalogVariantCode.variant_id != (variant_id or 0)))
            if conflict:
                raise ValueError('Этот штрихкод уже закреплён за другой фасовкой, в том числе архивной')
        if row is None:
            row = CatalogVariant(user_id=user_id, product_id=product_id)
            self.db.add(row)
        row.name = name
        row.is_archived = data['is_archived']
        for key,value in measurement.items():
            setattr(row,key,value)
        try:
            self.db.flush()
            self.db.execute(delete(CatalogVariantCode).where(CatalogVariantCode.variant_id == row.id, CatalogVariantCode.user_id == user_id))
            self.db.add_all([CatalogVariantCode(user_id=user_id, variant_id=row.id, code=code, gtin14=canonical) for canonical,code in codes.items()])
            ActivityService(self.db).record(user_id=user_id, actor_user_id=user_id, entity_type='catalog_product', entity_id=product_id, event_type='updated', title='Фасовка и штрихкоды сохранены', metadata={'variant_id':row.id, 'name':name, 'codes':list(codes.values()), 'is_archived':row.is_archived})
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError('Штрихкод уже занят другой фасовкой. Обновите карточку.') from exc
        CatalogProductService(self.db)._invalidate(user_id)
        return self.get(user_id=user_id, product_id=product_id)

    def save_offer(self, *, user_id, product_id, template_id, data):
        self.product(user_id, product_id)
        offer = self.db.scalar(select(OperationItemTemplate).where(OperationItemTemplate.id == template_id, OperationItemTemplate.product_id == product_id, OperationItemTemplate.user_id == user_id))
        if offer is None:
            raise LookupError('Предложение не найдено')
        row = self.db.get(CatalogOfferIdentity, template_id)
        if row is not None and row.user_id != user_id:
            raise LookupError('Предложение не найдено')
        if data['variant_id']:
            variant = self.db.scalar(select(CatalogVariant).where(CatalogVariant.id == data['variant_id'], CatalogVariant.product_id == product_id, CatalogVariant.user_id == user_id))
            if variant is None or (variant.is_archived and (row is None or row.variant_id != variant.id)):
                raise ValueError('Выберите действующую фасовку этого товара')
        if row is None:
            row = CatalogOfferIdentity(template_id=template_id, user_id=user_id)
            self.db.add(row)
        row.variant_id = data['variant_id']
        for key in ('retailer_code','external_name','product_url'):
            value = data[key]
            setattr(row,key,str(value).strip() or None if value is not None else None)
        ActivityService(self.db).record(user_id=user_id, actor_user_id=user_id, entity_type='catalog_product', entity_id=product_id, event_type='updated', title='Соответствие предложения сохранено', metadata={'template_id':template_id,'variant_id':row.variant_id,'retailer_code':row.retailer_code,'product_url':row.product_url})
        self.db.commit()
        CatalogProductService(self.db)._invalidate(user_id)
        return self.get(user_id=user_id, product_id=product_id)
