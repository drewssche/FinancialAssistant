from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category, CategoryGroup
from app.repositories.operation_repo import OperationRepository
from app.services.dashboard_analytics_timeline import DashboardAnalyticsTimelineService


class DashboardAnalyticsHighlightsService:
    def __init__(self, db: Session, repo: OperationRepository, timeline: DashboardAnalyticsTimelineService):
        self.db = db
        self.repo = repo
        self.timeline = timeline

    def build_receipt_analytics_snapshot(
        self,
        *,
        operations: list,
        receipt_items_by_operation: dict[int, list] | None = None,
    ) -> tuple[list[dict], dict[tuple[str, str | None], dict]]:
        grouped_receipt_items = receipt_items_by_operation or {}
        allocations: list[dict] = []
        position_stats: dict[tuple[str, str | None], dict] = defaultdict(
            lambda: {
                "name": "",
                "shop_name": None,
                "total_spent": Decimal("0"),
                "max_unit_price": Decimal("0"),
                "unit_price_sum": Decimal("0"),
                "unit_price_count": 0,
                "purchases_count": 0,
            }
        )
        for item in operations:
            operation_id = int(item["id"])
            amount = Decimal(item["amount"] or 0)
            receipt_rows = grouped_receipt_items.get(operation_id, []) or []
            if not receipt_rows:
                allocations.append(
                    {
                        "operation_id": operation_id,
                        "operation_date": item["operation_date"],
                        "kind": item["kind"],
                        "category_id": int(item["category_id"]) if item["category_id"] is not None else None,
                        "amount": amount,
                    }
                )
                continue

            receipt_total = Decimal("0")
            effective_receipt_category_ids: set[int | None] = set()
            for row in receipt_rows:
                line_total = Decimal(row.line_total or 0)
                receipt_total += line_total
                name = str(row.name or "").strip()
                if name:
                    shop_name = str(row.shop_name).strip() if row.shop_name else None
                    key = (name.casefold(), shop_name.casefold() if shop_name else None)
                    bucket = position_stats[key]
                    bucket["name"] = name
                    bucket["shop_name"] = shop_name
                    unit_price = Decimal(row.unit_price or 0)
                    bucket["total_spent"] += line_total
                    bucket["max_unit_price"] = max(bucket["max_unit_price"], unit_price)
                    bucket["unit_price_sum"] += unit_price
                    bucket["unit_price_count"] += 1
                    bucket["purchases_count"] += 1
                effective_category_id = (
                    int(row.category_id)
                    if row.category_id is not None
                    else (int(item["category_id"]) if item["category_id"] is not None else None)
                )
                effective_receipt_category_ids.add(effective_category_id)
                allocations.append(
                    {
                        "operation_id": operation_id,
                        "operation_date": item["operation_date"],
                        "kind": item["kind"],
                        "category_id": effective_category_id,
                        "amount": line_total,
                    }
                )

            discrepancy = amount - receipt_total
            if discrepancy != 0:
                if item["category_id"] is not None:
                    fallback_category_id = int(item["category_id"])
                elif len(effective_receipt_category_ids) == 1:
                    fallback_category_id = next(iter(effective_receipt_category_ids))
                else:
                    fallback_category_id = None
                allocations.append(
                    {
                        "operation_id": operation_id,
                        "operation_date": item["operation_date"],
                        "kind": item["kind"],
                        "category_id": fallback_category_id,
                        "amount": discrepancy,
                    }
                )
        return allocations, position_stats

    def load_category_maps_for_allocations(
        self,
        allocations: list[dict],
    ) -> tuple[dict[int, str], dict[int, str], dict[int, int | None], dict[int, str | None]]:
        category_ids = {
            int(item["category_id"])
            for item in allocations
            if item.get("category_id") is not None
        }
        if not category_ids:
            return {}, {}, {}, {}
        rows = self.db.execute(
            select(Category.id, Category.name, Category.kind, Category.group_id, CategoryGroup.name)
            .outerjoin(CategoryGroup, Category.group_id == CategoryGroup.id)
            .where(Category.id.in_(category_ids))
        ).all()
        category_name_map = {int(row[0]): str(row[1]) for row in rows}
        category_kind_map = {int(row[0]): str(row[2] or "expense") for row in rows}
        category_group_id_map = {
            int(row[0]): (int(row[3]) if row[3] is not None else None)
            for row in rows
        }
        category_group_name_map = {
            int(row[0]): (str(row[4]) if row[4] is not None else None)
            for row in rows
        }
        return category_name_map, category_kind_map, category_group_id_map, category_group_name_map

    def get_highlights(
        self,
        *,
        user_id: int,
        period: str = "month",
        category_kind: str = "expense",
        category_breakdown_level: str = "category",
        date_from: date | None = None,
        date_to: date | None = None,
        month_anchor: date | None = None,
    ) -> dict:
        if period == "month" and month_anchor is not None:
            resolved_from, resolved_to = self.timeline.month_bounds(month_anchor)
        else:
            resolved_from, resolved_to = self.timeline.resolve_period_bounds(
                user_id=user_id,
                period=period,
                date_from=date_from,
                date_to=date_to,
            )
        month_start, month_end = self.timeline.month_bounds(resolved_from)

        span_days = (resolved_to - resolved_from).days + 1
        prev_to = resolved_from - timedelta(days=1)
        prev_from = prev_to - timedelta(days=max(0, span_days - 1))

        operations = self.repo.list_snapshot_for_period(user_id=user_id, date_from=resolved_from, date_to=resolved_to)
        prev_operations = self.repo.list_snapshot_for_period(user_id=user_id, date_from=prev_from, date_to=prev_to)
        current_receipt_items = self.repo.list_receipt_items_for_operations(
            user_id=user_id,
            operation_ids=[int(item["id"]) for item in operations],
        )
        previous_receipt_items = self.repo.list_receipt_items_for_operations(
            user_id=user_id,
            operation_ids=[int(item["id"]) for item in prev_operations],
        )

        current_daily = self.repo.aggregate_daily_for_period(user_id=user_id, date_from=resolved_from, date_to=resolved_to)
        income_total, expense_total, operations_count = self.repo.summary_with_count_for_period(
            user_id=user_id,
            date_from=resolved_from,
            date_to=resolved_to,
        )
        prev_income_total, prev_expense_total, prev_operations_count = self.repo.summary_with_count_for_period(
            user_id=user_id,
            date_from=prev_from,
            date_to=prev_to,
        )

        max_expense_day_total = Decimal("0")
        max_expense_day_date: date | None = None
        for row in current_daily:
            expense_day_total = Decimal(row["expense_total"] or 0)
            if (expense_day_total, row["operation_date"]) >= (max_expense_day_total, max_expense_day_date or row["operation_date"]):
                max_expense_day_total = expense_day_total
                max_expense_day_date = row["operation_date"]

        avg_daily_expense = (expense_total / Decimal(span_days)) if span_days > 0 else Decimal("0")

        current_category_allocations, current_position_stats = self.build_receipt_analytics_snapshot(
            operations=operations,
            receipt_items_by_operation=current_receipt_items,
        )
        previous_category_allocations, previous_position_stats = self.build_receipt_analytics_snapshot(
            operations=prev_operations,
            receipt_items_by_operation=previous_receipt_items,
        )
        (
            category_name_map,
            category_kind_map,
            category_group_id_map,
            category_group_name_map,
        ) = self.load_category_maps_for_allocations([*current_category_allocations, *previous_category_allocations])

        heavy_candidates = [item for item in operations if item["kind"] == "expense"] or operations
        top_operations = sorted(
            heavy_candidates,
            key=lambda item: (Decimal(item["amount"] or 0), item["operation_date"], item["id"]),
            reverse=True,
        )[:5]

        def include_category_item(item_kind: str) -> bool:
            if category_kind == "all":
                return item_kind in {"income", "expense"}
            return item_kind == category_kind

        current_category_totals: dict[tuple[str, int | None], dict] = defaultdict(
            lambda: {
                "total_amount": Decimal("0"),
                "operations_count": 0,
                "category_kind": "expense",
                "category_id": None,
                "category_name": "Без категории",
                "group_id": None,
                "group_name": None,
            }
        )
        previous_category_totals: dict[tuple[str, int | None], Decimal] = defaultdict(lambda: Decimal("0"))

        def breakdown_key(category_id: int | None) -> tuple[str, int | None]:
            if category_breakdown_level == "group":
                if category_id is None:
                    return ("group", None)
                return ("group", category_group_id_map.get(category_id))
            return ("category", category_id)

        for allocation in current_category_allocations:
            if not include_category_item(allocation["kind"]):
                continue
            category_id = allocation["category_id"]
            key = breakdown_key(category_id)
            bucket = current_category_totals[key]
            bucket["total_amount"] += Decimal(allocation["amount"] or 0)
            bucket.setdefault("operation_ids", set()).add(int(allocation["operation_id"]))
            bucket["operations_count"] = len(bucket["operation_ids"])
            bucket["category_kind"] = allocation["kind"]
            if category_breakdown_level == "group":
                bucket["group_id"] = key[1]
                bucket["group_name"] = (
                    category_group_name_map.get(category_id)
                    if category_id is not None
                    else None
                ) or "Без группы"
                bucket["category_id"] = None
                bucket["category_name"] = bucket["group_name"]
            else:
                bucket["category_id"] = category_id
                bucket["category_name"] = (
                    category_name_map.get(category_id, "Без категории")
                    if category_id is not None
                    else "Без категории"
                )
                bucket["group_id"] = category_group_id_map.get(category_id) if category_id is not None else None
                bucket["group_name"] = category_group_name_map.get(category_id) if category_id is not None else None
        for allocation in previous_category_allocations:
            if not include_category_item(allocation["kind"]):
                continue
            previous_category_totals[breakdown_key(allocation["category_id"])] += Decimal(allocation["amount"] or 0)

        category_breakdown_total = sum(
            (bucket["total_amount"] for bucket in current_category_totals.values()),
            start=Decimal("0"),
        )
        sorted_categories = sorted(
            current_category_totals.items(),
            key=lambda pair: pair[1]["total_amount"],
            reverse=True,
        )
        top_categories = sorted_categories[:5]

        expense_values = sorted(Decimal(item["amount"] or 0) for item in operations if item["kind"] == "expense")
        median_expense = Decimal("0")
        if expense_values:
            mid = len(expense_values) // 2
            if len(expense_values) % 2 == 0:
                median_expense = (expense_values[mid - 1] + expense_values[mid]) / Decimal("2")
            else:
                median_expense = expense_values[mid]
        anomalies = []
        if median_expense > 0:
            for item in operations:
                if item["kind"] != "expense":
                    continue
                amount = Decimal(item["amount"] or 0)
                ratio = float(amount / median_expense) if median_expense > 0 else 0.0
                if ratio < 2.0:
                    continue
                category_name = (
                    category_name_map.get(int(item["category_id"]), "Без категории")
                    if item["category_id"] is not None
                    else "Без категории"
                )
                anomalies.append(
                    {
                        "operation_id": int(item["id"]),
                        "operation_date": item["operation_date"].isoformat(),
                        "amount": amount,
                        "note": item["note"],
                        "category_name": category_name,
                        "ratio_to_median": ratio,
                    }
                )
        anomalies.sort(key=lambda item: item["amount"], reverse=True)

        top_positions = sorted(
            current_position_stats.values(),
            key=lambda item: (item["max_unit_price"], item["total_spent"], item["purchases_count"]),
            reverse=True,
        )[:10]

        price_increases = []
        for key, current_item in current_position_stats.items():
            previous_item = previous_position_stats.get(key)
            if not previous_item:
                continue
            prev_count = int(previous_item["unit_price_count"] or 0)
            curr_count = int(current_item["unit_price_count"] or 0)
            if prev_count <= 0 or curr_count <= 0:
                continue
            prev_avg = previous_item["unit_price_sum"] / Decimal(prev_count)
            curr_avg = current_item["unit_price_sum"] / Decimal(curr_count)
            change_pct = self.timeline.percent_change(curr_avg, prev_avg)
            if change_pct is None or change_pct < 10.0:
                continue
            price_increases.append(
                {
                    "name": current_item["name"],
                    "shop_name": current_item["shop_name"],
                    "previous_avg_unit_price": prev_avg,
                    "current_avg_unit_price": curr_avg,
                    "change_pct": change_pct,
                }
            )

        price_increases.sort(key=lambda item: item["change_pct"], reverse=True)

        balance = income_total - expense_total
        prev_balance = prev_income_total - prev_expense_total
        surplus_total = balance if balance > 0 else Decimal("0")
        deficit_total = abs(balance) if balance < 0 else Decimal("0")
        return {
            "period": period,
            "category_breakdown_kind": category_kind,
            "category_breakdown_level": category_breakdown_level,
            "date_from": resolved_from.isoformat(),
            "date_to": resolved_to.isoformat(),
            "month": month_start.strftime("%Y-%m"),
            "month_start": month_start.isoformat(),
            "month_end": month_end.isoformat(),
            "income_total": income_total,
            "expense_total": expense_total,
            "balance": balance,
            "prev_income_total": prev_income_total,
            "prev_expense_total": prev_expense_total,
            "prev_balance": prev_balance,
            "prev_operations_count": prev_operations_count,
            "surplus_total": surplus_total,
            "deficit_total": deficit_total,
            "operations_count": operations_count,
            "avg_daily_expense": avg_daily_expense,
            "max_expense_day_date": max_expense_day_date.isoformat() if max_expense_day_date else None,
            "max_expense_day_total": max_expense_day_total,
            "income_change_pct": self.timeline.percent_change(income_total, prev_income_total),
            "expense_change_pct": self.timeline.percent_change(expense_total, prev_expense_total),
            "balance_change_pct": self.timeline.percent_change(balance, prev_balance),
            "operations_change_pct": self.timeline.percent_change(Decimal(operations_count), Decimal(prev_operations_count)),
            "category_breakdown": [
                {
                    "category_id": bucket["category_id"],
                    "category_name": bucket["category_name"],
                    "group_id": bucket["group_id"],
                    "group_name": bucket["group_name"],
                    "category_kind": (
                        category_kind_map.get(bucket["category_id"], bucket["category_kind"])
                        if bucket["category_id"] is not None
                        else bucket["category_kind"]
                    ),
                    "total_amount": bucket["total_amount"],
                    "total_expense": bucket["total_amount"],
                    "share_pct": (
                        float((bucket["total_amount"] / category_breakdown_total) * Decimal("100"))
                        if category_breakdown_total > 0
                        else 0.0
                    ),
                    "change_pct": self.timeline.percent_change(bucket["total_amount"], previous_category_totals[key]),
                    "operations_count": int(bucket["operations_count"]),
                }
                for key, bucket in sorted_categories
            ],
            "top_operations": [
                {
                    "operation_id": int(item["id"]),
                    "operation_date": item["operation_date"].isoformat(),
                    "kind": item["kind"],
                    "amount": Decimal(item["amount"] or 0),
                    "note": item["note"],
                }
                for item in top_operations
            ],
            "top_categories": [
                {
                    "category_id": bucket["category_id"],
                    "category_name": bucket["category_name"],
                    "group_id": bucket["group_id"],
                    "group_name": bucket["group_name"],
                    "category_kind": (
                        category_kind_map.get(bucket["category_id"], bucket["category_kind"])
                        if bucket["category_id"] is not None
                        else bucket["category_kind"]
                    ),
                    "total_amount": bucket["total_amount"],
                    "total_expense": bucket["total_amount"],
                    "share_pct": (
                        float((bucket["total_amount"] / category_breakdown_total) * Decimal("100"))
                        if category_breakdown_total > 0
                        else 0.0
                    ),
                    "change_pct": self.timeline.percent_change(bucket["total_amount"], previous_category_totals[key]),
                    "operations_count": int(bucket["operations_count"]),
                }
                for key, bucket in top_categories
            ],
            "anomalies": anomalies[:5],
            "top_positions": [
                {
                    "name": item["name"],
                    "shop_name": item["shop_name"],
                    "total_spent": item["total_spent"],
                    "max_unit_price": item["max_unit_price"],
                    "avg_unit_price": (
                        item["unit_price_sum"] / Decimal(item["unit_price_count"])
                        if int(item["unit_price_count"] or 0) > 0
                        else Decimal("0")
                    ),
                    "purchases_count": int(item["purchases_count"]),
                }
                for item in top_positions
            ],
            "price_increases": price_increases[:5],
        }
