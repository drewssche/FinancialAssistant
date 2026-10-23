"""Historical labels, deliberately independent of mutable catalog foreign keys."""
from copy import deepcopy


def variant_snapshot(source) -> dict:
    value = source.get("variant_snapshot") if isinstance(source, dict) else getattr(source, "variant_snapshot", None)
    return {"variant_snapshot": deepcopy(value)}


def guard_variant_replacement(incoming, existing):
    if any(getattr(row, "variant_snapshot", None) for row in existing):
        if any("variant_snapshot" not in row for row in incoming):
            raise ValueError("Чек содержит сохранённые фасовки. Обновите страницу перед редактированием.")


def receipt_code_snapshot(source) -> dict:
    """Codes printed on this receipt, independent of the shop's stable SKU."""
    value = source.get("receipt_codes") if isinstance(source, dict) else getattr(source, "receipt_codes", None)
    return {"receipt_codes": deepcopy(value or [])}


def guard_receipt_code_replacement(incoming, existing):
    if any(getattr(row, "receipt_codes", None) for row in existing):
        if any("receipt_codes" not in row and not row.get("catalog_codes") for row in incoming):
            raise ValueError("Чек содержит сохранённые коды. Обновите страницу перед редактированием.")
