from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class DebtMovementUpdate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    event_date: date
    note: str | None = None


class DebtMovementOut(DebtMovementUpdate):
    id: int
    debt_id: int
    movement_kind: Literal["issuance", "repayment"]
    currency: str
    title: str
    counterparty: str
    flow_direction: Literal["inflow", "outflow"]


class DebtCreate(BaseModel):
    counterparty: str
    direction: str  # lend|borrow
    principal: Decimal
    currency: str = "BYN"
    start_date: date
    due_date: date | None = None
    note: str | None = None


class DebtRepaymentCreate(BaseModel):
    amount: Decimal
    repayment_date: date
    note: str | None = None


class DebtIssuanceCreate(BaseModel):
    amount: Decimal
    issuance_date: date
    note: str | None = None


class DebtForgivenessCreate(BaseModel):
    amount: Decimal
    forgiven_date: date
    note: str | None = None


class DebtUpdate(BaseModel):
    counterparty: str | None = None
    direction: str | None = None
    principal: Decimal | None = None
    currency: str | None = None
    start_date: date | None = None
    due_date: date | None = None
    note: str | None = None


class DebtRepaymentOut(BaseModel):
    id: int
    debt_id: int
    amount: Decimal
    currency: str = "BYN"
    base_currency: str = "BYN"
    current_base_amount: Decimal | None = None
    repayment_date: date
    note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DebtForgivenessOut(BaseModel):
    id: int
    debt_id: int
    amount: Decimal
    currency: str = "BYN"
    base_currency: str = "BYN"
    current_base_amount: Decimal | None = None
    forgiven_date: date
    note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DebtIssuanceOut(BaseModel):
    id: int
    debt_id: int
    amount: Decimal
    currency: str = "BYN"
    base_currency: str = "BYN"
    current_base_amount: Decimal | None = None
    issuance_date: date
    note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DebtOut(BaseModel):
    id: int
    counterparty_id: int
    direction: str
    principal: Decimal
    original_principal: Decimal
    currency: str
    base_currency: str
    closure_reason: str | None = None
    current_rate: Decimal | None = None
    current_rate_date: date | None = None
    current_base_principal: Decimal
    repaid_total: Decimal
    current_base_repaid_total: Decimal
    forgiven_total: Decimal = Decimal("0")
    current_base_forgiven_total: Decimal = Decimal("0")
    outstanding_total: Decimal
    current_base_outstanding_total: Decimal
    start_date: date
    due_date: date | None = None
    note: str | None = None
    created_at: datetime
    repayments: list[DebtRepaymentOut]
    forgivenesses: list[DebtForgivenessOut] = []
    issuances: list[DebtIssuanceOut]


class DebtCardOut(BaseModel):
    counterparty_id: int
    counterparty: str
    principal_total: Decimal
    principal_lend_total: Decimal
    principal_borrow_total: Decimal
    repaid_total: Decimal
    outstanding_total: Decimal
    base_currency: str = "BYN"
    status: str  # active|closed
    nearest_due_date: date | None = None
    debts: list[DebtOut]
