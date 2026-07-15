from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.repositories.operation_repo import OperationRepository


class DashboardAnalyticsPositionsService:
    MONTH_LABELS = ("", "Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек")

    def __init__(self, repo: OperationRepository):
        self.repo = repo

    def get_positions(self, *, user_id: int, period: str, anchor: date | None = None) -> dict:
        resolved_anchor = anchor or date.today()
        date_from, date_to = self._period_bounds(period=period, anchor=resolved_anchor)
        buckets = self._build_buckets(period=period, date_from=date_from, date_to=date_to)
        bucket_by_date = self._bucket_by_date(buckets)
        positions: dict[tuple, dict] = {}

        for row in self.repo.aggregate_positions_for_period(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        ):
            template_id = row["template_id"]
            name = str(row["name"] or "Позиция").strip() or "Позиция"
            shop_name = str(row["shop_name"]).strip() if row["shop_name"] else None
            identity = (
                ("template", template_id)
                if template_id is not None
                else ("legacy", name.casefold(), shop_name.casefold() if shop_name else "")
            )
            position = positions.setdefault(
                identity,
                {
                    "template_id": template_id,
                    "name": name,
                    "shop_name": shop_name,
                    "purchases_count": 0,
                    "quantity_total": Decimal("0"),
                    "amount_total": Decimal("0"),
                    "buckets": defaultdict(
                        lambda: {
                            "purchases_count": 0,
                            "quantity_total": Decimal("0"),
                            "amount_total": Decimal("0"),
                        }
                    ),
                },
            )
            bucket_key = bucket_by_date.get(row["operation_date"])
            if not bucket_key:
                continue
            position["purchases_count"] += int(row["purchases_count"] or 0)
            position["quantity_total"] += Decimal(row["quantity_total"] or 0)
            position["amount_total"] += Decimal(row["amount_total"] or 0)
            position_bucket = position["buckets"][bucket_key]
            position_bucket["purchases_count"] += int(row["purchases_count"] or 0)
            position_bucket["quantity_total"] += Decimal(row["quantity_total"] or 0)
            position_bucket["amount_total"] += Decimal(row["amount_total"] or 0)

        rows = []
        for position in positions.values():
            values = []
            for bucket in buckets:
                metrics = position["buckets"].get(bucket["key"], {})
                values.append(
                    {
                        "key": bucket["key"],
                        "purchases_count": int(metrics.get("purchases_count", 0)),
                        "quantity_total": Decimal(metrics.get("quantity_total", 0)),
                        "amount_total": Decimal(metrics.get("amount_total", 0)),
                    }
                )
            rows.append(
                {
                    "template_id": position["template_id"],
                    "name": position["name"],
                    "shop_name": position["shop_name"],
                    "purchases_count": int(position["purchases_count"]),
                    "quantity_total": Decimal(position["quantity_total"]),
                    "amount_total": Decimal(position["amount_total"]),
                    "buckets": values,
                }
            )
        rows.sort(
            key=lambda item: (
                item["purchases_count"],
                item["quantity_total"],
                item["amount_total"],
                item["name"].casefold(),
            ),
            reverse=True,
        )
        return {
            "period": period,
            "anchor": resolved_anchor.isoformat(),
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "buckets": buckets,
            "positions": rows,
        }

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
