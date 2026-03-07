from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_is_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.user import UserOut
from app.services.user_cleanup_service import hard_delete_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(
    current_user: User = Depends(get_current_user),
    is_admin: bool = Depends(get_current_user_is_admin),
):
    telegram_identity = next(
        (identity for identity in (current_user.identities or []) if identity.provider == "telegram"),
        None,
    )
    return {
        "id": current_user.id,
        "display_name": current_user.display_name,
        "avatar_url": current_user.avatar_url,
        "username": telegram_identity.username if telegram_identity else None,
        "telegram_id": telegram_identity.provider_user_id if telegram_identity else None,
        "status": current_user.status,
        "is_admin": is_admin,
        "created_at": current_user.created_at,
    }


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hard_delete_user(db, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
