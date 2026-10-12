from decimal import Decimal
from types import SimpleNamespace

from app.core.receipt_pricing import discount_totals
from app.services.dashboard_analytics_highlights import DashboardAnalyticsHighlightsService


def test_savings_use_stored_line_amounts_and_do_not_infer_unknown_regular_price():
    row = SimpleNamespace(is_discounted=True, quantity=Decimal('0.242'), unit_price=Decimal('15.082645'),
                          regular_unit_price=Decimal('15.64'), discount_mode='amount',
                          line_subtotal=Decimal('3.78'), line_total=Decimal('3.65'))
    before, paid = discount_totals(row)
    assert sum(before - paid for _ in range(3)) == Decimal('0.39')
    service = object.__new__(DashboardAnalyticsHighlightsService)
    row.name = 'Сыр'
    row.discount_type = 'coupon'
    rows = {1: [row, row, row]}
    assert service.compute_discount_savings(rows) == (Decimal('0.39'), 3)
    assert service.compute_discount_savings_by_type(rows)[0]['savings_total'] == Decimal('0.39')
    assert service.build_top_discount_savings(rows)[0]['savings_total'] == Decimal('0.39')
    row.line_subtotal = None
    row.regular_unit_price = None
    assert discount_totals(row) is None
    # Preserve historical behavior for rows without the new calculation mode.
    row.discount_mode = None
    row.unit_price = Decimal('2')
    row.regular_unit_price = Decimal('3')
    row.quantity = Decimal('2')
    assert discount_totals(row) == (Decimal('6'), Decimal('4'))
