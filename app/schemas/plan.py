from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.operation import OperationOut, OperationReceiptItemIn, OperationReceiptItemOut


class PlanCreate(BaseModel):
    kind: str
    amount: Decimal | None = None
    scheduled_date: date
    category_id: int | None = None
    note: str | None = None
    receipt_items: list[OperationReceiptItemIn] = []
    recurrence_enabled: bool = False
    recurrence_frequency: str | None = Field(default=None, pattern="^(daily|weekly|monthly|yearly)$")
    recurrence_interval: int = Field(default=1, ge=1, le=365)
    recurrence_weekdays: list[int] = Field(default_factory=list)
    recurrence_workdays_only: bool = False
    recurrence_month_end: bool = False
    recurrence_end_date: date | None = None


class PlanUpdate(BaseModel):
    kind: str | None = None
    amount: Decimal | None = None
    scheduled_date: date | None = None
    category_id: int | None = None
    note: str | None = None
    receipt_items: list[OperationReceiptItemIn] | None = None
    recurrence_enabled: bool | None = None
    recurrence_frequency: str | None = Field(default=None, pattern="^(daily|weekly|monthly|yearly)$")
    recurrence_interval: int | None = Field(default=None, ge=1, le=365)
    recurrence_weekdays: list[int] | None = None
    recurrence_workdays_only: bool | None = None
    recurrence_month_end: bool | None = None
    recurrence_end_date: date | None = None


class PlanOut(BaseModel):
    id: int
    kind: str
    amount: Decimal
    scheduled_date: date
    due_date: date
    category_id: int | None
    category_name: str | None = None
    category_icon: str | None = None
    category_accent_color: str | None = None
    note: str | None
    receipt_items: list[OperationReceiptItemOut] = []
    receipt_total: Decimal | None = None
    recurrence_enabled: bool
    recurrence_frequency: str | None = None
    recurrence_interval: int = 1
    recurrence_weekdays: list[int] = []
    recurrence_workdays_only: bool = False
    recurrence_month_end: bool = False
    recurrence_end_date: date | None = None
    recurrence_label: str
    status: str
    progress_anchor_at: datetime | None = None
    next_reminder_at: datetime | None = None
    confirmed_operation_id: int | None = None
    confirm_count: int = 0
    skip_count: int = 0
    last_confirmed_at: datetime | None = None
    last_skipped_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True, "extra": "allow"}


class PlanListOut(BaseModel):
    items: list[PlanOut]
    total: int


class PlanConfirmOut(BaseModel):
    plan: PlanOut
    operation: OperationOut


class PlanEventOut(BaseModel):
    id: int
    plan_id: int
    operation_id: int | None = None
    event_type: str
    kind: str
    amount: Decimal
    effective_date: date
    note: str | None = None
    category_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True, "extra": "allow"}


class PlanEventListOut(BaseModel):
    items: list[PlanEventOut]
    total: int
