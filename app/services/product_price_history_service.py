"""Read-only price observations from actual receipt snapshots, never catalog defaults."""
from collections import OrderedDict
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select

from app.db.models import CatalogProduct, Operation, OperationItemTemplate, OperationReceiptItem

SCALES = {"kg": ("kg", Decimal(1)), "g": ("kg", Decimal("0.001")),
          "l": ("l", Decimal(1)), "ml": ("l", Decimal("0.001")),
          "piece": ("piece", Decimal(1))}


def percent(previous, current):
    if previous is None or previous <= 0:
        return None
    return ((current / previous - 1) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def content(item):
    if item.sale_unit in {"kg", "g", "l", "ml"}:
        return SCALES[item.sale_unit]
    if item.package_quantity and item.package_quantity > 0 and item.package_unit in SCALES:
        unit, scale = SCALES[item.package_unit]
        return unit, scale * item.package_quantity
    if item.sale_unit == "piece":
        return "piece", Decimal(1)
    return None, None


class ProductPriceHistoryService:
    def __init__(self, db):
        self.db = db

    def get(self, *, user_id, product_id, template_id, basis="unit", price_kind="paid", date_from=None, date_to=None):
        offer = self.db.scalar(select(OperationItemTemplate).join(
            CatalogProduct, CatalogProduct.id == OperationItemTemplate.product_id
        ).where(OperationItemTemplate.id == template_id, OperationItemTemplate.user_id == user_id,
                CatalogProduct.id == product_id, CatalogProduct.user_id == user_id))
        if offer is None:
            raise LookupError("Product offer not found")
        stmt = select(OperationReceiptItem, Operation.operation_date, Operation.currency).join(
            Operation, Operation.id == OperationReceiptItem.operation_id
        ).where(OperationReceiptItem.template_id == template_id,
                OperationReceiptItem.user_id == user_id, Operation.user_id == user_id,
                Operation.kind == "expense")
        if date_from:
            stmt = stmt.where(Operation.operation_date >= date_from)
        if date_to:
            stmt = stmt.where(Operation.operation_date <= date_to)
        rows = self.db.execute(stmt.order_by(Operation.operation_date, Operation.id, OperationReceiptItem.id))
        groups = OrderedDict()
        excluded = 0
        for item, recorded_at, currency in rows:
            if item.quantity <= 0 or item.line_total < 0:
                excluded += 1
                continue
            price = item.line_total / item.quantity if price_kind == "paid" else item.regular_unit_price
            if price is None:
                excluded += 1
                continue
            normalized_unit, divisor = content(item)
            package = (item.sale_unit, item.package_quantity, item.package_unit)
            if basis == "normalized":
                if divisor is None:
                    excluded += 1
                    continue
                price /= divisor
                unit, grouping = normalized_unit, normalized_unit
            else:
                unit, grouping = item.sale_unit, package
            # Receipt shop text is a snapshot too. Renaming/reassigning an offer must not
            # silently compare two different receipt shops as one observation series.
            shop = " ".join((item.shop_name or "").split())
            key = (currency, shop.casefold(), grouping)
            if key not in groups:
                groups[key] = {"currency": currency, "shop_name": shop or None, "unit": unit,
                               "sale_unit": item.sale_unit if basis == "unit" else None,
                               "package_quantity": item.package_quantity if basis == "unit" else None,
                               "package_unit": item.package_unit if basis == "unit" else None,
                               "observations": [], "increases": 0, "decreases": 0}
            group = groups[key]
            observations = group["observations"]
            previous = observations[-1] if observations else None
            change = percent(previous["price"], price) if previous else None
            direction = (1 if price > previous["price"] else -1 if price < previous["price"] else 0) if previous else 0
            group["increases"] += direction == 1
            group["decreases"] += direction == -1
            observations.append({"receipt_item_id": item.id, "operation_id": item.operation_id,
                "recorded_at": recorded_at, "name": item.name, "quantity": item.quantity,
                "line_total": item.line_total, "price": price, "change_percent": change,
                "direction": direction, "is_discounted": item.is_discounted,
                "discount_type": item.discount_type, "sale_unit": item.sale_unit,
                "package_quantity": item.package_quantity, "package_unit": item.package_unit,
                "package_changed": bool(previous and package != (previous["sale_unit"], previous["package_quantity"], previous["package_unit"]))})
        for group in groups.values():
            observations = group["observations"]
            group["change_percent"] = percent(observations[0]["price"], observations[-1]["price"])
        return {"basis": basis, "price_kind": price_kind, "series": list(groups.values()), "excluded_count": excluded}
