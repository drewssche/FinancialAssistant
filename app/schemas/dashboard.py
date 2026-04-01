from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class DashboardCurrencyPosition(BaseModel):
    currency: str
    quantity: Decimal
    average_buy_rate: Decimal
    current_rate: Decimal
    current_rate_date: str | None = None
    current_value: Decimal
    result_value: Decimal
    realized_result_value: Decimal = Decimal("0")
    total_result_value: Decimal = Decimal("0")


class DashboardSummary(BaseModel):
    date_from: str
    date_to: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    debt_cashflow_total: Decimal = Decimal("0")
    fx_cashflow_total: Decimal = Decimal("0")
    cashflow_total: Decimal = Decimal("0")
    balance_with_currency_result: Decimal = Decimal("0")
    debt_lend_outstanding: Decimal
    debt_borrow_outstanding: Decimal
    debt_net_position: Decimal
    active_debt_cards: int
    currency_book_value: Decimal = Decimal("0")
    currency_current_value: Decimal = Decimal("0")
    currency_result_value: Decimal = Decimal("0")
    currency_unrealized_result_value: Decimal = Decimal("0")
    currency_realized_result_value: Decimal = Decimal("0")
    currency_total_result_value: Decimal = Decimal("0")
    currency_buy_trades_count: int = 0
    currency_sell_trades_count: int = 0
    currency_buy_volume_base: Decimal = Decimal("0")
    currency_sell_volume_base: Decimal = Decimal("0")
    currency_buy_average_rate: Decimal = Decimal("0")
    currency_sell_average_rate: Decimal = Decimal("0")
    active_currency_positions: int = 0
    tracked_currency_positions: list[DashboardCurrencyPosition] = Field(default_factory=list)


class DashboardLatencyStats(BaseModel):
    samples: int
    avg_ms: float
    min_ms: float
    max_ms: float
    p50_ms: float
    p95_ms: float


class DashboardSummaryMetrics(BaseModel):
    cache_hit_total: int
    cache_miss_total: int
    cache_invalidate_total: int
    cache_invalidated_keys_total: int
    cache_hit_ratio: float
    latency_total: DashboardLatencyStats
    latency_miss_compute: DashboardLatencyStats
    endpoint_request_totals: dict[str, int]


class DashboardDebtPreviewDebt(BaseModel):
    id: int
    direction: str
    principal: Decimal
    original_principal: Decimal
    currency: str = "BYN"
    base_currency: str = "BYN"
    current_rate: Decimal | None = None
    current_rate_date: date | None = None
    current_base_principal: Decimal = Decimal("0")
    repaid_total: Decimal
    current_base_repaid_total: Decimal = Decimal("0")
    outstanding_total: Decimal
    current_base_outstanding_total: Decimal = Decimal("0")
    start_date: date
    due_date: date | None = None
    note: str | None = None
    created_at: datetime


class DashboardDebtPreviewCard(BaseModel):
    counterparty_id: int
    counterparty: str
    principal_total: Decimal
    principal_lend_total: Decimal
    principal_borrow_total: Decimal
    repaid_total: Decimal
    outstanding_total: Decimal
    status: str
    nearest_due_date: date | None = None
    debts: list[DashboardDebtPreviewDebt]


class AnalyticsCalendarDay(BaseModel):
    date: str
    in_month: bool
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    operations_count: int
    debt_cashflow_total: Decimal = Decimal("0")
    debt_events_count: int = 0
    fx_cashflow_total: Decimal = Decimal("0")
    fx_events_count: int = 0
    cashflow_total: Decimal = Decimal("0")
    cashflow_events_count: int = 0


class AnalyticsCalendarWeek(BaseModel):
    week_start: str
    week_end: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    operations_count: int
    debt_cashflow_total: Decimal = Decimal("0")
    debt_events_count: int = 0
    fx_cashflow_total: Decimal = Decimal("0")
    fx_events_count: int = 0
    cashflow_total: Decimal = Decimal("0")
    cashflow_events_count: int = 0
    days: list[AnalyticsCalendarDay]


class AnalyticsCalendarOut(BaseModel):
    month: str
    month_start: str
    month_end: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    operations_count: int
    debt_cashflow_total: Decimal = Decimal("0")
    debt_events_count: int = 0
    fx_cashflow_total: Decimal = Decimal("0")
    fx_events_count: int = 0
    cashflow_total: Decimal = Decimal("0")
    cashflow_events_count: int = 0
    weeks: list[AnalyticsCalendarWeek]


