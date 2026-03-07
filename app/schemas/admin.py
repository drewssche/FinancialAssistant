from datetime import datetime

from pydantic import BaseModel


class AdminUserItem(BaseModel):
    id: int
    display_name: str | None
    status: str
    created_at: datetime
    last_login_at: datetime | None
    telegram_id: str | None
    username: str | None


class AdminUsersOut(BaseModel):
    items: list[AdminUserItem]


class AdminUserStatusUpdateIn(BaseModel):
    status: str
