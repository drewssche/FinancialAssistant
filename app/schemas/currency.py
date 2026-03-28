from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CurrencyTradeCreate(BaseModel):
    side: str
    asset_currency: str = Field(min_length=3, max_length=3)
    quote_currency: str = Field(default="BYN", min_length=3, max_length=3)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    fee: Decimal = Field(default=Decimal("0"), ge=0)
    trade_date: date
    note: str | None = Field(default=None, max_length=500)


class CurrencyTradeUpdate(CurrencyTradeCreate):
    pass


class CurrencyTradeOut(BaseModel):
    id: int
    side: str
    asset_currency: str
    quote_currency: str
    quantity: Decimal
    unit_price: Decimal
    fee: Decimal
    trade_date: date
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CurrencyRateUpsert(BaseModel):
    currency: str = Field(min_length=3, max_length=3)
    rate: Decimal = Field(gt=0)
    rate_date: date
    source: str = Field(default="manual", min_length=1, max_length=20)


class CurrencyRateOut(BaseModel):
    currency: str
    rate: Decimal
    rate_date: date
    source: str
    previous_rate: Decimal | None = None
    change_value: Decimal | None = None
    change_pct: float | None = None
    average_buy_rate: Decimal | None = None
    average_sell_rate: Decimal | None = None


class CurrencyRateHistoryPointOut(BaseModel):
    currency: str
    rate: Decimal
    rate_date: date


class CurrencyPositionOut(BaseModel):
    currency: str
    quantity: Decimal
    average_buy_rate: Decimal
    book_value: Decimal
    current_rate: Decimal
    current_rate_date: str | None = None
    current_value: Decimal
    result_value: Decimal
    result_pct: float | None = None
    realized_result_value: Decimal


class CurrencyOverviewOut(BaseModel):
    base_currency: str
    tracked_currencies: list[str]
    active_positions: int
    total_book_value: Decimal
    total_current_value: Decimal
    total_result_value: Decimal
    buy_trades_count: int = 0
    sell_trades_count: int = 0
    buy_volume_base: Decimal = Decimal("0")
    sell_volume_base: Decimal = Decimal("0")
    buy_average_rate: Decimal = Decimal("0")
    sell_average_rate: Decimal = Decimal("0")
    positions: list[CurrencyPositionOut]
    recent_trades: list[CurrencyTradeOut]
    current_rates: list[CurrencyRateOut]
