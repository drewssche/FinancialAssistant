"""Optional purchase measurements. Missing data is unknown, never inferred."""
from decimal import Decimal, InvalidOperation

MEASUREMENT_FIELDS = ("sale_unit", "package_quantity", "package_unit")
SALE_UNITS = {"piece", "pack", "kg", "g", "l", "ml"}
CONTENT_UNITS = {"piece", "kg", "g", "l", "ml"}


def measurement_snapshot(source, *, json_safe=False):
    get = source.get if isinstance(source, dict) else lambda key: getattr(source, key, None)
    result = {key: get(key) for key in MEASUREMENT_FIELDS}
    if json_safe and result["package_quantity"] is not None:
        result["package_quantity"] = str(result["package_quantity"])
    return result


def normalize_measurement(source):
    result = measurement_snapshot(source)
    unit, quantity, content_unit = (result[key] for key in MEASUREMENT_FIELDS)
    if unit is not None and unit not in SALE_UNITS:
        raise ValueError("Неизвестная единица продажи")
    if content_unit is not None and content_unit not in CONTENT_UNITS:
        raise ValueError("Неизвестная единица содержимого упаковки")
    if (quantity is None) != (content_unit is None):
        raise ValueError("Укажите размер упаковки вместе с единицей содержимого")
    if quantity is not None:
        if unit not in {"piece", "pack"}:
            raise ValueError("Фасовку можно указать при продаже поштучно или упаковками")
        try:
            quantity = Decimal(str(quantity))
            if not quantity.is_finite() or quantity <= 0 or quantity >= Decimal("100000000000"):
                raise ValueError("Размер упаковки должен быть положительным числом")
            if quantity != quantity.quantize(Decimal("0.001")):
                raise ValueError("Размер упаковки: не более трёх знаков после запятой")
        except InvalidOperation as exc:
            raise ValueError("Некорректный размер упаковки") from exc
        result["package_quantity"] = quantity
    return result


def guard_measurement_replacement(incoming, existing):
    if any(any(measurement_snapshot(row).values()) for row in existing):
        if any(not all(key in row for key in MEASUREMENT_FIELDS) for row in incoming):
            raise ValueError("Обновите приложение перед изменением чека: в нём есть единицы и фасовка")
