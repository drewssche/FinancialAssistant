from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

DiscountType = Literal["promo", "coupon", "loyalty_points"]
FxRateSource = Literal["nbrb", "bank", "manual"]
FxRateKind = Literal["buy", "sell"]
FxPaymentMode = Literal["valuation", "direct_conversion", "foreign_balance"]


class OperationReceiptItemIn(BaseModel):
    template_id: int | None = Field(default=None, ge=1)
    product_id: int | None = Field(default=None, ge=1)
    source_id: int | None = Field(default=None, ge=1)
    brand_id: int | None = Field(default=None, ge=1)
    category_id: int | None = None
    category_touched: bool = False
    shop_name: str | None = Field(default=None, max_length=160)
    name: str = Field(min_length=1, max_length=160)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Decimal = Field(gt=0)
    is_discounted: bool = False
    regular_unit_price: Decimal | None = Field(default=None, gt=0)
    discount_type: DiscountType | None = None
    note: str | None = Field(default=None, max_length=300)


class OperationReceiptItemOut(BaseModel):
    id: int
    template_id: int | None
    product_id: int | None = None
    product_name: str | None = None
    product_image_id: int | None = None
    brand_id: int | None = None
    brand_name: str | None = None
    brand_accent_color: str | None = None
    brand_is_archived: bool = False
    item_image_id: int | None = None
    brand_image_id: int | None = None
    source_id: int | None = None
    source_name: str | None = None
    source_image_id: int | None = None
    category_id: int | None
    category_name: str | None = None
    category_icon: str | None = None
    category_accent_color: str | None = None
    shop_name: str | None
    name: str
    quantity: Decimal
    unit_price: Decimal
    is_discounted: bool = False
    regular_unit_price: Decimal | None = None
    discount_type: DiscountType | None = None
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
    fx_rate_source: FxRateSource | None = None
    fx_bank_code: str | None = Field(default=None, max_length=32)
    fx_bank_channel: str | None = Field(default=None, max_length=20)
    fx_rate_kind: FxRateKind | None = None
    fx_manual_rate: Decimal | None = Field(default=None, gt=0)
    fx_payment_mode: FxPaymentMode | None = None
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
    fx_rate_source: FxRateSource | None = None
    fx_bank_code: str | None = Field(default=None, max_length=32)
    fx_bank_channel: str | None = Field(default=None, max_length=20)
    fx_rate_kind: FxRateKind | None = None
    fx_manual_rate: Decimal | None = Field(default=None, gt=0)
    fx_payment_mode: FxPaymentMode | None = None
    fx_refresh_rate: bool | None = None
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
    fx_rate_source: FxRateSource | None = None
    fx_bank_code: str | None = None
    fx_bank_name: str | None = None
    fx_bank_channel: str | None = None
    fx_rate_kind: FxRateKind | None = None
    fx_rate_scale: int = 1
    fx_rate_display: Decimal = Decimal("1")
    fx_rate_date: date | None = None
    fx_quoted_at: datetime | None = None
    fx_fetched_at: datetime | None = None
    fx_rate_stale: bool = False
    fx_payment_mode: FxPaymentMode = "valuation"
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
    source_plan_id: int | None = None
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
    product_id: int | None = None
    product_name: str | None = None
    product_image_id: int | None = None
    image_id: int | None = None
    shop_name: str | None = None
    source_id: int | None = None
    source_name: str | None = None
    source_image_id: int | None = None
    name: str
    use_count: int
    last_used_at: datetime | None = None
    last_category_id: int | None = None
    brand_id: int | None = None
    brand_name: str | None = None
    brand_accent_color: str | None = None
    brand_is_archived: bool = False
    brand_image_id: int | None = None
    latest_unit_price: Decimal | None = None
    latest_price_date: date | None = None
    model_config = {"extra": "allow"}


class OperationItemTemplateCreate(BaseModel):
    product_id: int | None = Field(default=None, ge=1)
    shop_name: str | None = Field(default=None, max_length=160)
    source_id: int | None = Field(default=None, ge=1)
    name: str = Field(min_length=1, max_length=160)
    last_category_id: int | None = None
    brand_id: int | None = Field(default=None, ge=1)
    latest_unit_price: Decimal | None = Field(default=None, gt=0)
    latest_price_date: date | None = None


