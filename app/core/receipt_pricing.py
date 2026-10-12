"""Receipt line arithmetic. Paid totals are authoritative; unit price is derived."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

PRICING_FIELDS = ("discount_mode", "discount_value", "line_subtotal")
PRICING_INPUT_FIELDS = ("discount_mode", "discount_value")
CENT = Decimal("0.01")


def pricing_snapshot(source, *, json_safe=False):
    get = source.get if isinstance(source, dict) else lambda key: getattr(source, key, None)
    result = {key: get(key) for key in PRICING_FIELDS}
    for key in ("discount_value", "line_subtotal"):
        if result[key] is not None:
            result[key] = str(result[key]) if json_safe else Decimal(str(result[key]))
    return result


def guard_pricing_replacement(incoming, existing):
    if any(pricing_snapshot(row)["discount_mode"] for row in existing):
        if any(not all(key in row for key in PRICING_INPUT_FIELDS) for row in incoming):
            raise ValueError("Обновите приложение перед изменением чека: в нём есть скидка от суммы позиции")


def calculate_line_pricing(item, *, quantity, unit_price, regular_unit_price, is_discounted):
    mode = item.get("discount_mode")
    raw_value = item.get("discount_value")
    if mode is None:
        if raw_value is not None:
            raise ValueError("Укажите способ расчёта скидки")
        return dict(discount_mode=None, discount_value=None, line_subtotal=None,
                    unit_price=unit_price, line_total=(quantity * unit_price).quantize(CENT, rounding=ROUND_HALF_UP))
    if mode not in {"amount", "percent", "final"} or not is_discounted:
        raise ValueError("Некорректный способ расчёта скидки")
    try:
        value = Decimal(str(raw_value))
        if not value.is_finite() or value < 0 or value >= Decimal("1000000000000"):
            raise ValueError("Некорректное значение скидки или итога")
        precision = Decimal("0.0001") if mode == "percent" else CENT
        if value != value.quantize(precision):
            raise ValueError("Сумма: не более двух знаков; процент: не более четырёх")
    except InvalidOperation as exc:
        raise ValueError("Некорректное значение скидки или итога") from exc
    subtotal = ((quantity * regular_unit_price).quantize(CENT, rounding=ROUND_HALF_UP)
                if regular_unit_price is not None else None)
    if mode != "final" and subtotal is None:
        raise ValueError("Для расчёта скидки укажите цену до скидки")
    if mode == "percent":
        if value >= 100:
            raise ValueError("Процент скидки должен быть меньше 100")
        discount = (subtotal * value / 100).quantize(CENT, rounding=ROUND_HALF_UP)
        total = subtotal - discount
    elif mode == "amount":
        total = subtotal - value
    else:
        total = value
    if total <= 0 or total >= Decimal("1000000000000"):
        raise ValueError("Итог позиции должен быть больше нуля и помещаться в денежное поле")
    if subtotal is not None and (subtotal >= Decimal("1000000000000") or total > subtotal):
        raise ValueError("Итог после скидки не может превышать сумму до скидки")
    effective_price = (total / quantity).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    if effective_price <= 0 or effective_price >= Decimal("1000000000000"):
        raise ValueError("Цена за единицу выходит за допустимые пределы")
    return dict(discount_mode=mode, discount_value=value, line_subtotal=subtotal,
                unit_price=effective_price, line_total=total.quantize(CENT))


def discount_totals(row):
    """Preserve legacy analytics; new lines use the stored rounded amounts."""
    if not getattr(row, "is_discounted", False):
        return None
    quantity = Decimal(getattr(row, "quantity", 0) or 0)
    if getattr(row, "discount_mode", None):
        subtotal = getattr(row, "line_subtotal", None)
        if subtotal is None:
            return None
        regular, actual = Decimal(subtotal), Decimal(row.line_total)
    else:
        regular = Decimal(getattr(row, "regular_unit_price", 0) or 0) * quantity
        actual = Decimal(getattr(row, "unit_price", 0) or 0) * quantity
    return (regular, actual) if quantity > 0 and regular > actual > 0 else None
