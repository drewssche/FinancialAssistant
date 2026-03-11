from decimal import Decimal

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    date_from: str
    date_to: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    debt_lend_outstanding: Decimal
    debt_borrow_outstanding: Decimal
    debt_net_position: Decimal
    active_debt_cards: int


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


class AnalyticsCalendarDay(BaseModel):
    date: str
    in_month: bool
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    operations_count: int


class AnalyticsCalendarWeek(BaseModel):
    week_start: str
    week_end: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    operations_count: int
    days: list[AnalyticsCalendarDay]


class AnalyticsCalendarOut(BaseModel):
    month: str
    month_start: str
    month_end: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    operations_count: int
    weeks: list[AnalyticsCalendarWeek]


class AnalyticsCalendarYearMonth(BaseModel):
    month: str
    month_start: str
    month_end: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    operations_count: int


class AnalyticsCalendarYearOut(BaseModel):
    year: int
    year_start: str
    year_end: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    operations_count: int
    months: list[AnalyticsCalendarYearMonth]


class AnalyticsTrendPoint(BaseModel):
    bucket_start: str
    bucket_end: str
    label: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    operations_count: int


class AnalyticsTrendOut(BaseModel):
    period: str
    granularity: str
    date_from: str
    date_to: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    operations_count: int
    prev_income_total: Decimal
    prev_expense_total: Decimal
    prev_balance: Decimal
    prev_operations_count: int
    income_change_pct: float | None
    expense_change_pct: float | None
    balance_change_pct: float | None
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
    date_from: str
    date_to: str
    month: str
    month_start: str
    month_end: str
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    prev_income_total: Decimal
    prev_expense_total: Decimal
    prev_balance: Decimal
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
    operations_change_pct: float | None
    category_breakdown: list[AnalyticsTopCategory]
    top_operations: list[AnalyticsTopOperation]
    top_categories: list[AnalyticsTopCategory]
    anomalies: list[AnalyticsOperationAnomaly]
    top_positions: list[AnalyticsTopPosition]
    price_increases: list[AnalyticsPriceIncrease]
