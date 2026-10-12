from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field
from app.schemas.operation import MeasurementFields


class ReceiptPriceHintInput(MeasurementFields):
    template_id: int = Field(gt=0)
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    as_of: date
    shop_name: str | None = Field(default=None, max_length=160)
    variant_id: int | None = Field(default=None, gt=0)
    exclude_operation_id: int | None = Field(default=None, gt=0)


class PreviousReceiptPrice(BaseModel):
    operation_id: int
    receipt_item_id: int
    recorded_at: date
    quantity: Decimal
    line_total: Decimal
    price: Decimal
    is_discounted: bool
    discount_type: str | None


class ReceiptPriceHintOut(BaseModel):
    status: Literal['found', 'no_history', 'unknown_measurements']
    previous: PreviousReceiptPrice | None = None
