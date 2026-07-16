from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db.models import ActivityEvent


class ActivityRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, event: ActivityEvent) -> ActivityEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def exists(self, *, user_id: int, entity_type: str, entity_id: int, event_type: str, source: str | None = None) -> bool:
        conditions = [
            ActivityEvent.user_id == user_id,
            ActivityEvent.entity_type == entity_type,
            ActivityEvent.entity_id == entity_id,
            ActivityEvent.event_type == event_type,
        ]
        if source is not None:
            conditions.append(ActivityEvent.source == source)
        stmt = select(ActivityEvent.id).where(and_(*conditions)).limit(1)
        return self.db.scalar(stmt) is not None

    def list_for_entity(
        self,
        *,
        user_id: int,
        entity_type: str,
        entity_id: int,
        limit: int,
        offset: int,
    ) -> tuple[list[ActivityEvent], int]:
        conditions = [
            ActivityEvent.user_id == user_id,
            ActivityEvent.entity_type == entity_type,
            ActivityEvent.entity_id == entity_id,
        ]
        total = int(self.db.scalar(select(func.count()).select_from(ActivityEvent).where(and_(*conditions))) or 0)
        items = list(
            self.db.scalars(
                select(ActivityEvent)
                .where(and_(*conditions))
                .order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return items, total

    def list_recent_for_user(self, *, user_id: int, limit: int, offset: int) -> tuple[list[ActivityEvent], int]:
        total = int(self.db.scalar(select(func.count()).select_from(ActivityEvent).where(ActivityEvent.user_id == user_id)) or 0)
        items = list(
            self.db.scalars(
                select(ActivityEvent)
                .where(ActivityEvent.user_id == user_id)
                .order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return items, total

    def get_latest_for_entity(
        self,
        *,
        user_id: int,
        entity_type: str,
        entity_id: int,
        event_type: str,
        for_update: bool = False,
    ) -> ActivityEvent | None:
        stmt = (
            select(ActivityEvent)
            .where(
                ActivityEvent.user_id == user_id,
                ActivityEvent.entity_type == entity_type,
                ActivityEvent.entity_id == entity_id,
                ActivityEvent.event_type == event_type,
            )
            .order_by(ActivityEvent.id.desc())
            .limit(1)
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)
