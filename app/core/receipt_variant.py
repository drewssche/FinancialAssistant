"""Historical labels, deliberately independent of mutable catalog foreign keys."""
from copy import deepcopy


def variant_snapshot(source) -> dict:
    value = source.get("variant_snapshot") if isinstance(source, dict) else getattr(source, "variant_snapshot", None)
    return {"variant_snapshot": deepcopy(value)}


def guard_variant_replacement(incoming, existing):
    if any(getattr(row, "variant_snapshot", None) for row in existing):
        if any("variant_snapshot" not in row for row in incoming):
            raise ValueError("Чек содержит сохранённые фасовки. Обновите страницу перед редактированием.")
