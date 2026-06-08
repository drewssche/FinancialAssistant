from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.activity import ActivityEventListOut
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=ActivityEventListOut)
def list_activity(
    entity_type: str | None = Query(default=None, max_length=40),
    entity_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = ActivityService(db)
    if entity_type and entity_id:
        items, total = service.list_for_entity(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            page=page,
            page_size=page_size,
        )
    else:
        items, total = service.list_recent(user_id=user_id, page=page, page_size=page_size)
    return ActivityEventListOut(items=items, total=total)
