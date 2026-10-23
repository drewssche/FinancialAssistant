"""Explicit edits in receipt fields join the operation's transaction."""
from sqlalchemy import select
from app.core.measurement import measurement_snapshot, normalize_measurement
from app.db.models import CatalogProduct, CatalogVariant, CatalogVariantCode, CatalogOfferIdentity, OperationItemTemplate
from app.services.activity_service import ActivityService


class ReceiptCatalogEditService:
    def __init__(self, db):
        self.db = db

    def apply(self, *, user_id, product, template, item):
        rename = bool(item.get('catalog_name_touched'))
        resize = bool(item.get('catalog_measurement_touched'))
        if not (rename or resize):
            return
        if item.get('product_id') != product.id:
            raise ValueError('Для изменения карточки выберите товар из каталога')
        self.db.scalar(select(CatalogProduct).where(CatalogProduct.id == product.id,
            CatalogProduct.user_id == user_id).with_for_update())
        if product.is_archived:
            raise ValueError('Сначала восстановите товар из архива')
        before = {'name': product.name, **measurement_snapshot(product, json_safe=True)}
        if rename:
            name = ' '.join(item['name'].split())
            conflict = self.db.scalar(select(OperationItemTemplate.id).where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.id != template.id,
                OperationItemTemplate.shop_name_ci == template.shop_name_ci,
                OperationItemTemplate.name_ci == name.casefold()))
            if conflict:
                raise ValueError('В этом магазине уже есть позиция с таким названием. Выберите её или используйте объединение.')
            product.name = template.name = name
            product.name_ci = template.name_ci = name.casefold()
        if resize:
            new = normalize_measurement(item)
            old = normalize_measurement(product)
            variants = list(self.db.scalars(select(CatalogVariant).where(
                CatalogVariant.user_id == user_id, CatalogVariant.product_id == product.id,
                CatalogVariant.is_archived.is_(False)).with_for_update()))
            source_id = item.get('catalog_edit_variant_id')
            source = next((v for v in variants if v.id == source_id), None)
            if source_id and source is None:
                raise ValueError('Исходная фасовка недоступна. Выберите товар заново.')

            def ensure(measurement, name):
                matches = [v for v in variants if normalize_measurement(v) == measurement]
                if len(matches) > 1:
                    raise ValueError('Есть несколько одинаковых фасовок. Уточните их в карточке товара.')
                if matches:
                    return matches[0]
                v = CatalogVariant(user_id=user_id, product_id=product.id, name=name, **measurement)
                self.db.add(v); self.db.flush(); variants.append(v)
                return v

            previous = source or ensure(old, before['name'])
            target = previous if normalize_measurement(previous) == new else ensure(new, product.name)
            # Retain old dimensions as a variant, and freeze other shops' inherited defaults.
            old_default = ensure(old, before['name'])
            offers = list(self.db.scalars(select(OperationItemTemplate).where(
                OperationItemTemplate.user_id == user_id, OperationItemTemplate.product_id == product.id)))
            for offer in offers:
                mapping = self.db.get(CatalogOfferIdentity, offer.id)
                if mapping is None:
                    mapping = CatalogOfferIdentity(template_id=offer.id, user_id=user_id, variant_id=old_default.id)
                    self.db.add(mapping)
                if mapping.variant_id is None:
                    mapping.variant_id = old_default.id
                if offer.id == template.id:
                    mapping.variant_id = target.id
            if previous.id != target.id:
                # Codes identify the current package. Historical receipt snapshots retain
                # their original codes and dimensions; no past purchase is rewritten.
                supplied = {entry['code'].zfill(14) for entry in item.get('catalog_codes', []) if entry['kind'] == 'barcode'}
                for code in self.db.scalars(select(CatalogVariantCode).where(
                    CatalogVariantCode.user_id == user_id, CatalogVariantCode.variant_id == previous.id)):
                    if not supplied or code.gtin14 in supplied:
                        code.variant_id = target.id
            for key, value in new.items():
                setattr(product, key, value)
            item['variant_id'] = target.id
            item['variant_snapshot'] = None
        self.db.flush()
        ActivityService(self.db).record_updated(user_id=user_id, actor_user_id=user_id,
            entity_type='catalog_product', entity_id=product.id, before=before,
            after={'name':product.name, **measurement_snapshot(product, json_safe=True)},
            labels={'name':'Название', 'sale_unit':'Единица продажи', 'package_quantity':'Размер упаковки', 'package_unit':'Единица упаковки'},
            title='Товар уточнён при сохранении чека')
