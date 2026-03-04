from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class OperationCreate(BaseModel):
    kind: str
    amount: Decimal
    operation_date: date
    category_id: int | None = None
    note: str | None = None


class OperationUpdate(BaseModel):
    kind: str | None = None
    amount: Decimal | None = None
    operation_date: date | None = None
    category_id: int | None = None
    note: str | None = None


class OperationOut(BaseModel):
    id: int
    kind: str
    amount: Decimal
    operation_date: date
    category_id: int | None
    note: str | None

    model_config = {"from_attributes": True}


class OperationListOut(BaseModel):
    items: list[OperationOut]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
