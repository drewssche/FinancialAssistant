from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Select, and_, asc, case, delete, desc, func, or_, select, update
from sqlalchemy.orm import aliased
from sqlalchemy.orm import Session

from app.db.models import (
    Category,
    Operation,
    OperationItemPrice,
    OperationItemTemplate,
    OperationReceiptItem,
    PlanOperationEvent,
)
from app.repositories.operation_item_template_repo import OperationItemTemplateRepository


class OperationRepository:
    def __init__(self, db: Session):
        self.db = db
        self.item_templates = OperationItemTemplateRepository(db)

    def _build_list_conditions(
        self,
        *,
        user_id: int,
        kind: str | None,
        date_from: date | None,
        date_to: date | None,
        category_id: int | None,
        q: str | None,
        item_template_id: int | None = None,
        receipt_only: bool = False,
        uncategorized_only: bool = False,
        min_amount: Decimal | None = None,
        currency_scope: str = "all",
        base_currency: str = "BYN",
    ) -> list:
        conditions = [Operation.user_id == user_id]

        if kind:
            conditions.append(Operation.kind == kind)
        if date_from:
            conditions.append(Operation.operation_date >= date_from)
        if date_to:
            conditions.append(Operation.operation_date <= date_to)
        if category_id is not None:
            conditions.append(
                or_(
                    Operation.category_id == category_id,
                    select(OperationReceiptItem.id)
                    .where(
                        OperationReceiptItem.user_id == user_id,
                        OperationReceiptItem.operation_id == Operation.id,
                        OperationReceiptItem.category_id == category_id,
                    )
                    .exists(),
                )
            )
        if item_template_id is not None:
            conditions.append(
                select(OperationReceiptItem.id)
                .where(
                    OperationReceiptItem.user_id == user_id,
                    OperationReceiptItem.operation_id == Operation.id,
                    OperationReceiptItem.template_id == item_template_id,
                )
                .exists()
            )
        if uncategorized_only:
            conditions.append(
                and_(
                    Operation.category_id.is_(None),
                    ~select(OperationReceiptItem.id)
                    .where(
                        OperationReceiptItem.user_id == user_id,
                        OperationReceiptItem.operation_id == Operation.id,
                        OperationReceiptItem.category_id.is_not(None),
                    )
                    .exists(),
                )
            )
        if min_amount is not None:
            conditions.append(Operation.amount >= min_amount)
        if currency_scope == "base":
            conditions.append(Operation.currency == base_currency)
        elif currency_scope == "foreign":
            conditions.append(Operation.currency != base_currency)
        if receipt_only:
            conditions.append(
                select(OperationReceiptItem.id)
                .where(
                    OperationReceiptItem.user_id == user_id,
                    OperationReceiptItem.operation_id == Operation.id,
                )
                .exists()
            )
        if q:
            search = q.strip()
            if search:
                search_cf = search.casefold()
                variants = {search}
                variants.add(search.lower())
                variants.add(search.upper())
                variants.add(search[:1].upper() + search[1:])
                search_clauses = []
                receipt_category = aliased(Category)
                for variant in variants:
                    like = f"%{variant}%"
                    search_clauses.extend(
                        [
                            Operation.note.like(like),
                            Category.name.like(like),
                            Operation.kind.ilike(like),
                            select(OperationReceiptItem.id)
                            .join(receipt_category, receipt_category.id == OperationReceiptItem.category_id)
                            .where(
                                OperationReceiptItem.user_id == user_id,
                                OperationReceiptItem.operation_id == Operation.id,
                                receipt_category.name.like(like),
                            )
                            .exists(),
                        ]
                    )
                if "доход".startswith(search_cf):
                    search_clauses.append(Operation.kind == "income")
                if "расход".startswith(search_cf):
                    search_clauses.append(Operation.kind == "expense")
                conditions.append(or_(*search_clauses))
        return conditions

    def create(
        self,
        user_id: int,
        kind: str,
        amount: Decimal,
        original_amount: Decimal,
        currency: str,
        base_currency: str,
        fx_rate: Decimal,
        operation_date: date,
        category_id: int | None,
        note: str | None,
    ) -> Operation:
        operation = Operation(
            user_id=user_id,
            kind=kind,
            amount=amount,
            original_amount=original_amount,
            currency=currency,
            base_currency=base_currency,
            fx_rate=fx_rate,
            operation_date=operation_date,
            category_id=category_id,
            note=note,
        )
        self.db.add(operation)
        self.db.flush()
        return operation

    def restore(self, *, user_id: int, snapshot: dict) -> Operation:
        operation = Operation(
            id=int(snapshot["id"]),
            user_id=user_id,
            kind=snapshot["kind"],
            amount=Decimal(snapshot["amount"]),
            original_amount=Decimal(snapshot["original_amount"]),
            currency=snapshot["currency"],
            base_currency=snapshot["base_currency"],
            fx_rate=Decimal(snapshot["fx_rate"]),
            operation_date=date.fromisoformat(snapshot["operation_date"]),
            category_id=snapshot.get("category_id"),
            note=snapshot.get("note"),
        )
        if snapshot.get("created_at"):
            operation.created_at = datetime.fromisoformat(snapshot["created_at"])
        self.db.add(operation)
        self.db.flush()
        return operation

    def get_by_id(self, user_id: int, operation_id: int) -> Operation | None:
        stmt = select(Operation).where(Operation.user_id == user_id, Operation.id == operation_id)
        return self.db.scalar(stmt)

    def list_filtered(
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
        item_template_id: int | None = None,
        receipt_only: bool = False,
        uncategorized_only: bool = False,
        min_amount: Decimal | None = None,
        currency_scope: str = "all",
        base_currency: str = "BYN",
    ) -> tuple[list[Operation], int]:
        conditions = self._build_list_conditions(
            user_id=user_id,
            kind=kind,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            q=q,
            item_template_id=item_template_id,
            receipt_only=receipt_only,
            uncategorized_only=uncategorized_only,
            min_amount=min_amount,
            currency_scope=currency_scope,
            base_currency=base_currency,
        )

        base_stmt: Select[tuple[Operation]] = (
            select(Operation)
            .outerjoin(Category, Category.id == Operation.category_id)
            .where(and_(*conditions))
        )
        count_stmt = (
            select(func.count())
            .select_from(Operation)
            .outerjoin(Category, Category.id == Operation.category_id)
            .where(and_(*conditions))
        )

        sort_column = {
            "operation_date": Operation.operation_date,
            "amount": Operation.amount,
            "created_at": Operation.created_at,
        }[sort_by]
        order_expr = asc(sort_column) if sort_dir == "asc" else desc(sort_column)

        stmt = (
            base_stmt.order_by(order_expr, Operation.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.scalars(stmt))
        total = int(self.db.scalar(count_stmt) or 0)
        return items, total

    def list_filtered_all(
        self,
        *,
        user_id: int,
        sort_by: str,
        sort_dir: str,
        kind: str | None,
        date_from: date | None,
        date_to: date | None,
        category_id: int | None,
        q: str | None,
        item_template_id: int | None = None,
        receipt_only: bool = False,
        uncategorized_only: bool = False,
        min_amount: Decimal | None = None,
        currency_scope: str = "all",
        base_currency: str = "BYN",
        limit: int | None = None,
    ) -> list[Operation]:
        conditions = self._build_list_conditions(
            user_id=user_id,
            kind=kind,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            q=q,
            item_template_id=item_template_id,
            receipt_only=receipt_only,
            uncategorized_only=uncategorized_only,
            min_amount=min_amount,
            currency_scope=currency_scope,
            base_currency=base_currency,
        )
        sort_column = {
            "operation_date": Operation.operation_date,
            "amount": Operation.amount,
            "created_at": Operation.created_at,
        }[sort_by]
        order_expr = asc(sort_column) if sort_dir == "asc" else desc(sort_column)
        stmt = (
            select(Operation)
            .outerjoin(Category, Category.id == Operation.category_id)
            .where(and_(*conditions))
            .order_by(order_expr, Operation.id.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt))

    def summary_filtered(
        self,
        *,
        user_id: int,
        kind: str | None,
        date_from: date | None,
        date_to: date | None,
        category_id: int | None,
        q: str | None,
        item_template_id: int | None = None,
        receipt_only: bool = False,
        uncategorized_only: bool = False,
        min_amount: Decimal | None = None,
        currency_scope: str = "all",
        base_currency: str = "BYN",
    ) -> tuple[Decimal, Decimal, int]:
        conditions = self._build_list_conditions(
            user_id=user_id,
            kind=kind,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            q=q,
            item_template_id=item_template_id,
            receipt_only=receipt_only,
            uncategorized_only=uncategorized_only,
            min_amount=min_amount,
            currency_scope=currency_scope,
            base_currency=base_currency,
        )
        stmt = (
            select(
                func.coalesce(func.sum(case((Operation.kind == "income", Operation.amount), else_=0)), 0),
                func.coalesce(func.sum(case((Operation.kind == "expense", Operation.amount), else_=0)), 0),
                func.count(),
            )
            .select_from(Operation)
            .outerjoin(Category, Category.id == Operation.category_id)
            .where(and_(*conditions))
        )
        income_total, expense_total, total = self.db.execute(stmt).one()
        return Decimal(income_total or 0), Decimal(expense_total or 0), int(total or 0)

    def update(self, operation: Operation, updates: dict) -> Operation:
        for key, value in updates.items():
            setattr(operation, key, value)
        self.db.flush()
        return operation

    def delete(self, operation: Operation) -> None:
        self.db.execute(
            update(OperationItemPrice)
            .where(OperationItemPrice.source_operation_id == operation.id)
            .values(source_operation_id=None)
        )
        self.db.execute(
            delete(OperationReceiptItem).where(
                OperationReceiptItem.user_id == operation.user_id,
                OperationReceiptItem.operation_id == operation.id,
            )
        )
        self.db.delete(operation)
        self.db.flush()

    def replace_receipt_items(
        self,
        *,
        user_id: int,
        operation_id: int,
        items: list[dict],
    ) -> list[OperationReceiptItem]:
        self.db.execute(
            delete(OperationReceiptItem).where(
                OperationReceiptItem.user_id == user_id,
                OperationReceiptItem.operation_id == operation_id,
            )
        )
        created: list[OperationReceiptItem] = []
        for payload in items:
            row = OperationReceiptItem(
                operation_id=operation_id,
                user_id=user_id,
                template_id=payload.get("template_id"),
                category_id=payload.get("category_id"),
                shop_name=payload.get("shop_name"),
                name=payload["name"],
                quantity=payload["quantity"],
                unit_price=payload["unit_price"],
                is_discounted=bool(payload.get("is_discounted")),
                regular_unit_price=payload.get("regular_unit_price"),
                discount_type=payload.get("discount_type"),
                line_total=payload["line_total"],
                note=payload.get("note"),
            )
            self.db.add(row)
            created.append(row)
        self.db.flush()
        return created

    def restore_receipt_items(
        self,
        *,
        user_id: int,
        operation_id: int,
        items: list[dict],
    ) -> list[OperationReceiptItem]:
        created: list[OperationReceiptItem] = []
        for payload in items:
            row = OperationReceiptItem(
                id=int(payload["id"]),
                operation_id=operation_id,
                user_id=user_id,
                template_id=payload.get("template_id"),
                category_id=payload.get("category_id"),
                shop_name=payload.get("shop_name"),
                name=payload["name"],
                quantity=Decimal(payload["quantity"]),
                unit_price=Decimal(payload["unit_price"]),
                is_discounted=bool(payload.get("is_discounted")),
                regular_unit_price=(
                    Decimal(payload["regular_unit_price"])
                    if payload.get("regular_unit_price") not in (None, "")
                    else None
                ),
                discount_type=payload.get("discount_type"),
                line_total=Decimal(payload["line_total"]),
                note=payload.get("note"),
            )
            if payload.get("created_at"):
                row.created_at = datetime.fromisoformat(payload["created_at"])
            self.db.add(row)
            created.append(row)
        self.db.flush()
        return created

    def list_item_price_ids_for_operation(self, *, operation_id: int) -> list[int]:
        return [
            int(item_id)
            for item_id in self.db.scalars(
                select(OperationItemPrice.id).where(OperationItemPrice.source_operation_id == operation_id)
            )
        ]

    def restore_item_price_links(self, *, operation_id: int, price_ids: list[int]) -> None:
        if not price_ids:
            return
        rows = list(
            self.db.scalars(
                select(OperationItemPrice).where(OperationItemPrice.id.in_(price_ids))
            )
        )
        for row in rows:
            row.source_operation_id = operation_id
        self.db.flush()

    def list_receipt_items_for_operations(
        self,
        *,
        user_id: int,
        operation_ids: list[int],
    ) -> dict[int, list[OperationReceiptItem]]:
        if not operation_ids:
            return {}
        stmt = (
            select(OperationReceiptItem)
            .where(
                OperationReceiptItem.user_id == user_id,
                OperationReceiptItem.operation_id.in_(operation_ids),
            )
            .order_by(OperationReceiptItem.id.asc())
        )
        rows = list(self.db.scalars(stmt))
        grouped: dict[int, list[OperationReceiptItem]] = {op_id: [] for op_id in operation_ids}
        for row in rows:
            grouped.setdefault(int(row.operation_id), []).append(row)
        return grouped

    def list_source_plan_ids_for_operations(self, *, user_id: int, operation_ids: list[int]) -> dict[int, int]:
        if not operation_ids:
            return {}
        stmt = (
            select(PlanOperationEvent.operation_id, PlanOperationEvent.plan_id)
            .where(
                PlanOperationEvent.user_id == user_id,
                PlanOperationEvent.event_type == "confirmed",
                PlanOperationEvent.operation_id.in_(operation_ids),
            )
            .order_by(PlanOperationEvent.id.desc())
        )
        result: dict[int, int] = {}
        for operation_id, plan_id in self.db.execute(stmt):
            if operation_id is not None and int(operation_id) not in result:
                result[int(operation_id)] = int(plan_id)
        return result

    def get_item_template_by_name_ci(
        self,
        *,
        user_id: int,
        name_ci: str,
        shop_name_ci: str | None,
        include_archived: bool = False,
    ) -> OperationItemTemplate | None:
        return self.item_templates.get_item_template_by_name_ci(
            user_id=user_id,
            name_ci=name_ci,
            shop_name_ci=shop_name_ci,
            include_archived=include_archived,
        )

    def create_item_template(
        self,
        *,
        user_id: int,
        shop_name: str | None,
        shop_name_ci: str | None,
        name: str,
        name_ci: str,
        last_category_id: int | None,
        flush: bool = True,
    ) -> OperationItemTemplate:
        return self.item_templates.create_item_template(
            user_id=user_id,
            shop_name=shop_name,
            shop_name_ci=shop_name_ci,
            name=name,
            name_ci=name_ci,
            last_category_id=last_category_id,
            flush=flush,
        )

    def touch_item_template(
        self,
        *,
        item: OperationItemTemplate,
        last_category_id: int | None,
        flush: bool = True,
    ) -> OperationItemTemplate:
        return self.item_templates.touch_item_template(
            item=item,
            last_category_id=last_category_id,
            flush=flush,
        )

    def add_item_template_price(
        self,
        *,
        template_id: int,
        unit_price: Decimal,
        recorded_at: date,
        source_operation_id: int | None,
        flush: bool = True,
    ) -> OperationItemPrice:
        return self.item_templates.add_item_template_price(
            template_id=template_id,
            unit_price=unit_price,
            recorded_at=recorded_at,
            source_operation_id=source_operation_id,
            flush=flush,
        )

    def add_item_template_prices_bulk(self, *, rows: list[dict]) -> None:
        self.item_templates.add_item_template_prices_bulk(rows=rows)

    def has_item_template_price(self, *, template_id: int, unit_price: Decimal) -> bool:
        return self.item_templates.has_item_template_price(template_id=template_id, unit_price=unit_price)

    def cleanup_duplicate_item_template_prices(self, *, template_id: int) -> int:
        return self.item_templates.cleanup_duplicate_item_template_prices(template_id=template_id)

    def list_item_templates_for_names_ci(
        self,
        *,
        user_id: int,
        names_ci: list[str],
        include_archived: bool = False,
    ) -> list[OperationItemTemplate]:
        return self.item_templates.list_item_templates_for_names_ci(
            user_id=user_id,
            names_ci=names_ci,
            include_archived=include_archived,
        )

    def list_item_templates(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        q: str | None,
    ) -> tuple[list[OperationItemTemplate], int]:
        return self.item_templates.list_item_templates(
            user_id=user_id,
            page=page,
            page_size=page_size,
            q=q,
        )

    def get_item_template_by_id(self, *, user_id: int, template_id: int) -> OperationItemTemplate | None:
        return self.item_templates.get_item_template_by_id(user_id=user_id, template_id=template_id)

    def archive_item_template(self, *, user_id: int, template_id: int) -> bool:
        return self.item_templates.archive_item_template(user_id=user_id, template_id=template_id)

    def archive_all_item_templates(self, *, user_id: int) -> int:
        return self.item_templates.archive_all_item_templates(user_id=user_id)

    def update_linked_receipt_item_identity(
        self,
        *,
        user_id: int,
        template_id: int,
        shop_name: str | None,
        name: str,
    ) -> None:
        self.item_templates.update_linked_receipt_item_identity(
            user_id=user_id,
            template_id=template_id,
            shop_name=shop_name,
            name=name,
        )

    def list_item_prices(self, *, template_id: int, limit: int = 200) -> list[OperationItemPrice]:
        return self.item_templates.list_item_prices(template_id=template_id, limit=limit)

    def get_latest_prices_for_templates(self, *, template_ids: list[int]) -> dict[int, OperationItemPrice]:
        return self.item_templates.get_latest_prices_for_templates(template_ids=template_ids)

    def list_recommendation_templates(self, *, user_id: int) -> list[OperationItemTemplate]:
        return self.item_templates.list_recommendation_templates(user_id=user_id)

    def get_latest_purchases_for_templates(
        self,
        *,
        user_id: int,
        template_ids: list[int],
    ) -> dict[int, tuple[date, Decimal]]:
        return self.item_templates.get_latest_purchases_for_templates(
            user_id=user_id,
            template_ids=template_ids,
        )

    def summary_for_period(self, user_id: int, date_from: date, date_to: date):
        income_stmt = select(func.coalesce(func.sum(Operation.amount), 0)).where(
            and_(
                Operation.user_id == user_id,
                Operation.kind == "income",
                Operation.operation_date >= date_from,
                Operation.operation_date <= date_to,
            )
        )
        expense_stmt = select(func.coalesce(func.sum(Operation.amount), 0)).where(
            and_(
                Operation.user_id == user_id,
                Operation.kind == "expense",
                Operation.operation_date >= date_from,
                Operation.operation_date <= date_to,
            )
        )
        income_total = self.db.scalar(income_stmt)
        expense_total = self.db.scalar(expense_stmt)
        return income_total, expense_total

    def summary_with_count_for_period(self, *, user_id: int, date_from: date, date_to: date) -> tuple[Decimal, Decimal, int]:
        stmt = (
            select(
                func.coalesce(func.sum(case((Operation.kind == "income", Operation.amount), else_=0)), 0),
                func.coalesce(func.sum(case((Operation.kind == "expense", Operation.amount), else_=0)), 0),
                func.count(),
            )
            .where(
                and_(
                    Operation.user_id == user_id,
                    Operation.operation_date >= date_from,
                    Operation.operation_date <= date_to,
                )
            )
        )
        income_total, expense_total, total = self.db.execute(stmt).one()
        return Decimal(income_total or 0), Decimal(expense_total or 0), int(total or 0)

    def aggregate_daily_for_period(self, *, user_id: int, date_from: date, date_to: date) -> list[dict]:
        stmt = (
            select(
                Operation.operation_date,
                func.coalesce(func.sum(case((Operation.kind == "income", Operation.amount), else_=0)), 0),
                func.coalesce(func.sum(case((Operation.kind == "expense", Operation.amount), else_=0)), 0),
                func.count(),
            )
            .where(
                and_(
                    Operation.user_id == user_id,
                    Operation.operation_date >= date_from,
                    Operation.operation_date <= date_to,
                )
            )
            .group_by(Operation.operation_date)
            .order_by(Operation.operation_date.asc())
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "operation_date": row[0],
                "income_total": Decimal(row[1] or 0),
                "expense_total": Decimal(row[2] or 0),
                "operations_count": int(row[3] or 0),
            }
            for row in rows
        ]

    def aggregate_positions_for_period(self, *, user_id: int, date_from: date, date_to: date) -> list[dict]:
        display_name = func.coalesce(OperationItemTemplate.name, OperationReceiptItem.name)
        display_shop = func.coalesce(OperationItemTemplate.shop_name, OperationReceiptItem.shop_name)
        stmt = (
            select(
                OperationReceiptItem.template_id,
                display_name.label("position_name"),
                display_shop.label("shop_name"),
                Operation.operation_date,
                func.count(func.distinct(Operation.id)).label("purchases_count"),
                func.coalesce(func.sum(OperationReceiptItem.quantity), 0).label("quantity_total"),
                func.coalesce(func.sum(OperationReceiptItem.line_total), 0).label("amount_total"),
            )
            .join(Operation, Operation.id == OperationReceiptItem.operation_id)
            .outerjoin(OperationItemTemplate, OperationItemTemplate.id == OperationReceiptItem.template_id)
            .where(
                Operation.user_id == user_id,
                Operation.kind == "expense",
                Operation.operation_date >= date_from,
                Operation.operation_date <= date_to,
            )
            .group_by(
                OperationReceiptItem.template_id,
                display_name,
                display_shop,
                Operation.operation_date,
            )
            .order_by(Operation.operation_date.asc(), display_name.asc())
        )
        return [
            {
                "template_id": int(row.template_id) if row.template_id is not None else None,
                "name": str(row.position_name or "Позиция"),
                "shop_name": str(row.shop_name) if row.shop_name else None,
                "operation_date": row.operation_date,
                "purchases_count": int(row.purchases_count or 0),
                "quantity_total": Decimal(row.quantity_total or 0),
                "amount_total": Decimal(row.amount_total or 0),
            }
            for row in self.db.execute(stmt)
        ]

    def list_for_period(self, user_id: int, date_from: date, date_to: date) -> list[Operation]:
        stmt = (
            select(Operation)
            .where(
                and_(
                    Operation.user_id == user_id,
                    Operation.operation_date >= date_from,
                    Operation.operation_date <= date_to,
                )
            )
            .order_by(Operation.operation_date.asc(), Operation.id.asc())
        )
        return list(self.db.scalars(stmt))

    def list_snapshot_for_period(self, *, user_id: int, date_from: date, date_to: date) -> list[dict]:
        stmt = (
            select(
                Operation.id,
                Operation.kind,
                Operation.amount,
                Operation.operation_date,
                Operation.category_id,
                Operation.note,
            )
            .where(
                and_(
                    Operation.user_id == user_id,
                    Operation.operation_date >= date_from,
                    Operation.operation_date <= date_to,
                )
            )
            .order_by(Operation.operation_date.asc(), Operation.id.asc())
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "id": int(row[0]),
                "kind": str(row[1]),
                "amount": Decimal(row[2] or 0),
                "operation_date": row[3],
                "category_id": int(row[4]) if row[4] is not None else None,
                "note": row[5],
            }
            for row in rows
        ]

    def first_operation_date(self, user_id: int) -> date | None:
        stmt = select(func.min(Operation.operation_date)).where(Operation.user_id == user_id)
        return self.db.scalar(stmt)
