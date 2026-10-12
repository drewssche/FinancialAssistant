"""Add only comparable quantities, using immutable purchase snapshots."""
from decimal import Decimal

QUANTITY_FIELDS = ("pieces", "packs", "mass_kg", "volume_l", "content_pieces")
COUNT_FIELDS = ("rows_count", "unknown_rows_count", "unmeasured_package_rows_count")


def empty_quantities():
    return {**{key: Decimal("0") for key in QUANTITY_FIELDS}, **{key: 0 for key in COUNT_FIELDS}}


def add_quantities(totals, source, *, rows_count=1):
    get = source.get if isinstance(source, dict) else lambda key: getattr(source, key, None)
    quantity = Decimal(str(get("quantity") or 0))
    unit = get("sale_unit")
    totals["rows_count"] += rows_count
    if unit not in {"piece", "pack", "kg", "g", "l", "ml"}:
        totals["unknown_rows_count"] += rows_count
        return
    if unit in {"piece", "pack"}:
        totals["pieces" if unit == "piece" else "packs"] += quantity
        package_quantity, package_unit = get("package_quantity"), get("package_unit")
        if package_quantity is None or package_unit not in {"piece", "kg", "g", "l", "ml"}:
            totals["unmeasured_package_rows_count"] += rows_count
            return
        quantity *= Decimal(str(package_quantity))
        unit = package_unit
        if unit == "piece":
            totals["content_pieces"] += quantity
            return
    if unit in {"kg", "g"}:
        totals["mass_kg"] += quantity / (1000 if unit == "g" else 1)
    elif unit in {"l", "ml"}:
        totals["volume_l"] += quantity / (1000 if unit == "ml" else 1)
