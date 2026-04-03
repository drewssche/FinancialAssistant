from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class OperationReceiptItemIn(BaseModel):
    category_id: int | None = None
    shop_name: str | None = Field(default=None, max_length=160)
    name: str = Field(min_length=1, max_length=160)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Decimal = Field(gt=0)
    note: str | None = Field(default=None, max_length=300)


class OperationReceiptItemOut(BaseModel):
    id: int
    template_id: int | None
    category_id: int | None
    category_name: str | None = None
    category_icon: str | None = None
    category_accent_color: str | None = None
    shop_name: str | None
    name: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    note: str | None


class OperationFxSettlementIn(BaseModel):
    asset_currency: str = Field(min_length=3, max_length=3)
    quantity: Decimal = Field(gt=0)
    quote_total: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    note: str | None = Field(default=None, max_length=300)


class OperationFxSettlementOut(BaseModel):
    trade_id: int
    asset_currency: str
    quote_currency: str
    quantity: Decimal
    quote_total: Decimal
    unit_price: Decimal
    trade_date: date
    note: str | None = None


class OperationCreate(BaseModel):
    kind: str
    amount: Decimal | None = None
    currency: str = Field(default="BYN", min_length=3, max_length=3)
    fx_rate: Decimal | None = Field(default=None, gt=0)
    operation_date: date
    category_id: int | None = None
    note: str | None = None
    receipt_items: list[OperationReceiptItemIn] = []
    fx_settlement: OperationFxSettlementIn | None = None


class OperationUpdate(BaseModel):
    kind: str | None = None
    amount: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    fx_rate: Decimal | None = Field(default=None, gt=0)
    operation_date: date | None = None
    category_id: int | None = None
    note: str | None = None
    receipt_items: list[OperationReceiptItemIn] | None = None
    fx_settlement: OperationFxSettlementIn | None = None


class OperationOut(BaseModel):
    id: int
    kind: str
    amount: Decimal
    original_amount: Decimal
    currency: str
    base_currency: str
    fx_rate: Decimal
    operation_date: date
    category_id: int | None
    category_name: str | None = None
    category_icon: str | None = None
    category_accent_color: str | None = None
    note: str | None
    receipt_items: list[OperationReceiptItemOut] = []
    receipt_total: Decimal | None = None
    receipt_discrepancy: Decimal | None = None
    fx_settlement: OperationFxSettlementOut | None = None

    model_config = {"from_attributes": True, "extra": "allow"}


class OperationListOut(BaseModel):
    items: list[OperationOut]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class OperationSummaryOut(BaseModel):
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    total: int


class MoneyFlowItemOut(BaseModel):
    id: str
    source_kind: str
    source_id: int | None = None
    flow_direction: str
    event_date: date
    amount: Decimal
    original_amount: Decimal
    currency: str
    base_currency: str
    fx_rate: Decimal = Decimal("1")
    title: str
    subtitle: str | None = None
    note: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    category_icon: str | None = None
    category_accent_color: str | None = None
    counterparty_id: int | None = None
    counterparty_name: str | None = None
    asset_currency: str | None = None
    asset_quantity: Decimal | None = None
    quote_currency: str | None = None
    trade_side: str | None = None
    has_fx_settlement: bool = False
    settlement_asset_currency: str | None = None
    receipt_items: list[OperationReceiptItemOut] = []
    receipt_total: Decimal | None = None
    receipt_discrepancy: Decimal | None = None
    can_open_source: bool = False
    open_section: str | None = None
    open_label: str | None = None


class MoneyFlowListOut(BaseModel):
    items: list[MoneyFlowItemOut]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class OperationItemTemplateOut(BaseModel):
    id: int
    shop_name: str | None = None
    name: str
    use_count: int
    last_used_at: datetime | None = None
    last_category_id: int | None = None
    latest_unit_price: Decimal | None = None
    latest_price_date: date | None = None

    model_config = {"extra": "allow"}


class OperationItemTemplateCreate(BaseModel):
    shop_name: str | None = Field(default=None, max_length=160)
    name: str = Field(min_length=1, max_length=160)
    latest_unit_price: Decimal | None = Field(default=None, gt=0)
    latest_price_date: date | None = None


class OperationItemTemplateUpdate(BaseModel):
    shop_name: str | None = Field(default=None, max_length=160)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    latest_unit_price: Decimal | None = Field(default=None, gt=0)
    latest_price_date: date | None = None


class OperationItemTemplateDeleteAllOut(BaseModel):
    deleted: int


class OperationItemTemplateListOut(BaseModel):
    items: list[OperationItemTemplateOut]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class OperationItemPriceOut(BaseModel):
    id: int
    unit_price: Decimal
    recorded_at: date
    source_operation_id: int | None = None
