from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

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
from app.repositories.operation_repo import OperationRepository
from app.services.activity_service import ActivityService


MONEY_Q = Decimal("0.01")


class OperationItemTemplateService:
    ACTIVITY_FIELDS = [
        "shop_name",
        "name",
        "last_category_id",
        "use_count",
        "is_archived",
        "last_used_at",
        "recommendation_enabled",
        "recommendation_mode",
        "recommendation_interval_days",
        "recommendation_base_quantity",
        "recommendation_next_date",
        "recommendation_snoozed_until",
    ]
    ACTIVITY_LABELS = {
        "shop_name": "Источник",
        "name": "Название",
        "last_category_id": "Категория",
        "use_count": "Использований",
        "is_archived": "Архив",
        "last_used_at": "Последнее использование",
        "recommendation_enabled": "Рекомендации",
        "recommendation_mode": "Режим рекомендаций",
        "recommendation_interval_days": "Запас в днях",
        "recommendation_base_quantity": "Базовое количество",
        "recommendation_next_date": "Следующая рекомендация",
        "recommendation_snoozed_until": "Отложено до",
    }

    def __init__(self, db: Session, repo: OperationRepository):
        self.db = db
        self.repo = repo
        self.activity = ActivityService(db)

    def list_item_templates(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        q: str | None,
    ) -> tuple[list[dict], int]:
        cache_key = build_item_templates_cache_key(
            user_id=user_id,
            view="list",
            page=page,
            page_size=page_size,
            q=q,
        )
        cached = get_json(cache_key)
        if cached is not None:
            return cached["items"], int(cached["total"])
        templates, total = self.repo.list_item_templates(
            user_id=user_id,
            page=page,
            page_size=page_size,
            q=q,
        )
        latest_prices = self.repo.get_latest_prices_for_templates(template_ids=[int(item.id) for item in templates])
        payload = []
        for item in templates:
            latest = latest_prices.get(int(item.id))
            payload.append(
                {
                    "id": int(item.id),
                    "shop_name": item.shop_name,
                    "name": item.name,
                    "use_count": int(item.use_count or 0),
                    "last_used_at": item.last_used_at,
                    "last_category_id": item.last_category_id,
                    "latest_unit_price": self._money(latest.unit_price) if latest else None,
                    "latest_price_date": latest.recorded_at if latest else None,
                    **self._serialize_recommendation_settings(item),
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

    def create_item_template(
        self,
        *,
        user_id: int,
        shop_name: str | None,
        name: str,
        last_category_id: int | None,
        latest_unit_price: Decimal | None,
        latest_price_date: date | None = None,
        recommendation_enabled: bool = False,
        recommendation_mode: str = "manual",
        recommendation_interval_days: int | None = None,
        recommendation_base_quantity: Decimal = Decimal("1"),
    ) -> dict:
        normalized_shop, normalized_name = self._normalize_item_template_fields(shop_name=shop_name, name=name)
        shop_name_ci = normalized_shop.casefold() if normalized_shop else None
        name_ci = normalized_name.casefold()
        validated_category_id = self._validate_category_id(user_id=user_id, category_id=last_category_id)
        existing = self.repo.get_item_template_by_name_ci(
            user_id=user_id,
            name_ci=name_ci,
            shop_name_ci=shop_name_ci,
            include_archived=True,
        )
        item = existing
        if not item:
            item = self.repo.create_item_template(
                user_id=user_id,
                shop_name=normalized_shop,
                shop_name_ci=shop_name_ci,
                name=normalized_name,
                name_ci=name_ci,
                last_category_id=validated_category_id,
            )
            self._apply_recommendation_settings(
                item,
                {
                    "recommendation_enabled": recommendation_enabled,
                    "recommendation_mode": recommendation_mode,
                    "recommendation_interval_days": recommendation_interval_days,
                    "recommendation_base_quantity": recommendation_base_quantity,
                },
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
            if item.name != normalized_name:
                item.name = normalized_name
                item.name_ci = name_ci
            if validated_category_id is not None:
                item.last_category_id = validated_category_id
            self._apply_recommendation_settings(
                item,
                {
                    "recommendation_enabled": recommendation_enabled,
                    "recommendation_mode": recommendation_mode,
                    "recommendation_interval_days": recommendation_interval_days,
                    "recommendation_base_quantity": recommendation_base_quantity,
                },
            )
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
        if item.recommendation_enabled:
            latest_purchase = self.repo.get_latest_purchases_for_templates(
                user_id=user_id,
                template_ids=[int(item.id)],
            ).get(int(item.id))
            if latest_purchase:
                self._schedule_recommendation_after_purchase(
                    item,
                    purchased_at=latest_purchase[0],
                    quantity=latest_purchase[1],
                    clear_snooze=False,
                )
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
        next_shop = updates["shop_name"] if "shop_name" in updates else item.shop_name
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

        item.shop_name = normalized_shop
        item.shop_name_ci = shop_name_ci
        item.name = normalized_name
        item.name_ci = name_ci
        previous_category_id = item.last_category_id
        if "last_category_id" in updates:
            item.last_category_id = self._validate_category_id(
                user_id=user_id,
                category_id=updates.get("last_category_id"),
            )
        recommendation_fields = {
            key: value
            for key, value in updates.items()
            if key.startswith("recommendation_")
        }
        if recommendation_fields:
            self._apply_recommendation_settings(item, recommendation_fields)
            if item.recommendation_enabled:
                latest_purchase = self.repo.get_latest_purchases_for_templates(
                    user_id=user_id,
                    template_ids=[int(item.id)],
                ).get(int(item.id))
                if latest_purchase:
                    self._schedule_recommendation_after_purchase(
                        item,
                        purchased_at=latest_purchase[0],
                        quantity=latest_purchase[1],
                        clear_snooze=False,
                    )
        if "shop_name" in updates or "name" in updates:
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
                category_id=item.last_category_id,
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
        if "shop_name" in updates or "name" in updates or "last_category_id" in updates:
            invalidate_operations_cache(user_id)
            invalidate_plans_cache(user_id)
            invalidate_dashboard_analytics_cache(user_id)
        return self._serialize_item_template(item)

    def list_item_recommendations(self, *, user_id: int, limit: int = 12) -> list[dict]:
        templates = self.repo.list_recommendation_templates(user_id=user_id)
        template_ids = [int(item.id) for item in templates]
        latest_purchases = self.repo.get_latest_purchases_for_templates(
            user_id=user_id,
            template_ids=template_ids,
        )
        latest_prices = self.repo.get_latest_prices_for_templates(template_ids=template_ids)
        today = date.today()
        payload: list[dict] = []
        for item in templates:
            template_id = int(item.id)
            latest_purchase = latest_purchases.get(template_id)
            if not latest_purchase:
                continue
            last_purchase_date, last_quantity = latest_purchase
            interval_days = int(item.recommendation_interval_days or 1)
            base_quantity = Decimal(item.recommendation_base_quantity or 1)
            scaled_days = self._scaled_recommendation_days(
                interval_days=interval_days,
                base_quantity=base_quantity,
                quantity=last_quantity,
            )
            next_date = last_purchase_date + timedelta(days=scaled_days)
            snoozed_until = item.recommendation_snoozed_until
            effective_date = max(next_date, snoozed_until) if snoozed_until else next_date
            days_until = (effective_date - today).days
            status = "overdue" if days_until < 0 else "due" if days_until == 0 else "upcoming"
            explanation = (
                f"Последняя покупка: {self._format_quantity(last_quantity)} · "
                f"расчётный запас на {scaled_days} дн."
            )
            if snoozed_until and snoozed_until > next_date:
                explanation += f" · отложено до {snoozed_until.strftime('%d.%m.%Y')}"
            latest_price = latest_prices.get(template_id)
            payload.append(
                {
                    "template_id": template_id,
                    "shop_name": item.shop_name,
                    "name": item.name,
                    "category_id": item.last_category_id,
                    "latest_unit_price": self._money(latest_price.unit_price) if latest_price else None,
                    "last_purchase_date": last_purchase_date,
                    "last_quantity": last_quantity,
                    "interval_days": interval_days,
                    "base_quantity": base_quantity,
                    "next_date": next_date,
                    "effective_date": effective_date,
                    "days_until": days_until,
                    "status": status,
                    "explanation": explanation,
                }
            )
        payload.sort(key=lambda entry: (entry["effective_date"], entry["template_id"]))
        return payload[:limit]

    def list_item_recommendation_management(self, *, user_id: int) -> list[dict]:
        templates = self.repo.list_item_templates_for_recommendation_management(user_id=user_id)
        template_ids = [int(item.id) for item in templates]
        latest_purchases = self.repo.get_latest_purchases_for_templates(
            user_id=user_id,
            template_ids=template_ids,
        )
        latest_prices = self.repo.get_latest_prices_for_templates(template_ids=template_ids)
        today = date.today()
        payload: list[dict] = []
        for item in templates:
            template_id = int(item.id)
            latest_purchase = latest_purchases.get(template_id)
            last_purchase_date = latest_purchase[0] if latest_purchase else None
            last_quantity = latest_purchase[1] if latest_purchase else None
            interval_days = int(item.recommendation_interval_days) if item.recommendation_interval_days else None
            base_quantity = Decimal(item.recommendation_base_quantity or 1)
            next_date = None
            effective_date = None
            days_until = None
            status = "unconfigured"
            if item.recommendation_enabled and latest_purchase and interval_days:
                scaled_days = self._scaled_recommendation_days(
                    interval_days=interval_days,
                    base_quantity=base_quantity,
                    quantity=last_quantity,
                )
                next_date = last_purchase_date + timedelta(days=scaled_days)
                snoozed_until = item.recommendation_snoozed_until
                effective_date = max(next_date, snoozed_until) if snoozed_until else next_date
                days_until = (effective_date - today).days
                if snoozed_until and snoozed_until > next_date and snoozed_until > today:
                    status = "snoozed"
                else:
                    status = "overdue" if days_until < 0 else "due" if days_until == 0 else "upcoming"
            elif item.recommendation_enabled:
                status = "awaiting_purchase"
            latest_price = latest_prices.get(template_id)
            payload.append(
                {
                    "template_id": template_id,
                    "shop_name": item.shop_name,
                    "name": item.name,
                    "category_id": item.last_category_id,
                    "use_count": int(item.use_count or 0),
                    "latest_unit_price": self._money(latest_price.unit_price) if latest_price else None,
                    "last_purchase_date": last_purchase_date,
                    "last_quantity": last_quantity,
                    "recommendation_enabled": bool(item.recommendation_enabled),
                    "recommendation_mode": item.recommendation_mode or "manual",
                    "interval_days": interval_days,
                    "base_quantity": base_quantity,
                    "next_date": next_date,
                    "snoozed_until": item.recommendation_snoozed_until,
                    "effective_date": effective_date,
                    "days_until": days_until,
                    "status": status,
                    "candidate": bool(not item.recommendation_enabled and latest_purchase and int(item.use_count or 0) >= 2),
                }
            )
        return payload

    def bulk_update_item_recommendations(
        self,
        *,
        user_id: int,
        template_ids: list[int],
        action: str,
        interval_days: int | None,
        base_quantity: Decimal | None,
        snooze_days: int,
    ) -> int:
        normalized_ids = list(dict.fromkeys(int(item_id) for item_id in template_ids if int(item_id) > 0))
        items = self.repo.list_item_templates_by_ids(user_id=user_id, template_ids=normalized_ids)
        if len(items) != len(normalized_ids):
            raise LookupError("One or more item templates were not found")
        latest_purchases = (
            self.repo.get_latest_purchases_for_templates(user_id=user_id, template_ids=normalized_ids)
            if action == "enable"
            else {}
        )
        updated_count = 0
        for item in items:
            before_activity = ActivityService.snapshot(item, self.ACTIVITY_FIELDS)
            if action == "enable":
                resolved_interval = interval_days or item.recommendation_interval_days
                if resolved_interval is None:
                    raise ValueError("Recommendation interval is required")
                self._apply_recommendation_settings(
                    item,
                    {
                        "recommendation_enabled": True,
                        "recommendation_mode": "manual",
                        "recommendation_interval_days": resolved_interval,
                        "recommendation_base_quantity": base_quantity or item.recommendation_base_quantity or 1,
                        "recommendation_snoozed_until": None,
                    },
                )
                latest_purchase = latest_purchases.get(int(item.id))
                if latest_purchase:
                    self._schedule_recommendation_after_purchase(
                        item,
                        purchased_at=latest_purchase[0],
                        quantity=latest_purchase[1],
                    )
            elif action == "disable":
                self._apply_recommendation_settings(
                    item,
                    {
                        "recommendation_enabled": False,
                        "recommendation_snoozed_until": None,
                    },
                )
            elif action == "snooze":
                if not item.recommendation_enabled:
                    continue
                item.recommendation_snoozed_until = date.today() + timedelta(days=snooze_days)
            else:
                raise ValueError("Unsupported recommendation action")
            self.activity.record_updated(
                user_id=user_id,
                actor_user_id=user_id,
                entity_type="item_template",
                entity_id=int(item.id),
                before=before_activity,
                after=ActivityService.snapshot(item, self.ACTIVITY_FIELDS),
                labels=self.ACTIVITY_LABELS,
                title="Рекомендация позиции изменена",
            )
            updated_count += 1
        self.db.commit()
        invalidate_item_templates_cache(user_id)
        return updated_count

    def snooze_item_recommendation(self, *, user_id: int, template_id: int, days: int) -> dict:
        item = self.repo.get_item_template_by_id(user_id=user_id, template_id=template_id)
        if not item:
            raise LookupError("Item template not found")
        if not item.recommendation_enabled:
            raise ValueError("Recommendations are disabled for this item")
        item.recommendation_snoozed_until = date.today() + timedelta(days=days)
        self.db.commit()
        invalidate_item_templates_cache(user_id)
        return self._serialize_item_template(item)

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

        created_templates = []
        for name_ci, shop_name_ci in key_order:
            key = (name_ci, shop_name_ci)
            if key in template_by_key:
                continue
            matched_item = sample_by_key.get(key)
            if not matched_item:
                continue
            template = self.repo.create_item_template(
                user_id=user_id,
                shop_name=matched_item.get("shop_name"),
                shop_name_ci=shop_name_ci,
                name=matched_item["name"],
                name_ci=name_ci,
                last_category_id=matched_item.get("category_id", category_id),
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
            template.is_archived = False
            if template.name != name:
                template.name = name
            if template.shop_name != shop_name:
                template.shop_name = shop_name
                template.shop_name_ci = shop_name_ci
            self.repo.touch_item_template(
                item=template,
                last_category_id=item.get("category_id", category_id),
                flush=False,
            )
            self._schedule_recommendation_after_purchase(
                template,
                purchased_at=operation_date,
                quantity=Decimal(item.get("quantity") or 0),
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

        created_templates = []
        for name_ci, shop_name_ci in key_order:
            key = (name_ci, shop_name_ci)
            if key in template_by_key:
                continue
            matched_item = sample_by_key[key]
            template = self.repo.create_item_template(
                user_id=user_id,
                shop_name=matched_item.get("shop_name"),
                shop_name_ci=shop_name_ci,
                name=matched_item["name"],
                name_ci=name_ci,
                last_category_id=matched_item.get("category_id", category_id),
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
            template.is_archived = False
            next_category_id = item.get("category_id", category_id)
            if next_category_id is not None:
                template.last_category_id = next_category_id
            template_id = int(template.id)
            resolved_items.append({**item, "template_id": template_id})
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
        return {
            "id": int(item.id),
            "shop_name": item.shop_name,
            "name": item.name,
            "use_count": int(item.use_count or 0),
            "last_used_at": item.last_used_at,
            "last_category_id": item.last_category_id,
            "latest_unit_price": self._money(latest.unit_price) if latest else None,
            "latest_price_date": latest.recorded_at if latest else None,
            **self._serialize_recommendation_settings(item),
        }

    def _apply_recommendation_settings(self, item, updates: dict) -> None:
        enabled = bool(updates.get("recommendation_enabled", item.recommendation_enabled))
        mode = str(updates.get("recommendation_mode", item.recommendation_mode or "manual"))
        interval_value = updates.get("recommendation_interval_days", item.recommendation_interval_days)
        base_value = updates.get("recommendation_base_quantity", item.recommendation_base_quantity or 1)
        if enabled and mode != "manual":
            raise ValueError("Automatic recommendations are not available yet")
        if enabled and interval_value is None:
            raise ValueError("Recommendation interval is required")
        interval_days = int(interval_value) if interval_value is not None else None
        if interval_days is not None and not 1 <= interval_days <= 3650:
            raise ValueError("Recommendation interval must be between 1 and 3650 days")
        base_quantity = Decimal(base_value or 0)
        if base_quantity <= 0:
            raise ValueError("Recommendation base quantity must be greater than zero")
        item.recommendation_enabled = enabled
        item.recommendation_mode = mode
        item.recommendation_interval_days = interval_days
        item.recommendation_base_quantity = base_quantity
        if "recommendation_snoozed_until" in updates:
            item.recommendation_snoozed_until = updates.get("recommendation_snoozed_until")

    def _schedule_recommendation_after_purchase(
        self,
        item,
        *,
        purchased_at: date,
        quantity: Decimal,
        clear_snooze: bool = True,
    ) -> None:
        if not item.recommendation_enabled or not item.recommendation_interval_days:
            return
        days = self._scaled_recommendation_days(
            interval_days=int(item.recommendation_interval_days),
            base_quantity=Decimal(item.recommendation_base_quantity or 1),
            quantity=quantity,
        )
        item.recommendation_next_date = purchased_at + timedelta(days=days)
        if clear_snooze:
            item.recommendation_snoozed_until = None

    @staticmethod
    def _scaled_recommendation_days(*, interval_days: int, base_quantity: Decimal, quantity: Decimal) -> int:
        safe_base = max(Decimal(base_quantity), Decimal("0.001"))
        safe_quantity = max(Decimal(quantity), Decimal("0.001"))
        scaled = (Decimal(interval_days) * safe_quantity / safe_base).to_integral_value(rounding=ROUND_CEILING)
        return max(1, int(scaled))

    @staticmethod
    def _format_quantity(value: Decimal) -> str:
        normalized = Decimal(value).quantize(Decimal("0.001")).normalize()
        return format(normalized, "f")

    @staticmethod
    def _serialize_recommendation_settings(item) -> dict:
        return {
            "recommendation_enabled": bool(item.recommendation_enabled),
            "recommendation_mode": item.recommendation_mode or "manual",
            "recommendation_interval_days": item.recommendation_interval_days,
            "recommendation_base_quantity": Decimal(item.recommendation_base_quantity or 1),
            "recommendation_next_date": item.recommendation_next_date,
            "recommendation_snoozed_until": item.recommendation_snoozed_until,
        }

    def _normalize_item_template_fields(self, *, shop_name: str | None, name: str | None) -> tuple[str | None, str]:
        normalized_shop_raw = " ".join(str(shop_name or "").split())
        normalized_shop = normalized_shop_raw or None
        normalized_name = " ".join(str(name or "").split())
        if not normalized_name:
            raise ValueError("template name must not be empty")
        return normalized_shop, normalized_name

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
