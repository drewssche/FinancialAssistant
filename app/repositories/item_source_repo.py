from __future__ import annotations

from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import Session

from app.db.models import (
    ItemSource,
    OperationItemTemplate,
    OperationReceiptItem,
    PlanReceiptItem,
)


class ItemSourceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        *,
        user_id: int,
        source_id: int,
        include_archived: bool = False,
    ) -> ItemSource | None:
        conditions = [ItemSource.user_id == user_id, ItemSource.id == source_id]
        if not include_archived:
            conditions.append(ItemSource.is_archived.is_(False))
        return self.db.scalar(select(ItemSource).where(*conditions))

    def get_by_name_ci(
        self,
        *,
        user_id: int,
        name_ci: str,
        include_archived: bool = False,
    ) -> ItemSource | None:
        conditions = [ItemSource.user_id == user_id, ItemSource.name_ci == name_ci]
        if not include_archived:
            conditions.append(ItemSource.is_archived.is_(False))
        return self.db.scalar(select(ItemSource).where(*conditions))

    def create(self, *, user_id: int, name: str, name_ci: str) -> ItemSource:
        item = ItemSource(
            user_id=user_id, name=name, name_ci=name_ci, is_archived=False
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
    ) -> tuple[list[ItemSource], int]:
        conditions = [ItemSource.user_id == user_id]
        if not include_archived:
            conditions.append(ItemSource.is_archived.is_(False))
        search = " ".join((q or "").split())
        if search:
            conditions.append(ItemSource.name.ilike(f"%{search}%"))
        where = and_(*conditions)
        rows = list(
            self.db.scalars(
                select(ItemSource)
                .where(where)
                .order_by(
                    ItemSource.is_archived.asc(),
                    ItemSource.name_ci.asc(),
                    ItemSource.id.asc(),
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        total = int(
            self.db.scalar(select(func.count()).select_from(ItemSource).where(where))
            or 0
        )
        return rows, total

    def position_counts(self, *, user_id: int, source_ids: list[int]) -> dict[int, int]:
        normalized_ids = sorted(
            {int(source_id) for source_id in source_ids if int(source_id) > 0}
        )
        if not normalized_ids:
            return {}
        rows = self.db.execute(
            select(
                OperationItemTemplate.source_id, func.count(OperationItemTemplate.id)
            )
            .where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.source_id.in_(normalized_ids),
                OperationItemTemplate.is_archived.is_(False),
            )
            .group_by(OperationItemTemplate.source_id)
        )
        return {int(source_id): int(count or 0) for source_id, count in rows}

    def rename_linked_templates(self, *, user_id: int, source: ItemSource) -> None:
        template_ids = select(OperationItemTemplate.id).where(
            OperationItemTemplate.user_id == user_id,
            OperationItemTemplate.source_id == source.id,
        )
        self.db.execute(
            update(OperationItemTemplate)
            .where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.source_id == source.id,
            )
            .values(shop_name=source.name, shop_name_ci=source.name_ci)
        )
        self.db.execute(
            update(OperationReceiptItem)
            .where(
                OperationReceiptItem.user_id == user_id,
                OperationReceiptItem.template_id.in_(template_ids),
            )
            .values(shop_name=source.name)
        )
        self.db.execute(
            update(PlanReceiptItem)
            .where(
                PlanReceiptItem.user_id == user_id,
                PlanReceiptItem.template_id.in_(template_ids),
            )
            .values(shop_name=source.name)
        )
        self.db.flush()

    def archive_with_templates(self, *, user_id: int, source: ItemSource) -> int:
        source.is_archived = True
        result = self.db.execute(
            update(OperationItemTemplate)
            .where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.source_id == source.id,
                OperationItemTemplate.is_archived.is_(False),
            )
            .values(is_archived=True)
        )
        self.db.flush()
        return int(result.rowcount or 0)