class AnalyticsCalendarYearMonth(BaseModel):
    month: str
    month_start: str
    month_end: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    operations_count: int
    debt_cashflow_total: Decimal = Decimal("0")
    debt_events_count: int = 0
    fx_cashflow_total: Decimal = Decimal("0")
    fx_events_count: int = 0
    cashflow_total: Decimal = Decimal("0")
    cashflow_events_count: int = 0


class AnalyticsCalendarYearOut(BaseModel):
    year: int
    year_start: str
    year_end: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    operations_count: int
    debt_cashflow_total: Decimal = Decimal("0")
    debt_events_count: int = 0
    fx_cashflow_total: Decimal = Decimal("0")
    fx_events_count: int = 0
    cashflow_total: Decimal = Decimal("0")
    cashflow_events_count: int = 0
    months: list[AnalyticsCalendarYearMonth]


class AnalyticsTrendPoint(BaseModel):
    bucket_start: str
    bucket_end: str
    label: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    debt_cashflow_total: Decimal = Decimal("0")
    debt_events_count: int = 0
    fx_cashflow_total: Decimal = Decimal("0")
    fx_events_count: int = 0
    cashflow_total: Decimal = Decimal("0")
    cashflow_events_count: int = 0
    operations_count: int


class AnalyticsTrendOut(BaseModel):
    period: str
    granularity: str
    date_from: str
    date_to: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    debt_cashflow_total: Decimal = Decimal("0")
    fx_cashflow_total: Decimal = Decimal("0")
    cashflow_total: Decimal = Decimal("0")
    operations_count: int
    prev_income_total: Decimal
    prev_expense_total: Decimal
    prev_balance: Decimal
    prev_debt_cashflow_total: Decimal = Decimal("0")
    prev_fx_cashflow_total: Decimal = Decimal("0")
    prev_cashflow_total: Decimal = Decimal("0")
    prev_operations_count: int
    income_change_pct: float | None
    expense_change_pct: float | None
    balance_change_pct: float | None
    debt_cashflow_change_pct: float | None = None
    fx_cashflow_change_pct: float | None = None
    cashflow_change_pct: float | None = None
    operations_change_pct: float | None
    points: list[AnalyticsTrendPoint]


class AnalyticsTopOperation(BaseModel):
    operation_id: int
    operation_date: str
    kind: str
    amount: Decimal
    note: str | None


class AnalyticsTopPosition(BaseModel):
    name: str
    shop_name: str | None
    total_spent: Decimal
    max_unit_price: Decimal
    avg_unit_price: Decimal
    purchases_count: int


class AnalyticsTopCategory(BaseModel):
    category_id: int | None
    category_name: str
    category_kind: str
    group_id: int | None = None
    group_name: str | None = None
    total_amount: Decimal
    total_expense: Decimal
    share_pct: float
    change_pct: float | None
    operations_count: int


class AnalyticsOperationAnomaly(BaseModel):
    operation_id: int
    operation_date: str
    amount: Decimal
    note: str | None
    category_name: str
    ratio_to_median: float


class AnalyticsPriceIncrease(BaseModel):
    name: str
    shop_name: str | None
    previous_avg_unit_price: Decimal
    current_avg_unit_price: Decimal
    change_pct: float


class AnalyticsHighlightsOut(BaseModel):
    period: str
    category_breakdown_kind: str
    category_breakdown_level: str = "category"
    date_from: str
    date_to: str
    month: str
    month_start: str
    month_end: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    debt_cashflow_total: Decimal = Decimal("0")
    fx_cashflow_total: Decimal = Decimal("0")
    cashflow_total: Decimal = Decimal("0")
    prev_income_total: Decimal
    prev_expense_total: Decimal
    prev_balance: Decimal
    prev_debt_cashflow_total: Decimal = Decimal("0")
    prev_fx_cashflow_total: Decimal = Decimal("0")
    prev_cashflow_total: Decimal = Decimal("0")
    prev_operations_count: int
    surplus_total: Decimal
    deficit_total: Decimal
    operations_count: int
    avg_daily_expense: Decimal
    max_expense_day_date: str | None
    max_expense_day_total: Decimal
    income_change_pct: float | None
    expense_change_pct: float | None
    balance_change_pct: float | None
    debt_cashflow_change_pct: float | None = None
    fx_cashflow_change_pct: float | None = None
    cashflow_change_pct: float | None = None
    operations_change_pct: float | None
    category_breakdown: list[AnalyticsTopCategory]
    top_operations: list[AnalyticsTopOperation]
    top_categories: list[AnalyticsTopCategory]
    anomalies: list[AnalyticsOperationAnomaly]
    top_positions: list[AnalyticsTopPosition]
    price_increases: list[AnalyticsPriceIncrease]
