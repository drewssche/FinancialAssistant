"""Exact, owner-scoped receipt identifiers. Writes join the receipt transaction."""
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from app.db.models import CatalogProduct, CatalogVariant, CatalogVariantCode, CatalogOfferIdentity, OperationItemTemplate
from app.db.models.item_source import ItemSource
from app.core.measurement import normalize_measurement, measurement_snapshot
from app.services.catalog_identity_service import normalize_codes


def variable_code(code):
    if len(code) == 14 and code.startswith('0'): code = code[1:]
    return len(code) == 13 and code[:2] in {str(n) for n in range(20, 30)}


class ReceiptCodeService:
    def __init__(self, db):
        self.db = db

    def lookup(self, *, user_id, codes, shop_name='', source_id=None):
        source_query = select(ItemSource).where(ItemSource.user_id == user_id, ItemSource.is_archived.is_(False))
        source = self.db.scalar(source_query.where(ItemSource.id == source_id)) if source_id else self.db.scalar(source_query.where(ItemSource.name_ci == ' '.join((shop_name or '').split()).casefold()))
        results, warnings, matched = {}, [], set()
        restricted = False
        for index, entry in enumerate(codes):
            code, kind = entry['code'].strip(), entry['kind']
            canonical = None
            if kind in ('barcode', 'unknown'):
                try:
                    canonical = next(iter(normalize_codes([code])))
                except ValueError:
                    if kind == 'barcode':
                        warnings.append(f'{code}: проверьте цифры штрихкода')
                if variable_code(code):
                    warnings.append(f'{code}: весовой код, подтвердите товар вручную')
                    restricted = True
            variants = []
            if canonical:
                variants = self.db.scalars(select(CatalogVariant).join(CatalogVariantCode, CatalogVariantCode.variant_id == CatalogVariant.id).where(
                    CatalogVariant.user_id == user_id, CatalogVariantCode.user_id == user_id,
                    CatalogVariantCode.gtin14 == canonical, CatalogVariant.is_archived.is_(False))).all()
            pairs = []
            for variant in variants:
                offers = self.db.scalars(select(OperationItemTemplate).outerjoin(CatalogOfferIdentity, CatalogOfferIdentity.template_id == OperationItemTemplate.id).where(
                    OperationItemTemplate.user_id == user_id, OperationItemTemplate.product_id == variant.product_id,
                    OperationItemTemplate.source_id == source.id, OperationItemTemplate.is_archived.is_(False),
                    or_(CatalogOfferIdentity.variant_id.is_(None), CatalogOfferIdentity.variant_id == variant.id))).all() if source else []
                pairs.extend((variant, offer, 'barcode') for offer in (offers or [None]))
            if kind in ('retailer', 'unknown') and source:
                rows = self.db.execute(select(CatalogOfferIdentity, OperationItemTemplate).join(OperationItemTemplate, CatalogOfferIdentity.template_id == OperationItemTemplate.id).where(
                    CatalogOfferIdentity.user_id == user_id, OperationItemTemplate.user_id == user_id,
                    OperationItemTemplate.source_id == source.id, OperationItemTemplate.is_archived.is_(False),
                    CatalogOfferIdentity.retailer_code == code)).all()
                for mapping, offer in rows:
                    variant = self.db.scalar(select(CatalogVariant).where(CatalogVariant.id == mapping.variant_id, CatalogVariant.product_id == offer.product_id, CatalogVariant.user_id == user_id, CatalogVariant.is_archived.is_(False))) if mapping.variant_id else None
                    if mapping.variant_id and variant is None:
                        continue
                    pairs.append((variant, offer, 'retailer'))
            elif kind == 'retailer' and not source:
                warnings.append('Для поиска артикула выберите магазин из каталога')
            for variant, offer, method in pairs:
                product_id = variant.product_id if variant else offer.product_id
                product = self.db.scalar(select(CatalogProduct).where(CatalogProduct.id == product_id, CatalogProduct.user_id == user_id, CatalogProduct.is_archived.is_(False)))
                if product is None:
                    continue
                key = (product.id, variant.id if variant else None, offer.id if offer else None)
                if key not in results:
                    variant_codes = list(self.db.scalars(select(CatalogVariantCode.code).where(CatalogVariantCode.user_id == user_id, CatalogVariantCode.variant_id == variant.id))) if variant else []
                    results[key] = dict(product_id=product.id, product_name=product.name, name=offer.name if offer else product.name,
                        template_id=offer.id if offer else None, source_id=source.id if source else None,
                        category_id=product.category_id, brand_id=product.brand_id,
                        variant_id=variant.id if variant else None,
                        variant_snapshot=dict(variant_id=variant.id, name=variant.name, codes=variant_codes) if variant else None,
                        **measurement_snapshot(variant or product, json_safe=True), matched_by=[], matched_codes=[])
                result = results[key]
                if method not in result['matched_by']: result['matched_by'].append(method)
                result['matched_codes'].append(code)
                matched.add(index)
        # An SKU without a package link can corroborate one exact barcode result for the same offer.
        for key, entry in list(results.items()):
            if entry['variant_id'] is not None: continue
            specific = [v for v in results.values() if v['product_id'] == entry['product_id'] and v['template_id'] == entry['template_id'] and v['variant_id'] is not None]
            if len(specific) == 1:
                target = specific[0]
                target['matched_by'] = list(dict.fromkeys(target['matched_by'] + entry['matched_by']))
                target['matched_codes'] = list(dict.fromkeys(target['matched_codes'] + entry['matched_codes']))
                del results[key]
        items = list(results.values())
        # Two codes resolving to different variants/offers must not silently select one.
        return dict(items=items[:20], auto_match=len(items) == 1 and len(matched) == len(codes) and not restricted,
                    warnings=list(dict.fromkeys(warnings)), unmatched=[c['code'] for i,c in enumerate(codes) if i not in matched])

    def attach(self, *, user_id, product, template, item):
        try:
            self._attach(user_id=user_id, product=product, template=template, item=item)
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError('Код уже занят. Обновите поиск и выберите найденный товар.') from exc

    def _attach(self, *, user_id, product, template, item):
        entries = item.get('catalog_codes') or []
        if not entries: return
        # Serialize competing attachments to this product; GTIN also has a global per-owner unique constraint.
        self.db.scalar(select(CatalogProduct).where(CatalogProduct.id == product.id, CatalogProduct.user_id == user_id).with_for_update())
        barcode_values = [e['code'] for e in entries if e['kind'] == 'barcode']
        codes = normalize_codes(barcode_values)
        retailers = {e['code'].strip() for e in entries if e['kind'] == 'retailer'}
        if len(retailers) > 1: raise ValueError('Укажите один артикул магазина для предложения')
        if any(not e['code'].strip() or e['kind'] not in ('barcode','retailer') for e in entries):
            raise ValueError('Подтвердите тип каждого кода: штрихкод или артикул')
        variant = None
        variant_id = item.get('variant_id') or (item.get('variant_snapshot') or {}).get('variant_id')
        if variant_id:
            variant = self.db.scalar(select(CatalogVariant).where(CatalogVariant.id == variant_id, CatalogVariant.product_id == product.id, CatalogVariant.user_id == user_id, CatalogVariant.is_archived.is_(False)))
            if variant is None: raise ValueError('Выберите действующую фасовку перед добавлением кода')
        if codes:
            existing = self.db.scalars(select(CatalogVariantCode).where(CatalogVariantCode.user_id == user_id, CatalogVariantCode.gtin14.in_(codes))).all()
            ids = {c.variant_id for c in existing}
            if len(ids) > 1 or (variant and ids and ids != {variant.id}): raise ValueError('Штрихкоды относятся к разным фасовкам')
            if ids and variant is None:
                variant = self.db.scalar(select(CatalogVariant).where(CatalogVariant.id == next(iter(ids)), CatalogVariant.product_id == product.id, CatalogVariant.user_id == user_id, CatalogVariant.is_archived.is_(False)))
                if variant is None: raise ValueError('Штрихкод уже закреплён за другим товаром или архивной фасовкой')
            measurement = normalize_measurement(item)
            if variant and normalize_measurement(measurement_snapshot(variant)) != measurement:
                raise ValueError('Штрихкод относится к другой фасовке. Выберите найденный вариант.')
            if variant is None:
                variants = self.db.scalars(select(CatalogVariant).where(CatalogVariant.user_id == user_id, CatalogVariant.product_id == product.id, CatalogVariant.is_archived.is_(False))).all()
                matches = [v for v in variants if normalize_measurement(measurement_snapshot(v)) == measurement]
                if len(matches) > 1: raise ValueError('У товара несколько одинаковых фасовок. Выберите нужную для штрихкода.')
                variant = matches[0] if matches else CatalogVariant(user_id=user_id,product_id=product.id,name=product.name[:160],**measurement)
                if not matches: self.db.add(variant); self.db.flush()
            present = {c.gtin14 for c in existing}
            self.db.add_all([CatalogVariantCode(user_id=user_id,variant_id=variant.id,code=value,gtin14=key) for key,value in codes.items() if key not in present])
            self.db.flush()
            item['variant_id'] = variant.id
        if retailers:
            if not template.source_id: raise ValueError('Для артикула укажите магазин')
            code = next(iter(retailers))
            # Source lock prevents two simultaneous registrations assigning the same SKU differently.
            self.db.scalar(select(ItemSource).where(ItemSource.id == template.source_id, ItemSource.user_id == user_id).with_for_update())
            conflict = self.db.scalar(select(CatalogOfferIdentity).join(OperationItemTemplate, OperationItemTemplate.id == CatalogOfferIdentity.template_id).where(
                CatalogOfferIdentity.user_id == user_id, OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.source_id == template.source_id, CatalogOfferIdentity.retailer_code == code,
                CatalogOfferIdentity.template_id != template.id))
            if conflict: raise ValueError('Артикул этого магазина уже закреплён за другим предложением')
            mapping = self.db.get(CatalogOfferIdentity, template.id)
            if mapping and mapping.retailer_code and mapping.retailer_code != code:
                raise ValueError('У предложения уже другой артикул. Измените его в карточке товара.')
            if mapping is None:
                mapping = CatalogOfferIdentity(template_id=template.id,user_id=user_id)
                self.db.add(mapping)
            if mapping.variant_id and variant and mapping.variant_id != variant.id:
                raise ValueError('Артикул уже связан с другой фасовкой')
            mapping.retailer_code = code
            if variant: mapping.variant_id = variant.id
        self.db.flush()
