from datetime import datetime
from decimal import Decimal

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


class AdminCurrencyDiagnosticsItem(BaseModel):
    currency: str
    tracked_users: int
    digest_users: int
    alert_rules: int
    latest_rate: Decimal | None = None
    latest_rate_date: str | None = None
    stale_users: int
    missing_users: int


class AdminCurrencyDiagnosticsOut(BaseModel):
    tracked_users: int
    tracked_currency_slots: int
    digest_enabled_users: int
    alert_rules_count: int
    stale_slots: int
    missing_slots: int
    freshest_rate_date: str | None = None
    items: list[AdminCurrencyDiagnosticsItem]
