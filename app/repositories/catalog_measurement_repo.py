from sqlalchemy import select, and_
from app.core.measurement import measurement_snapshot
from app.db.models import CatalogProduct, CatalogVariant, CatalogOfferIdentity, OperationItemTemplate


def offer_measurements(db, *, user_id, template_ids):
    """Resolve explicit source sizes, otherwise inherit the current product size."""
    if not template_ids:
        return {}
    rows = db.execute(
        select(OperationItemTemplate.id, CatalogProduct, CatalogVariant)
        .join(CatalogProduct, and_(
            CatalogProduct.id == OperationItemTemplate.product_id,
            CatalogProduct.user_id == user_id,
        ))
        .outerjoin(CatalogOfferIdentity, and_(
            CatalogOfferIdentity.template_id == OperationItemTemplate.id,
            CatalogOfferIdentity.user_id == user_id,
        ))
        .outerjoin(CatalogVariant, and_(
            CatalogVariant.id == CatalogOfferIdentity.variant_id,
            CatalogVariant.product_id == CatalogProduct.id,
            CatalogVariant.user_id == user_id,
            CatalogVariant.is_archived.is_(False),
        ))
        .where(OperationItemTemplate.user_id == user_id,
               OperationItemTemplate.id.in_(template_ids))
    )
    return {
        int(tid): {
            **measurement_snapshot(variant or product),
            'measurement_source': 'offer' if variant else 'product',
            'variant_id': variant.id if variant else None,
        }
        for tid, product, variant in rows
    }
