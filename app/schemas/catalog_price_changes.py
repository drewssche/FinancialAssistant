from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel


class CatalogPriceChange(BaseModel):
    product_id: int
    product_name: str
    template_id: int
    offer_name: str
    shop_name: str | None
    currency: str
    unit: str | None
    sale_unit: str | None
    package_quantity: Decimal | None
    package_unit: str | None
    observations_count: int
    increases: int
    decreases: int
    package_changed: bool
    reference_price: Decimal
    latest_price: Decimal
    reference_date: date
    latest_date: date
    latest_operation_id: int
    latest_receipt_item_id: int
    direction: int
    change_percent: Decimal | None
    period_change_percent: Decimal | None
    last_change_percent: Decimal | None
    baseline_cost: Decimal
    latest_cost: Decimal
    cost_difference: Decimal
    latest_is_discounted: bool
    reference_is_discounted: bool


class CatalogPriceChangesOut(BaseModel):
    items: list[CatalogPriceChange]
    total: int
    page: int
    page_size: int
    excluded_count: int
    insufficient_series_count: int
    basis: Literal['unit', 'normalized']
    price_kind: Literal['paid', 'regular']
    comparison: Literal['period', 'previous']
