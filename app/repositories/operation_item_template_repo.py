from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from app.db.models import (
    Operation,
    OperationItemPrice,
    OperationItemTemplate,
    OperationReceiptItem,
    PlanOperation,
    PlanReceiptItem,
)


class OperationItemTemplateRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_item_template_by_name_ci(
        self,
        *,
        user_id: int,
        name_ci: str,
        shop_name_ci: str | None,
        include_archived: bool = False,
    ) -> OperationItemTemplate | None:
        shop_condition = (
            OperationItemTemplate.shop_name_ci.is_(None)
            if shop_name_ci is None
            else OperationItemTemplate.shop_name_ci == shop_name_ci
        )
        conditions = [
            OperationItemTemplate.user_id == user_id,
            OperationItemTemplate.name_ci == name_ci,
            shop_condition,
        ]
        if not include_archived:
            conditions.append(OperationItemTemplate.is_archived.is_(False))
        stmt = select(OperationItemTemplate).where(*conditions)
        return self.db.scalar(stmt)

    def create_item_template(
        self,
        *,
        user_id: int,
        shop_name: str | None,
        shop_name_ci: str | None,
        name: str,
        name_ci: str,
        last_category_id: int | None,
        brand_id: int | None = None,
        flush: bool = True,
    ) -> OperationItemTemplate:
        item = OperationItemTemplate(
            user_id=user_id,
            shop_name=shop_name,
            shop_name_ci=shop_name_ci,
            name=name,
            name_ci=name_ci,
            last_category_id=last_category_id,
            brand_id=brand_id,
            use_count=0,
        )
        self.db.add(item)
        if flush:
            self.db.flush()
        return item

    def touch_item_template(
        self,
        *,
        item: OperationItemTemplate,
        last_category_id: int | None,
        flush: bool = True,
    ) -> OperationItemTemplate:
        item.use_count = int(item.use_count or 0) + 1
        item.last_used_at = datetime.now(timezone.utc)
        if last_category_id is not None:
            item.last_category_id = last_category_id
        if flush:
            self.db.flush()
        return item

    def add_item_template_price(
        self,
        *,
        template_id: int,
        unit_price: Decimal,
        recorded_at: date,
        source_operation_id: int | None,
        flush: bool = True,
    ) -> OperationItemPrice:
        row = OperationItemPrice(
            template_id=template_id,
            unit_price=unit_price,
            recorded_at=recorded_at,
            source_operation_id=source_operation_id,
        )
        self.db.add(row)
        if flush:
            self.db.flush()
        return row

    def add_item_template_prices_bulk(self, *, rows: list[dict]) -> None:
        if not rows:
            return
        payload = [
            OperationItemPrice(
                template_id=int(item["template_id"]),
                unit_price=item["unit_price"],
                recorded_at=item["recorded_at"],
                source_operation_id=item.get("source_operation_id"),
            )
            for item in rows
        ]
        self.db.add_all(payload)
        self.db.flush()

    def get_item_template_price(
        self,
        *,
        template_id: int,
        price_id: int,
    ) -> OperationItemPrice | None:
        stmt = select(OperationItemPrice).where(
            OperationItemPrice.id == price_id,
            OperationItemPrice.template_id == template_id,
        )
        return self.db.scalar(stmt)

    def delete_item_template_price(self, *, row: OperationItemPrice) -> None:
        self.db.delete(row)
        self.db.flush()

    def has_item_template_price(
        self,
        *,
        template_id: int,
        unit_price: Decimal,
        recorded_at: date | None = None,
    ) -> bool:
        conditions = [
            OperationItemPrice.template_id == template_id,
            OperationItemPrice.unit_price == unit_price,
        ]
        if recorded_at is not None:
            conditions.append(OperationItemPrice.recorded_at == recorded_at)
        stmt = select(OperationItemPrice.id).where(*conditions).limit(1)
        return self.db.scalar(stmt) is not None

    def cleanup_duplicate_item_template_prices(self, *, template_id: int) -> int:
        rows = self.list_item_prices(template_id=template_id, limit=10000)
        seen: set[tuple[date, Decimal]] = set()
        deleted = 0
        for row in rows:
            key = (row.recorded_at, row.unit_price)
            if key in seen:
                self.db.delete(row)
                deleted += 1
                continue
            seen.add(key)
        if deleted:
            self.db.flush()
        return deleted

    def list_item_templates_for_names_ci(
        self,
        *,
        user_id: int,
        names_ci: list[str],
        include_archived: bool = False,
    ) -> list[OperationItemTemplate]:
        if not names_ci:
            return []
        conditions = [
            OperationItemTemplate.user_id == user_id,
            OperationItemTemplate.name_ci.in_(names_ci),
        ]
        if not include_archived:
            conditions.append(OperationItemTemplate.is_archived.is_(False))
        stmt = select(OperationItemTemplate).where(*conditions)
        return list(self.db.scalars(stmt))

    def list_item_templates(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        q: str | None,
        brand_id: int | None = None,
    ) -> tuple[list[OperationItemTemplate], int]:
        conditions = [
            OperationItemTemplate.user_id == user_id,
            OperationItemTemplate.is_archived.is_(False),
        ]
        if q:
            search = " ".join(q.split())
            if search:
                like = f"%{search}%"
                conditions.append(
                    or_(
                        OperationItemTemplate.name.ilike(like),
                        OperationItemTemplate.shop_name.ilike(like),
                    )
                )
        if brand_id is not None:
            conditions.append(OperationItemTemplate.brand_id == brand_id)
        stmt = (
            select(OperationItemTemplate)
            .where(and_(*conditions))
            .order_by(
                OperationItemTemplate.use_count.desc(),
                OperationItemTemplate.last_used_at.desc().nullslast(),
                OperationItemTemplate.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count_stmt = select(func.count()).select_from(OperationItemTemplate).where(and_(*conditions))
        items = list(self.db.scalars(stmt))
        total = int(self.db.scalar(count_stmt) or 0)
        return items, total

    def get_item_template_by_id(self, *, user_id: int, template_id: int) -> OperationItemTemplate | None:
        stmt = select(OperationItemTemplate).where(
            OperationItemTemplate.user_id == user_id,
            OperationItemTemplate.id == template_id,
            OperationItemTemplate.is_archived.is_(False),
        )
        return self.db.scalar(stmt)

    def archive_item_template(self, *, user_id: int, template_id: int) -> bool:
        stmt = (
            update(OperationItemTemplate)
            .where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.id == template_id,
                OperationItemTemplate.is_archived.is_(False),
            )
            .values(is_archived=True)
        )
        result = self.db.execute(stmt)
        self.db.flush()
        return int(result.rowcount or 0) > 0

    def archive_all_item_templates(self, *, user_id: int) -> int:
        stmt = (
            update(OperationItemTemplate)
            .where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.is_archived.is_(False),
            )
            .values(is_archived=True)
        )
        result = self.db.execute(stmt)
        self.db.flush()
        return int(result.rowcount or 0)

    def update_linked_receipt_item_identity(
        self,
        *,
        user_id: int,
        template_id: int,
        shop_name: str | None,
        name: str,
    ) -> None:
        values = {"shop_name": shop_name, "name": name}
        self.db.execute(
            update(OperationReceiptItem)
            .where(
                OperationReceiptItem.user_id == user_id,
                OperationReceiptItem.template_id == template_id,
            )
            .values(**values)
        )
        self.db.execute(
            update(PlanReceiptItem)
            .where(
                PlanReceiptItem.user_id == user_id,
                PlanReceiptItem.template_id == template_id,
            )
            .values(**values)
        )
        self.db.flush()

    def update_linked_receipt_item_category(
        self,
        *,
        user_id: int,
        template_id: int,
        previous_category_id: int | None,
        category_id: int | None,
    ) -> None:
        operation_previous_categories: dict[int, set[int | None]] = {}
        for operation_id, linked_category_id in self.db.execute(
            select(OperationReceiptItem.operation_id, OperationReceiptItem.category_id).where(
                OperationReceiptItem.user_id == user_id,
                OperationReceiptItem.template_id == template_id,
            )
        ):
            operation_previous_categories.setdefault(int(operation_id), set()).add(linked_category_id)
        plan_previous_categories: dict[int, set[int | None]] = {}
        for plan_id, linked_category_id in self.db.execute(
            select(PlanReceiptItem.plan_id, PlanReceiptItem.category_id).where(
                PlanReceiptItem.user_id == user_id,
                PlanReceiptItem.template_id == template_id,
            )
        ):
            plan_previous_categories.setdefault(int(plan_id), set()).add(linked_category_id)
        self.db.execute(
            update(OperationReceiptItem)
            .where(
                OperationReceiptItem.user_id == user_id,
                OperationReceiptItem.template_id == template_id,
            )
            .values(category_id=category_id)
        )
        self.db.execute(
            update(PlanReceiptItem)
            .where(
                PlanReceiptItem.user_id == user_id,
                PlanReceiptItem.template_id == template_id,
            )
            .values(category_id=category_id)
        )
        self.db.flush()

        for operation_id, linked_previous_categories in operation_previous_categories.items():
            operation = self.db.scalar(
                select(Operation).where(
                    Operation.user_id == user_id,
                    Operation.id == int(operation_id),
                )
            )
            if operation and (
                operation.category_id in {None, previous_category_id}
                or operation.category_id in linked_previous_categories
            ):
                operation.category_id = self._single_receipt_category_id(
                    model=OperationReceiptItem,
                    parent_field=OperationReceiptItem.operation_id,
                    parent_id=int(operation_id),
                )

        for plan_id, linked_previous_categories in plan_previous_categories.items():
            plan = self.db.scalar(
                select(PlanOperation).where(
                    PlanOperation.user_id == user_id,
                    PlanOperation.id == int(plan_id),
                )
            )
            if plan and (
                plan.category_id in {None, previous_category_id}
                or plan.category_id in linked_previous_categories
            ):
                plan.category_id = self._single_receipt_category_id(
                    model=PlanReceiptItem,
                    parent_field=PlanReceiptItem.plan_id,
                    parent_id=int(plan_id),
                )
        self.db.flush()

    def _single_receipt_category_id(self, *, model, parent_field, parent_id: int) -> int | None:
        category_ids = list(
            self.db.scalars(
                select(model.category_id)
                .where(
                    parent_field == parent_id,
                    model.category_id.is_not(None),
                )
                .distinct()
            )
        )
        return int(category_ids[0]) if len(category_ids) == 1 else None

    def list_item_prices(self, *, template_id: int, limit: int = 200) -> list[OperationItemPrice]:
        stmt = (
            select(OperationItemPrice)
            .where(OperationItemPrice.template_id == template_id)
            .order_by(
                OperationItemPrice.recorded_at.desc(),
                OperationItemPrice.id.desc(),
            )
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def get_latest_prices_for_templates(self, *, template_ids: list[int]) -> dict[int, OperationItemPrice]:
        if not template_ids:
            return {}
        stmt = (
            select(OperationItemPrice)
            .where(OperationItemPrice.template_id.in_(template_ids))
            .order_by(
                OperationItemPrice.template_id.asc(),
                OperationItemPrice.recorded_at.desc(),
                OperationItemPrice.id.desc(),
            )
        )
        rows = list(self.db.scalars(stmt))
        latest_by_template: dict[int, OperationItemPrice] = {}
        for row in rows:
            key = int(row.template_id)
            if key not in latest_by_template:
                latest_by_template[key] = row
        return latest_by_template

    def list_recommendation_templates(self, *, user_id: int) -> list[OperationItemTemplate]:
        stmt = (
            select(OperationItemTemplate)
            .where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.is_archived.is_(False),
                OperationItemTemplate.recommendation_enabled.is_(True),
            )
            .order_by(OperationItemTemplate.recommendation_next_date.asc().nullslast(), OperationItemTemplate.id.asc())
        )
        return list(self.db.scalars(stmt))

    def list_item_templates_for_recommendation_management(self, *, user_id: int) -> list[OperationItemTemplate]:
        stmt = (
            select(OperationItemTemplate)
            .where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.is_archived.is_(False),
            )
            .order_by(
                OperationItemTemplate.recommendation_enabled.desc(),
                OperationItemTemplate.use_count.desc(),
                OperationItemTemplate.last_used_at.desc().nullslast(),
                OperationItemTemplate.id.desc(),
            )
        )
        return list(self.db.scalars(stmt))

    def list_item_templates_by_ids(
        self,
        *,
        user_id: int,
        template_ids: list[int],
        include_archived: bool = False,
    ) -> list[OperationItemTemplate]:
        if not template_ids:
            return []
        conditions = [
            OperationItemTemplate.user_id == user_id,
            OperationItemTemplate.id.in_(template_ids),
        ]
        if not include_archived:
            conditions.append(OperationItemTemplate.is_archived.is_(False))
        stmt = select(OperationItemTemplate).where(*conditions)
        return list(self.db.scalars(stmt))

    def get_latest_purchases_for_templates(
        self,
        *,
        user_id: int,
        template_ids: list[int],
    ) -> dict[int, tuple[date, Decimal]]:
        if not template_ids:
            return {}
        stmt = (
            select(OperationReceiptItem.template_id, Operation.operation_date, OperationReceiptItem.quantity)
            .join(Operation, Operation.id == OperationReceiptItem.operation_id)
            .where(
                OperationReceiptItem.user_id == user_id,
                OperationReceiptItem.template_id.in_(template_ids),
                Operation.kind == "expense",
            )
            .order_by(
                OperationReceiptItem.template_id.asc(),
                Operation.operation_date.desc(),
                OperationReceiptItem.id.desc(),
            )
        )
        latest: dict[int, tuple[date, Decimal]] = {}
        for template_id, operation_date, quantity in self.db.execute(stmt):
            key = int(template_id)
            if key not in latest:
                latest[key] = (operation_date, Decimal(quantity))
        return latest
