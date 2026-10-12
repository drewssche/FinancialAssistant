from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class PriceObservation(BaseModel):
    receipt_item_id: int
    operation_id: int
    recorded_at: date
    name: str
    quantity: Decimal
    line_total: Decimal
    price: Decimal
    change_percent: Decimal | None
    direction: int
    is_discounted: bool
    discount_type: str | None
    sale_unit: str | None
    package_quantity: Decimal | None
    package_unit: str | None
    package_changed: bool


class PriceSeries(BaseModel):
    currency: str
    shop_name: str | None
    unit: str | None
    sale_unit: str | None
    package_quantity: Decimal | None
    package_unit: str | None
    observations: list[PriceObservation]
    increases: int
    decreases: int
    change_percent: Decimal | None


class ProductPriceHistoryOut(BaseModel):
    basis: Literal["unit", "normalized"]
    price_kind: Literal["paid", "regular"]
    series: list[PriceSeries]
    excluded_count: int
