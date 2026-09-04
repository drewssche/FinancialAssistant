import unicodedata

from app.core.cache import (
    invalidate_dashboard_analytics_cache,
    invalidate_item_templates_cache,
    invalidate_operations_cache,
    invalidate_plans_cache,
)
from app.repositories.item_source_repo import ItemSourceRepository
from app.services.activity_service import ActivityService


class ItemSourceService:
    ACTIVITY_FIELDS = ["name", "image_id", "is_archived"]
    ACTIVITY_LABELS = {
        "name": "Название",
        "image_id": "Логотип",
        "is_archived": "Архив",
    }

    def __init__(self, db):
        self.db = db
        self.repo = ItemSourceRepository(db)
        self.activity = ActivityService(db)

    @staticmethod
    def normalize_name(name: str) -> tuple[str, str]:
        normalized = unicodedata.normalize("NFKC", " ".join(str(name or "").split()))
        if not normalized:
            raise ValueError("Source name must not be empty")
        if len(normalized) > 160:
            raise ValueError("Source name must be at most 160 characters")
        return normalized, normalized.casefold()

    @staticmethod
    def _serialize(item, positions_count: int = 0) -> dict:
        return {
            "id": int(item.id),
            "name": item.name,
            "image_id": item.image_id,
            "is_archived": bool(item.is_archived),
            "positions_count": int(positions_count or 0),
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    def list(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        q: str | None,
        include_archived: bool,
    ) -> tuple[list[dict], int]:
        items, total = self.repo.list(
            user_id=user_id,
            page=page,
            page_size=page_size,
            q=q,
            include_archived=include_archived,
        )
        counts = self.repo.position_counts(
            user_id=user_id, source_ids=[int(item.id) for item in items]
        )
        return [
            self._serialize(item, counts.get(int(item.id), 0)) for item in items
        ], total

    def get(
        self, *, user_id: int, source_id: int, include_archived: bool = False
    ) -> dict:
        item = self.repo.get_by_id(
            user_id=user_id,
            source_id=source_id,
            include_archived=include_archived,
        )
        if item is None:
            raise LookupError("Source not found")
        counts = self.repo.position_counts(user_id=user_id, source_ids=[source_id])
        return self._serialize(item, counts.get(source_id, 0))

    def resolve(
        self,
        *,
        user_id: int,
        source_id: int | None,
        shop_name: str | None,
        unchanged_source_id: int | None = None,
        create_from_name: bool = True,
    ):
        if source_id is not None:
            source = self.repo.get_by_id(user_id=user_id, source_id=int(source_id))
            if (
                source is None
                and unchanged_source_id is not None
                and int(source_id) == int(unchanged_source_id)
            ):
                source = self.repo.get_by_id(
                    user_id=user_id,
                    source_id=int(source_id),
                    include_archived=True,
                )
            if source is None:
                raise ValueError("Source not found")
            return source
        if not str(shop_name or "").strip():
            return None
        name, name_ci = self.normalize_name(str(shop_name))
        source = self.repo.get_by_name_ci(
            user_id=user_id, name_ci=name_ci, include_archived=True
        )
        if source is not None and source.is_archived:
            if not create_from_name:
                raise ValueError("Source not found")
            source.is_archived = False
        if source is None and create_from_name:
            source = self.repo.create(user_id=user_id, name=name, name_ci=name_ci)
        return source

    def create(self, *, user_id: int, name: str) -> dict:
        normalized_name, name_ci = self.normalize_name(name)
        existing = self.repo.get_by_name_ci(
            user_id=user_id, name_ci=name_ci, include_archived=True
        )
        if existing is not None and not existing.is_archived:
            raise ValueError("Source with the same name already exists")
        if existing is None:
            item = self.repo.create(
                user_id=user_id, name=normalized_name, name_ci=name_ci
            )
            self.activity.record_created(
                user_id=user_id,
                actor_user_id=user_id,
                entity_type="item_source",
                entity_id=int(item.id),
                title="Источник создан",
                metadata=ActivityService.snapshot(item, self.ACTIVITY_FIELDS),
            )
        else:
            item = existing
            before = ActivityService.snapshot(item, self.ACTIVITY_FIELDS)
            item.name = normalized_name
            item.name_ci = name_ci
            item.is_archived = False
            self.activity.record_updated(
                user_id=user_id,
                actor_user_id=user_id,
                entity_type="item_source",
                entity_id=int(item.id),
                before=before,
                after=ActivityService.snapshot(item, self.ACTIVITY_FIELDS),
                labels=self.ACTIVITY_LABELS,
                title="Источник восстановлен",
            )
        self.db.commit()
        self._invalidate(user_id)
        return self.get(user_id=user_id, source_id=int(item.id))

    def update(self, *, user_id: int, source_id: int, updates: dict) -> dict:
        item = self.repo.get_by_id(user_id=user_id, source_id=source_id)
        if item is None:
            raise LookupError("Source not found")
        before = ActivityService.snapshot(item, self.ACTIVITY_FIELDS)
        if "name" in updates:
            name, name_ci = self.normalize_name(updates["name"])
            duplicate = self.repo.get_by_name_ci(
                user_id=user_id, name_ci=name_ci, include_archived=True
            )
            if duplicate is not None and int(duplicate.id) != int(item.id):
                raise ValueError("Source with the same name already exists")
            item.name = name
            item.name_ci = name_ci
            self.repo.rename_linked_templates(user_id=user_id, source=item)
        self.activity.record_updated(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="item_source",
            entity_id=int(item.id),
            before=before,
            after=ActivityService.snapshot(item, self.ACTIVITY_FIELDS),
            labels=self.ACTIVITY_LABELS,
            title="Источник изменён",
        )
        self.db.commit()
        self._invalidate(user_id)
        return self.get(user_id=user_id, source_id=source_id)

    def archive(self, *, user_id: int, source_id: int) -> int:
        item = self.repo.get_by_id(user_id=user_id, source_id=source_id)
        if item is None:
            raise LookupError("Source not found")
        archived_positions = self.repo.archive_with_templates(
            user_id=user_id, source=item
        )
        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="item_source",
            entity_id=int(item.id),
            event_type="deleted",
            title="Источник удалён",
            metadata={
                **ActivityService.snapshot(item, self.ACTIVITY_FIELDS),
                "archived_positions": archived_positions,
            },
        )
        self.db.commit()
        self._invalidate(user_id)
        return archived_positions

    @staticmethod
    def _invalidate(user_id: int) -> None:
        invalidate_item_templates_cache(user_id)
        invalidate_operations_cache(user_id)
        invalidate_plans_cache(user_id)
        invalidate_dashboard_analytics_cache(user_id)
