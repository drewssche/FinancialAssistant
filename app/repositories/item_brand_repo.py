from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import Session

from app.core.money import allocate_largest_remainder
from app.db.models import ItemBrand, Operation, OperationItemTemplate, OperationReceiptItem


class ItemBrandRepository:
    MONEY_Q = Decimal("0.01")

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        *,
        user_id: int,
        brand_id: int,
        include_archived: bool = False,
    ) -> ItemBrand | None:
        conditions = [ItemBrand.user_id == user_id, ItemBrand.id == brand_id]
        if not include_archived:
            conditions.append(ItemBrand.is_archived.is_(False))
        return self.db.scalar(select(ItemBrand).where(*conditions))

    def get_by_name_ci(
        self,
        *,
        user_id: int,
        name_ci: str,
        include_archived: bool = False,
    ) -> ItemBrand | None:
        conditions = [ItemBrand.user_id == user_id, ItemBrand.name_ci == name_ci]
        if not include_archived:
            conditions.append(ItemBrand.is_archived.is_(False))
        return self.db.scalar(select(ItemBrand).where(*conditions))

    def create(self, *, user_id: int, name: str, name_ci: str, accent_color: str | None) -> ItemBrand:
        item = ItemBrand(
            user_id=user_id,
            name=name,
            name_ci=name_ci,
            accent_color=accent_color,
            is_archived=False,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def list(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        q: str | None,
        include_archived: bool,
    ) -> tuple[list[ItemBrand], int]:
        conditions = [ItemBrand.user_id == user_id]
        if not include_archived:
            conditions.append(ItemBrand.is_archived.is_(False))
        search = " ".join((q or "").split())
        if search:
            conditions.append(ItemBrand.name.ilike(f"%{search}%"))
        where = and_(*conditions)
        rows = list(
            self.db.scalars(
                select(ItemBrand)
                .where(where)
                .order_by(ItemBrand.is_archived.asc(), ItemBrand.name_ci.asc(), ItemBrand.id.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        total = int(self.db.scalar(select(func.count()).select_from(ItemBrand).where(where)) or 0)
        return rows, total

    def archive(self, *, brand: ItemBrand) -> None:
        brand.is_archived = True
        self.db.flush()

    def reassign_templates(self, *, user_id: int, source_brand_id: int, target_brand_id: int) -> int:
        result = self.db.execute(
            update(OperationItemTemplate)
            .where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.brand_id == source_brand_id,
            )
            .values(brand_id=target_brand_id)
        )
        self.db.flush()
        return int(result.rowcount or 0)

    def metrics_for_brands(self, *, user_id: int, brand_ids: list[int]) -> dict[int, dict]:
        normalized_ids = sorted({int(brand_id) for brand_id in brand_ids if int(brand_id) > 0})
        metrics = {
            brand_id: {
                "positions_count": 0,
                "purchases_count": 0,
                "spent_total": Decimal("0.00"),
                "last_purchase_date": None,
            }
            for brand_id in normalized_ids
        }
        if not normalized_ids:
            return metrics

        position_rows = self.db.execute(
            select(OperationItemTemplate.brand_id, func.count(OperationItemTemplate.id))
            .where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.brand_id.in_(normalized_ids),
                OperationItemTemplate.is_archived.is_(False),
            )
            .group_by(OperationItemTemplate.brand_id)
        )
        for brand_id, count in position_rows:
            metrics[int(brand_id)]["positions_count"] = int(count or 0)

        relevant_operation_ids = (
            select(OperationReceiptItem.operation_id)
            .join(OperationItemTemplate, OperationItemTemplate.id == OperationReceiptItem.template_id)
            .where(
                OperationReceiptItem.user_id == user_id,
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.brand_id.in_(normalized_ids),
            )
            .distinct()
        )
        rows = self.db.execute(
            select(
                Operation.id,
                Operation.operation_date,
                Operation.amount,
                Operation.fx_rate,
                OperationReceiptItem.line_total,
                OperationItemTemplate.brand_id,
            )
            .join(OperationReceiptItem, OperationReceiptItem.operation_id == Operation.id)
            .outerjoin(OperationItemTemplate, OperationItemTemplate.id == OperationReceiptItem.template_id)
            .where(
                Operation.user_id == user_id,
                Operation.kind == "expense",
                Operation.id.in_(relevant_operation_ids),
            )
            .order_by(Operation.id.asc(), OperationReceiptItem.id.asc())
        ).all()
        grouped: dict[int, list] = defaultdict(list)
        for row in rows:
            grouped[int(row[0])].append(row)
        operation_ids_by_brand: dict[int, set[int]] = defaultdict(set)
        for operation_id, operation_rows in grouped.items():
            fx_rate = Decimal(operation_rows[0][3] or 1)
            base_line_totals = [
                (Decimal(row[4] or 0) * fx_rate).quantize(
                    self.MONEY_Q,
                    rounding=ROUND_HALF_UP,
                )
                for row in operation_rows
            ]
            receipt_total = sum(base_line_totals, start=Decimal("0"))
            base_amount = abs(Decimal(operation_rows[0][2] or 0))
            if receipt_total <= 0 or base_amount <= 0:
                continue
            scale_down = receipt_total > base_amount
            allocated_amounts = (
                allocate_largest_remainder(
                    base_line_totals,
                    base_amount,
                    quantum=self.MONEY_Q,
                )
                if scale_down
                else base_line_totals
            )
            for row, allocated in zip(operation_rows, allocated_amounts, strict=True):
                brand_id = int(row[5]) if row[5] is not None else None
                if brand_id not in metrics:
                    continue
                bucket = metrics[brand_id]
                bucket["spent_total"] += allocated
                operation_ids_by_brand[brand_id].add(operation_id)
                purchase_date = row[1]
                if bucket["last_purchase_date"] is None or purchase_date > bucket["last_purchase_date"]:
                    bucket["last_purchase_date"] = purchase_date
        for brand_id, operation_ids in operation_ids_by_brand.items():
            metrics[brand_id]["purchases_count"] = len(operation_ids)
            metrics[brand_id]["spent_total"] = Decimal(metrics[brand_id]["spent_total"]).quantize(self.MONEY_Q)
        return metrics

    def brand_meta_for_templates(self, *, user_id: int, template_ids: list[int]) -> dict[int, dict]:
        ids = sorted({int(template_id) for template_id in template_ids if int(template_id) > 0})
        if not ids:
            return {}
        rows = self.db.execute(
            select(
                OperationItemTemplate.id,
                ItemBrand.id,
                ItemBrand.name,
                ItemBrand.accent_color,
                ItemBrand.is_archived,
            )
            .outerjoin(
                ItemBrand,
                and_(
                    ItemBrand.id == OperationItemTemplate.brand_id,
                    ItemBrand.user_id == user_id,
                ),
            )
            .where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.id.in_(ids),
            )
        )
        return {
            int(template_id): {
                "brand_id": int(brand_id) if brand_id is not None else None,
                "brand_name": name,
                "brand_accent_color": accent_color,
                "brand_is_archived": bool(is_archived) if brand_id is not None else False,
            }
            for template_id, brand_id, name, accent_color, is_archived in rows
        }
