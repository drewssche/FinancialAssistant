from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ActivityEvent
from app.repositories.activity_repo import ActivityRepository


class ActivityService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ActivityRepository(db)

    @staticmethod
    def _raw(value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    @staticmethod
    def _display(value: Any) -> str:
        if value is None:
            return "Не задано"
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, bool):
            return "Да" if value else "Нет"
        return str(value)

    @classmethod
    def snapshot(cls, obj: Any, fields: list[str]) -> dict:
        return {field: cls._raw(getattr(obj, field, None)) for field in fields}

    @classmethod
    def build_changes(cls, before: dict, after: dict, labels: dict[str, str]) -> list[dict]:
        changes: list[dict] = []
        for field, label in labels.items():
            old = before.get(field)
            new = after.get(field)
            if old == new:
                continue
            changes.append(
                {
                    "field": field,
                    "label": label,
                    "old": old,
                    "new": new,
                    "old_display": cls._display(old),
                    "new_display": cls._display(new),
                }
            )
        return changes

    def record(
        self,
        *,
        user_id: int,
        entity_type: str,
        entity_id: int,
        event_type: str,
        title: str,
        actor_user_id: int | None = None,
        changes: list[dict] | None = None,
        metadata: dict | None = None,
        source: str = "web",
        created_at: datetime | None = None,
    ) -> ActivityEvent | None:
        event = ActivityEvent(
            user_id=user_id,
            actor_user_id=actor_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            title=title,
            changes_json=changes or [],
            metadata_json=metadata or {},
            source=source,
        )
        if created_at is not None:
            event.created_at = created_at
        return self.repo.create(event)

    def record_created(
        self,
        *,
        user_id: int,
        entity_type: str,
        entity_id: int,
        title: str,
        actor_user_id: int | None = None,
        metadata: dict | None = None,
        source: str = "web",
        created_at: datetime | None = None,
    ) -> ActivityEvent | None:
        return self.record(
            user_id=user_id,
            actor_user_id=actor_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type="created",
            title=title,
            metadata=metadata,
            source=source,
            created_at=created_at,
        )

    def record_updated(
        self,
        *,
        user_id: int,
        entity_type: str,
        entity_id: int,
        before: dict,
        after: dict,
        labels: dict[str, str],
        title: str = "Изменения сохранены",
        actor_user_id: int | None = None,
        metadata: dict | None = None,
        source: str = "web",
    ) -> ActivityEvent | None:
        changes = self.build_changes(before, after, labels)
        if not changes:
            return None
        return self.record(
            user_id=user_id,
            actor_user_id=actor_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type="updated",
            title=title,
            changes=changes,
            metadata=metadata,
            source=source,
        )

    def list_for_entity(self, *, user_id: int, entity_type: str, entity_id: int, page: int = 1, page_size: int = 50) -> tuple[list[dict], int]:
        items, total = self.repo.list_for_entity(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return [self._serialize(row) for row in items], total

    def list_recent(self, *, user_id: int, page: int = 1, page_size: int = 50) -> tuple[list[dict], int]:
        items, total = self.repo.list_recent_for_user(
            user_id=user_id,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return [self._serialize(row) for row in items], total

    @staticmethod
    def _serialize(row: ActivityEvent) -> dict:
        return {
            "id": int(row.id),
            "user_id": int(row.user_id),
            "actor_user_id": int(row.actor_user_id) if row.actor_user_id is not None else None,
            "entity_type": row.entity_type,
            "entity_id": int(row.entity_id),
            "event_type": row.event_type,
            "title": row.title,
            "changes": row.changes_json or [],
            "metadata": row.metadata_json or {},
            "source": row.source,
            "created_at": row.created_at,
        }
