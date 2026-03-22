from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import log_admin_notification_event
from app.db.models import User
from app.repositories.user_repo import UserRepository
from app.schemas.admin import AdminUserItem, AdminUsersOut
from app.services.user_cleanup_service import hard_delete_user


class AdminUserServiceError(Exception):
    pass


class InvalidAdminUserRequestError(AdminUserServiceError):
    pass


class AdminUserNotFoundError(AdminUserServiceError):
    pass


class AdminUserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    @staticmethod
    def _to_admin_user_item(user: User) -> AdminUserItem:
        telegram_identity = next((identity for identity in (user.identities or []) if identity.provider == "telegram"), None)
        return AdminUserItem(
            id=user.id,
            display_name=user.display_name,
            status="approved" if user.status == "active" else user.status,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            telegram_id=telegram_identity.provider_user_id if telegram_identity else None,
            username=telegram_identity.username if telegram_identity else None,
        )

    def list_users(self, *, status_filter: str) -> AdminUsersOut:
        allowed = {"pending", "approved", "rejected", "active", "all"}
        if status_filter not in allowed:
            raise InvalidAdminUserRequestError("Invalid status filter")

        status_value = None if status_filter == "all" else status_filter
        users = self.repo.list_users(status=status_value)
        return AdminUsersOut(items=[self._to_admin_user_item(user) for user in users])

    def update_user_status(self, *, user_id: int, next_status: str, current_admin_id: int) -> AdminUserItem:
        if next_status not in {"pending", "approved", "rejected"}:
            raise InvalidAdminUserRequestError("Invalid status value")
        if current_admin_id == user_id:
            log_admin_notification_event(
                "admin_user_self_action_blocked",
                admin_id=current_admin_id,
                action="status_change",
                target_user_id=user_id,
            )
            raise InvalidAdminUserRequestError("Cannot change own status")

        user = self.repo.get_by_id(user_id)
        if not user:
            raise AdminUserNotFoundError("User not found")

        previous_status = user.status
        if previous_status == next_status:
            log_admin_notification_event(
                "admin_user_status_already_set",
                admin_id=current_admin_id,
                target_user_id=user_id,
                status=next_status,
            )
        else:
            log_admin_notification_event(
                "admin_user_status_changed",
                admin_id=current_admin_id,
                target_user_id=user_id,
                previous_status=previous_status,
                next_status=next_status,
            )
        user.status = next_status
        self.db.commit()
        self.db.refresh(user)
        return self._to_admin_user_item(user)

    def delete_user(self, *, user_id: int, current_admin_id: int) -> None:
        if current_admin_id == user_id:
            log_admin_notification_event(
                "admin_user_self_action_blocked",
                admin_id=current_admin_id,
                action="delete",
                target_user_id=user_id,
            )
            raise InvalidAdminUserRequestError("Cannot delete own account")

        deleted = hard_delete_user(self.db, user_id=user_id)
        if not deleted:
            log_admin_notification_event(
                "admin_user_delete_not_found",
                admin_id=current_admin_id,
                target_user_id=user_id,
            )
            raise AdminUserNotFoundError("User not found")
        log_admin_notification_event(
            "admin_user_deleted",
            admin_id=current_admin_id,
            target_user_id=user_id,
        )
