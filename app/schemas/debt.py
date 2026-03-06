from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class DebtCreate(BaseModel):
    counterparty: str
    direction: str  # lend|borrow
    principal: Decimal
    start_date: date
    due_date: date | None = None
    note: str | None = None


class DebtRepaymentCreate(BaseModel):
    amount: Decimal
    repayment_date: date
    note: str | None = None


class DebtUpdate(BaseModel):
    counterparty: str | None = None
    direction: str | None = None
    principal: Decimal | None = None
    start_date: date | None = None
    due_date: date | None = None
    note: str | None = None


class DebtRepaymentOut(BaseModel):
    id: int
    debt_id: int
    amount: Decimal
    repayment_date: date
    note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DebtIssuanceOut(BaseModel):
    id: int
    debt_id: int
    amount: Decimal
    issuance_date: date
    note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DebtOut(BaseModel):
    id: int
    counterparty_id: int
    direction: str
    principal: Decimal
    repaid_total: Decimal
    outstanding_total: Decimal
    start_date: date
    due_date: date | None = None
    note: str | None = None
    created_at: datetime
    repayments: list[DebtRepaymentOut]
    issuances: list[DebtIssuanceOut]


class DebtCardOut(BaseModel):
    counterparty_id: int
    counterparty: str
    principal_total: Decimal
    principal_lend_total: Decimal
    principal_borrow_total: Decimal
    repaid_total: Decimal
    outstanding_total: Decimal
    status: str  # active|closed
    nearest_due_date: date | None = None
    debts: list[DebtOut]
