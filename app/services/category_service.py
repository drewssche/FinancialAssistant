from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import (
    build_categories_cache_key,
    get_json,
    get_namespace_ttl_seconds,
    invalidate_categories_cache,
    invalidate_dashboard_analytics_cache,
    invalidate_item_templates_cache,
    invalidate_operations_cache,
    invalidate_plans_cache,
    set_json,
)
from app.db.models import (
    CatalogProduct,
    Category,
    Operation,
    OperationItemTemplate,
    OperationReceiptItem,
    PlanOperation,
    PlanReceiptItem,
)
from app.repositories.category_repo import CategoryRepository
from app.services.activity_service import ActivityService


class CategoryService:
    CATEGORY_FIELDS = ["name", "kind", "icon", "group_id", "include_in_statistics"]
    CATEGORY_LABELS = {
        "name": "Название",
        "kind": "Тип",
        "icon": "Иконка",
        "group_id": "Группа",
        "include_in_statistics": "В статистике",
    }
    GROUP_FIELDS = ["name", "kind", "accent_color"]
    GROUP_LABELS = {
        "name": "Название",
        "kind": "Тип",
        "accent_color": "Цвет",
    }

    def __init__(self, db: Session):
        self.db = db
        self.repo = CategoryRepository(db)
        self.activity = ActivityService(db)

    @staticmethod
    def _serialize_category_row(row) -> dict:
        payload = dict(row)
        return {
            "id": int(payload["id"]),
            "name": payload["name"],
            "icon": payload["icon"],
            "kind": payload["kind"],
            "include_in_statistics": bool(payload["include_in_statistics"]),
            "group_id": payload["group_id"],
            "is_system": bool(payload["is_system"]),
            "group_name": payload.get("group_name"),
            "group_icon": payload.get("group_icon"),
            "group_accent_color": payload.get("group_accent_color"),
        }

    @staticmethod
    def _serialize_group(group) -> dict:
        return {
            "id": int(group.id),
            "name": group.name,
            "kind": group.kind,
            "accent_color": group.accent_color,
        }

    def list_categories(self, user_id: int):
        cache_key = build_categories_cache_key(
            user_id=user_id,
            view="list",
        )
        cached = get_json(cache_key)
        if cached is not None:
            return cached["items"]
        rows = [self._serialize_category_row(row) for row in self.repo.list_for_user(user_id)]
        set_json(
            cache_key,
            {"items": rows},
            ttl_seconds=get_namespace_ttl_seconds("categories"),
        )
        return rows

    def list_categories_paginated(
        self,
        user_id: int,
        page: int,
        page_size: int,
        kind: str | None = None,
        q: str | None = None,
    ) -> tuple[list, int]:
        if kind and kind not in {"income", "expense"}:
            raise ValueError("kind must be either 'income' or 'expense'")
        cache_key = build_categories_cache_key(
            user_id=user_id,
            view="paginated",
            page=page,
            page_size=page_size,
            kind=kind,
            q=q,
        )
        cached = get_json(cache_key)
        if cached is not None:
            return cached["items"], int(cached["total"])
        rows, total = self.repo.list_for_user_paginated(
            user_id=user_id,
            page=page,
            page_size=page_size,
            kind=kind,
            q=q,
        )
        serialized_rows = [self._serialize_category_row(row) for row in rows]
        set_json(
            cache_key,
            {"items": serialized_rows, "total": total},
            ttl_seconds=get_namespace_ttl_seconds("categories"),
        )
        return serialized_rows, total

    def create_category(
        self,
        user_id: int,
        name: str,
        kind: str,
        group_id: int | None = None,
        icon: str | None = None,
        include_in_statistics: bool = True,
    ):
        if kind not in {"income", "expense"}:
            raise ValueError("kind must be either 'income' or 'expense'")
        if group_id is not None:
            group = self.repo.get_group_by_id_for_user(user_id=user_id, group_id=group_id)
            if not group:
                raise ValueError("Group not found")
            if group.kind != kind:
                raise ValueError("Group kind must match category kind")
        category = self.repo.create(
            user_id=user_id,
            name=name,
            kind=kind,
            group_id=group_id,
            icon=icon,
            include_in_statistics=include_in_statistics,
        )
        self.activity.record_created(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="category",
            entity_id=int(category.id),
            title="Категория создана",
            metadata=ActivityService.snapshot(category, self.CATEGORY_FIELDS),
        )
        self.db.commit()
        invalidate_dashboard_analytics_cache(user_id)
        invalidate_categories_cache(user_id)
        self.db.refresh(category)
        return category

    def delete_category(self, user_id: int, category_id: int) -> None:
        category = self.repo.get_by_id_for_user(user_id=user_id, category_id=category_id)
        if not category:
            raise LookupError("Category not found")
        restore_snapshot = self._build_category_restore_snapshot(
            user_id=user_id,
            category=category,
        )
        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="category",
            entity_id=int(category.id),
            event_type="deleted",
            title="Категория удалена",
            metadata={
                **ActivityService.snapshot(category, self.CATEGORY_FIELDS),
                "_restore_snapshot": restore_snapshot,
            },
        )
        self.repo.delete(category)
        self.db.commit()
        invalidate_dashboard_analytics_cache(user_id)
        invalidate_categories_cache(user_id)
        invalidate_operations_cache(user_id)
        invalidate_plans_cache(user_id)
        invalidate_item_templates_cache(user_id)

    def _build_category_restore_snapshot(self, *, user_id: int, category: Category) -> dict:
        def ids(model) -> list[int]:
            return [
                int(item_id)
                for item_id in self.db.scalars(
                    select(model.id).where(
                        model.user_id == user_id,
                        model.category_id == category.id,
                    )
                )
            ]

        template_ids = [
            int(item_id)
            for item_id in self.db.scalars(
                select(OperationItemTemplate.id).where(
                    OperationItemTemplate.user_id == user_id,
                    OperationItemTemplate.last_category_id == category.id,
                )
            )
        ]
        return {
            "version": 1,
            "category": {
                "id": int(category.id),
                "name": category.name,
                "kind": category.kind,
                "icon": category.icon,
                "group_id": category.group_id,
                "include_in_statistics": bool(category.include_in_statistics),
                "created_at": category.created_at.isoformat() if category.created_at else None,
            },
            "references": {
                "catalog_product_ids": ids(CatalogProduct),
                "operation_ids": ids(Operation),
                "receipt_item_ids": ids(OperationReceiptItem),
                "plan_ids": ids(PlanOperation),
                "plan_receipt_item_ids": ids(PlanReceiptItem),
                "item_template_ids": template_ids,
            },
        }

    def restore_deleted_category(self, *, user_id: int, category_id: int) -> Category:
        if self.repo.get_by_id_for_user(user_id=user_id, category_id=category_id) is not None:
            raise ValueError("Category already exists")
        event = self.activity.get_restore_event(
            user_id=user_id,
            entity_type="category",
            entity_id=category_id,
        )
        snapshot = dict((event.metadata_json or {})["_restore_snapshot"])
        if snapshot.get("version") != 1 or not isinstance(snapshot.get("category"), dict):
            raise ValueError("Unsupported category restore snapshot")
        category_data = dict(snapshot["category"])
        if int(category_data.get("id") or 0) != category_id:
            raise ValueError("Category restore snapshot does not match the requested category")
        group_id = category_data.get("group_id")
        if group_id is not None and self.repo.get_group_by_id_for_user(user_id=user_id, group_id=int(group_id)) is None:
            raise ValueError("The category group no longer exists")

        category = Category(
            id=category_id,
            user_id=user_id,
            name=category_data["name"],
            kind=category_data["kind"],
            icon=category_data.get("icon"),
            group_id=group_id,
            is_system=False,
            include_in_statistics=bool(category_data.get("include_in_statistics", True)),
        )
        if category_data.get("created_at"):
            category.created_at = datetime.fromisoformat(category_data["created_at"])
        self.db.add(category)
        self.db.flush()

        references = snapshot.get("references") if isinstance(snapshot.get("references"), dict) else {}
        template_ids = [
            int(item_id)
            for item_id in (references.get("item_template_ids") or [])
            if int(item_id or 0) > 0
        ]
        catalog_product_ids = {
            int(item_id)
            for item_id in (references.get("catalog_product_ids") or [])
            if int(item_id or 0) > 0
        }
        if template_ids:
            catalog_product_ids.update(
                int(product_id)
                for product_id in self.db.scalars(
                    select(OperationItemTemplate.product_id).where(
                        OperationItemTemplate.user_id == user_id,
                        OperationItemTemplate.id.in_(template_ids),
                        OperationItemTemplate.product_id.is_not(None),
                    )
                )
                if product_id is not None
            )
        self._restore_category_reference_ids(
            model=CatalogProduct,
            user_id=user_id,
            category_id=category_id,
            item_ids=sorted(catalog_product_ids),
            field="category_id",
        )
        self._restore_category_reference_ids(
            model=Operation,
            user_id=user_id,
            category_id=category_id,
            item_ids=references.get("operation_ids") or [],
            field="category_id",
        )
        self._restore_category_reference_ids(
            model=OperationReceiptItem,
            user_id=user_id,
            category_id=category_id,
            item_ids=references.get("receipt_item_ids") or [],
            field="category_id",
        )
        self._restore_category_reference_ids(
            model=PlanOperation,
            user_id=user_id,
            category_id=category_id,
            item_ids=references.get("plan_ids") or [],
            field="category_id",
        )
        self._restore_category_reference_ids(
            model=PlanReceiptItem,
            user_id=user_id,
            category_id=category_id,
            item_ids=references.get("plan_receipt_item_ids") or [],
            field="category_id",
        )
        self._restore_category_reference_ids(
            model=OperationItemTemplate,
            user_id=user_id,
            category_id=category_id,
            item_ids=template_ids,
            field="last_category_id",
        )
        self.activity.mark_restored(event, entity_id=category_id)
        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="category",
            entity_id=category_id,
            event_type="restored",
            title="Категория восстановлена",
        )
        self.db.commit()
        invalidate_dashboard_analytics_cache(user_id)
        invalidate_categories_cache(user_id)
        invalidate_operations_cache(user_id)
        invalidate_plans_cache(user_id)
        invalidate_item_templates_cache(user_id)
        self.db.refresh(category)
        return category

    def _restore_category_reference_ids(
        self,
        *,
        model,
        user_id: int,
        category_id: int,
        item_ids: list[int],
        field: str,
    ) -> None:
        normalized_ids = [int(item_id) for item_id in item_ids if int(item_id or 0) > 0]
        if not normalized_ids:
            return
        rows = list(
            self.db.scalars(
                select(model).where(
                    model.user_id == user_id,
                    model.id.in_(normalized_ids),
                )
            )
        )
        for row in rows:
            setattr(row, field, category_id)
        self.db.flush()

    def update_category(self, user_id: int, category_id: int, updates: dict):
        category = self.repo.get_by_id_for_user(user_id=user_id, category_id=category_id)
        if not category:
            raise LookupError("Category not found")
        before_activity = ActivityService.snapshot(category, self.CATEGORY_FIELDS)

        kind = updates.get("kind", category.kind)
        if kind not in {"income", "expense"}:
            raise ValueError("kind must be either 'income' or 'expense'")

        if "group_id" in updates and updates["group_id"] is not None:
            group = self.repo.get_group_by_id_for_user(user_id=user_id, group_id=updates["group_id"])
            if not group:
                raise ValueError("Group not found")
            if group.kind != kind:
                raise ValueError("Group kind must match category kind")

        if "name" in updates and not updates["name"]:
            raise ValueError("name must not be empty")

        category = self.repo.update(category, updates)
        after_activity = ActivityService.snapshot(category, self.CATEGORY_FIELDS)
        self.activity.record_updated(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="category",
            entity_id=int(category.id),
            before=before_activity,
            after=after_activity,
            labels=self.CATEGORY_LABELS,
            title="Категория изменена",
        )
        self.db.commit()
        invalidate_dashboard_analytics_cache(user_id)
        invalidate_categories_cache(user_id)
        self.db.refresh(category)
        return category

    def list_groups(self, user_id: int):
        cache_key = build_categories_cache_key(
            user_id=user_id,
            view="groups",
        )
        cached = get_json(cache_key)
        if cached is not None:
            return cached["items"]
        rows = [self._serialize_group(group) for group in self.repo.list_groups_for_user(user_id)]
        set_json(
            cache_key,
            {"items": rows},
            ttl_seconds=get_namespace_ttl_seconds("categories"),
        )
        return rows

    def create_group(
        self,
        user_id: int,
        name: str,
        kind: str,
        accent_color: str | None = None,
    ):
        if kind not in {"income", "expense"}:
            raise ValueError("kind must be either 'income' or 'expense'")
        group = self.repo.create_group(
            user_id=user_id,
            name=name,
            kind=kind,
            accent_color=accent_color,
        )
        self.activity.record_created(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="category_group",
            entity_id=int(group.id),
            title="Группа категорий создана",
            metadata=ActivityService.snapshot(group, self.GROUP_FIELDS),
        )
        self.db.commit()
        invalidate_dashboard_analytics_cache(user_id)
        invalidate_categories_cache(user_id)
        self.db.refresh(group)
        return group

    def update_group(self, user_id: int, group_id: int, updates: dict):
        group = self.repo.get_group_by_id_for_user(user_id=user_id, group_id=group_id)
        if not group:
            raise LookupError("Group not found")
        before_activity = ActivityService.snapshot(group, self.GROUP_FIELDS)
        if "name" in updates and not updates["name"]:
            raise ValueError("name must not be empty")
        group = self.repo.update_group(group, updates)
        after_activity = ActivityService.snapshot(group, self.GROUP_FIELDS)
        self.activity.record_updated(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="category_group",
            entity_id=int(group.id),
            before=before_activity,
            after=after_activity,
            labels=self.GROUP_LABELS,
            title="Группа категорий изменена",
        )
        self.db.commit()
        invalidate_dashboard_analytics_cache(user_id)
        invalidate_categories_cache(user_id)
        self.db.refresh(group)
        return group

    def delete_group(self, user_id: int, group_id: int) -> None:
        group = self.repo.get_group_by_id_for_user(user_id=user_id, group_id=group_id)
        if not group:
            raise LookupError("Group not found")
        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="category_group",
            entity_id=int(group.id),
            event_type="deleted",
            title="Группа категорий удалена",
            metadata=ActivityService.snapshot(group, self.GROUP_FIELDS),
        )
        self.repo.clear_group_refs(user_id=user_id, group_id=group_id)
        self.repo.delete_group(group)
        self.db.commit()
        invalidate_dashboard_analytics_cache(user_id)
        invalidate_categories_cache(user_id)
