from decimal import Decimal

import pytest

from app.core.money import allocate_largest_remainder


def test_allocate_largest_remainder_is_exact_nonnegative_and_stable_for_equal_ties():
    allocations = allocate_largest_remainder(
        [Decimal("0.01")] * 4,
        Decimal("0.02"),
    )

    assert allocations == [Decimal("0.01"), Decimal("0.01"), Decimal("0.00"), Decimal("0.00")]
    assert sum(allocations, start=Decimal("0")) == Decimal("0.02")
    assert all(amount >= 0 for amount in allocations)


@pytest.mark.parametrize(
    ("weights", "target", "message"),
    [
        ([Decimal("-0.01")], Decimal("0.01"), "weights must be nonnegative"),
        ([Decimal("1")], Decimal("-0.01"), "target must be nonnegative"),
        ([Decimal("1")], Decimal("0.001"), "target must be a whole number"),
    ],
)
def test_allocate_largest_remainder_rejects_invalid_money_inputs(weights, target, message):
    with pytest.raises(ValueError, match=message):
        allocate_largest_remainder(weights, target)