class OperationItemTemplateUpdate(BaseModel):
    shop_name: str | None = Field(default=None, max_length=160)
    source_id: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    last_category_id: int | None = None
    brand_id: int | None = Field(default=None, ge=1)
    latest_unit_price: Decimal | None = Field(default=None, gt=0)
    latest_price_date: date | None = None


class OperationItemTemplateBulkBrandUpdateIn(BaseModel):
    template_ids: list[int] = Field(min_length=1, max_length=500)
    brand_id: int | None = Field(default=None, ge=1)


class OperationItemTemplateBulkBrandUpdateOut(BaseModel):
    updated: int


class OperationItemTemplateDeleteAllOut(BaseModel):
    deleted: int


class OperationItemTemplateListOut(BaseModel):
    items: list[OperationItemTemplateOut]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class CatalogProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    brand_id: int | None = Field(default=None, ge=1)
    category_id: int | None = Field(default=None, ge=1)


class CatalogProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    brand_id: int | None = Field(default=None, ge=1)
    category_id: int | None = Field(default=None, ge=1)


class CatalogProductOut(BaseModel):
    id: int
    name: str
    image_id: int | None = None
    brand_id: int | None = None
    brand_name: str | None = None
    brand_accent_color: str | None = None
    brand_image_id: int | None = None
    category_id: int | None = None
    category_name: str | None = None
    category_icon: str | None = None
    category_accent_color: str | None = None
    is_archived: bool = False
    offers_count: int = 0
    sources_count: int = 0
    use_count: int = 0
    last_used_at: datetime | None = None
    min_unit_price: Decimal | None = None
    max_unit_price: Decimal | None = None
    offers: list[OperationItemTemplateOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CatalogProductListOut(BaseModel):
    items: list[CatalogProductOut]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class CatalogProductMergeIn(BaseModel):
    source_product_ids: list[int] = Field(min_length=1, max_length=100)


class CatalogProductSourceConflictOut(BaseModel):
    source_id: int | None = None
    source_name: str | None = None
    offer_ids: list[int]


class CatalogProductMergeOut(BaseModel):
    product: CatalogProductOut
    merged_product_ids: list[int]
    reassigned_offers: int
    source_conflicts: list[CatalogProductSourceConflictOut] = Field(
        default_factory=list
    )


class CatalogProductDetachIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    brand_id: int | None = Field(default=None, ge=1)
    category_id: int | None = Field(default=None, ge=1)


class CatalogProductDetachOut(BaseModel):
    product: CatalogProductOut
    moved_offer_id: int


class CatalogProductMergeCandidateOut(BaseModel):
    name: str
    products: list[CatalogProductOut]
    reasons: list[str]


class CatalogProductMergeCandidateListOut(BaseModel):
    items: list[CatalogProductMergeCandidateOut]
    total: int


class ItemBrandCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    accent_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class ItemBrandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    accent_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class ItemBrandOut(BaseModel):
    id: int
    name: str
    accent_color: str | None = None
    image_id: int | None = None
    is_archived: bool = False
    positions_count: int = 0
    purchases_count: int = 0
    spent_total: Decimal = Decimal("0.00")
    last_purchase_date: date | None = None
    created_at: datetime
    updated_at: datetime


class ItemBrandListOut(BaseModel):
    items: list[ItemBrandOut]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class ItemBrandMergeIn(BaseModel):
    target_brand_id: int = Field(ge=1)


class ItemBrandMergeOut(BaseModel):
    brand: ItemBrandOut
    reassigned_positions: int


class ItemSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class ItemSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)


class ItemSourceOut(BaseModel):
    id: int
    name: str
    image_id: int | None = None
    is_archived: bool = False
    positions_count: int = 0
    created_at: datetime
    updated_at: datetime


class ItemSourceListOut(BaseModel):
    items: list[ItemSourceOut]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class OperationItemPriceOut(BaseModel):
    id: int
    unit_price: Decimal
    recorded_at: date
    source_operation_id: int | None = None
