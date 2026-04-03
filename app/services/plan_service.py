import calendar
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.cache import (
    build_plans_cache_key,
    get_json,
    get_namespace_ttl_seconds,
    invalidate_plans_cache,
    set_json,
)
from app.core.logging import log_background_job_event
from app.repositories.currency_repo import CurrencyRepository
from app.repositories.plan_repo import PlanRepository
from app.services.operation_service import OperationService
from app.services.plan_reminder_service import PlanReminderService


class PlanService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PlanRepository(db)
        self.currency_repo = CurrencyRepository(db)
        self.operation_service = OperationService(db)
        self.reminder_service = PlanReminderService(db)

    def list_plans(self, *, user_id: int, q: str | None = None, kind: str | None = None) -> tuple[list[dict], int]:
        cache_key = build_plans_cache_key(user_id=user_id, view="list", q=q, kind=kind)
        cached = get_json(cache_key)
        if cached:
            items = cached.get("items")
            total = cached.get("total")
            if isinstance(items, list) and isinstance(total, int):
                return items, total
        rows = self.repo.list_for_user(user_id=user_id, q=q, kind=kind)
        plan_ids = [int(row.PlanOperation.id) for row in rows]
        receipt_by_plan = self.repo.list_receipt_items_for_plans(user_id=user_id, plan_ids=plan_ids)
        reminder_jobs = self.repo.list_next_pending_jobs_for_plans(user_id=user_id, plan_ids=plan_ids)
        items = [
            self._serialize_plan_row(
                row=row,
                receipt_items=receipt_by_plan.get(int(row.PlanOperation.id), []),
                reminder_job=reminder_jobs.get(int(row.PlanOperation.id)),
            )
            for row in rows
        ]
        set_json(cache_key, {"items": items, "total": len(items)}, ttl_seconds=get_namespace_ttl_seconds("plans"))
        return items, len(items)

    def get_plan(self, *, user_id: int, plan_id: int) -> dict:
        row = self.repo.get_by_id(user_id=user_id, plan_id=plan_id)
        if not row:
            raise LookupError("Plan not found")
        receipt_by_plan = self.repo.list_receipt_items_for_plans(user_id=user_id, plan_ids=[plan_id])
        reminder_job = self.repo.list_next_pending_jobs_for_plans(user_id=user_id, plan_ids=[plan_id]).get(plan_id)
        return self._serialize_plan_row(row=row, receipt_items=receipt_by_plan.get(plan_id, []), reminder_job=reminder_job)

    def list_history(self, *, user_id: int, q: str | None = None, kind: str | None = None) -> tuple[list[dict], int]:
        cache_key = build_plans_cache_key(user_id=user_id, view="history", q=q, kind=kind)
        cached = get_json(cache_key)
        if cached:
            items = cached.get("items")
            total = cached.get("total")
            if isinstance(items, list) and isinstance(total, int):
                return items, total
        rows = self.repo.list_history_for_user(user_id=user_id, q=q, kind=kind)
        items = [self._serialize_event_row(row) for row in rows]
        set_json(cache_key, {"items": items, "total": len(items)}, ttl_seconds=get_namespace_ttl_seconds("plans"))
        return items, len(items)

    def create_plan(
        self,
        *,
        user_id: int,
        kind: str,
        amount: Decimal | None,
        currency: str = "BYN",
        scheduled_date: date,
        category_id: int | None,
        note: str | None,
        receipt_items: list[dict] | None = None,
        recurrence_enabled: bool = False,
        recurrence_frequency: str | None = None,
        recurrence_interval: int = 1,
        recurrence_weekdays: list[int] | None = None,
        recurrence_workdays_only: bool = False,
        recurrence_month_end: bool = False,
        recurrence_end_date: date | None = None,
    ) -> dict:
        self.operation_service._validate_kind(kind)
        normalized_items, receipt_total = self.operation_service._normalize_receipt_items(receipt_items or [])
        resolved_amount = self.operation_service._resolve_operation_amount(amount=amount, receipt_total=receipt_total)
        base_currency = self.operation_service._get_user_base_currency(user_id)
        normalized_currency = self.operation_service._normalize_currency(currency or base_currency, default=base_currency)
        recurrence_frequency, recurrence_interval, recurrence_weekdays, recurrence_workdays_only, recurrence_month_end, recurrence_end_date = self._validate_recurrence(
            recurrence_enabled=recurrence_enabled,
            recurrence_frequency=recurrence_frequency,
            recurrence_interval=recurrence_interval,
            recurrence_weekdays=recurrence_weekdays,
            recurrence_workdays_only=recurrence_workdays_only,
            recurrence_month_end=recurrence_month_end,
            scheduled_date=scheduled_date,
            recurrence_end_date=recurrence_end_date,
        )
        item = self.repo.create(
            user_id=user_id,
            kind=kind,
            amount=resolved_amount,
            original_amount=resolved_amount,
            currency=normalized_currency,
            base_currency=base_currency,
            scheduled_date=scheduled_date,
            category_id=category_id,
            note=note,
            recurrence_enabled=recurrence_enabled,
            recurrence_frequency=recurrence_frequency,
            recurrence_interval=recurrence_interval,
            recurrence_weekdays=recurrence_weekdays,
            recurrence_workdays_only=recurrence_workdays_only,
            recurrence_month_end=recurrence_month_end,
            recurrence_end_date=recurrence_end_date,
        )
        if normalized_items:
            self.repo.replace_receipt_items(user_id=user_id, plan_id=item.id, items=normalized_items)
            self.operation_service.item_templates.sync_templates_from_receipt_items(
                user_id=user_id,
                category_id=category_id,
                normalized_items=normalized_items,
                recorded_at=scheduled_date,
            )
            log_background_job_event(
                "plan_service",
                "plan_item_templates_synced",
                user_id=user_id,
                plan_id=int(item.id),
                receipt_items_count=len(normalized_items),
            )
        self.reminder_service.sync_plan_job(item)
        log_background_job_event(
            "plan_service",
            "plan_reminder_sync_requested",
            action="create",
            user_id=user_id,
            plan_id=int(item.id),
            recurrence_enabled=bool(item.recurrence_enabled),
        )
        self.db.commit()
        invalidate_plans_cache(user_id)
        log_background_job_event(
            "plan_service",
            "plan_created",
            user_id=user_id,
            plan_id=int(item.id),
            kind=item.kind,
            status=item.status,
            recurrence_enabled=bool(item.recurrence_enabled),
        )
        return self.get_plan(user_id=user_id, plan_id=int(item.id))

    def update_plan(self, *, user_id: int, plan_id: int, updates: dict) -> dict:
        row = self.repo.get_by_id(user_id=user_id, plan_id=plan_id)
        if not row:
            raise LookupError("Plan not found")
        item = row.PlanOperation
        if "kind" in updates and updates["kind"] is not None:
            self.operation_service._validate_kind(updates["kind"])
        base_currency = self.operation_service._get_user_base_currency(user_id)
        receipt_items_input = updates.pop("receipt_items", None) if "receipt_items" in updates else None
        normalized_items = None
        receipt_total = None
        if receipt_items_input is not None:
            normalized_items, receipt_total = self.operation_service._normalize_receipt_items(receipt_items_input)
        if "amount" in updates:
            if updates["amount"] is None:
                if receipt_items_input is None:
                    raise ValueError("amount must not be null")
                updates["amount"] = self.operation_service._resolve_operation_amount(amount=None, receipt_total=receipt_total)
            else:
                updates["amount"] = self.operation_service._money(updates["amount"])
        if "currency" in updates and updates["currency"] is not None:
            updates["currency"] = self.operation_service._normalize_currency(updates["currency"], default=base_currency)
        updates["base_currency"] = base_currency
        if "amount" in updates:
            updates["original_amount"] = updates["amount"]
        next_scheduled_date = updates.get("scheduled_date", item.scheduled_date)
        next_recurrence_enabled = updates.get("recurrence_enabled", item.recurrence_enabled)
        next_recurrence_frequency = updates["recurrence_frequency"] if "recurrence_frequency" in updates else item.recurrence_frequency
        next_recurrence_interval = updates.get("recurrence_interval", item.recurrence_interval)
        next_recurrence_weekdays = updates["recurrence_weekdays"] if "recurrence_weekdays" in updates else self._parse_weekdays(item.recurrence_weekdays)
        next_recurrence_workdays_only = updates.get("recurrence_workdays_only", bool(item.recurrence_workdays_only))
        next_recurrence_month_end = updates.get("recurrence_month_end", bool(item.recurrence_month_end))
        next_recurrence_end_date = updates["recurrence_end_date"] if "recurrence_end_date" in updates else item.recurrence_end_date
        (
            updates["recurrence_frequency"],
            updates["recurrence_interval"],
            updates["recurrence_weekdays"],
            updates["recurrence_workdays_only"],
            updates["recurrence_month_end"],
            updates["recurrence_end_date"],
        ) = self._validate_recurrence(
            recurrence_enabled=next_recurrence_enabled,
            recurrence_frequency=next_recurrence_frequency,
            recurrence_interval=next_recurrence_interval,
            recurrence_weekdays=next_recurrence_weekdays,
            recurrence_workdays_only=next_recurrence_workdays_only,
            recurrence_month_end=next_recurrence_month_end,
            scheduled_date=next_scheduled_date,
            recurrence_end_date=next_recurrence_end_date,
        )
        updates["recurrence_enabled"] = bool(next_recurrence_enabled)
        self.repo.update(item, updates)
        if normalized_items is not None:
            self.repo.replace_receipt_items(user_id=user_id, plan_id=item.id, items=normalized_items)
            if normalized_items:
                next_category_id = updates.get("category_id", item.category_id)
                self.operation_service.item_templates.sync_templates_from_receipt_items(
                    user_id=user_id,
                    category_id=next_category_id,
                    normalized_items=normalized_items,
                    recorded_at=updates.get("scheduled_date", item.scheduled_date),
                )
                log_background_job_event(
                    "plan_service",
                    "plan_item_templates_synced",
                    user_id=user_id,
                    plan_id=int(item.id),
                    receipt_items_count=len(normalized_items),
                )
        self.reminder_service.sync_plan_job(item)
        log_background_job_event(
            "plan_service",
            "plan_reminder_sync_requested",
            action="update",
            user_id=user_id,
            plan_id=int(item.id),
            recurrence_enabled=bool(item.recurrence_enabled),
        )
        self.db.commit()
        invalidate_plans_cache(user_id)
        log_background_job_event(
            "plan_service",
            "plan_updated",
            user_id=user_id,
            plan_id=int(item.id),
            kind=item.kind,
            status=item.status,
            recurrence_enabled=bool(item.recurrence_enabled),
        )
        return self.get_plan(user_id=user_id, plan_id=plan_id)

    def delete_plan(self, *, user_id: int, plan_id: int) -> None:
        row = self.repo.get_by_id(user_id=user_id, plan_id=plan_id)
        if not row:
            raise LookupError("Plan not found")
        self.repo.cancel_pending_reminder_jobs(
            user_id=user_id,
            plan_id=plan_id,
            canceled_at=datetime.now(timezone.utc),
        )
        self.repo.delete(row.PlanOperation)
        self.db.commit()
        invalidate_plans_cache(user_id)
        log_background_job_event(
            "plan_service",
            "plan_deleted",
            user_id=user_id,
            plan_id=plan_id,
        )

    def confirm_plan(self, *, user_id: int, plan_id: int) -> dict:
        row = self.repo.get_by_id(user_id=user_id, plan_id=plan_id)
        if not row:
            raise LookupError("Plan not found")
        item = row.PlanOperation
        category_name = row.Category.name if row.Category else self.repo.get_category_name(category_id=item.category_id)
        effective_date = date.today()
        if item.status in {"confirmed", "skipped"} and not item.recurrence_enabled:
            raise ValueError("Plan is already completed")
        receipt_map = self.repo.list_receipt_items_for_plans(user_id=user_id, plan_ids=[plan_id])
        receipt_items = receipt_map.get(plan_id, [])
        operation = self.operation_service.create_operation(
            user_id=user_id,
            kind=item.kind,
            amount=getattr(item, "original_amount", item.amount),
            currency=getattr(item, "currency", "BYN"),
            fx_rate=self._resolve_plan_current_rate(item=item),
            operation_date=effective_date,
            category_id=item.category_id,
            note=item.note,
            receipt_items=[
                {
                    "category_id": row_item.category_id,
                    "shop_name": row_item.shop_name,
                    "name": row_item.name,
                    "quantity": row_item.quantity,
                    "unit_price": row_item.unit_price,
                    "note": row_item.note,
                }
                for row_item in receipt_items
            ],
        )
        item.confirmed_operation_id = int(operation["id"])
        item.confirm_count = int(item.confirm_count or 0) + 1
        item.last_confirmed_at = datetime.now(timezone.utc)
        item.last_skipped_at = None
        self.repo.create_event(
            user_id=user_id,
            plan_id=int(item.id),
            operation_id=int(operation["id"]),
            event_type="confirmed",
            kind=item.kind,
            amount=item.amount,
            effective_date=effective_date,
            note=item.note,
            category_name=category_name,
        )
        if item.recurrence_enabled:
            next_date = self._advance_recurrence(
                scheduled_date=item.scheduled_date,
                frequency=item.recurrence_frequency,
                interval=item.recurrence_interval,
                weekdays=self._parse_weekdays(item.recurrence_weekdays),
                workdays_only=bool(item.recurrence_workdays_only),
                month_end=bool(item.recurrence_month_end),
            )
            if item.recurrence_end_date and next_date > item.recurrence_end_date:
                item.status = "confirmed"
            else:
                item.scheduled_date = next_date
                item.status = "active"
        else:
            item.status = "confirmed"
        self.reminder_service.sync_plan_job(item)
        log_background_job_event(
            "plan_service",
            "plan_reminder_sync_requested",
            action="confirm",
            user_id=user_id,
            plan_id=int(item.id),
            recurrence_enabled=bool(item.recurrence_enabled),
        )
        self.db.commit()
        invalidate_plans_cache(user_id)
        log_background_job_event(
            "plan_service",
            "plan_completed",
            user_id=user_id,
            plan_id=int(item.id),
            event_type="confirmed",
            status=item.status,
            recurrence_enabled=bool(item.recurrence_enabled),
        )
        return {
            "plan": self.get_plan(user_id=user_id, plan_id=plan_id),
            "operation": operation,
        }

    def skip_plan(self, *, user_id: int, plan_id: int) -> dict:
        row = self.repo.get_by_id(user_id=user_id, plan_id=plan_id)
        if not row:
            raise LookupError("Plan not found")
        item = row.PlanOperation
        category_name = row.Category.name if row.Category else self.repo.get_category_name(category_id=item.category_id)
        effective_date = item.scheduled_date
        if item.status in {"confirmed", "skipped"} and not item.recurrence_enabled:
            raise ValueError("Plan is already completed")
        item.skip_count = int(item.skip_count or 0) + 1
        item.last_skipped_at = datetime.now(timezone.utc)
        self.repo.create_event(
            user_id=user_id,
            plan_id=int(item.id),
            operation_id=None,
            event_type="skipped",
            kind=item.kind,
            amount=item.amount,
            effective_date=effective_date,
            note=item.note,
            category_name=category_name,
        )
        if item.recurrence_enabled:
            next_date = self._advance_recurrence(
                scheduled_date=item.scheduled_date,
                frequency=item.recurrence_frequency,
                interval=item.recurrence_interval,
                weekdays=self._parse_weekdays(item.recurrence_weekdays),
                workdays_only=bool(item.recurrence_workdays_only),
                month_end=bool(item.recurrence_month_end),
            )
            if item.recurrence_end_date and next_date > item.recurrence_end_date:
                item.status = "skipped"
            else:
                item.scheduled_date = next_date
                item.status = "active"
        else:
            item.status = "skipped"
        self.reminder_service.sync_plan_job(item)
        log_background_job_event(
            "plan_service",
            "plan_reminder_sync_requested",
            action="skip",
            user_id=user_id,
            plan_id=int(item.id),
            recurrence_enabled=bool(item.recurrence_enabled),
        )
        self.db.commit()
        invalidate_plans_cache(user_id)
        log_background_job_event(
            "plan_service",
            "plan_completed",
            user_id=user_id,
            plan_id=int(item.id),
            event_type="skipped",
            status=item.status,
            recurrence_enabled=bool(item.recurrence_enabled),
        )
        return self.get_plan(user_id=user_id, plan_id=plan_id)

    def _serialize_plan_row(self, *, row, receipt_items: list, reminder_job=None) -> dict:
        item = row.PlanOperation
        category = row.Category
        group = row[2]
        category_meta_map = self.operation_service._get_category_meta_map([receipt_item.category_id for receipt_item in receipt_items or []])
        receipt_payload = []
        receipt_total = Decimal("0")
        for receipt_item in receipt_items or []:
            line_total = self.operation_service._money(receipt_item.line_total)
            receipt_total += line_total
            category_meta = category_meta_map.get(int(receipt_item.category_id or 0), {})
            receipt_payload.append(
                {
                    "id": int(receipt_item.id),
                    "template_id": None,
                    "category_id": receipt_item.category_id,
                    "category_name": category_meta.get("name"),
                    "category_icon": category_meta.get("icon"),
                    "category_accent_color": category_meta.get("accent_color"),
                    "shop_name": receipt_item.shop_name,
                    "name": receipt_item.name,
                    "quantity": self.operation_service._qty(receipt_item.quantity),
                    "unit_price": self.operation_service._money(receipt_item.unit_price),
                    "line_total": line_total,
                    "note": receipt_item.note,
                }
            )
        currency = str(getattr(item, "currency", "BYN") or "BYN").upper()
        base_currency = str(getattr(item, "base_currency", "BYN") or "BYN").upper()
        original_amount = self.operation_service._money(getattr(item, "original_amount", item.amount))
        current_rate_row = self.currency_repo.get_latest_rate_map(user_id=int(item.user_id)).get(currency) if currency != base_currency else None
        current_rate = self.operation_service._rate(current_rate_row.rate) if current_rate_row else None
        current_base_amount = self._resolve_live_plan_base_amount(
            amount=original_amount,
            currency=currency,
            base_currency=base_currency,
            current_rate=current_rate,
        )
        return {
            "id": int(item.id),
            "kind": item.kind,
            "amount": self.operation_service._money(item.amount),
            "original_amount": original_amount,
            "currency": currency,
            "base_currency": base_currency,
            "current_rate": current_rate,
            "current_rate_date": current_rate_row.rate_date if current_rate_row else None,
            "current_base_amount": current_base_amount,
            "scheduled_date": item.scheduled_date,
            "due_date": item.scheduled_date,
            "category_id": item.category_id,
            "category_name": category.name if category else None,
            "category_icon": (category.icon if category and category.icon else (group.icon if group else None)),
            "category_accent_color": group.accent_color if group else None,
            "note": item.note,
            "receipt_items": receipt_payload,
            "receipt_total": self.operation_service._money(receipt_total) if receipt_payload else None,
            "recurrence_enabled": bool(item.recurrence_enabled),
            "recurrence_frequency": item.recurrence_frequency,
            "recurrence_interval": int(item.recurrence_interval or 1),
            "recurrence_weekdays": self._parse_weekdays(item.recurrence_weekdays),
            "recurrence_workdays_only": bool(item.recurrence_workdays_only),
            "recurrence_month_end": bool(item.recurrence_month_end),
            "recurrence_end_date": item.recurrence_end_date,
            "recurrence_label": self._recurrence_label(
                enabled=bool(item.recurrence_enabled),
                frequency=item.recurrence_frequency,
                interval=int(item.recurrence_interval or 1),
                weekdays=self._parse_weekdays(item.recurrence_weekdays),
                workdays_only=bool(item.recurrence_workdays_only),
                month_end=bool(item.recurrence_month_end),
            ),
            "status": self._display_status(item),
            "progress_anchor_at": self._progress_anchor_at(item),
            "next_reminder_at": reminder_job.scheduled_for if reminder_job else None,
            "confirmed_operation_id": item.confirmed_operation_id,
            "confirm_count": int(item.confirm_count or 0),
            "skip_count": int(item.skip_count or 0),
            "last_confirmed_at": item.last_confirmed_at,
            "last_skipped_at": item.last_skipped_at,
            "created_at": item.created_at,
        }

    def _resolve_live_plan_base_amount(
        self,
        *,
        amount: Decimal,
        currency: str,
        base_currency: str,
        current_rate: Decimal | None,
    ) -> Decimal:
        if currency == base_currency:
            return self.operation_service._money(amount)
        if current_rate is None or Decimal(current_rate) <= 0:
            return self.operation_service._money(0)
        return self.operation_service._money(Decimal(amount) * Decimal(current_rate))

    def _resolve_plan_current_rate(self, *, item) -> Decimal | None:
        currency = str(getattr(item, "currency", "BYN") or "BYN").upper()
        base_currency = str(getattr(item, "base_currency", "BYN") or "BYN").upper()
        if currency == base_currency:
            return Decimal("1.000000")
        latest_rate = self.currency_repo.get_latest_rate_map(user_id=int(item.user_id)).get(currency)
        if not latest_rate:
            raise ValueError(f"Нет текущего курса для {currency}")
        return self.operation_service._rate(latest_rate.rate)

    def _display_status(self, item) -> str:
        if item.status in {"confirmed", "skipped"}:
            return item.status
        today = date.today()
        if item.scheduled_date < today:
            return "overdue"
        if item.scheduled_date == today:
            return "due"
        return "upcoming"

    def _serialize_event_row(self, item) -> dict:
        return {
            "id": int(item.id),
            "plan_id": int(item.plan_id),
            "operation_id": int(item.operation_id) if item.operation_id else None,
            "event_type": item.event_type,
            "kind": item.kind,
            "amount": self.operation_service._money(item.amount),
            "effective_date": item.effective_date,
            "note": item.note,
            "category_name": item.category_name,
            "created_at": item.created_at,
        }

    @staticmethod
    def _progress_anchor_at(item) -> datetime | None:
        if bool(item.recurrence_enabled):
            anchors = [value for value in (item.last_confirmed_at, item.last_skipped_at, item.created_at) if value]
            return max(anchors) if anchors else None
        return item.created_at

    def _validate_recurrence(
        self,
        *,
        recurrence_enabled: bool,
        recurrence_frequency: str | None,
        recurrence_interval: int,
        recurrence_weekdays: list[int] | None,
        recurrence_workdays_only: bool,
        recurrence_month_end: bool,
        scheduled_date: date,
        recurrence_end_date: date | None,
    ) -> tuple[str | None, int, str | None, bool, bool, date | None]:
        if not recurrence_enabled:
            return None, 1, None, False, False, None
        if recurrence_frequency not in {"daily", "weekly", "monthly", "yearly"}:
            raise ValueError("recurrence_frequency must be one of daily, weekly, monthly, yearly")
        if recurrence_interval < 1:
            raise ValueError("recurrence_interval must be greater than 0")
        if recurrence_end_date and recurrence_end_date < scheduled_date:
            raise ValueError("recurrence_end_date must be greater than or equal to scheduled_date")
        normalized_weekdays = None
        if recurrence_frequency == "weekly":
            normalized_weekdays = self._normalize_weekdays(recurrence_weekdays, scheduled_date=scheduled_date)
        normalized_workdays_only = bool(recurrence_workdays_only) if recurrence_frequency == "daily" else False
        normalized_month_end = bool(recurrence_month_end) if recurrence_frequency == "monthly" else False
        return recurrence_frequency, int(recurrence_interval), normalized_weekdays, normalized_workdays_only, normalized_month_end, recurrence_end_date

    def _recurrence_label(
        self,
        *,
        enabled: bool,
        frequency: str | None,
        interval: int,
        weekdays: list[int] | None = None,
        workdays_only: bool = False,
        month_end: bool = False,
    ) -> str:
        if not enabled:
            return "Разовый"
        labels = {
            "daily": "Ежедневно",
            "weekly": "Еженедельно",
            "monthly": "Ежемесячно",
            "yearly": "Ежегодно",
        }
        base = labels.get(frequency or "", "Регулярно")
        if frequency == "daily" and workdays_only:
            base = "По будням"
        if frequency == "weekly" and weekdays:
            weekday_labels = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            base = f"{base}: {', '.join(weekday_labels[idx] for idx in weekdays if 0 <= idx <= 6)}"
        if frequency == "monthly" and month_end:
            base = f"{base}: в последний день месяца"
        if interval <= 1:
            return base
        return f"{base}, шаг {interval}"

    def _advance_recurrence(
        self,
        *,
        scheduled_date: date,
        frequency: str | None,
        interval: int,
        weekdays: list[int] | None = None,
        workdays_only: bool = False,
        month_end: bool = False,
    ) -> date:
        if frequency == "daily":
            if workdays_only:
                return self._advance_daily_workdays_only(scheduled_date=scheduled_date, interval=interval)
            return date.fromordinal(scheduled_date.toordinal() + interval)
        if frequency == "weekly":
            if weekdays:
                return self._advance_weekly_by_weekdays(scheduled_date=scheduled_date, interval=interval, weekdays=weekdays)
            return date.fromordinal(scheduled_date.toordinal() + 7 * interval)
        if frequency == "monthly":
            month_index = (scheduled_date.month - 1) + interval
            year = scheduled_date.year + (month_index // 12)
            month = (month_index % 12) + 1
            last_day = calendar.monthrange(year, month)[1]
            target_day = last_day if month_end else min(scheduled_date.day, last_day)
            return date(year, month, target_day)
        if frequency == "yearly":
            year = scheduled_date.year + interval
            last_day = calendar.monthrange(year, scheduled_date.month)[1]
            return date(year, scheduled_date.month, min(scheduled_date.day, last_day))
        raise ValueError("Unsupported recurrence_frequency")

    def _advance_daily_workdays_only(self, *, scheduled_date: date, interval: int) -> date:
        remaining = max(1, int(interval))
        current = scheduled_date
        while remaining > 0:
            current = date.fromordinal(current.toordinal() + 1)
            if current.weekday() >= 5:
                continue
            remaining -= 1
        return current

    def _normalize_weekdays(self, weekdays: list[int] | None, *, scheduled_date: date) -> str:
        raw_values = weekdays if isinstance(weekdays, list) else []
        if not raw_values:
            raw_values = [scheduled_date.weekday()]
        normalized = sorted({int(value) for value in raw_values})
        if any(value < 0 or value > 6 for value in normalized):
            raise ValueError("recurrence_weekdays must contain values from 0 to 6")
        return ",".join(str(value) for value in normalized)

    def _parse_weekdays(self, value: str | None) -> list[int]:
        if not value:
            return []
        result = []
        for chunk in str(value).split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            result.append(int(chunk))
        return sorted(set(result))

    def _advance_weekly_by_weekdays(self, *, scheduled_date: date, interval: int, weekdays: list[int]) -> date:
        normalized = sorted(set(int(value) for value in weekdays))
        current_weekday = scheduled_date.weekday()
        for weekday in normalized:
            if weekday > current_weekday:
                return date.fromordinal(scheduled_date.toordinal() + (weekday - current_weekday))
        start_of_week = date.fromordinal(scheduled_date.toordinal() - current_weekday)
        next_cycle_start = date.fromordinal(start_of_week.toordinal() + (7 * interval))
        return date.fromordinal(next_cycle_start.toordinal() + normalized[0])
