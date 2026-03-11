from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class OperationReceiptItemIn(BaseModel):
    shop_name: str | None = Field(default=None, max_length=160)
    name: str = Field(min_length=1, max_length=160)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Decimal = Field(gt=0)
    note: str | None = Field(default=None, max_length=300)


class OperationReceiptItemOut(BaseModel):
    id: int
    template_id: int | None
    shop_name: str | None
    name: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    note: str | None


class OperationCreate(BaseModel):
    kind: str
    amount: Decimal | None = None
    operation_date: date
    category_id: int | None = None
    note: str | None = None
    receipt_items: list[OperationReceiptItemIn] = []


class OperationUpdate(BaseModel):
    kind: str | None = None
    amount: Decimal | None = None
    operation_date: date | None = None
    category_id: int | None = None
    note: str | None = None
    receipt_items: list[OperationReceiptItemIn] | None = None


class OperationOut(BaseModel):
    id: int
    kind: str
    amount: Decimal
    operation_date: date
    category_id: int | None
    note: str | None
    receipt_items: list[OperationReceiptItemOut] = []
    receipt_total: Decimal | None = None
    receipt_discrepancy: Decimal | None = None

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
