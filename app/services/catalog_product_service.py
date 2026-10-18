from __future__ import annotations

import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import or_, select, update

from app.core.measurement import MEASUREMENT_FIELDS, measurement_snapshot, normalize_measurement
from app.core.cache import (
    invalidate_dashboard_analytics_cache,
    invalidate_item_templates_cache,
    invalidate_operations_cache,
    invalidate_plans_cache,
)
from app.db.models import CatalogProduct, Category, ItemBrand, CatalogPackageReplacement, CatalogVariant, CatalogOfferIdentity
from app.repositories.catalog_product_repo import CatalogProductRepository
from app.repositories.operation_item_template_repo import (
    OperationItemTemplateRepository,
)
from app.services.activity_service import ActivityService


class CatalogProductService:
    ACTIVITY_FIELDS = [
        *MEASUREMENT_FIELDS,
        "name",
        "brand_id",
        "category_id",
        "image_id",
        "is_archived",
    ]
    ACTIVITY_LABELS = {
        "sale_unit": "Единица продажи",
        "package_quantity": "Содержимое упаковки",
        "package_unit": "Единица содержимого",
        "name": "Название",
        "brand_id": "Бренд",
        "category_id": "Категория",
        "image_id": "Изображение",
        "is_archived": "Архив",
    }
    MONEY_Q = Decimal("0.01")

    def __init__(self, db):
        self.db = db
        self.repo = CatalogProductRepository(db)
        self.offer_repo = OperationItemTemplateRepository(db)
        self.activity = ActivityService(db)

    @staticmethod
    def _normalize_name(name: str) -> tuple[str, str]:
        normalized = unicodedata.normalize("NFKC", " ".join(str(name or "").split()))
        if not normalized:
            raise ValueError("Product name must not be empty")
        if len(normalized) > 160:
            raise ValueError("Product name must be at most 160 characters")
        return normalized, normalized.casefold()

    def _validate_brand_id(
        self, *, user_id: int, brand_id: int | None
    ) -> int | None:
        if brand_id is None:
            return None
        item = self.db.scalar(
            select(ItemBrand).where(
                ItemBrand.user_id == user_id,
                ItemBrand.id == brand_id,
                ItemBrand.is_archived.is_(False),
            )
        )
        if item is None:
            raise ValueError("Brand not found")
        return int(item.id)

    def _validate_category_id(
        self, *, user_id: int, category_id: int | None
    ) -> int | None:
        if category_id is None:
            return None
        item = self.db.scalar(
            select(Category).where(
                Category.id == category_id,
                or_(Category.user_id == user_id, Category.user_id.is_(None)),
            )
        )
        if item is None:
            raise ValueError("Category not found")
        return int(item.id)

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
        include_identifiers: bool = False,
    ) -> tuple[list[dict], int]:
        products, total = self.repo.list(
            user_id=user_id,
            page=page,
            page_size=page_size,
            q=q,
            brand_id=brand_id,
            category_id=category_id,
            include_archived=include_archived,
            include_identifiers=include_identifiers,
        )
        return (
            self._serialize_many(
                user_id=user_id,
                products=products,
                include_archived_offers=include_archived,
            ),
            total,
        )

    def get(
        self,
        *,
        user_id: int,
        product_id: int,
        include_archived: bool = False,
    ) -> dict:
        product = self.repo.get_by_id(
            user_id=user_id,
            product_id=product_id,
            include_archived=include_archived,
        )
        if product is None:
            raise LookupError("Catalog product not found")
        return self._serialize_many(
            user_id=user_id,
            products=[product],
            include_archived_offers=include_archived,
        )[0]

    def create(
        self,
        *,
        user_id: int,
        name: str,
        codes: dict | None = None,
        brand_id: int | None,
        category_id: int | None,
        sale_unit: str | None = None,
        package_quantity: Decimal | None = None,
        package_unit: str | None = None,
    ) -> dict:
        measurement = normalize_measurement({
            "sale_unit": sale_unit,
            "package_quantity": package_quantity,
            "package_unit": package_unit,
        })
        product = self.create_for_offer(
            user_id=user_id,
            name=name,
            brand_id=brand_id,
            category_id=category_id,
            measurement=measurement,
        )
        if codes:
            from app.services.catalog_identity_service import CatalogIdentityService
            CatalogIdentityService(self.db).save_product_codes(user_id=user_id, product_id=product.id, data=codes)
        self.db.commit()
        self._invalidate(user_id)
        return self.get(user_id=user_id, product_id=int(product.id))

    def create_for_offer(
        self,
        *,
        user_id: int,
        name: str,
        brand_id: int | None,
        category_id: int | None,
        image_id: int | None = None,
        record_activity: bool = True,
        measurement: dict | None = None,
    ) -> CatalogProduct:
        normalized_name, name_ci = self._normalize_name(name)
        product = self.repo.create(
            user_id=user_id,
            name=normalized_name,
            name_ci=name_ci,
            brand_id=self._validate_brand_id(user_id=user_id, brand_id=brand_id),
            category_id=self._validate_category_id(
                user_id=user_id,
                category_id=category_id,
            ),
            image_id=image_id,
        )
        for key, value in normalize_measurement(measurement or {}).items():
            setattr(product, key, value)
        if record_activity:
            self.activity.record_created(
                user_id=user_id,
                actor_user_id=user_id,
                entity_type="catalog_product",
                entity_id=int(product.id),
                title="Товар создан",
                metadata=ActivityService.snapshot(product, self.ACTIVITY_FIELDS),
            )
        return product

    # Transaction-friendly helper for receipt/template services. It deliberately
    # does not commit, so the product and its first offer remain atomic.
    def ensure_for_offer(
        self,
        *,
        user_id: int,
        offer,
        requested_product_id: int | None = None,
    ) -> CatalogProduct:
        current_product_id = getattr(offer, "product_id", None)
        if (
            requested_product_id is not None
            and current_product_id is not None
            and int(requested_product_id) != int(current_product_id)
        ):
            raise ValueError(
                "Offer already belongs to another product; use merge or detach"
            )
        product_id = requested_product_id or current_product_id
        if product_id is not None:
            product = self.repo.get_by_id(
                user_id=user_id,
                product_id=int(product_id),
                include_archived=True,
            )
            if product is None:
                raise ValueError("Catalog product not found")
            product.is_archived = False
        else:
            product = self.create_for_offer(
                user_id=user_id,
                name=offer.name,
                brand_id=getattr(offer, "brand_id", None),
                category_id=getattr(offer, "last_category_id", None),
                image_id=getattr(offer, "image_id", None),
            )
        offer.product_id = int(product.id)
        self.db.flush()
        self.repo.sync_offer_compatibility(
            user_id=user_id,
            product_id=int(product.id),
            brand_id=product.brand_id,
            category_id=product.category_id,
            image_id=product.image_id,
            offer_ids=[int(offer.id)],
        )
        return product

    # Alias kept explicit for callers that deal in the legacy template name.
    def ensure_for_template(
        self,
        *,
        user_id: int,
        template,
        requested_product_id: int | None = None,
    ) -> CatalogProduct:
        return self.ensure_for_offer(
            user_id=user_id,
            offer=template,
            requested_product_id=requested_product_id,
        )

    def find_compatible_exact_product(
        self,
        *,
        user_id: int,
        name: str,
        brand_id: int | None,
        category_id: int | None,
        source_id: int | None,
        shop_name: str | None,
    ) -> CatalogProduct | None:
        _, name_ci = self._normalize_name(name)
        products = [
            product
            for product in self.repo.list_exact_name(
                user_id=user_id,
                name_ci=name_ci,
            )
            if self._compatible_dimension(product.brand_id, brand_id)
            and self._compatible_dimension(product.category_id, category_id)
        ]
        if not products:
            return None
        offers = self.repo.list_offers_for_products(
            user_id=user_id,
            product_ids=[int(product.id) for product in products],
        )
        offers_by_product: dict[int, list] = defaultdict(list)
        for offer in offers:
            offers_by_product[int(offer.product_id)].append(offer)
        requested_source = self._source_key(
            source_id=source_id,
            shop_name=shop_name,
        )
        eligible = []
        for product in products:
            source_keys = {
                self._source_key(
                    source_id=offer.source_id,
                    shop_name=offer.shop_name,
                )
                for offer in offers_by_product.get(int(product.id), [])
            }
            if requested_source is not None and requested_source in source_keys:
                continue
            eligible.append(product)
        return eligible[0] if len(eligible) == 1 else None

    def update(
        self,
        *,
        user_id: int,
        product_id: int,
        updates: dict,
    ) -> dict:
        product = self.repo.get_by_id(user_id=user_id, product_id=product_id)
        if product is None:
            raise LookupError("Catalog product not found")
        measurement = normalize_measurement({
            **measurement_snapshot(product),
            **{key: updates[key] for key in MEASUREMENT_FIELDS if key in updates},
        })
        size_changed = measurement_snapshot(product) != measurement
        before = ActivityService.snapshot(product, self.ACTIVITY_FIELDS)
        for key, value in measurement.items():
            setattr(product, key, value)
        offers = self.repo.list_offers(
            user_id=user_id,
            product_id=product_id,
            include_archived=True,
        )
        previous_categories = {
            int(offer.id): offer.last_category_id for offer in offers
        }
        if "name" in updates:
            product.name, product.name_ci = self._normalize_name(updates["name"])
        if "brand_id" in updates:
            product.brand_id = self._validate_brand_id(
                user_id=user_id,
                brand_id=updates.get("brand_id"),
            )
        if "category_id" in updates:
            product.category_id = self._validate_category_id(
                user_id=user_id,
                category_id=updates.get("category_id"),
            )
        self.db.flush()
        self.repo.sync_offer_compatibility(
            user_id=user_id,
            product_id=product_id,
            brand_id=product.brand_id,
            category_id=product.category_id,
            image_id=product.image_id,
        )
        self._sync_linked_item_categories(
            user_id=user_id,
            previous_categories=previous_categories,
            category_id=product.category_id,
        )
        self.activity.record_updated(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="catalog_product",
            entity_id=int(product.id),
            before=before,
            after=ActivityService.snapshot(product, self.ACTIVITY_FIELDS),
            labels=self.ACTIVITY_LABELS,
            title="Размер товара изменён" if size_changed else "Товар изменён",
        )
        if updates.get("codes"):
            from app.services.catalog_identity_service import CatalogIdentityService
            CatalogIdentityService(self.db).save_product_codes(user_id=user_id, product_id=product.id, data=updates["codes"])
        self.db.commit()
        self._invalidate(user_id)
        return self.get(user_id=user_id, product_id=product_id)

    def archive(self, *, user_id: int, product_id: int) -> None:
        product = self.repo.get_by_id(user_id=user_id, product_id=product_id)
        if product is None:
            raise LookupError("Catalog product not found")
        self.repo.archive(product=product)
        archived_offers = self.repo.archive_offers(
            user_id=user_id,
            product_id=product_id,
        )
        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="catalog_product",
            entity_id=product_id,
            event_type="deleted",
            title="Товар архивирован",
            metadata={
                **ActivityService.snapshot(product, self.ACTIVITY_FIELDS),
                "archived_offers": archived_offers,
            },
        )
        self.db.commit()
        self._invalidate(user_id)

    def merge(
        self,
        *,
        user_id: int,
        target_product_id: int,
        source_product_ids: Sequence[int],
    ) -> dict:
        source_ids = list(dict.fromkeys(int(value) for value in source_product_ids))
        if target_product_id in source_ids:
            raise ValueError("Target product cannot be merged into itself")
        # Serialize merges with package confirmations/variant edits in stable ID order.
        list(self.db.scalars(select(CatalogProduct).where(CatalogProduct.user_id == user_id,
            CatalogProduct.id.in_([target_product_id, *source_ids])).order_by(CatalogProduct.id).with_for_update()))
        target = self.repo.get_by_id(
            user_id=user_id,
            product_id=target_product_id,
        )
        sources = self.repo.list_by_ids(
            user_id=user_id,
            product_ids=source_ids,
        )
        if target is None or len(sources) != len(source_ids):
            raise LookupError("One or more catalog products were not found")
        target_measurement = measurement_snapshot(target)
        def compatible(source):
            measurement = measurement_snapshot(source)
            if measurement == target_measurement:
                return True
            # A boxed item can be priced per piece or per pack in different stores.
            # Keep those units on the offers; never infer or convert package sizes.
            return (measurement["sale_unit"] in {"piece", "pack"}
                    and target_measurement["sale_unit"] in {"piece", "pack"}
                    and all(measurement[key] == target_measurement[key]
                            for key in ("package_quantity", "package_unit")))
        if any(not compatible(source) for source in sources):
            raise ValueError("Размеры упаковки или единицы веса различаются. Проверьте их в карточках товаров перед объединением.")
        source_by_id = {int(product.id): product for product in sources}
        ordered_sources = [source_by_id[product_id] for product_id in source_ids]
        if target.brand_id is None:
            source_brand_ids = {
                int(product.brand_id)
                for product in ordered_sources
                if product.brand_id is not None
            }
            if len(source_brand_ids) == 1:
                target.brand_id = source_brand_ids.pop()
        if target.category_id is None:
            source_category_ids = {
                int(product.category_id)
                for product in ordered_sources
                if product.category_id is not None
            }
            if len(source_category_ids) == 1:
                target.category_id = source_category_ids.pop()
        if target.image_id is None:
            image_source = next(
                (product for product in ordered_sources if product.image_id is not None),
                None,
            )
            if image_source is not None:
                target.image_id = image_source.image_id
                image_source.image_id = None
        self.db.flush()
        all_ids = [target_product_id, *source_ids]
        offers = self.repo.list_offers_for_products(
            user_id=user_id,
            product_ids=all_ids,
            include_archived=True,
        )
        previous_categories = {
            int(offer.id): offer.last_category_id for offer in offers
        }
        conflicts = self._source_conflicts(offers=offers)
        # Offers without their own variant inherit the product's defaults. Freeze
        # the old defaults before moving them to a target with a different unit.
        for source in ordered_sources:
            measurement = measurement_snapshot(source)
            if measurement == target_measurement:
                continue
            inherited = []
            for offer in offers:
                if offer.product_id != source.id:
                    continue
                identity = self.db.get(CatalogOfferIdentity, offer.id)
                mapped = self.db.get(CatalogVariant, identity.variant_id) if identity and identity.variant_id else None
                if mapped is None or mapped.is_archived:
                    inherited.append((offer, identity))
            if not inherited:
                continue
            variant = CatalogVariant(user_id=user_id, product_id=target_product_id,
                                     name=source.name[:160], **measurement)
            self.db.add(variant)
            self.db.flush()
            for offer, identity in inherited:
                if identity is None:
                    identity = CatalogOfferIdentity(user_id=user_id, template_id=offer.id)
                    self.db.add(identity)
                identity.variant_id = variant.id
            self.db.flush()
        reassigned = self.repo.reassign_offers(
            user_id=user_id,
            source_product_ids=source_ids,
            target_product_id=target_product_id,
        )
        self.repo.sync_offer_compatibility(
            user_id=user_id,
            product_id=target_product_id,
            brand_id=target.brand_id,
            category_id=target.category_id,
            image_id=target.image_id,
        )
        self._sync_linked_item_categories(
            user_id=user_id,
            previous_categories=previous_categories,
            category_id=target.category_id,
        )
        self.db.execute(update(CatalogVariant).where(CatalogVariant.user_id == user_id, CatalogVariant.product_id.in_(source_ids)).values(product_id=target_product_id))
        self.db.execute(update(CatalogPackageReplacement).where(CatalogPackageReplacement.user_id == user_id, CatalogPackageReplacement.product_id.in_(source_ids)).values(product_id=target_product_id))
        self.repo.archive_many(user_id=user_id, product_ids=source_ids)
        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="catalog_product",
            entity_id=target_product_id,
            event_type="merged",
            title="Товары объединены",
            metadata={
                "source_product_ids": source_ids,
                "reassigned_offers": reassigned,
            },
        )
        self.db.commit()
        self._invalidate(user_id)
        return {
            "product": self.get(user_id=user_id, product_id=target_product_id),
            "merged_product_ids": source_ids,
            "reassigned_offers": reassigned,
            "source_conflicts": conflicts,
        }

    def detach_offer(
        self,
        *,
        user_id: int,
        product_id: int,
        offer_id: int,
        updates: dict,
    ) -> dict:
        source = self.repo.get_by_id(user_id=user_id, product_id=product_id)
        if source is None:
            raise LookupError("Catalog product not found")
        offers = self.repo.list_offers(
            user_id=user_id,
            product_id=product_id,
            include_archived=False,
        )
        offer = next((item for item in offers if int(item.id) == offer_id), None)
        if offer is None:
            raise LookupError("Catalog product offer not found")
        previous_category_id = offer.last_category_id
        name = updates.get("name") if "name" in updates else offer.name
        brand_id = (
            updates.get("brand_id")
            if "brand_id" in updates
            else source.brand_id
        )
        category_id = (
            updates.get("category_id")
            if "category_id" in updates
            else source.category_id
        )
        product = self.create_for_offer(
            user_id=user_id,
            name=name,
            brand_id=brand_id,
            category_id=category_id,
            image_id=source.image_id,
            measurement=measurement_snapshot(source),
        )
        if not self.repo.move_offer(
            user_id=user_id,
            product_id=product_id,
            offer_id=offer_id,
            target_product_id=int(product.id),
        ):
            raise LookupError("Catalog product offer not found")
        # A detached offer belongs to a different product. Keep retailer metadata,
        # but do not move shared variant codes or leave a cross-product mapping.
        self.db.execute(update(CatalogOfferIdentity).where(CatalogOfferIdentity.user_id == user_id, CatalogOfferIdentity.template_id == offer_id).values(variant_id=None))
        self.repo.sync_offer_compatibility(
            user_id=user_id,
            product_id=int(product.id),
            brand_id=product.brand_id,
            category_id=product.category_id,
            image_id=product.image_id,
            offer_ids=[offer_id],
        )
        self._sync_linked_item_categories(
            user_id=user_id,
            previous_categories={offer_id: previous_category_id},
            category_id=product.category_id,
        )
        remaining = self.repo.list_offers(
            user_id=user_id,
            product_id=product_id,
            include_archived=False,
        )
        if not remaining:
            if source.image_id == product.image_id:
                source.image_id = None
            self.repo.archive(product=source)
            self.repo.sync_offer_compatibility(
                user_id=user_id,
                product_id=product_id,
                brand_id=source.brand_id,
                category_id=source.category_id,
                image_id=source.image_id,
            )
        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="catalog_product",
            entity_id=int(product.id),
            event_type="split",
            title="Предложение отделено в новый товар",
            metadata={
                "source_product_id": product_id,
                "offer_id": offer_id,
            },
        )
        self.db.commit()
        self._invalidate(user_id)
        return {
            "product": self.get(user_id=user_id, product_id=int(product.id)),
            "moved_offer_id": offer_id,
        }

    def list_merge_candidates(
        self,
        *,
        user_id: int,
        limit: int,
    ) -> tuple[list[dict], int]:
        products = self.repo.list_active(user_id=user_id)
        offers = self.repo.list_offers_for_products(
            user_id=user_id,
            product_ids=[int(product.id) for product in products],
        )
        offers_by_product: dict[int, list] = defaultdict(list)
        for offer in offers:
            offers_by_product[int(offer.product_id)].append(offer)
        groups: dict[str, list[CatalogProduct]] = defaultdict(list)
        for product in products:
            groups[str(product.name_ci)].append(product)

        candidates: list[tuple[str, list[CatalogProduct], list[str]]] = []
        for group in groups.values():
            clusters: list[list[CatalogProduct]] = []
            cluster_sources: list[set[tuple[str, int | str]]] = []
            for product in group:
                product_sources = self._offer_source_keys(
                    offers_by_product.get(int(product.id), [])
                )
                if not product_sources:
                    continue
                for index, cluster in enumerate(clusters):
                    if not product_sources.isdisjoint(cluster_sources[index]):
                        continue
                    if not all(
                        measurement_snapshot(item) == measurement_snapshot(product)
                        and self._compatible_dimension(item.brand_id, product.brand_id)
                        and self._compatible_dimension(
                            item.category_id,
                            product.category_id,
                        )
                        for item in cluster
                    ):
                        continue
                    cluster.append(product)
                    cluster_sources[index].update(product_sources)
                    break
                else:
                    clusters.append([product])
                    cluster_sources.append(set(product_sources))
            for cluster in clusters:
                if len(cluster) < 2:
                    continue
                brand_ids = {
                    int(product.brand_id)
                    for product in cluster
                    if product.brand_id is not None
                }
                category_ids = {
                    int(product.category_id)
                    for product in cluster
                    if product.category_id is not None
                }
                reasons = [
                    "exact_name",
                    "different_sources",
                    "same_brand" if len(brand_ids) == 1 and all(
                        product.brand_id is not None for product in cluster
                    ) else "compatible_brand",
                    "same_category" if len(category_ids) == 1 and all(
                        product.category_id is not None for product in cluster
                    ) else "compatible_category",
                ]
                candidates.append((cluster[0].name, cluster, reasons))

        total = len(candidates)
        selected = candidates[:limit]
        selected_products: list[CatalogProduct] = []
        for _, products_in_candidate, _ in selected:
            selected_products.extend(products_in_candidate)
        serialized = {
            int(item["id"]): item
            for item in self._serialize_many(
                user_id=user_id,
                products=list(
                    {
                        int(product.id): product
                        for product in selected_products
                    }.values()
                ),
            )
        }
        return (
            [
                {
                    "name": name,
                    "products": [
                        serialized[int(product.id)]
                        for product in products_in_candidate
                    ],
                    "reasons": reasons,
                }
                for name, products_in_candidate, reasons in selected
            ],
            total,
        )

    def _serialize_many(
        self,
        *,
        user_id: int,
        products: Sequence[CatalogProduct],
        include_archived_offers: bool = False,
    ) -> list[dict]:
        if not products:
            return []
        product_ids = [int(product.id) for product in products]
        offers = self.repo.list_offers_for_products(
            user_id=user_id,
            product_ids=product_ids,
            include_archived=include_archived_offers,
        )
        offers_by_product: dict[int, list] = defaultdict(list)
        for offer in offers:
            offers_by_product[int(offer.product_id)].append(offer)
        latest_prices = self.repo.latest_prices_for_offers(
            offer_ids=[int(offer.id) for offer in offers]
        )
        product_meta = self.repo.product_metadata(
            user_id=user_id,
            product_ids=product_ids,
        )
        source_meta = self.repo.offer_source_metadata(
            user_id=user_id,
            offer_ids=[int(offer.id) for offer in offers],
        )

        from app.repositories.catalog_measurement_repo import offer_measurements
        measurements = offer_measurements(self.db, user_id=user_id, template_ids=[int(o.id) for o in offers])
        result: list[dict] = []
        for product in products:
            product_offers = offers_by_product.get(int(product.id), [])
            meta = product_meta.get(int(product.id), {})
            offer_payloads = [
                self._serialize_offer(
                    product=product,
                    offer=offer,
                    latest_price=latest_prices.get(int(offer.id)),
                    source_meta=source_meta.get(int(offer.id), {}),
                    product_meta=meta,
                )
                for offer in product_offers
            ]
            for payload in offer_payloads:
                payload.update(measurements.get(payload['id'], {}))
            current_prices = [
                item["latest_unit_price"]
                for item in offer_payloads
                if item["latest_unit_price"] is not None
            ]
            source_keys = self._offer_source_keys(product_offers)
            last_used = [
                offer.last_used_at
                for offer in product_offers
                if offer.last_used_at is not None
            ]
            result.append(
                {
                    "id": int(product.id),
                    **measurement_snapshot(product),
                    "name": product.name,
                    "image_id": product.image_id,
                    "brand_id": product.brand_id,
                    "brand_name": meta.get("brand_name"),
                    "brand_accent_color": meta.get("brand_accent_color"),
                    "brand_image_id": meta.get("brand_image_id"),
                    "category_id": product.category_id,
                    "category_name": meta.get("category_name"),
                    "category_icon": meta.get("category_icon"),
                    "category_accent_color": meta.get("category_accent_color"),
                    "is_archived": bool(product.is_archived),
                    "offers_count": len(product_offers),
                    "sources_count": len(source_keys),
                    "use_count": sum(
                        int(offer.use_count or 0) for offer in product_offers
                    ),
                    "last_used_at": max(last_used) if last_used else None,
                    "min_unit_price": min(current_prices) if current_prices else None,
                    "max_unit_price": max(current_prices) if current_prices else None,
                    "offers": offer_payloads,
                    "created_at": product.created_at,
                    "updated_at": product.updated_at,
                }
            )
        return result

    def _serialize_offer(
        self,
        *,
        product: CatalogProduct,
        offer,
        latest_price,
        source_meta: dict,
        product_meta: dict,
    ) -> dict:
        latest_value = (
            Decimal(latest_price.unit_price).quantize(
                self.MONEY_Q,
                rounding=ROUND_HALF_UP,
            )
            if latest_price is not None
            else None
        )
        return {
            "id": int(offer.id),
            "product_id": int(product.id),
            "product_name": product.name,
            "product_image_id": product.image_id,
            "image_id": offer.image_id,
            "shop_name": offer.shop_name,
            "source_id": source_meta.get("source_id", offer.source_id),
            "source_name": source_meta.get("source_name") or offer.shop_name,
            "source_image_id": source_meta.get("source_image_id"),
            "name": offer.name,
            "use_count": int(offer.use_count or 0),
            "last_used_at": offer.last_used_at,
            "last_category_id": product.category_id,
            "brand_id": product.brand_id,
            "brand_name": product_meta.get("brand_name"),
            "brand_accent_color": product_meta.get("brand_accent_color"),
            "brand_is_archived": bool(
                product_meta.get("brand_is_archived", False)
            ),
            "brand_image_id": product_meta.get("brand_image_id"),
            "latest_unit_price": latest_value,
            "latest_price_date": (
                latest_price.recorded_at if latest_price is not None else None
            ),
        }

    @staticmethod
    def _compatible_dimension(left: int | None, right: int | None) -> bool:
        return left is None or right is None or int(left) == int(right)

    @staticmethod
    def _source_key(
        *, source_id: int | None, shop_name: str | None
    ) -> tuple[str, int | str] | None:
        if source_id is not None:
            return "id", int(source_id)
        normalized = " ".join(str(shop_name or "").split()).casefold()
        return ("name", normalized) if normalized else None

    def _offer_source_keys(self, offers: Sequence) -> set[tuple[str, int | str]]:
        return {
            key
            for offer in offers
            if (
                key := self._source_key(
                    source_id=offer.source_id,
                    shop_name=offer.shop_name,
                )
            )
            is not None
        }

    def _source_conflicts(self, *, offers: Sequence) -> list[dict]:
        grouped: dict[tuple[str, int | str] | None, list] = defaultdict(list)
        for offer in offers:
            grouped[
                self._source_key(
                    source_id=offer.source_id,
                    shop_name=offer.shop_name,
                )
            ].append(offer)
        conflicts = []
        for key, grouped_offers in grouped.items():
            product_ids = {int(offer.product_id) for offer in grouped_offers}
            if key is None or len(product_ids) < 2:
                continue
            conflicts.append(
                {
                    "source_id": (
                        int(grouped_offers[0].source_id)
                        if grouped_offers[0].source_id is not None
                        else None
                    ),
                    "source_name": grouped_offers[0].shop_name,
                    "offer_ids": [int(offer.id) for offer in grouped_offers],
                }
            )
        return conflicts

    def _sync_linked_item_categories(
        self,
        *,
        user_id: int,
        previous_categories: dict[int, int | None],
        category_id: int | None,
    ) -> None:
        for offer_id, previous_category_id in previous_categories.items():
            if previous_category_id == category_id:
                continue
            self.offer_repo.update_linked_receipt_item_category(
                user_id=user_id,
                template_id=offer_id,
                previous_category_id=previous_category_id,
                category_id=category_id,
            )

    @staticmethod
    def _invalidate(user_id: int) -> None:
        invalidate_item_templates_cache(user_id)
        invalidate_operations_cache(user_id)
        invalidate_plans_cache(user_id)
        invalidate_dashboard_analytics_cache(user_id)
