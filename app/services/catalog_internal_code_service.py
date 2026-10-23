"""Exact internal barcodes are scoped to one owner's store, never global GTINs."""
import re
from sqlalchemy import select
from app.db.models import CatalogOfferIdentity, CatalogProduct, OperationItemTemplate
from app.db.models.item_source import ItemSource


def normalize_internal_codes(values):
    codes = list(dict.fromkeys(str(value).strip() for value in values))
    if len(codes) > 100 or any(not re.fullmatch(r'[0-9]{1,32}', code) for code in codes):
        raise ValueError('Внутренний штрихкод: от 1 до 32 цифр; не более 100 кодов на предложение')
    return codes


class CatalogInternalCodeService:
    def __init__(self, db):
        self.db = db

    def matches(self, *, user_id, source_id, codes, include_archived=False):
        query = select(CatalogOfferIdentity, OperationItemTemplate, CatalogProduct).join(
            OperationItemTemplate, OperationItemTemplate.id == CatalogOfferIdentity.template_id).join(
            CatalogProduct, CatalogProduct.id == OperationItemTemplate.product_id).where(
            CatalogOfferIdentity.user_id == user_id, OperationItemTemplate.user_id == user_id,
            CatalogProduct.user_id == user_id, OperationItemTemplate.source_id == source_id,
            CatalogOfferIdentity.internal_codes.is_not(None))
        if not include_archived:
            query = query.where(OperationItemTemplate.is_archived.is_(False), CatalogProduct.is_archived.is_(False))
        requested = set(codes)
        return [(mapping, offer, product) for mapping, offer, product in self.db.execute(query)
                if requested.intersection(mapping.internal_codes or [])]

    def save(self, *, user_id, template, codes, append=False):
        codes = normalize_internal_codes(codes)
        if template.user_id != user_id or not template.source_id:
            raise ValueError('Для внутреннего штрихкода выберите магазин')
        # Serialize claims within a store; different stores may reuse identical digits.
        source = self.db.scalar(select(ItemSource).where(ItemSource.id == template.source_id,
            ItemSource.user_id == user_id, ItemSource.is_archived.is_(False)).with_for_update())
        if source is None:
            raise ValueError('Выберите действующий магазин для внутреннего штрихкода')
        # The receipt may already have staged an identity for a global barcode.
        self.db.flush()
        for mapping, offer, product in self.matches(user_id=user_id, source_id=source.id, codes=codes, include_archived=True):
            if offer.id == template.id:
                continue
            conflicts = sorted(set(codes).intersection(mapping.internal_codes or []))
            from app.services.receipt_code_service import ReceiptCodeConflict
            raise ReceiptCodeConflict('Внутренний штрихкод этого магазина закреплён за другим предложением',
                [{'kind':'internal', 'code':code} for code in conflicts],
                [dict(kind='internal', code=code, product_id=product.id, product_name=product.name,
                      archived=bool(product.is_archived or offer.is_archived)) for code in conflicts])
        mapping = self.db.get(CatalogOfferIdentity, template.id)
        if mapping is None:
            mapping = CatalogOfferIdentity(template_id=template.id, user_id=user_id)
            self.db.add(mapping)
        mapping.internal_codes = normalize_internal_codes([*(mapping.internal_codes or []), *codes]) if append else codes
        self.db.flush()
        return mapping
