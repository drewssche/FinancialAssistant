from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.repositories.operation_repo import OperationRepository
from app.core.purchase_quantities import add_quantities, empty_quantities


class DashboardAnalyticsPositionsService:
    MONTH_LABELS = ("", "Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек")

    def __init__(self, repo: OperationRepository):
        self.repo = repo

    def get_positions(self, *, user_id: int, period: str, anchor: date | None = None) -> dict:
        resolved_anchor = anchor or date.today()
        date_from, date_to = self._period_bounds(period=period, anchor=resolved_anchor)
        buckets = self._build_buckets(period=period, date_from=date_from, date_to=date_to)
        result = self.summarize_period(user_id=user_id, date_from=date_from, date_to=date_to, buckets=buckets)
        return {
            "period": period, "anchor": resolved_anchor.isoformat(),
            "date_from": date_from.isoformat(), "date_to": date_to.isoformat(),
            "buckets": buckets, **result,
        }

    def summarize_period(self, *, user_id: int, date_from: date, date_to: date, buckets=None) -> dict:
        buckets = buckets or []
        bucket_by_date = self._bucket_by_date(buckets)
        positions = {}
        summary = self._empty_totals()
        for row in self.repo.aggregate_positions_for_period(user_id=user_id, date_from=date_from, date_to=date_to):
            product_id, template_id = row.get("product_id"), row["template_id"]
            name = str(row["name"] or "Позиция").strip() or "Позиция"
            shop_name = str(row["shop_name"]).strip() if row["shop_name"] else None
            identity = (("product", product_id) if product_id is not None else
                        ("template", template_id) if template_id is not None else
                        ("legacy", name.casefold(), (shop_name or "").casefold()))
            position = positions.setdefault(identity, {
                "product_id": product_id, "template_id": template_id, "name": name,
                "source_names": set(), "buckets": defaultdict(self._empty_totals), **self._empty_totals(),
            })
            if shop_name:
                position["source_names"].add(shop_name)
            self._add_row(position, row)
            self._add_row(summary, row)
            bucket_key = bucket_by_date.get(row["operation_date"])
            if bucket_key:
                self._add_row(position["buckets"][bucket_key], row)
        result = []
        for position in positions.values():
            sources = sorted(position["source_names"], key=str.casefold)
            result.append({
                "product_id": position["product_id"], "template_id": position["template_id"],
                "name": position["name"], "shop_name": sources[0] if len(sources) == 1 else None,
                "source_names": sources, "sources_count": len(sources),
                **self._serialize_totals(position),
                "buckets": [{"key": bucket["key"], **self._serialize_totals(position["buckets"].get(bucket["key"]))}
                            for bucket in buckets],
            })
        result.sort(key=lambda item: (-item["purchases_count"], item["name"].casefold()))
        return {"positions": result, "summary": self._serialize_totals(summary)}

    @staticmethod
    def _empty_totals():
        return {"operation_ids": set(), "quantity_totals": empty_quantities(),
                "quantity_total": Decimal("0"), "amount_total": Decimal("0"), "amount_totals": defaultdict(Decimal)}

    @staticmethod
    def _add_row(target, row):
        target["operation_ids"].add(row["operation_id"])
        add_quantities(target["quantity_totals"], {**row, "quantity": row["quantity_total"]}, rows_count=row["rows_count"])
        target["amount_totals"][row["currency"]] += row["amount_total"]
        # Legacy API compatibility only. New UI must never compare these untyped sums.
        target["quantity_total"] += row["quantity_total"]
        target["amount_total"] += row["amount_total"]

    @staticmethod
    def _serialize_totals(totals):
        if totals is None:
            return {"purchases_count": 0, "quantity_total": Decimal("0"), "amount_total": Decimal("0"),
                    "quantity_totals": None, "amount_totals": {}}
        return {"purchases_count": len(totals["operation_ids"]),
                "quantity_total": totals["quantity_total"], "amount_total": totals["amount_total"],
                "quantity_totals": totals["quantity_totals"], "amount_totals": dict(totals["amount_totals"])}

    @staticmethod
    def _period_bounds(*, period: str, anchor: date) -> tuple[date, date]:
        if period == "day":
            return anchor, anchor
        if period == "week":
            start = anchor - timedelta(days=anchor.weekday())
            return start, start + timedelta(days=6)
        if period == "month":
            start = anchor.replace(day=1)
            end = start.replace(day=calendar.monthrange(start.year, start.month)[1])
            return start, end
        if period == "year":
            return anchor.replace(month=1, day=1), anchor.replace(month=12, day=31)
        raise ValueError("Invalid position analytics period")

    @staticmethod
    def _build_buckets(*, period: str, date_from: date, date_to: date) -> list[dict]:
        if period == "year":
            return [
                {
                    "key": f"{date_from.year:04d}-{month:02d}",
                    "label": DashboardAnalyticsPositionsService.MONTH_LABELS[month],
                    "date_from": date(date_from.year, month, 1).isoformat(),
                    "date_to": date(
                        date_from.year,
                        month,
                        calendar.monthrange(date_from.year, month)[1],
                    ).isoformat(),
                }
                for month in range(1, 13)
            ]
        buckets = []
        cursor = date_from
        while cursor <= date_to:
            buckets.append(
                {
                    "key": cursor.isoformat(),
                    "label": cursor.strftime("%d.%m") if period in {"day", "week"} else str(cursor.day),
                    "date_from": cursor.isoformat(),
                    "date_to": cursor.isoformat(),
                }
            )
            cursor += timedelta(days=1)
        return buckets

    @staticmethod
    def _bucket_by_date(buckets: list[dict]) -> dict[date, str]:
        result = {}
        for bucket in buckets:
            start = date.fromisoformat(bucket["date_from"])
            end = date.fromisoformat(bucket["date_to"])
            cursor = start
            while cursor <= end:
                result[cursor] = bucket["key"]
                cursor += timedelta(days=1)
        return result
