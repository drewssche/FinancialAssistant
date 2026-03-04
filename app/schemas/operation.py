from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class OperationCreate(BaseModel):
    kind: str
    amount: Decimal
    operation_date: date
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
