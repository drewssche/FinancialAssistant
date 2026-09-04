from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.cache import (
    build_item_templates_cache_key,
    get_json,
    get_namespace_ttl_seconds,
    invalidate_dashboard_analytics_cache,
    invalidate_item_templates_cache,
    invalidate_operations_cache,
    invalidate_plans_cache,
    set_json,
)
from app.db.models import Category
from app.repositories.catalog_product_repo import CatalogProductRepository
from app.repositories.item_brand_repo import ItemBrandRepository
from app.repositories.operation_repo import OperationRepository
from app.services.activity_service import ActivityService
from app.services.catalog_product_service import CatalogProductService
from app.services.item_source_service import ItemSourceService


MONEY_Q = Decimal("0.01")


class OperationItemTemplateService:
    ACTIVITY_FIELDS = [
        "shop_name",
        "source_id",
        "name",
        "last_category_id",
        "brand_id",
        "image_id",
        "product_id",
        "use_count",
        "is_archived",
        "last_used_at",
    ]
    ACTIVITY_LABELS = {
        "shop_name": "Источник",
        "source_id": "Источник",
        "name": "Название",
        "last_category_id": "Категория",
        "brand_id": "Бренд",
        "image_id": "Изображение",
        "product_id": "Товар",
        "use_count": "Использований",
        "is_archived": "Архив",
        "last_used_at": "Последнее использование",
    }

    def __init__(self, db: Session, repo: OperationRepository):
        self.db = db
        self.repo = repo
        self.brand_repo = ItemBrandRepository(db)
        self.product_repo = CatalogProductRepository(db)
        self.products = CatalogProductService(db)
        self.source_service = ItemSourceService(db)
        self.activity = ActivityService(db)

    def list_item_templates(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        q: str | None,
        brand_id: int | None = None,
    ) -> tuple[list[dict], int]:
        cache_key = build_item_templates_cache_key(
            user_id=user_id,
            view="list",
            page=page,
            page_size=page_size,
            q=q,
            brand_id=brand_id,
        )
        cached = get_json(cache_key)
        if cached is not None:
            return cached["items"], int(cached["total"])
        templates, total = self.repo.list_item_templates(
            user_id=user_id,
            page=page,
            page_size=page_size,
            q=q,
            brand_id=brand_id,
        )
        latest_prices = self.repo.get_latest_prices_for_templates(template_ids=[int(item.id) for item in templates])
        brand_meta = self.brand_repo.brand_meta_for_templates(
            user_id=user_id,
            template_ids=[int(item.id) for item in templates],
        )
        payload = []
        for item in templates:
            latest = latest_prices.get(int(item.id))
            payload.append(
                {
                    "id": int(item.id),
                    "product_id": item.product_id,
                    "image_id": item.image_id,
                    "shop_name": item.shop_name,
                    "name": item.name,
                    "use_count": int(item.use_count or 0),
                    "last_used_at": item.last_used_at,
                    "last_category_id": item.last_category_id,
                    **brand_meta.get(
                        int(item.id),
                        {
                            "brand_id": None,
                            "brand_name": None,
                            "brand_accent_color": None,
                            "brand_is_archived": False,
                            "brand_image_id": None,
                            "source_id": item.source_id,
                            "source_name": item.shop_name,
                            "source_image_id": None,
                            "product_id": item.product_id,
                            "product_name": None,
                            "product_image_id": None,
                        },
                    ),
                    "latest_unit_price": self._money(latest.unit_price) if latest else None,
                    "latest_price_date": latest.recorded_at if latest else None,
                }
            )
        set_json(
            cache_key,
            {"items": payload, "total": total},
            ttl_seconds=get_namespace_ttl_seconds("item_templates"),
        )
        return payload, total

    def list_item_template_prices(
        self,
        *,
        user_id: int,
        template_id: int,
        limit: int = 200,
    ) -> list[dict]:
        template = self.repo.get_item_template_by_id(user_id=user_id, template_id=template_id)
        if not template:
            raise LookupError("Item template not found")
        self.repo.cleanup_duplicate_item_template_prices(template_id=template_id)
        self.db.commit()
        cache_key = build_item_templates_cache_key(
            user_id=user_id,
            view="prices",
            template_id=template_id,
            limit=limit,
        )
        cached = get_json(cache_key)
        if cached is not None:
            return cached["items"]
        rows = self.repo.list_item_prices(template_id=template_id, limit=limit)
        payload = [
            {
                "id": int(row.id),
                "unit_price": self._money(row.unit_price),
                "recorded_at": row.recorded_at,
                "source_operation_id": row.source_operation_id,
            }
            for row in rows
        ]
        set_json(
            cache_key,
            {"items": payload},
            ttl_seconds=get_namespace_ttl_seconds("item_templates"),
        )
        return payload

    def delete_item_template_price(
        self,
        *,
        user_id: int,
        template_id: int,
        price_id: int,
    ) -> dict:
        item = self.repo.get_item_template_by_id(user_id=user_id, template_id=template_id)
        if not item:
            raise LookupError("Item template not found")
        price = self.repo.get_item_template_price(template_id=template_id, price_id=price_id)
        if not price:
            raise LookupError("Item template price not found")
        metadata = {
            "unit_price": str(self._money(price.unit_price)),
            "recorded_at": price.recorded_at.isoformat(),
            "source_operation_id": price.source_operation_id,
        }
        self.repo.delete_item_template_price(row=price)
        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="item_template",
            entity_id=int(item.id),
            event_type="price_deleted",
            title="Цена позиции удалена",
            metadata=metadata,
        )
        self.db.commit()
        invalidate_item_templates_cache(user_id)
        return self._serialize_item_template(item)

    def create_item_template(
        self,
        *,
        user_id: int,
        shop_name: str | None,
        source_id: int | None,
        name: str,
        last_category_id: int | None,
        brand_id: int | None,
        latest_unit_price: Decimal | None,
        latest_price_date: date | None = None,
        product_id: int | None = None,
    ) -> dict:
        source = self.source_service.resolve(
            user_id=user_id,
            source_id=source_id,
            shop_name=shop_name,
        )
        normalized_shop, normalized_name = self._normalize_item_template_fields(
            shop_name=source.name if source is not None else shop_name,
            name=name,
        )
        shop_name_ci = normalized_shop.casefold() if normalized_shop else None
        name_ci = normalized_name.casefold()
        validated_category_id = self._validate_category_id(user_id=user_id, category_id=last_category_id)
        validated_brand_id = self._validate_brand_id(user_id=user_id, brand_id=brand_id)
        existing = self.repo.get_item_template_by_name_ci(
            user_id=user_id,
            name_ci=name_ci,
            shop_name_ci=shop_name_ci,
            include_archived=True,
        )
        item = existing
        product = self._resolve_catalog_product(
            user_id=user_id,
            product_id=product_id,
            name=normalized_name,
            brand_id=validated_brand_id,
            category_id=validated_category_id,
            existing_template=item,
        )
        if product_id is None and item is not None:
            if validated_category_id is not None:
                product.category_id = validated_category_id
            if validated_brand_id is not None:
                product.brand_id = validated_brand_id
        resolved_category_id = product.category_id
        resolved_brand_id = product.brand_id
        previous_brand_id = item.brand_id if item is not None else None
        if not item:
            item = self.repo.create_item_template(
                user_id=user_id,
                shop_name=normalized_shop,
                shop_name_ci=shop_name_ci,
                source_id=int(source.id) if source is not None else None,
                name=normalized_name,
                name_ci=name_ci,
                last_category_id=resolved_category_id,
                brand_id=resolved_brand_id,
                product_id=int(product.id),
            )
            self.activity.record_created(
                user_id=user_id,
                actor_user_id=user_id,
                entity_type="item_template",
                entity_id=int(item.id),
                title="Позиция каталога создана",
                metadata=ActivityService.snapshot(item, self.ACTIVITY_FIELDS),
            )
        else:
            before_activity = ActivityService.snapshot(item, self.ACTIVITY_FIELDS)
            item.is_archived = False
            if item.shop_name != normalized_shop:
                item.shop_name = normalized_shop
                item.shop_name_ci = shop_name_ci
            item.source_id = int(source.id) if source is not None else None
            item.product_id = int(product.id)
            if item.name != normalized_name:
                item.name = normalized_name
                item.name_ci = name_ci
            if resolved_category_id is not None:
                item.last_category_id = resolved_category_id
            if resolved_brand_id is not None:
                item.brand_id = resolved_brand_id
            self.db.flush()
            self.activity.record_updated(
                user_id=user_id,
                actor_user_id=user_id,
                entity_type="item_template",
                entity_id=int(item.id),
                before=before_activity,
                after=ActivityService.snapshot(item, self.ACTIVITY_FIELDS),
                labels=self.ACTIVITY_LABELS,
                title="Позиция каталога восстановлена",
            )
        self._sync_product_compatibility(product=product)
        if latest_unit_price is not None:
            next_price = self._money(latest_unit_price)
            recorded_at = latest_price_date or date.today()
            price_added = not self.repo.has_item_template_price(
                template_id=int(item.id),
                unit_price=next_price,
                recorded_at=recorded_at,
            )
            if price_added:
                self.repo.add_item_template_price(
                    template_id=int(item.id),
                    unit_price=next_price,
                    recorded_at=recorded_at,
                    source_operation_id=None,
                )
                self.activity.record(
                    user_id=user_id,
                    actor_user_id=user_id,
                    entity_type="item_template",
                    entity_id=int(item.id),
                    event_type="price_added",
                    title="Цена позиции добавлена",
                    metadata={"unit_price": str(next_price), "recorded_at": recorded_at.isoformat()},
                )
        self.db.commit()
        invalidate_item_templates_cache(user_id)
        if item is existing and previous_brand_id != item.brand_id:
            invalidate_operations_cache(user_id)
            invalidate_plans_cache(user_id)
            invalidate_dashboard_analytics_cache(user_id)
        return self._serialize_item_template(item)

    def update_item_template(
        self,
        *,
        user_id: int,
        template_id: int,
        updates: dict,
    ) -> dict:
        item = self.repo.get_item_template_by_id(user_id=user_id, template_id=template_id)
        if not item:
            raise LookupError("Item template not found")
        before_activity = ActivityService.snapshot(item, self.ACTIVITY_FIELDS)
        if "source_id" in updates:
            requested_source_id = updates.get("source_id")
            requested_shop = updates.get("shop_name")
        else:
            requested_source_id = None
            requested_shop = updates["shop_name"] if "shop_name" in updates else item.shop_name
        source = self.source_service.resolve(
            user_id=user_id,
            source_id=requested_source_id,
            shop_name=requested_shop,
            unchanged_source_id=item.source_id,
        )
        next_shop = source.name if source is not None else requested_shop
        next_name = updates["name"] if "name" in updates else item.name
        normalized_shop, normalized_name = self._normalize_item_template_fields(shop_name=next_shop, name=next_name)
        shop_name_ci = normalized_shop.casefold() if normalized_shop else None
        name_ci = normalized_name.casefold()

        duplicate = self.repo.get_item_template_by_name_ci(
            user_id=user_id,
            name_ci=name_ci,
            shop_name_ci=shop_name_ci,
            include_archived=True,
        )
        if duplicate and int(duplicate.id) != int(item.id):
            raise ValueError("Template with same source and name already exists")

        product = self._resolve_catalog_product(
            user_id=user_id,
            product_id=None,
            name=normalized_name,
            brand_id=item.brand_id,
            category_id=item.last_category_id,
            existing_template=item,
        )

        item.shop_name = normalized_shop
        item.shop_name_ci = shop_name_ci
        item.source_id = int(source.id) if source is not None else None
        item.name = normalized_name
        item.name_ci = name_ci
        previous_category_id = item.last_category_id
        if "last_category_id" in updates:
            product.category_id = self._validate_category_id(
                user_id=user_id,
                category_id=updates.get("last_category_id"),
            )
        if "brand_id" in updates:
            product.brand_id = self._validate_brand_id(
                user_id=user_id,
                brand_id=updates.get("brand_id"),
                unchanged_brand_id=item.brand_id,
            )
        item.product_id = int(product.id)
        self._sync_product_compatibility(product=product)
        if "shop_name" in updates or "source_id" in updates or "name" in updates:
            self.repo.update_linked_receipt_item_identity(
                user_id=user_id,
                template_id=int(item.id),
                shop_name=normalized_shop,
                name=normalized_name,
            )
        if "last_category_id" in updates:
            self.repo.update_linked_receipt_item_category(
                user_id=user_id,
                template_id=int(item.id),
                previous_category_id=previous_category_id,
                category_id=product.category_id,
            )
        self.db.flush()

        latest_unit_price = updates.get("latest_unit_price")
        if latest_unit_price is not None:
            next_price = self._money(latest_unit_price)
            recorded_at = updates.get("latest_price_date") or date.today()
            price_added = not self.repo.has_item_template_price(
                template_id=int(item.id),
                unit_price=next_price,
                recorded_at=recorded_at,
            )
            if price_added:
                self.repo.add_item_template_price(
                    template_id=int(item.id),
                    unit_price=next_price,
                    recorded_at=recorded_at,
                    source_operation_id=None,
                )
                self.activity.record(
                    user_id=user_id,
                    actor_user_id=user_id,
                    entity_type="item_template",
                    entity_id=int(item.id),
                    event_type="price_added",
                    title="Цена позиции добавлена",
                    metadata={"unit_price": str(next_price), "recorded_at": recorded_at.isoformat()},
                )
        self.activity.record_updated(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="item_template",
            entity_id=int(item.id),
            before=before_activity,
            after=ActivityService.snapshot(item, self.ACTIVITY_FIELDS),
            labels=self.ACTIVITY_LABELS,
            title="Позиция каталога изменена",
        )
        self.db.commit()
        invalidate_item_templates_cache(user_id)
        if "shop_name" in updates or "source_id" in updates or "name" in updates or "last_category_id" in updates or "brand_id" in updates:
            invalidate_operations_cache(user_id)
            invalidate_plans_cache(user_id)
            invalidate_dashboard_analytics_cache(user_id)
        return self._serialize_item_template(item)

    def bulk_update_item_template_brand(
        self,
        *,
        user_id: int,
        template_ids: list[int],
        brand_id: int | None,
    ) -> int:
        if any(int(template_id) <= 0 for template_id in template_ids):
            raise ValueError("Template ids must be positive")
        normalized_ids = list(dict.fromkeys(int(template_id) for template_id in template_ids))

        # Resolve every user-scoped dependency before the first mutation so a
        # malformed batch cannot leave a partially updated catalog behind.
        validated_brand_id = self._validate_brand_id(user_id=user_id, brand_id=brand_id)
        items = self.repo.list_item_templates_by_ids(
            user_id=user_id,
            template_ids=normalized_ids,
        )
        if len(items) != len(normalized_ids):
            raise LookupError("One or more item templates were not found")

        updated_count = 0
        touched_products = {}
        for item in items:
            if item.brand_id == validated_brand_id:
                continue
            before_activity = ActivityService.snapshot(item, self.ACTIVITY_FIELDS)
            product = self._resolve_catalog_product(
                user_id=user_id,
                product_id=None,
                name=item.name,
                brand_id=item.brand_id,
                category_id=item.last_category_id,
                existing_template=item,
            )
            product.brand_id = validated_brand_id
            touched_products[int(product.id)] = product
            item.brand_id = validated_brand_id
            self.activity.record_updated(
                user_id=user_id,
                actor_user_id=user_id,
                entity_type="item_template",
                entity_id=int(item.id),
                before=before_activity,
                after=ActivityService.snapshot(item, self.ACTIVITY_FIELDS),
                labels=self.ACTIVITY_LABELS,
                title="Бренд позиции каталога изменён",
                metadata={"bulk": True},
            )
            updated_count += 1

        for product in touched_products.values():
            self._sync_product_compatibility(product=product)

        self.db.commit()
        if updated_count:
            invalidate_item_templates_cache(user_id)
            invalidate_operations_cache(user_id)
            invalidate_plans_cache(user_id)
            invalidate_dashboard_analytics_cache(user_id)
        return updated_count

    def delete_item_template(self, *, user_id: int, template_id: int) -> None:
        item = self.repo.get_item_template_by_id(user_id=user_id, template_id=template_id)
        if not item:
            raise LookupError("Item template not found")
        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="item_template",
            entity_id=int(item.id),
            event_type="deleted",
            title="Позиция каталога удалена",
            metadata=ActivityService.snapshot(item, self.ACTIVITY_FIELDS),
        )
        deleted = self.repo.archive_item_template(user_id=user_id, template_id=template_id)
        if not deleted:
            raise LookupError("Item template not found")
        self.db.commit()
        invalidate_item_templates_cache(user_id)

    def delete_all_item_templates(self, *, user_id: int) -> int:
        deleted = self.repo.archive_all_item_templates(user_id=user_id)
        self.db.commit()
        invalidate_item_templates_cache(user_id)
        return deleted

    def resolve_templates_and_prices(
        self,
        *,
        user_id: int,
        operation_id: int,
        operation_date: date,
        category_id: int | None,
        normalized_items: list[dict],
    ) -> list[dict]:
        storage_items: list[dict] = []
        self._validate_receipt_brand_ids(user_id=user_id, items=normalized_items)
        self._validate_receipt_category_ids(
            user_id=user_id,
            items=normalized_items,
            fallback_category_id=category_id,
        )
        self._ensure_item_sources(user_id=user_id, items=normalized_items)
        key_order: list[tuple[str, str | None]] = []
        sample_by_key: dict[tuple[str, str | None], dict] = {}
        for item in normalized_items:
            name_ci = item["name"].casefold()
            shop_name = item.get("shop_name")
            shop_name_ci = shop_name.casefold() if shop_name else None
            key = (name_ci, shop_name_ci)
            if key not in key_order:
                key_order.append(key)
                sample_by_key[key] = item

        existing_templates = self.repo.list_item_templates_for_names_ci(
            user_id=user_id,
            names_ci=[name_ci for name_ci, _ in key_order],
            include_archived=True,
        )
        template_by_key: dict[tuple[str, str | None], object] = {}
        for template in existing_templates:
            template_by_key[(str(template.name_ci), template.shop_name_ci)] = template
        self._apply_explicit_template_links(
            user_id=user_id,
            items=normalized_items,
            template_by_key=template_by_key,
        )
        self._apply_explicit_product_links(
            user_id=user_id,
            items=normalized_items,
            template_by_key=template_by_key,
        )

        created_templates = []
        for name_ci, shop_name_ci in key_order:
            key = (name_ci, shop_name_ci)
            if key in template_by_key:
                continue
            matched_item = sample_by_key.get(key)
            if not matched_item:
                continue
            requested_product_id = matched_item.get("product_id")
            if requested_product_id is not None:
                product = self.product_repo.get_by_id(
                    user_id=user_id,
                    product_id=int(requested_product_id),
                )
                if product is None:
                    raise ValueError("Catalog product not found")
            else:
                product = self.products.create_for_offer(
                    user_id=user_id,
                    name=matched_item["name"],
                    brand_id=matched_item.get("brand_id"),
                    category_id=matched_item.get("category_id") or category_id,
                )
            template = self.repo.create_item_template(
                user_id=user_id,
                shop_name=matched_item.get("shop_name"),
                shop_name_ci=shop_name_ci,
                source_id=matched_item.get("source_id"),
                name=matched_item["name"],
                name_ci=name_ci,
                last_category_id=product.category_id,
                brand_id=product.brand_id,
                product_id=int(product.id),
                flush=False,
            )
            template_by_key[key] = template
            created_templates.append(template)
        if created_templates:
            self.db.flush()

        latest_price_rows = self.repo.get_latest_prices_for_templates(
            template_ids=[int(template.id) for template in template_by_key.values()],
        )
        latest_price_by_template: dict[int, Decimal] = {
            int(template_id): self._money(row.unit_price)
            for template_id, row in latest_price_rows.items()
        }
        existing_price_values: dict[int, set[Decimal]] = {}
        for template in template_by_key.values():
            template_id = int(template.id)
            existing_price_values[template_id] = {
                self._money(row.unit_price)
                for row in self.repo.list_item_prices(template_id=template_id, limit=500)
            }
        price_rows: list[dict] = []
        for item in normalized_items:
            shop_name = item.get("shop_name")
            shop_name_ci = shop_name.casefold() if shop_name else None
            name = item["name"]
            name_ci = name.casefold()
            template = template_by_key.get((name_ci, shop_name_ci))
            if not template:
                continue
            product = self.products.ensure_for_template(
                user_id=user_id,
                template=template,
            )
            previous_categories = self._apply_receipt_product_metadata(
                user_id=user_id,
                product=product,
                item=item,
                fallback_category_id=category_id,
            )
            template.is_archived = False
            if template.name != name:
                template.name = name
            if template.shop_name != shop_name:
                template.shop_name = shop_name
                template.shop_name_ci = shop_name_ci
            if "source_id" in item:
                template.source_id = item.get("source_id")
            self._sync_product_compatibility(product=product)
            if previous_categories is not None:
                self.products._sync_linked_item_categories(
                    user_id=user_id,
                    previous_categories=previous_categories,
                    category_id=product.category_id,
                )
            self.repo.touch_item_template(
                item=template,
                last_category_id=product.category_id,
                flush=False,
            )
            template_id = int(template.id)
            price_history_unit_price = self._receipt_item_price_for_history(item)
            if (
                price_history_unit_price is not None
                and price_history_unit_price not in existing_price_values.setdefault(template_id, set())
            ):
                price_rows.append(
                    {
                        "template_id": template_id,
                        "unit_price": price_history_unit_price,
                        "recorded_at": operation_date,
                        "source_operation_id": operation_id,
                    }
                )
                existing_price_values[template_id].add(price_history_unit_price)
                latest_price_by_template[template_id] = price_history_unit_price
            storage_items.append(
                {
                    **item,
                    "template_id": template_id,
                    "product_id": int(product.id),
                }
            )
        if price_rows:
            self.repo.add_item_template_prices_bulk(rows=price_rows)
        else:
            self.db.flush()
        return storage_items

    def sync_templates_from_receipt_items(
        self,
        *,
        user_id: int,
        category_id: int | None,
        normalized_items: list[dict],
        recorded_at: date | None = None,
    ) -> list[dict]:
        if not normalized_items:
            return []
        self._validate_receipt_brand_ids(user_id=user_id, items=normalized_items)
        self._validate_receipt_category_ids(
            user_id=user_id,
            items=normalized_items,
            fallback_category_id=category_id,
        )
        self._ensure_item_sources(user_id=user_id, items=normalized_items)

        key_order: list[tuple[str, str | None]] = []
        sample_by_key: dict[tuple[str, str | None], dict] = {}
        for item in normalized_items:
            name_ci = item["name"].casefold()
            shop_name = item.get("shop_name")
            shop_name_ci = shop_name.casefold() if shop_name else None
            key = (name_ci, shop_name_ci)
            if key not in sample_by_key:
                key_order.append(key)
                sample_by_key[key] = item

        existing_templates = self.repo.list_item_templates_for_names_ci(
            user_id=user_id,
            names_ci=[name_ci for name_ci, _ in key_order],
            include_archived=True,
        )
        template_by_key: dict[tuple[str, str | None], object] = {}
        for template in existing_templates:
            template_by_key[(str(template.name_ci), template.shop_name_ci)] = template
        self._apply_explicit_template_links(
            user_id=user_id,
            items=normalized_items,
            template_by_key=template_by_key,
        )
        self._apply_explicit_product_links(
            user_id=user_id,
            items=normalized_items,
            template_by_key=template_by_key,
        )

        created_templates = []
        for name_ci, shop_name_ci in key_order:
            key = (name_ci, shop_name_ci)
            if key in template_by_key:
                continue
            matched_item = sample_by_key[key]
            requested_product_id = matched_item.get("product_id")
            if requested_product_id is not None:
                product = self.product_repo.get_by_id(
                    user_id=user_id,
                    product_id=int(requested_product_id),
                )
                if product is None:
                    raise ValueError("Catalog product not found")
            else:
                product = self.products.create_for_offer(
                    user_id=user_id,
                    name=matched_item["name"],
                    brand_id=matched_item.get("brand_id"),
                    category_id=matched_item.get("category_id") or category_id,
                )
            template = self.repo.create_item_template(
                user_id=user_id,
                shop_name=matched_item.get("shop_name"),
                shop_name_ci=shop_name_ci,
                source_id=matched_item.get("source_id"),
                name=matched_item["name"],
                name_ci=name_ci,
                last_category_id=product.category_id,
                brand_id=product.brand_id,
                product_id=int(product.id),
                flush=False,
            )
            template_by_key[key] = template
            created_templates.append(template)
        if created_templates:
            self.db.flush()

        existing_price_values: dict[int, set[Decimal]] = {}
        for template in template_by_key.values():
            template_id = int(template.id)
            existing_price_values[template_id] = {
                self._money(row.unit_price)
                for row in self.repo.list_item_prices(template_id=template_id, limit=500)
            }

        price_rows: list[dict] = []
        resolved_items: list[dict] = []
        effective_date = recorded_at or date.today()
        for item in normalized_items:
            shop_name = item.get("shop_name")
            shop_name_ci = shop_name.casefold() if shop_name else None
            template = template_by_key.get((item["name"].casefold(), shop_name_ci))
            if not template:
                continue
            product = self.products.ensure_for_template(
                user_id=user_id,
                template=template,
            )
            previous_categories = self._apply_receipt_product_metadata(
                user_id=user_id,
                product=product,
                item=item,
                fallback_category_id=category_id,
            )
            template.is_archived = False
            if "source_id" in item:
                template.source_id = item.get("source_id")
            self._sync_product_compatibility(product=product)
            if previous_categories is not None:
                self.products._sync_linked_item_categories(
                    user_id=user_id,
                    previous_categories=previous_categories,
                    category_id=product.category_id,
                )
            template_id = int(template.id)
            resolved_items.append(
                {
                    **item,
                    "template_id": template_id,
                    "product_id": int(product.id),
                }
            )
            price_history_unit_price = self._receipt_item_price_for_history(item)
            if (
                price_history_unit_price is not None
                and price_history_unit_price not in existing_price_values.setdefault(template_id, set())
            ):
                price_rows.append(
                    {
                        "template_id": template_id,
                        "unit_price": price_history_unit_price,
                        "recorded_at": effective_date,
                        "source_operation_id": None,
                    }
                )
                existing_price_values[template_id].add(price_history_unit_price)
        if price_rows:
            self.repo.add_item_template_prices_bulk(rows=price_rows)
        else:
            self.db.flush()
        return resolved_items

    def _receipt_item_price_for_history(self, item: dict) -> Decimal | None:
        if bool(item.get("is_discounted")):
            regular_unit_price = item.get("regular_unit_price")
            return self._money(regular_unit_price) if regular_unit_price is not None else None
        return self._money(item["unit_price"])

    def _serialize_item_template(self, item) -> dict:
        latest_map = self.repo.get_latest_prices_for_templates(template_ids=[int(item.id)])
        latest = latest_map.get(int(item.id))
        brand_meta = self.brand_repo.brand_meta_for_templates(
            user_id=int(item.user_id),
            template_ids=[int(item.id)],
        ).get(
            int(item.id),
            {
                "brand_id": None,
                "brand_name": None,
                "brand_accent_color": None,
                "brand_is_archived": False,
                "brand_image_id": None,
                "source_id": item.source_id,
                "source_name": item.shop_name,
                "source_image_id": None,
                "product_id": item.product_id,
                "product_name": None,
                "product_image_id": None,
            },
        )
        return {
            "id": int(item.id),
            "product_id": brand_meta.get("product_id", item.product_id),
            "product_name": brand_meta.get("product_name"),
            "product_image_id": brand_meta.get("product_image_id"),
            "image_id": brand_meta.get("item_image_id", item.image_id),
            "shop_name": item.shop_name,
            "name": item.name,
            "use_count": int(item.use_count or 0),
            "last_used_at": item.last_used_at,
            "last_category_id": item.last_category_id,
            **brand_meta,
            "latest_unit_price": self._money(latest.unit_price) if latest else None,
            "latest_price_date": latest.recorded_at if latest else None,
        }

    def get_item_template(self, *, user_id: int, template_id: int) -> dict:
        item = self.repo.get_item_template_by_id(user_id=user_id, template_id=template_id)
        if item is None:
            raise LookupError("Item template not found")
        return self._serialize_item_template(item)

    def _ensure_item_sources(self, *, user_id: int, items: list[dict]) -> None:
        template_ids = sorted(
            {
                int(item["template_id"])
                for item in items
                if item.get("template_id") is not None
            }
        )
        templates = self.repo.list_item_templates_by_ids(
            user_id=user_id,
            template_ids=template_ids,
            include_archived=True,
        )
        template_by_id = {int(template.id): template for template in templates}
        for item in items:
            template = template_by_id.get(int(item.get("template_id") or 0))
            unchanged_source_id = (
                int(template.source_id)
                if template is not None and template.source_id is not None
                else None
            )
            requested_source_id = item.get("source_id")
            shop_name = item.get("shop_name")
            # Older clients do not send source_id. Preserve the stable relation
            # when their source label still matches the linked catalog item,
            # including an archived source shown in historical receipts.
            if (
                requested_source_id is None
                and unchanged_source_id is not None
                and shop_name
                and template is not None
            ):
                _, requested_name_ci = self.source_service.normalize_name(shop_name)
                if requested_name_ci == template.shop_name_ci:
                    requested_source_id = unchanged_source_id
            source = self.source_service.resolve(
                user_id=user_id,
                source_id=requested_source_id,
                shop_name=shop_name,
                unchanged_source_id=unchanged_source_id,
            )
            if source is None:
                item.pop("source_id", None)
                item["shop_name"] = None
                continue
            item["source_id"] = int(source.id)
            item["shop_name"] = source.name

    def _validate_brand_id(
        self,
        *,
        user_id: int,
        brand_id: int | None,
        unchanged_brand_id: int | None = None,
    ) -> int | None:
        if brand_id is None:
            return None
        normalized_id = int(brand_id)
        if self.brand_repo.get_by_id(user_id=user_id, brand_id=normalized_id) is not None:
            return normalized_id

        # An archived brand remains a valid historical relation for the catalog
        # position that already owns it. Let an edit round-trip that exact value,
        # while keeping archived brands unavailable for every new assignment.
        if unchanged_brand_id is not None and normalized_id == int(unchanged_brand_id):
            archived = self.brand_repo.get_by_id(
                user_id=user_id,
                brand_id=normalized_id,
                include_archived=True,
            )
            if archived is not None and archived.is_archived:
                return normalized_id
        raise ValueError("Brand not found")

    def _validate_receipt_brand_ids(self, *, user_id: int, items: list[dict]) -> None:
        explicit_brand_items = [
            item
            for item in items
            if "brand_id" in item and item.get("brand_id") is not None
        ]
        if not explicit_brand_items:
            return

        template_ids = sorted(
            {
                int(item["template_id"])
                for item in explicit_brand_items
                if item.get("template_id") is not None
            }
        )
        templates = self.repo.list_item_templates_by_ids(
            user_id=user_id,
            template_ids=template_ids,
            include_archived=True,
        )
        template_brand_ids = {
            int(template.id): int(template.brand_id) if template.brand_id is not None else None
            for template in templates
        }

        for item in explicit_brand_items:
            brand_id = int(item["brand_id"])
            if self.brand_repo.get_by_id(user_id=user_id, brand_id=brand_id) is not None:
                continue

            # Archived brands stay visible on existing catalog positions. A receipt
            # editor may round-trip that unchanged relation, but must not assign an
            # archived brand to another or newly created position.
            archived = self.brand_repo.get_by_id(
                user_id=user_id,
                brand_id=brand_id,
                include_archived=True,
            )
            template_id = item.get("template_id")
            if (
                archived is None
                or not archived.is_archived
                or template_id is None
                or template_brand_ids.get(int(template_id)) != brand_id
            ):
                raise ValueError("Brand not found")

    def _validate_receipt_category_ids(
        self,
        *,
        user_id: int,
        items: list[dict],
        fallback_category_id: int | None,
    ) -> None:
        """Validate snapshots and the fallback before mutating any catalog rows."""
        category_ids = {
            int(item["category_id"])
            for item in items
            if item.get("category_id") is not None
        }
        if fallback_category_id is not None:
            category_ids.add(int(fallback_category_id))
        for category_id in category_ids:
            self._validate_category_id(user_id=user_id, category_id=category_id)

    def _apply_explicit_template_links(
        self,
        *,
        user_id: int,
        items: list[dict],
        template_by_key: dict[tuple[str, str | None], object],
    ) -> None:
        explicit_ids = {
            int(item["template_id"])
            for item in items
            if item.get("template_id") is not None
        }
        if not explicit_ids:
            return
        templates = self.repo.list_item_templates_by_ids(
            user_id=user_id,
            template_ids=sorted(explicit_ids),
            include_archived=True,
        )
        by_id = {int(template.id): template for template in templates}
        if set(by_id) != explicit_ids:
            raise ValueError("Item template not found")
        for item in items:
            explicit_id = item.get("template_id")
            if explicit_id is None:
                continue
            template = by_id[int(explicit_id)]
            shop_name = item.get("shop_name")
            key = (
                item["name"].casefold(),
                shop_name.casefold() if shop_name else None,
            )
            template_key = (str(template.name_ci), template.shop_name_ci)
            if key != template_key:
                raise ValueError("Selected item template does not match source and name")
            requested_product_id = item.get("product_id")
            if (
                requested_product_id is not None
                and template.product_id is not None
                and int(template.product_id) != int(requested_product_id)
            ):
                raise ValueError("Selected item template belongs to another product")
            template_by_key[key] = template

    def _apply_explicit_product_links(
        self,
        *,
        user_id: int,
        items: list[dict],
        template_by_key: dict[tuple[str, str | None], object],
    ) -> None:
        product_ids = sorted(
            {
                int(item["product_id"])
                for item in items
                if item.get("product_id") is not None
            }
        )
        if not product_ids:
            return
        products = self.product_repo.list_by_ids(
            user_id=user_id,
            product_ids=product_ids,
        )
        if {int(product.id) for product in products} != set(product_ids):
            raise ValueError("Catalog product not found")
        offers = self.product_repo.list_offers_for_products(
            user_id=user_id,
            product_ids=product_ids,
            include_archived=True,
        )
        offers_by_product_and_key: dict[
            tuple[int, str, str | None], list
        ] = {}
        for offer in offers:
            key = (
                int(offer.product_id),
                str(offer.name_ci),
                offer.shop_name_ci,
            )
            offers_by_product_and_key.setdefault(key, []).append(offer)

        for item in items:
            requested_product_id = item.get("product_id")
            if requested_product_id is None:
                continue
            shop_name = item.get("shop_name")
            item_key = (
                item["name"].casefold(),
                shop_name.casefold() if shop_name else None,
            )
            selected = template_by_key.get(item_key)
            if selected is not None:
                current_product_id = getattr(selected, "product_id", None)
                if current_product_id is None:
                    selected.product_id = int(requested_product_id)
                elif int(current_product_id) != int(requested_product_id):
                    raise ValueError(
                        "Offer identity already belongs to another product; use merge"
                    )
                continue
            candidates = offers_by_product_and_key.get(
                (int(requested_product_id), item_key[0], item_key[1]),
                [],
            )
            if len(candidates) > 1:
                raise ValueError("Multiple product offers match source and name")
            if candidates:
                template_by_key[item_key] = candidates[0]

    def _normalize_item_template_fields(self, *, shop_name: str | None, name: str | None) -> tuple[str | None, str]:
        normalized_shop_raw = " ".join(str(shop_name or "").split())
        normalized_shop = normalized_shop_raw or None
        normalized_name = " ".join(str(name or "").split())
        if not normalized_name:
            raise ValueError("template name must not be empty")
        return normalized_shop, normalized_name

    def _resolve_catalog_product(
        self,
        *,
        user_id: int,
        product_id: int | None,
        name: str,
        brand_id: int | None,
        category_id: int | None,
        existing_template=None,
    ):
        """Resolve the canonical owner without silently moving an existing offer."""
        if product_id is not None:
            product = self.product_repo.get_by_id(
                user_id=user_id,
                product_id=int(product_id),
                include_archived=False,
            )
            if product is None:
                raise ValueError("Catalog product not found")
            current_product_id = getattr(existing_template, "product_id", None)
            if current_product_id is not None and int(current_product_id) != int(product.id):
                raise ValueError(
                    "Offer already belongs to another product; use merge or detach"
                )
            return product
        if existing_template is not None:
            return self.products.ensure_for_template(
                user_id=user_id,
                template=existing_template,
            )
        return self.products.create_for_offer(
            user_id=user_id,
            name=name,
            brand_id=brand_id,
            category_id=category_id,
        )

    def _sync_product_compatibility(self, *, product) -> None:
        """Keep legacy offer fields readable for older clients and reports."""
        offers = self.product_repo.list_offers(
            user_id=int(product.user_id),
            product_id=int(product.id),
            include_archived=True,
        )
        for offer in offers:
            offer.brand_id = product.brand_id
            offer.last_category_id = product.category_id
            offer.image_id = product.image_id
        self.db.flush()

    def _apply_receipt_product_metadata(
        self,
        *,
        user_id: int,
        product,
        item: dict,
        fallback_category_id: int | None,
    ) -> dict[int, int | None] | None:
        if "brand_id" in item:
            product.brand_id = item.get("brand_id")

        category_requested = False
        requested_category_id = None
        if item.get("product_id") is None:
            requested_category_id = item.get("category_id") or fallback_category_id
            category_requested = requested_category_id is not None
        elif bool(item.get("category_touched")):
            requested_category_id = item.get("category_id")
            category_requested = True
        if not category_requested:
            return None

        validated_category_id = self._validate_category_id(
            user_id=user_id,
            category_id=requested_category_id,
        )
        offers = self.product_repo.list_offers(
            user_id=user_id,
            product_id=int(product.id),
            include_archived=True,
        )
        previous_categories = {
            int(offer.id): offer.last_category_id for offer in offers
        }
        product.category_id = validated_category_id
        return previous_categories

    def _validate_category_id(self, *, user_id: int, category_id: int | None) -> int | None:
        if category_id is None:
            return None
        normalized_id = int(category_id)
        stmt = select(Category.id).where(
            Category.id == normalized_id,
            or_(Category.user_id == user_id, Category.is_system.is_(True)),
        )
        if self.db.scalar(stmt) is None:
            raise ValueError("Category not found")
        return normalized_id

    @staticmethod
    def _money(value) -> Decimal:
        return Decimal(value).quantize(MONEY_Q, rounding=ROUND_HALF_UP)
