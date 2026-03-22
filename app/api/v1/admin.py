from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.admin import AdminUserItem, AdminUsersOut, AdminUserStatusUpdateIn
from app.services.admin_user_service import (
    AdminUserNotFoundError,
    AdminUserService,
    InvalidAdminUserRequestError,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=AdminUsersOut)
def list_users(
    status_filter: str = "pending",
    _: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    try:
        return AdminUserService(db).list_users(status_filter=status_filter)
    except InvalidAdminUserRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/users/{user_id}/status", response_model=AdminUserItem)
def update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdateIn,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    try:
        return AdminUserService(db).update_user_status(
            user_id=user_id,
            next_status=payload.status,
            current_admin_id=current_admin.id,
        )
    except InvalidAdminUserRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AdminUserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    try:
        AdminUserService(db).delete_user(user_id=user_id, current_admin_id=current_admin.id)
    except InvalidAdminUserRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AdminUserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
