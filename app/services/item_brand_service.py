import unicodedata

from app.core.cache import (
    invalidate_dashboard_analytics_cache,
    invalidate_item_templates_cache,
    invalidate_operations_cache,
    invalidate_plans_cache,
)
from app.repositories.item_brand_repo import ItemBrandRepository
from app.services.activity_service import ActivityService


class ItemBrandService:
    ACTIVITY_FIELDS = ["name", "accent_color", "is_archived"]
    ACTIVITY_LABELS = {
        "name": "Название",
        "accent_color": "Цвет",
        "is_archived": "Архив",
    }

    def __init__(self, db):
        self.db = db
        self.repo = ItemBrandRepository(db)
        self.activity = ActivityService(db)

    @staticmethod
    def _normalize_name(name: str) -> tuple[str, str]:
        normalized = unicodedata.normalize("NFKC", " ".join(str(name or "").split()))
        if not normalized:
            raise ValueError("Brand name must not be empty")
        return normalized, normalized.casefold()

    @staticmethod
    def _normalize_color(value: str | None) -> str | None:
        return str(value).upper() if value else None

    @staticmethod
    def _serialize(item, metrics: dict | None = None) -> dict:
        values = metrics or {}
        return {
            "id": int(item.id),
            "name": item.name,
            "accent_color": item.accent_color,
            "is_archived": bool(item.is_archived),
            "positions_count": int(values.get("positions_count") or 0),
            "purchases_count": int(values.get("purchases_count") or 0),
            "spent_total": values.get("spent_total", 0),
            "last_purchase_date": values.get("last_purchase_date"),
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
        metrics = self.repo.metrics_for_brands(user_id=user_id, brand_ids=[int(item.id) for item in items])
        return [self._serialize(item, metrics.get(int(item.id))) for item in items], total

    def get(self, *, user_id: int, brand_id: int, include_archived: bool = False) -> dict:
        item = self.repo.get_by_id(
            user_id=user_id,
            brand_id=brand_id,
            include_archived=include_archived,
        )
        if item is None:
            raise LookupError("Brand not found")
        metrics = self.repo.metrics_for_brands(user_id=user_id, brand_ids=[brand_id])
        return self._serialize(item, metrics.get(brand_id))

    def create(self, *, user_id: int, name: str, accent_color: str | None) -> dict:
        normalized_name, name_ci = self._normalize_name(name)
        existing = self.repo.get_by_name_ci(user_id=user_id, name_ci=name_ci, include_archived=True)
        if existing is None:
            item = self.repo.create(
                user_id=user_id,
                name=normalized_name,
                name_ci=name_ci,
                accent_color=self._normalize_color(accent_color),
            )
            self.activity.record_created(
                user_id=user_id,
                actor_user_id=user_id,
                entity_type="item_brand",
                entity_id=int(item.id),
                title="Бренд создан",
                metadata=ActivityService.snapshot(item, self.ACTIVITY_FIELDS),
            )
        elif not existing.is_archived:
            raise ValueError("Brand with the same name already exists")
        else:
            item = existing
            before = ActivityService.snapshot(item, self.ACTIVITY_FIELDS)
            item.is_archived = False
            item.name = normalized_name
            item.name_ci = name_ci
            item.accent_color = self._normalize_color(accent_color)
            self.activity.record_updated(
                user_id=user_id,
                actor_user_id=user_id,
                entity_type="item_brand",
                entity_id=int(item.id),
                before=before,
                after=ActivityService.snapshot(item, self.ACTIVITY_FIELDS),
                labels=self.ACTIVITY_LABELS,
                title="Бренд восстановлен",
            )
        self.db.commit()
        self._invalidate(user_id)
        return self.get(user_id=user_id, brand_id=int(item.id))

    def update(self, *, user_id: int, brand_id: int, updates: dict) -> dict:
        item = self.repo.get_by_id(user_id=user_id, brand_id=brand_id)
        if item is None:
            raise LookupError("Brand not found")
        before = ActivityService.snapshot(item, self.ACTIVITY_FIELDS)
        if "name" in updates:
            name, name_ci = self._normalize_name(updates["name"])
            duplicate = self.repo.get_by_name_ci(user_id=user_id, name_ci=name_ci, include_archived=True)
            if duplicate is not None and int(duplicate.id) != int(item.id):
                raise ValueError("Brand with the same name already exists")
            item.name = name
            item.name_ci = name_ci
        if "accent_color" in updates:
            item.accent_color = self._normalize_color(updates.get("accent_color"))
        self.db.flush()
        self.activity.record_updated(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="item_brand",
            entity_id=int(item.id),
            before=before,
            after=ActivityService.snapshot(item, self.ACTIVITY_FIELDS),
            labels=self.ACTIVITY_LABELS,
            title="Бренд изменён",
        )
        self.db.commit()
        self._invalidate(user_id)
        return self.get(user_id=user_id, brand_id=brand_id)

    def archive(self, *, user_id: int, brand_id: int) -> None:
        item = self.repo.get_by_id(user_id=user_id, brand_id=brand_id)
        if item is None:
            raise LookupError("Brand not found")
        self.repo.archive(brand=item)
        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="item_brand",
            entity_id=int(item.id),
            event_type="deleted",
            title="Бренд архивирован",
            metadata=ActivityService.snapshot(item, self.ACTIVITY_FIELDS),
        )
        self.db.commit()
        self._invalidate(user_id)

    def merge(self, *, user_id: int, source_brand_id: int, target_brand_id: int) -> tuple[dict, int]:
        if source_brand_id == target_brand_id:
            raise ValueError("Source and target brands must differ")
        source = self.repo.get_by_id(user_id=user_id, brand_id=source_brand_id)
        target = self.repo.get_by_id(user_id=user_id, brand_id=target_brand_id)
        if source is None or target is None:
            raise LookupError("Brand not found")
        reassigned = self.repo.reassign_templates(
            user_id=user_id,
            source_brand_id=source_brand_id,
            target_brand_id=target_brand_id,
        )
        self.repo.archive(brand=source)
        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="item_brand",
            entity_id=source_brand_id,
            event_type="merged",
            title="Бренды объединены",
            metadata={"target_brand_id": target_brand_id, "reassigned_positions": reassigned},
        )
        self.db.commit()
        self._invalidate(user_id)
        return self.get(user_id=user_id, brand_id=target_brand_id), reassigned

    @staticmethod
    def _invalidate(user_id: int) -> None:
        invalidate_item_templates_cache(user_id)
        invalidate_operations_cache(user_id)
        invalidate_plans_cache(user_id)
        invalidate_dashboard_analytics_cache(user_id)
