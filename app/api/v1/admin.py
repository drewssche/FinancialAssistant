from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.models import User
from app.db.session import get_db
from app.repositories.user_repo import UserRepository
from app.schemas.admin import AdminUserItem, AdminUsersOut, AdminUserStatusUpdateIn
from app.services.user_cleanup_service import hard_delete_user

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=AdminUsersOut)
def list_users(
    status_filter: str = "pending",
    _: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    allowed = {"pending", "approved", "rejected", "active", "all"}
    if status_filter not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status filter")

    repo = UserRepository(db)
    status_value = None if status_filter == "all" else status_filter
    users = repo.list_users(status=status_value)
    items: list[AdminUserItem] = []
    for user in users:
        telegram_identity = next((identity for identity in (user.identities or []) if identity.provider == "telegram"), None)
        items.append(
            AdminUserItem(
                id=user.id,
                display_name=user.display_name,
                status="approved" if user.status == "active" else user.status,
                created_at=user.created_at,
                last_login_at=user.last_login_at,
                telegram_id=telegram_identity.provider_user_id if telegram_identity else None,
                username=telegram_identity.username if telegram_identity else None,
            )
        )
    return AdminUsersOut(items=items)


@router.patch("/users/{user_id}/status", response_model=AdminUserItem)
def update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdateIn,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    next_status = payload.status
    if next_status not in {"pending", "approved", "rejected"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status value")
    if current_admin.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change own status")

    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.status = next_status
    db.commit()
    db.refresh(user)
    telegram_identity = next((identity for identity in (user.identities or []) if identity.provider == "telegram"), None)
    return AdminUserItem(
        id=user.id,
        display_name=user.display_name,
        status=user.status,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        telegram_id=telegram_identity.provider_user_id if telegram_identity else None,
        username=telegram_identity.username if telegram_identity else None,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    if current_admin.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete own account")
    deleted = hard_delete_user(db, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
