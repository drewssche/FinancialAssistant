from decimal import Decimal

from pydantic import BaseModel


class DashboardSummary(BaseModel):
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
