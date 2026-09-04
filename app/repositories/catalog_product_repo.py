from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import and_, exists, func, or_, select, update
from sqlalchemy.orm import Session

from app.db.models import (
    CatalogProduct,
    Category,
    CategoryGroup,
    ItemBrand,
    ItemSource,
    OperationItemPrice,
    OperationItemTemplate,
)


class CatalogProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        *,
        user_id: int,
        product_id: int,
        include_archived: bool = False,
    ) -> CatalogProduct | None:
        conditions = [
            CatalogProduct.user_id == user_id,
            CatalogProduct.id == product_id,
        ]
        if not include_archived:
            conditions.append(CatalogProduct.is_archived.is_(False))
        return self.db.scalar(select(CatalogProduct).where(*conditions))

    def list_by_ids(
        self,
        *,
        user_id: int,
        product_ids: Sequence[int],
        include_archived: bool = False,
    ) -> list[CatalogProduct]:
        ids = sorted({int(product_id) for product_id in product_ids})
        if not ids:
            return []
        conditions = [
            CatalogProduct.user_id == user_id,
            CatalogProduct.id.in_(ids),
        ]
        if not include_archived:
            conditions.append(CatalogProduct.is_archived.is_(False))
        return list(self.db.scalars(select(CatalogProduct).where(*conditions)))

    def list_exact_name(
        self,
        *,
        user_id: int,
        name_ci: str,
        include_archived: bool = False,
    ) -> list[CatalogProduct]:
        conditions = [
            CatalogProduct.user_id == user_id,
            CatalogProduct.name_ci == name_ci,
        ]
        if not include_archived:
            conditions.append(CatalogProduct.is_archived.is_(False))
        return list(
            self.db.scalars(
                select(CatalogProduct)
                .where(*conditions)
                .order_by(CatalogProduct.id.asc())
            )
        )

    def list_active(self, *, user_id: int) -> list[CatalogProduct]:
        return list(
            self.db.scalars(
                select(CatalogProduct)
                .where(
                    CatalogProduct.user_id == user_id,
                    CatalogProduct.is_archived.is_(False),
                )
                .order_by(CatalogProduct.name_ci.asc(), CatalogProduct.id.asc())
            )
        )

    def list(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        q: str | None,
        brand_id: int | None,
        category_id: int | None,
        include_archived: bool,
    ) -> tuple[list[CatalogProduct], int]:
        conditions = [CatalogProduct.user_id == user_id]
        if not include_archived:
            conditions.append(CatalogProduct.is_archived.is_(False))
        if brand_id is not None:
            conditions.append(CatalogProduct.brand_id == brand_id)
        if category_id is not None:
            conditions.append(CatalogProduct.category_id == category_id)
        search = " ".join((q or "").split())
        if search:
            like = f"%{search}%"
            offer_search_conditions = [
                OperationItemTemplate.product_id == CatalogProduct.id,
                OperationItemTemplate.user_id == user_id,
                or_(
                    OperationItemTemplate.name.ilike(like),
                    OperationItemTemplate.shop_name.ilike(like),
                ),
            ]
            if not include_archived:
                offer_search_conditions.append(
                    OperationItemTemplate.is_archived.is_(False)
                )
            conditions.append(
                or_(
                    CatalogProduct.name.ilike(like),
                    exists(
                        select(ItemBrand.id).where(
                            ItemBrand.id == CatalogProduct.brand_id,
                            ItemBrand.user_id == user_id,
                            ItemBrand.name.ilike(like),
                        )
                    ),
                    exists(
                        select(Category.id).where(
                            Category.id == CatalogProduct.category_id,
                            or_(
                                Category.user_id == user_id,
                                Category.user_id.is_(None),
                            ),
                            Category.name.ilike(like),
                        )
                    ),
                    exists(
                        select(OperationItemTemplate.id).where(
                            *offer_search_conditions
                        )
                    ),
                )
            )
        where = and_(*conditions)
        latest_use = (
            select(
                OperationItemTemplate.product_id.label("product_id"),
                func.max(OperationItemTemplate.last_used_at).label("last_used_at"),
                func.sum(OperationItemTemplate.use_count).label("use_count"),
            )
            .where(OperationItemTemplate.is_archived.is_(False))
            .group_by(OperationItemTemplate.product_id)
            .subquery()
        )
        items = list(
            self.db.scalars(
                select(CatalogProduct)
                .outerjoin(latest_use, latest_use.c.product_id == CatalogProduct.id)
                .where(where)
                .order_by(
                    CatalogProduct.is_archived.asc(),
                    latest_use.c.last_used_at.desc().nullslast(),
                    latest_use.c.use_count.desc().nullslast(),
                    CatalogProduct.name_ci.asc(),
                    CatalogProduct.id.asc(),
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        total = int(
            self.db.scalar(
                select(func.count()).select_from(CatalogProduct).where(where)
            )
            or 0
        )
        return items, total

    def create(
        self,
        *,
        user_id: int,
        name: str,
        name_ci: str,
        brand_id: int | None,
        category_id: int | None,
        image_id: int | None = None,
        flush: bool = True,
    ) -> CatalogProduct:
        product = CatalogProduct(
            user_id=user_id,
            name=name,
            name_ci=name_ci,
            brand_id=brand_id,
            category_id=category_id,
            image_id=image_id,
            is_archived=False,
        )
        self.db.add(product)
        if flush:
            self.db.flush()
        return product

    def list_offers(
        self,
        *,
        user_id: int,
        product_id: int,
        include_archived: bool = False,
    ) -> list[OperationItemTemplate]:
        return self.list_offers_for_products(
            user_id=user_id,
            product_ids=[product_id],
            include_archived=include_archived,
        )

    def list_offers_for_products(
        self,
        *,
        user_id: int,
        product_ids: Sequence[int],
        include_archived: bool = False,
    ) -> list[OperationItemTemplate]:
        ids = sorted({int(product_id) for product_id in product_ids})
        if not ids:
            return []
        conditions = [
            OperationItemTemplate.user_id == user_id,
            OperationItemTemplate.product_id.in_(ids),
        ]
        if not include_archived:
            conditions.append(OperationItemTemplate.is_archived.is_(False))
        return list(
            self.db.scalars(
                select(OperationItemTemplate)
                .where(*conditions)
                .order_by(
                    OperationItemTemplate.product_id.asc(),
                    OperationItemTemplate.use_count.desc(),
                    OperationItemTemplate.last_used_at.desc().nullslast(),
                    OperationItemTemplate.id.asc(),
                )
            )
        )

    def latest_prices_for_offers(
        self, *, offer_ids: Sequence[int]
    ) -> dict[int, OperationItemPrice]:
        ids = sorted({int(offer_id) for offer_id in offer_ids})
        if not ids:
            return {}
        rows = self.db.scalars(
            select(OperationItemPrice)
            .where(OperationItemPrice.template_id.in_(ids))
            .order_by(
                OperationItemPrice.template_id.asc(),
                OperationItemPrice.recorded_at.desc(),
                OperationItemPrice.id.desc(),
            )
        )
        result: dict[int, OperationItemPrice] = {}
        for row in rows:
            result.setdefault(int(row.template_id), row)
        return result

    def product_metadata(
        self, *, user_id: int, product_ids: Sequence[int]
    ) -> dict[int, dict]:
        ids = sorted({int(product_id) for product_id in product_ids})
        if not ids:
            return {}
        rows = self.db.execute(
            select(
                CatalogProduct.id,
                ItemBrand.name,
                ItemBrand.accent_color,
                ItemBrand.image_id,
                ItemBrand.is_archived,
                Category.name,
                Category.icon,
                CategoryGroup.accent_color,
            )
            .outerjoin(
                ItemBrand,
                and_(
                    ItemBrand.id == CatalogProduct.brand_id,
                    ItemBrand.user_id == user_id,
                ),
            )
            .outerjoin(
                Category,
                and_(
                    Category.id == CatalogProduct.category_id,
                    or_(Category.user_id == user_id, Category.user_id.is_(None)),
                ),
            )
            .outerjoin(
                CategoryGroup,
                and_(
                    CategoryGroup.id == Category.group_id,
                    CategoryGroup.user_id == user_id,
                ),
            )
            .where(
                CatalogProduct.user_id == user_id,
                CatalogProduct.id.in_(ids),
            )
        )
        return {
            int(product_id): {
                "brand_name": brand_name,
                "brand_accent_color": brand_accent_color,
                "brand_image_id": brand_image_id,
                "brand_is_archived": bool(brand_is_archived),
                "category_name": category_name,
                "category_icon": category_icon,
                "category_accent_color": category_accent_color,
            }
            for (
                product_id,
                brand_name,
                brand_accent_color,
                brand_image_id,
                brand_is_archived,
                category_name,
                category_icon,
                category_accent_color,
            ) in rows
        }

    def offer_source_metadata(
        self, *, user_id: int, offer_ids: Sequence[int]
    ) -> dict[int, dict]:
        ids = sorted({int(offer_id) for offer_id in offer_ids})
        if not ids:
            return {}
        rows = self.db.execute(
            select(
                OperationItemTemplate.id,
                ItemSource.id,
                ItemSource.name,
                ItemSource.image_id,
            )
            .outerjoin(
                ItemSource,
                and_(
                    ItemSource.id == OperationItemTemplate.source_id,
                    ItemSource.user_id == user_id,
                ),
            )
            .where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.id.in_(ids),
            )
        )
        return {
            int(offer_id): {
                "source_id": int(source_id) if source_id is not None else None,
                "source_name": source_name,
                "source_image_id": source_image_id,
            }
            for offer_id, source_id, source_name, source_image_id in rows
        }

    def reassign_offers(
        self,
        *,
        user_id: int,
        source_product_ids: Sequence[int],
        target_product_id: int,
    ) -> int:
        source_ids = sorted({int(product_id) for product_id in source_product_ids})
        if not source_ids:
            return 0
        result = self.db.execute(
            update(OperationItemTemplate)
            .where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.product_id.in_(source_ids),
            )
            .values(product_id=target_product_id)
        )
        self.db.flush()
        return int(result.rowcount or 0)

    def move_offer(
        self,
        *,
        user_id: int,
        product_id: int,
        offer_id: int,
        target_product_id: int,
    ) -> bool:
        result = self.db.execute(
            update(OperationItemTemplate)
            .where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.id == offer_id,
                OperationItemTemplate.product_id == product_id,
            )
            .values(product_id=target_product_id)
        )
        self.db.flush()
        return int(result.rowcount or 0) == 1

    def sync_offer_compatibility(
        self,
        *,
        user_id: int,
        product_id: int,
        brand_id: int | None,
        category_id: int | None,
        image_id: int | None,
        offer_ids: Sequence[int] | None = None,
    ) -> int:
        conditions = [
            OperationItemTemplate.user_id == user_id,
            OperationItemTemplate.product_id == product_id,
        ]
        if offer_ids is not None:
            ids = sorted({int(offer_id) for offer_id in offer_ids})
            if not ids:
                return 0
            conditions.append(OperationItemTemplate.id.in_(ids))
        result = self.db.execute(
            update(OperationItemTemplate)
            .where(*conditions)
            .values(
                brand_id=brand_id,
                last_category_id=category_id,
                image_id=image_id,
            )
        )
        self.db.flush()
        return int(result.rowcount or 0)

    def archive(self, *, product: CatalogProduct) -> None:
        product.is_archived = True
        self.db.flush()

    def archive_many(
        self, *, user_id: int, product_ids: Sequence[int]
    ) -> int:
        ids = sorted({int(product_id) for product_id in product_ids})
        if not ids:
            return 0
        result = self.db.execute(
            update(CatalogProduct)
            .where(
                CatalogProduct.user_id == user_id,
                CatalogProduct.id.in_(ids),
            )
            .values(is_archived=True)
        )
        self.db.flush()
        return int(result.rowcount or 0)

    def archive_offers(self, *, user_id: int, product_id: int) -> int:
        result = self.db.execute(
            update(OperationItemTemplate)
            .where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.product_id == product_id,
                OperationItemTemplate.is_archived.is_(False),
            )
            .values(is_archived=True)
        )
        self.db.flush()
        return int(result.rowcount or 0)
