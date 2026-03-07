from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_summary_cache
from app.repositories.operation_repo import OperationRepository


MONEY_Q = Decimal("0.01")
QTY_Q = Decimal("0.001")


class OperationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OperationRepository(db)

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
            storage_items = self._resolve_templates_and_prices(
                user_id=user_id,
                operation_id=item.id,
                operation_date=operation_date,
                category_id=category_id,
                normalized_items=normalized_items,
            )
            self.repo.replace_receipt_items(user_id=user_id, operation_id=item.id, items=storage_items)
        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)
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
    ) -> tuple[list, int]:
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        if kind:
            self._validate_kind(kind)

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
        return result, total

    def get_operation(self, user_id: int, operation_id: int):
        item = self.repo.get_by_id(user_id=user_id, operation_id=operation_id)
        if not item:
            raise LookupError("Operation not found")
        return self._serialize_operation(user_id=user_id, operation=item)

    def update_operation(self, user_id: int, operation_id: int, updates: dict):
        if "kind" in updates and updates["kind"] is not None:
            self._validate_kind(updates["kind"])
        if "amount" in updates and updates["amount"] is None:
            raise ValueError("amount must not be null")

        item = self.repo.get_by_id(user_id=user_id, operation_id=operation_id)
        if not item:
            raise LookupError("Operation not found")

        receipt_items_input = updates.pop("receipt_items", None) if "receipt_items" in updates else None
        normalized_items: list[dict] | None = None
        receipt_total: Decimal | None = None
        if receipt_items_input is not None:
            normalized_items, receipt_total = self._normalize_receipt_items(receipt_items_input)

        if "amount" in updates and updates["amount"] is not None:
            updates["amount"] = self._money(updates["amount"])

        item = self.repo.update(item, updates)

        if normalized_items is not None:
            storage_items: list[dict] = []
            if normalized_items:
                storage_items = self._resolve_templates_and_prices(
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
        self.db.refresh(item)
        return self._serialize_operation(user_id=user_id, operation=item)

    def delete_operation(self, user_id: int, operation_id: int) -> None:
        item = self.repo.get_by_id(user_id=user_id, operation_id=operation_id)
        if not item:
            raise LookupError("Operation not found")

        self.repo.delete(item)
        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)

    def list_item_templates(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        q: str | None,
    ) -> tuple[list[dict], int]:
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
                }
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
        rows = self.repo.list_item_prices(template_id=template_id, limit=limit)
        return [
            {
                "id": int(row.id),
                "unit_price": self._money(row.unit_price),
                "recorded_at": row.recorded_at,
                "source_operation_id": row.source_operation_id,
            }
            for row in rows
        ]

    def create_item_template(
        self,
        *,
        user_id: int,
        shop_name: str | None,
        name: str,
        latest_unit_price: Decimal | None,
    ) -> dict:
        normalized_shop, normalized_name = self._normalize_item_template_fields(shop_name=shop_name, name=name)
        shop_name_ci = normalized_shop.casefold() if normalized_shop else None
        name_ci = normalized_name.casefold()
        existing = self.repo.get_item_template_by_name_ci(
            user_id=user_id,
            name_ci=name_ci,
            shop_name_ci=shop_name_ci,
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
            if item.shop_name != normalized_shop:
                item.shop_name = normalized_shop
                item.shop_name_ci = shop_name_ci
            if item.name != normalized_name:
                item.name = normalized_name
                item.name_ci = name_ci
            self.db.flush()
        if latest_unit_price is not None:
            next_price = self._money(latest_unit_price)
            latest_map = self.repo.get_latest_prices_for_templates(template_ids=[int(item.id)])
            latest = latest_map.get(int(item.id))
            if not latest or self._money(latest.unit_price) != next_price:
                self.repo.add_item_template_price(
                    template_id=int(item.id),
                    unit_price=next_price,
                    recorded_at=date.today(),
                    source_operation_id=None,
                )
        self.db.commit()
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
            latest_map = self.repo.get_latest_prices_for_templates(template_ids=[int(item.id)])
            latest = latest_map.get(int(item.id))
            if not latest or self._money(latest.unit_price) != next_price:
                self.repo.add_item_template_price(
                    template_id=int(item.id),
                    unit_price=next_price,
                    recorded_at=date.today(),
                    source_operation_id=None,
                )
        self.db.commit()
        return self._serialize_item_template(item)

    def delete_item_template(self, *, user_id: int, template_id: int) -> None:
        deleted = self.repo.archive_item_template(user_id=user_id, template_id=template_id)
        if not deleted:
            raise LookupError("Item template not found")
        self.db.commit()

    def delete_all_item_templates(self, *, user_id: int) -> int:
        deleted = self.repo.archive_all_item_templates(user_id=user_id)
        self.db.commit()
        return deleted

    def _resolve_templates_and_prices(
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
                last_category_id=category_id,
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
        price_rows: list[dict] = []
        for item in normalized_items:
            shop_name = item.get("shop_name")
            shop_name_ci = shop_name.casefold() if shop_name else None
            name = item["name"]
            name_ci = name.casefold()
            template = template_by_key.get((name_ci, shop_name_ci))
            if not template:
                continue
            if template.name != name:
                template.name = name
            if template.shop_name != shop_name:
                template.shop_name = shop_name
                template.shop_name_ci = shop_name_ci
            self.repo.touch_item_template(item=template, last_category_id=category_id, flush=False)
            template_id = int(template.id)
            unit_price = self._money(item["unit_price"])
            if latest_price_by_template.get(template_id) != unit_price:
                price_rows.append(
                    {
                        "template_id": template_id,
                        "unit_price": unit_price,
                        "recorded_at": operation_date,
                        "source_operation_id": operation_id,
                    }
                )
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

    def _serialize_operation(self, *, user_id: int, operation, receipt_items: list | None = None) -> dict:
        loaded_items = receipt_items
        if loaded_items is None:
            loaded = self.repo.list_receipt_items_for_operations(
                user_id=user_id,
                operation_ids=[int(operation.id)],
            )
            loaded_items = loaded.get(int(operation.id), [])
        receipt_payload = []
        receipt_total = Decimal("0")
        for row in loaded_items or []:
            line_total = self._money(row.line_total)
            receipt_total += line_total
            receipt_payload.append(
                {
                    "id": int(row.id),
                    "template_id": row.template_id,
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
        return {
            "id": int(operation.id),
            "kind": operation.kind,
            "amount": amount,
            "operation_date": operation.operation_date,
            "category_id": operation.category_id,
            "note": operation.note,
            "receipt_items": receipt_payload,
            "receipt_total": receipt_total_value,
            "receipt_discrepancy": discrepancy,
        }

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
        }

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

    def _normalize_item_template_fields(self, *, shop_name: str | None, name: str | None) -> tuple[str | None, str]:
        normalized_shop_raw = " ".join(str(shop_name or "").split())
        normalized_shop = normalized_shop_raw or None
        normalized_name = " ".join(str(name or "").split())
        if not normalized_name:
            raise ValueError("template name must not be empty")
        return normalized_shop, normalized_name

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
