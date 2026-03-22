from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import (
    build_operations_cache_key,
    get_json,
    get_namespace_ttl_seconds,
    invalidate_dashboard_analytics_cache,
    invalidate_dashboard_summary_cache,
    invalidate_item_templates_cache,
    invalidate_operations_cache,
    set_json,
)
from app.db.models import Category, CategoryGroup
from app.repositories.operation_repo import OperationRepository
from app.services.operation_item_template_service import OperationItemTemplateService


MONEY_Q = Decimal("0.01")
QTY_Q = Decimal("0.001")


class OperationService:
    LARGE_OPERATION_THRESHOLD = Decimal("100")

    def __init__(self, db: Session):
        self.db = db
        self.repo = OperationRepository(db)
        self.item_templates = OperationItemTemplateService(db, self.repo)

    @classmethod
    def _resolve_quick_view_filters(cls, quick_view: str | None) -> dict:
        view = (quick_view or "all").strip()
        if view == "receipt":
            return {"receipt_only": True, "uncategorized_only": False, "min_amount": None}
        if view == "large":
            return {"receipt_only": False, "uncategorized_only": False, "min_amount": cls.LARGE_OPERATION_THRESHOLD}
        if view == "uncategorized":
            return {"receipt_only": False, "uncategorized_only": True, "min_amount": None}
        return {"receipt_only": False, "uncategorized_only": False, "min_amount": None}

    @staticmethod
    def _normalize_quick_view_cache_token(quick_view_filters: dict) -> str:
        if quick_view_filters["receipt_only"]:
            return "receipt"
        if quick_view_filters["uncategorized_only"]:
            return "uncategorized"
        if quick_view_filters["min_amount"] is not None:
            return "large"
        return "all"

    def create_operation(
        self,
        user_id: int,
        kind: str,
        amount: Decimal | None,
        operation_date: date,
        category_id: int | None,
        note: str | None,
        receipt_items: list[dict] | None = None,
    ):
        self._validate_kind(kind)
        normalized_items, receipt_total = self._normalize_receipt_items(receipt_items or [])
        resolved_amount = self._resolve_operation_amount(amount=amount, receipt_total=receipt_total)

        item = self.repo.create(user_id, kind, resolved_amount, operation_date, category_id, note)
        if normalized_items:
            storage_items = self.item_templates.resolve_templates_and_prices(
                user_id=user_id,
                operation_id=item.id,
                operation_date=operation_date,
                category_id=category_id,
                normalized_items=normalized_items,
            )
            self.repo.replace_receipt_items(user_id=user_id, operation_id=item.id, items=storage_items)
        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)
        invalidate_dashboard_analytics_cache(user_id)
        invalidate_item_templates_cache(user_id)
        invalidate_operations_cache(user_id)
        self.db.refresh(item)
        return self._serialize_operation(user_id=user_id, operation=item)

    def list_operations(
        self,
        user_id: int,
        page: int,
        page_size: int,
        sort_by: str,
        sort_dir: str,
        kind: str | None,
        date_from: date | None,
        date_to: date | None,
        category_id: int | None,
        q: str | None,
        quick_view: str | None = None,
    ) -> tuple[list, int]:
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        if kind:
            self._validate_kind(kind)
        quick_view_filters = self._resolve_quick_view_filters(quick_view)
        quick_view_token = self._normalize_quick_view_cache_token(quick_view_filters)
        cache_key = build_operations_cache_key(
            user_id=user_id,
            view="list",
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            kind=kind,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            q=q,
            quick_view=quick_view_token,
        )
        cached = get_json(cache_key)
        if cached is not None:
            return cached["items"], int(cached["total"])

        items, total = self.repo.list_filtered(
            user_id=user_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            kind=kind,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            q=q,
            receipt_only=quick_view_filters["receipt_only"],
            uncategorized_only=quick_view_filters["uncategorized_only"],
            min_amount=quick_view_filters["min_amount"],
        )
        operation_ids = [int(item.id) for item in items]
        receipt_by_operation = self.repo.list_receipt_items_for_operations(
            user_id=user_id,
            operation_ids=operation_ids,
        )
        result = [
            self._serialize_operation(
                user_id=user_id,
                operation=item,
                receipt_items=receipt_by_operation.get(int(item.id), []),
            )
            for item in items
        ]
        set_json(
            cache_key,
            {"items": result, "total": total},
            ttl_seconds=get_namespace_ttl_seconds("operations"),
        )
        return result, total

    def summarize_operations(
        self,
        *,
        user_id: int,
        kind: str | None,
        date_from: date | None,
        date_to: date | None,
        category_id: int | None,
        q: str | None,
        quick_view: str | None = None,
    ) -> dict:
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        if kind:
            self._validate_kind(kind)
        quick_view_filters = self._resolve_quick_view_filters(quick_view)
        quick_view_token = self._normalize_quick_view_cache_token(quick_view_filters)
        cache_key = build_operations_cache_key(
            user_id=user_id,
            view="summary",
            page=None,
            page_size=None,
            sort_by=None,
            sort_dir=None,
            kind=kind,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            q=q,
            quick_view=quick_view_token,
        )
        cached = get_json(cache_key)
        if cached is not None:
            return cached
        income_total, expense_total, total = self.repo.summary_filtered(
            user_id=user_id,
            kind=kind,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            q=q,
            receipt_only=quick_view_filters["receipt_only"],
            uncategorized_only=quick_view_filters["uncategorized_only"],
            min_amount=quick_view_filters["min_amount"],
        )
        payload = {
            "income_total": income_total,
            "expense_total": expense_total,
            "balance": income_total - expense_total,
            "total": total,
        }
        set_json(
            cache_key,
            payload,
            ttl_seconds=get_namespace_ttl_seconds("operations"),
        )
        return payload

    def get_operation(self, user_id: int, operation_id: int):
        item = self.repo.get_by_id(user_id=user_id, operation_id=operation_id)
        if not item:
            raise LookupError("Operation not found")
        return self._serialize_operation(user_id=user_id, operation=item)

    def update_operation(self, user_id: int, operation_id: int, updates: dict):
        if "kind" in updates and updates["kind"] is not None:
            self._validate_kind(updates["kind"])

        item = self.repo.get_by_id(user_id=user_id, operation_id=operation_id)
        if not item:
            raise LookupError("Operation not found")

        receipt_items_input = updates.pop("receipt_items", None) if "receipt_items" in updates else None
        normalized_items: list[dict] | None = None
        receipt_total: Decimal | None = None
        if receipt_items_input is not None:
            normalized_items, receipt_total = self._normalize_receipt_items(receipt_items_input)

        if "amount" in updates:
            if updates["amount"] is None:
                if receipt_items_input is None:
                    raise ValueError("amount must not be null")
                updates["amount"] = self._resolve_operation_amount(amount=None, receipt_total=receipt_total)
            else:
                updates["amount"] = self._money(updates["amount"])

        item = self.repo.update(item, updates)

        if normalized_items is not None:
            storage_items: list[dict] = []
            if normalized_items:
                storage_items = self.item_templates.resolve_templates_and_prices(
                    user_id=user_id,
                    operation_id=item.id,
                    operation_date=item.operation_date,
                    category_id=item.category_id,
                    normalized_items=normalized_items,
                )
            self.repo.replace_receipt_items(user_id=user_id, operation_id=item.id, items=storage_items)
            if receipt_total is not None and "amount" not in updates:
                # Keep operation amount as source of truth; discrepancy is reported in output.
                _ = receipt_total

        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)
        invalidate_dashboard_analytics_cache(user_id)
        invalidate_item_templates_cache(user_id)
        invalidate_operations_cache(user_id)
        self.db.refresh(item)
        return self._serialize_operation(user_id=user_id, operation=item)

    def delete_operation(self, user_id: int, operation_id: int) -> None:
        item = self.repo.get_by_id(user_id=user_id, operation_id=operation_id)
        if not item:
            raise LookupError("Operation not found")

        self.repo.delete(item)
        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)
        invalidate_dashboard_analytics_cache(user_id)
        invalidate_item_templates_cache(user_id)
        invalidate_operations_cache(user_id)

    def list_item_templates(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        q: str | None,
    ) -> tuple[list[dict], int]:
        return self.item_templates.list_item_templates(
            user_id=user_id,
            page=page,
            page_size=page_size,
            q=q,
        )

    def list_item_template_prices(
        self,
        *,
        user_id: int,
        template_id: int,
        limit: int = 200,
    ) -> list[dict]:
        return self.item_templates.list_item_template_prices(
            user_id=user_id,
            template_id=template_id,
            limit=limit,
        )

    def create_item_template(
        self,
        *,
        user_id: int,
        shop_name: str | None,
        name: str,
        latest_unit_price: Decimal | None,
        latest_price_date: date | None = None,
    ) -> dict:
        return self.item_templates.create_item_template(
            user_id=user_id,
            shop_name=shop_name,
            name=name,
            latest_unit_price=latest_unit_price,
            latest_price_date=latest_price_date,
        )

    def update_item_template(
        self,
        *,
        user_id: int,
        template_id: int,
        updates: dict,
    ) -> dict:
        return self.item_templates.update_item_template(
            user_id=user_id,
            template_id=template_id,
            updates=updates,
        )

    def delete_item_template(self, *, user_id: int, template_id: int) -> None:
        self.item_templates.delete_item_template(user_id=user_id, template_id=template_id)

    def delete_all_item_templates(self, *, user_id: int) -> int:
        return self.item_templates.delete_all_item_templates(user_id=user_id)

    def _serialize_operation(self, *, user_id: int, operation, receipt_items: list | None = None) -> dict:
        loaded_items = receipt_items
        if loaded_items is None:
            loaded = self.repo.list_receipt_items_for_operations(
                user_id=user_id,
                operation_ids=[int(operation.id)],
            )
            loaded_items = loaded.get(int(operation.id), [])
        category_meta_map = self._get_category_meta_map([row.category_id for row in loaded_items or []] + [operation.category_id])
        receipt_payload = []
        receipt_total = Decimal("0")
        for row in loaded_items or []:
            line_total = self._money(row.line_total)
            receipt_total += line_total
            category_meta = category_meta_map.get(int(row.category_id or 0), {})
            receipt_payload.append(
                {
                    "id": int(row.id),
                    "template_id": row.template_id,
                    "category_id": row.category_id,
                    "category_name": category_meta.get("name"),
                    "category_icon": category_meta.get("icon"),
                    "category_accent_color": category_meta.get("accent_color"),
                    "shop_name": row.shop_name,
                    "name": row.name,
                    "quantity": self._qty(row.quantity),
                    "unit_price": self._money(row.unit_price),
                    "line_total": line_total,
                    "note": row.note,
                }
            )
        amount = self._money(operation.amount)
        receipt_total_value = self._money(receipt_total) if receipt_payload else None
        discrepancy = self._money(amount - receipt_total) if receipt_payload else None
        operation_category_meta = category_meta_map.get(int(operation.category_id or 0), {})
        return {
            "id": int(operation.id),
            "kind": operation.kind,
            "amount": amount,
            "operation_date": operation.operation_date,
            "category_id": operation.category_id,
            "category_name": operation_category_meta.get("name"),
            "category_icon": operation_category_meta.get("icon"),
            "category_accent_color": operation_category_meta.get("accent_color"),
            "note": operation.note,
            "receipt_items": receipt_payload,
            "receipt_total": receipt_total_value,
            "receipt_discrepancy": discrepancy,
        }

    def _get_category_meta_map(self, category_ids: list[int | None]) -> dict[int, dict]:
        normalized_ids = sorted({int(category_id) for category_id in category_ids if int(category_id or 0) > 0})
        if not normalized_ids:
            return {}
        stmt = (
            select(Category, CategoryGroup)
            .outerjoin(CategoryGroup, CategoryGroup.id == Category.group_id)
            .where(Category.id.in_(normalized_ids))
        )
        result: dict[int, dict] = {}
        for category, group in self.db.execute(stmt).all():
            result[int(category.id)] = {
                "name": category.name,
                "icon": category.icon or (group.icon if group else None),
                "accent_color": group.accent_color if group else None,
            }
        return result

    def _normalize_receipt_items(self, receipt_items: list[dict]) -> tuple[list[dict], Decimal | None]:
        normalized: list[dict] = []
        receipt_total = Decimal("0")
        for item in receipt_items:
            shop_name_raw = " ".join(str(item.get("shop_name") or "").split())
            shop_name = shop_name_raw or None
            name = " ".join(str(item.get("name") or "").split())
            if not name:
                raise ValueError("receipt item name must not be empty")
            quantity = self._qty(item.get("quantity") or Decimal("0"))
            if quantity <= 0:
                raise ValueError("receipt item quantity must be greater than 0")
            unit_price = self._money(item.get("unit_price") or Decimal("0"))
            if unit_price <= 0:
                raise ValueError("receipt item unit_price must be greater than 0")
            line_total = self._money(quantity * unit_price)
            note = item.get("note")
            normalized.append(
                {
                    "category_id": item.get("category_id"),
                    "shop_name": shop_name,
                    "name": name,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": line_total,
                    "note": note,
                }
            )
            receipt_total += line_total
        if not normalized:
            return normalized, None
        return normalized, self._money(receipt_total)

    def _resolve_operation_amount(self, *, amount: Decimal | None, receipt_total: Decimal | None) -> Decimal:
        if amount is None and receipt_total is None:
            raise ValueError("amount is required when receipt_items are empty")
        if amount is None and receipt_total is not None:
            return self._money(receipt_total)
        if amount is None:
            raise ValueError("amount is required")
        return self._money(amount)

    @staticmethod
    def _validate_kind(kind: str) -> None:
        if kind not in {"income", "expense"}:
            raise ValueError("kind must be either 'income' or 'expense'")

    @staticmethod
    def _money(value) -> Decimal:
        return Decimal(value).quantize(MONEY_Q, rounding=ROUND_HALF_UP)

    @staticmethod
    def _qty(value) -> Decimal:
        return Decimal(value).quantize(QTY_Q, rounding=ROUND_HALF_UP)
