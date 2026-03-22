from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import (
    build_item_templates_cache_key,
    get_json,
    get_namespace_ttl_seconds,
    invalidate_item_templates_cache,
    set_json,
)
from app.db.models import PlanOperation, PlanReceiptItem
from app.repositories.operation_repo import OperationRepository


MONEY_Q = Decimal("0.01")


class OperationItemTemplateService:
    def __init__(self, db: Session, repo: OperationRepository):
        self.db = db
        self.repo = repo

    def list_item_templates(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        q: str | None,
    ) -> tuple[list[dict], int]:
        backfilled = self.backfill_templates_from_plan_receipts(user_id=user_id)
        if backfilled:
            invalidate_item_templates_cache(user_id)
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
                }
            )
        set_json(
            cache_key,
            {"items": payload, "total": total},
            ttl_seconds=get_namespace_ttl_seconds("item_templates"),
        )
        return payload, total

    def backfill_templates_from_plan_receipts(self, *, user_id: int) -> bool:
        stmt = (
            select(PlanOperation, PlanReceiptItem)
            .join(PlanReceiptItem, PlanReceiptItem.plan_id == PlanOperation.id)
            .where(
                PlanOperation.user_id == user_id,
                PlanReceiptItem.user_id == user_id,
            )
            .order_by(PlanOperation.id.asc(), PlanReceiptItem.id.asc())
        )
        grouped: dict[int, dict] = {}
        for plan, receipt_item in self.db.execute(stmt).all():
            bucket = grouped.setdefault(
                int(plan.id),
                {
                    "category_id": plan.category_id,
                    "recorded_at": plan.scheduled_date,
                    "items": [],
                },
            )
            bucket["items"].append(
                {
                    "category_id": receipt_item.category_id,
                    "shop_name": receipt_item.shop_name,
                    "name": receipt_item.name,
                    "quantity": receipt_item.quantity,
                    "unit_price": receipt_item.unit_price,
                    "line_total": receipt_item.line_total,
                    "note": receipt_item.note,
                }
            )
        if not grouped:
            return False
        for payload in grouped.values():
            self.sync_templates_from_receipt_items(
                user_id=user_id,
                category_id=payload["category_id"],
                normalized_items=payload["items"],
                recorded_at=payload["recorded_at"],
            )
        self.db.commit()
        return True

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
        latest_unit_price: Decimal | None,
        latest_price_date: date | None = None,
    ) -> dict:
        normalized_shop, normalized_name = self._normalize_item_template_fields(shop_name=shop_name, name=name)
        shop_name_ci = normalized_shop.casefold() if normalized_shop else None
        name_ci = normalized_name.casefold()
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
                last_category_id=None,
            )
        else:
            item.is_archived = False
            if item.shop_name != normalized_shop:
                item.shop_name = normalized_shop
                item.shop_name_ci = shop_name_ci
            if item.name != normalized_name:
                item.name = normalized_name
                item.name_ci = name_ci
            self.db.flush()
        if latest_unit_price is not None:
            next_price = self._money(latest_unit_price)
            recorded_at = latest_price_date or date.today()
            if not self.repo.has_item_template_price(template_id=int(item.id), unit_price=next_price):
                self.repo.add_item_template_price(
                    template_id=int(item.id),
                    unit_price=next_price,
                    recorded_at=recorded_at,
                    source_operation_id=None,
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
        self.db.flush()

        latest_unit_price = updates.get("latest_unit_price")
        if latest_unit_price is not None:
            next_price = self._money(latest_unit_price)
            recorded_at = updates.get("latest_price_date") or date.today()
            if not self.repo.has_item_template_price(template_id=int(item.id), unit_price=next_price):
                self.repo.add_item_template_price(
                    template_id=int(item.id),
                    unit_price=next_price,
                    recorded_at=recorded_at,
                    source_operation_id=None,
                )
        self.db.commit()
        invalidate_item_templates_cache(user_id)
        return self._serialize_item_template(item)

    def delete_item_template(self, *, user_id: int, template_id: int) -> None:
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
            template_id = int(template.id)
            unit_price = self._money(item["unit_price"])
            if unit_price not in existing_price_values.setdefault(template_id, set()):
                price_rows.append(
                    {
                        "template_id": template_id,
                        "unit_price": unit_price,
                        "recorded_at": operation_date,
                        "source_operation_id": operation_id,
                    }
                )
                existing_price_values[template_id].add(unit_price)
                latest_price_by_template[template_id] = unit_price
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
    ) -> None:
        if not normalized_items:
            return

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
            unit_price = self._money(item["unit_price"])
            if unit_price not in existing_price_values.setdefault(template_id, set()):
                price_rows.append(
                    {
                        "template_id": template_id,
                        "unit_price": unit_price,
                        "recorded_at": effective_date,
                        "source_operation_id": None,
                    }
                )
                existing_price_values[template_id].add(unit_price)
        if price_rows:
            self.repo.add_item_template_prices_bulk(rows=price_rows)
        else:
            self.db.flush()

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
        }

    def _normalize_item_template_fields(self, *, shop_name: str | None, name: str | None) -> tuple[str | None, str]:
        normalized_shop_raw = " ".join(str(shop_name or "").split())
        normalized_shop = normalized_shop_raw or None
        normalized_name = " ".join(str(name or "").split())
        if not normalized_name:
            raise ValueError("template name must not be empty")
        return normalized_shop, normalized_name

    @staticmethod
    def _money(value) -> Decimal:
        return Decimal(value).quantize(MONEY_Q, rounding=ROUND_HALF_UP)
