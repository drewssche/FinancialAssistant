from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from typing import Sequence


MONEY_QUANTUM = Decimal("0.01")


def allocate_largest_remainder(
    weights: Sequence[Decimal],
    target: Decimal,
    *,
    quantum: Decimal = MONEY_QUANTUM,
) -> list[Decimal]:
    """Allocate ``target`` proportionally without negative or lost minor units.

    Equal fractional remainders are resolved by the original item order.  Both
    the target and every result use whole ``quantum`` units, so the returned
    values always add up to the target exactly.
    """
    normalized_weights = [Decimal(weight) for weight in weights]
    normalized_target = Decimal(target)
    normalized_quantum = Decimal(quantum)

    if normalized_quantum <= 0:
        raise ValueError("quantum must be positive")
    if normalized_target < 0:
        raise ValueError("target must be nonnegative")
    if any(weight < 0 for weight in normalized_weights):
        raise ValueError("weights must be nonnegative")

    target_units_exact = Fraction(*normalized_target.as_integer_ratio()) / Fraction(
        *normalized_quantum.as_integer_ratio()
    )
    if target_units_exact.denominator != 1:
        raise ValueError("target must be a whole number of quantum units")
    target_units = target_units_exact.numerator

    if not normalized_weights:
        if target_units == 0:
            return []
        raise ValueError("positive target requires at least one weight")
    if target_units == 0:
        return [normalized_quantum * 0 for _weight in normalized_weights]

    fractional_weights = [Fraction(*weight.as_integer_ratio()) for weight in normalized_weights]
    total_weight = sum(fractional_weights, start=Fraction(0))
    if total_weight <= 0:
        raise ValueError("positive target requires a positive total weight")

    exact_units = [weight * target_units / total_weight for weight in fractional_weights]
    allocated_units = [value.numerator // value.denominator for value in exact_units]
    units_left = target_units - sum(allocated_units)
    remainder_order = sorted(
        range(len(normalized_weights)),
        key=lambda index: (-(exact_units[index] - allocated_units[index]), index),
    )
    if units_left < 0 or units_left > len(remainder_order):
        raise ArithmeticError("proportional allocation lost numeric precision")
    for index in remainder_order[:units_left]:
        allocated_units[index] += 1

    return [normalized_quantum * units for units in allocated_units]
