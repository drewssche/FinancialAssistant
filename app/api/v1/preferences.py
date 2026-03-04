from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.preferences import PreferencesOut, PreferencesPayload
from app.services.preferences_service import PreferencesService

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=PreferencesOut)
def get_preferences(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = PreferencesService(db)
    return service.get_preferences(user_id)


@router.put("", response_model=PreferencesOut)
def update_preferences(
    payload: PreferencesPayload,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = PreferencesService(db)
    return service.update_preferences(
        user_id=user_id,
        preferences_version=payload.preferences_version,
        data=payload.data,
    )
