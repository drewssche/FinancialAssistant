import calendar
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cache import invalidate_plans_cache
from app.db.models import EmploymentContract, WorkDayOverride, WorkPaymentLink, WorkProfile
from app.repositories.work_repo import WorkRepository
from app.services.activity_service import ActivityService
from app.services.plan_reminder_service import PlanReminderService
from app.services.work_calendar import (
    baseline_day,
    is_shortened_workday,
    money_hours,
    PAYROLL_CALENDAR_OVERRIDE_STATUSES,
    parse_workweek_mask,
    resolve_payment_date,
)


STATUS_LABELS = {
    "workday": "Рабочий день",
    "vacation": "Отпуск",
    "sick_paid": "Сикдей с оплатой",
    "sick_unpaid": "Больничный / сикдей без оплаты",
    "company_day_off": "Выходной за счёт компании",
    "day_off": "Отгул",
    "unpaid_leave": "Отпуск без сохранения зарплаты",
    "transferred_workday": "Перенесённый рабочий день",
    "overtime": "Сверхурочная работа",
    "holiday": "Праздничный день",
    "weekend": "Выходной",
}

PAID_ABSENCE_STATUSES = {"vacation", "sick_paid", "company_day_off"}
UNPAID_ABSENCE_STATUSES = {"sick_unpaid", "day_off", "unpaid_leave", "holiday", "weekend"}
WORKING_STATUSES = {"workday", "transferred_workday", "overtime"}
WORK_TIMEZONE = ZoneInfo("Europe/Minsk")
PAYMENT_ROLES = (
    ("salary", "Основная часть", "salary_plan_id", "salary_nominal_day"),
    ("advance", "Аванс", "advance_plan_id", "advance_nominal_day"),
)
PAYMENT_ROLE_LABELS = {role: label for role, label, _, _ in PAYMENT_ROLES}


class WorkService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = WorkRepository(db)
        self.reminders = PlanReminderService(db)
        self.activity = ActivityService(db)

    def get_profile(self, *, user_id: int) -> dict:
        return self._serialize_profile(self.repo.get_profile(user_id=user_id))

    def update_profile(self, *, user_id: int, payload: dict) -> dict:
        profile = self.repo.get_profile(user_id=user_id) or self.repo.create_profile(user_id=user_id)
        for field in (
            "company",
            "position",
            "employment_start_date",
            "standard_hours_per_day",
            "workday_start_time",
            "workday_end_time",
            "lunch_start_time",
            "lunch_end_time",
        ):
            if field in payload:
                setattr(profile, field, payload[field])
        profile.workweek_mask = ",".join(str(day) for day in sorted(set(payload.get("workweek_days", [0, 1, 2, 3, 4]))))
        profile.country_code = "BY"
        profile.advance_nominal_day = int(payload.get("advance_nominal_day", 20))
        profile.salary_nominal_day = int(payload.get("salary_nominal_day", 5))
        profile.payment_shift_rule = "previous_workday"

        linked = []
        for role, field, nominal_field in (
            ("advance", "advance_plan_id", "advance_nominal_day"),
            ("salary", "salary_plan_id", "salary_nominal_day"),
        ):
            plan_id = payload.get(field)
            if plan_id is not None:
                plan = self.repo.get_plan(user_id=user_id, plan_id=int(plan_id))
                if not plan:
                    raise ValueError(f"План для роли {role} не найден")
                if plan.kind != "income":
                    raise ValueError("С зарплатой можно связать только план дохода")
                linked.append((plan, int(payload[nominal_field])))
            setattr(profile, field, plan_id)

        self.db.flush()
        for plan, nominal_day in linked:
            self._sync_linked_plan(profile=profile, plan=plan, nominal_day=nominal_day)
        self.db.commit()
        invalidate_plans_cache(user_id)
        return self._serialize_profile(profile)

    def get_month(
        self,
        *,
        user_id: int,
        year: int,
        month: int,
        today: date | None = None,
        now: datetime | None = None,
    ) -> dict:
        if month < 1 or month > 12:
            raise ValueError("month must be between 1 and 12")
        if year < 2000 or year > 2100:
            raise ValueError("year must be between 2000 and 2100")
        profile = self.repo.get_profile(user_id=user_id)
        profile_data = self._serialize_profile(profile)
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        rows = self.repo.list_overrides(user_id=user_id, date_from=start - timedelta(days=10), date_to=end)
        overrides = {row.work_date: row for row in rows}
        current_day, local_now = self._resolve_current_time(today=today, now=now)
        days = [
            self._build_day(
                day=date(year, month, day_number),
                profile_data=profile_data,
                override=overrides.get(date(year, month, day_number)),
                today=current_day,
                now=local_now,
            )
            for day_number in range(1, end.day + 1)
        ]
        statuses = {
            row.work_date: row.status
            for row in rows
            if row.status in PAYROLL_CALENDAR_OVERRIDE_STATUSES
        }
        payment_rows = self.repo.list_payment_links(
            user_id=user_id,
            date_from=start,
            date_to=end,
        )
        payment_history = [self._serialize_payment_link_row(row) for row in payment_rows]
        actual_by_role: dict[str, list[dict]] = {}
        frozen_forecast_by_role: dict[str, WorkPaymentLink] = {}
        for row, history_item in zip(payment_rows, payment_history, strict=True):
            role = str(history_item["role"])
            actual_by_role.setdefault(role, []).append(history_item)
            frozen_forecast_by_role.setdefault(role, row.WorkPaymentLink)

        payments = []
        for role, label, plan_key, nominal_key in PAYMENT_ROLES:
            nominal, effective = resolve_payment_date(
                year,
                month,
                profile_data[nominal_key],
                workweek_mask=self._workweek_mask(profile_data["workweek_days"]),
                country_code=profile_data["country_code"],
                override_statuses=statuses,
            )
            plan_id = profile_data[plan_key]
            plan = self.repo.get_plan(user_id=user_id, plan_id=int(plan_id)) if plan_id else None
            forecast_amount = None
            forecast_currency = None
            forecast_base_amount = None
            forecast_base_currency = None
            if plan:
                forecast_amount = money_hours(getattr(plan, "original_amount", None) or 0)
                if forecast_amount <= 0:
                    forecast_amount = money_hours(plan.amount)
                forecast_currency = str(plan.currency or "BYN").upper()
                forecast_base_amount = money_hours(plan.amount)
                forecast_base_currency = str(plan.base_currency or forecast_currency).upper()
            frozen_forecast = frozen_forecast_by_role.get(role)
            if frozen_forecast and frozen_forecast.forecast_amount is not None:
                forecast_amount = money_hours(frozen_forecast.forecast_amount)
                forecast_currency = str(frozen_forecast.forecast_currency or "BYN").upper()
                forecast_base_amount = money_hours(
                    frozen_forecast.forecast_base_amount
                    if frozen_forecast.forecast_base_amount is not None
                    else frozen_forecast.forecast_amount
                )
                forecast_base_currency = str(
                    frozen_forecast.forecast_base_currency
                    or frozen_forecast.forecast_currency
                    or "BYN"
                ).upper()
            payments.append(
                {
                    "role": role,
                    "label": label,
                    "plan_id": plan_id,
                    "nominal_date": nominal,
                    "effective_date": effective,
                    "shifted": nominal != effective,
                    "forecast_amount": forecast_amount,
                    "forecast_currency": forecast_currency,
                    "forecast_base_amount": forecast_base_amount,
                    "forecast_base_currency": forecast_base_currency,
                    "actual_operations": [
                        {
                            key: value
                            for key, value in item.items()
                            if key not in {"role", "label", "plan_id"}
                        }
                        for item in actual_by_role.get(role, [])
                    ],
                }
            )
        return {
            "year": year,
            "month": month,
            "profile": profile_data,
            "summary": self._summarize_days(days),
            "payments": payments,
            "days": days,
        }

    def get_statistics(
        self,
        *,
        user_id: int,
        period: str,
        anchor: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        today: date | None = None,
        now: datetime | None = None,
    ) -> dict:
        current_day, local_now = self._resolve_current_time(today=today, now=now)
        profile = self.repo.get_profile(user_id=user_id)
        profile_data = self._serialize_profile(profile)
        contracts = self.repo.list_contracts(user_id=user_id)
        known_starts = [item.effective_from for item in contracts]
        if profile_data.get("employment_start_date"):
            known_starts.append(profile_data["employment_start_date"])
        range_from, range_to = self._statistics_bounds(
            period=period,
            anchor=anchor or current_day,
            date_from=date_from,
            date_to=date_to,
            employment_start=min(known_starts) if known_starts else None,
            today=current_day,
        )
        rows = self.repo.list_overrides(user_id=user_id, date_from=range_from, date_to=range_to)
        overrides = {row.work_date: row for row in rows}
        days = []
        cursor = range_from
        while cursor <= range_to:
            days.append(
                self._build_day(
                    day=cursor,
                    profile_data=profile_data,
                    override=overrides.get(cursor),
                    today=current_day,
                    now=local_now,
                )
            )
            cursor += timedelta(days=1)
        summary = self._summarize_days(days)
        planned_hours = money_hours(summary["planned_hours"])
        actual_hours = money_hours(summary["actual_hours"])
        completion = Decimal("0.00")
        if planned_hours > 0:
            completion = min(Decimal("100.00"), (actual_hours / planned_hours * Decimal("100")).quantize(Decimal("0.01")))
        return {
            "period": period,
            "date_from": range_from,
            "date_to": range_to,
            "calendar_days": len(days),
            **summary,
            "future_planned_hours": sum(
                (item["planned_hours"] for item in days if item["is_future"]),
                Decimal("0.00"),
            ),
            "completion_percent": completion,
            "overtime_hours": sum(
                (max(Decimal("0.00"), item["actual_hours"] - item["planned_hours"]) for item in days),
                Decimal("0.00"),
            ),
            "months": self._statistics_months(days),
        }

    def list_payment_history(
        self,
        *,
        user_id: int,
        date_from: date,
        date_to: date,
    ) -> dict:
        self._validate_payment_date_range(date_from=date_from, date_to=date_to)
        rows = self.repo.list_payment_links(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
        items = [self._serialize_payment_link_row(row) for row in rows]
        return {"items": items, "total": len(items)}

    def list_payment_candidates(
        self,
        *,
        user_id: int,
        date_from: date,
        date_to: date,
        q: str | None,
        limit: int,
    ) -> dict:
        self._validate_payment_date_range(date_from=date_from, date_to=date_to)
        received_through = min(date_to, datetime.now(WORK_TIMEZONE).date())
        if date_from > received_through:
            return {"items": [], "total": 0}
        rows, total = self.repo.list_income_payment_candidates(
            user_id=user_id,
            date_from=date_from,
            date_to=received_through,
            q=q,
            limit=limit,
        )
        items = []
        for row in rows:
            operation = row.Operation
            link = row.WorkPaymentLink
            amount = money_hours(getattr(operation, "original_amount", None) or 0)
            if amount <= 0:
                amount = money_hours(operation.amount)
            items.append(
                {
                    "operation_id": int(operation.id),
                    "operation_date": operation.operation_date,
                    "amount": amount,
                    "currency": str(operation.currency or "BYN").upper(),
                    "base_amount": money_hours(operation.amount),
                    "base_currency": str(operation.base_currency or operation.currency or "BYN").upper(),
                    "note": operation.note,
                    "category_name": row.Category.name if row.Category else None,
                    "is_linked": link is not None,
                    "link_id": int(link.id) if link else None,
                    "linked_role": link.role if link else None,
                }
            )
        return {"items": items, "total": total}

    def create_payment_link(self, *, user_id: int, operation_id: int, role: str) -> dict:
        row = self.repo.get_operation_with_category(user_id=user_id, operation_id=operation_id)
        if not row:
            raise LookupError("Операция дохода не найдена")
        operation = row.Operation
        if operation.kind != "income":
            raise ValueError("С выплатой можно связать только операцию дохода")
        if operation.operation_date < date(2000, 1, 1):
            raise ValueError("Дата операции выплаты должна быть не раньше 01.01.2000")
        if operation.operation_date > datetime.now(WORK_TIMEZONE).date():
            raise ValueError("Будущую операцию нельзя отметить как фактически полученную выплату")
        if self.repo.get_payment_link_by_operation(user_id=user_id, operation_id=operation_id):
            raise ValueError("Операция уже связана с выплатой")
        try:
            link = self._create_payment_link_record(
                user_id=user_id,
                role=role,
                source="manual",
                operation=operation,
                category_name=row.Category.name if row.Category else None,
                plan=None,
            )
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("Операция уже связана с выплатой") from exc
        self.activity.record_created(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="work_payment_link",
            entity_id=int(link.id),
            title="Выплата связана с операцией",
            metadata={
                "operation_id": int(operation.id),
                "role": role,
                "source": "manual",
                "amount": str(link.snapshot_original_amount),
                "currency": link.snapshot_currency,
                "operation_date": link.snapshot_operation_date.isoformat(),
            },
        )
        self.db.commit()
        return self._serialize_payment_link(
            link=link,
            operation=operation,
            category=row.Category,
        )

    def delete_payment_link(self, *, user_id: int, link_id: int) -> None:
        link = self.repo.get_payment_link(user_id=user_id, link_id=link_id)
        if not link:
            raise LookupError("Связь выплаты не найдена")
        audit_snapshot = {
            "operation_id": link.snapshot_operation_id,
            "role": link.role,
            "source": link.source,
            "plan_id": link.plan_id,
            "amount": str(link.snapshot_original_amount),
            "currency": link.snapshot_currency,
            "operation_date": link.snapshot_operation_date.isoformat(),
        }
        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="work_payment_link",
            entity_id=int(link.id),
            event_type="deleted",
            title="Связь выплаты удалена",
            metadata=audit_snapshot,
        )
        self.repo.delete_payment_link(link)
        self.db.commit()

    def link_confirmed_plan_payment(
        self,
        *,
        user_id: int,
        plan,
        operation_id: int,
    ) -> WorkPaymentLink | None:
        role = self.repo.payment_role_for_plan(user_id=user_id, plan_id=int(plan.id))
        if not role:
            return None
        row = self.repo.get_operation_with_category(user_id=user_id, operation_id=operation_id)
        if not row or row.Operation.kind != "income":
            return None
        existing = self.repo.get_payment_link_by_operation(
            user_id=user_id,
            operation_id=operation_id,
        )
        if existing:
            return existing
        return self._create_payment_link_record(
            user_id=user_id,
            role=role,
            source="plan_confirmation",
            operation=row.Operation,
            category_name=row.Category.name if row.Category else None,
            plan=plan,
        )

    def upsert_override(self, *, user_id: int, work_date: date, payload: dict) -> dict:
        profile = self.repo.get_profile(user_id=user_id) or self.repo.create_profile(user_id=user_id)
        self._set_override(user_id=user_id, profile=profile, work_date=work_date, payload=payload)
        self.db.flush()
        self._resync_linked_plans(profile)
        self.db.commit()
        invalidate_plans_cache(user_id)
        return self.get_month(user_id=user_id, year=work_date.year, month=work_date.month)["days"][work_date.day - 1]

    def upsert_override_range(self, *, user_id: int, date_from: date, date_to: date, payload: dict) -> int:
        profile = self.repo.get_profile(user_id=user_id) or self.repo.create_profile(user_id=user_id)
        current = date_from
        count = 0
        while current <= date_to:
            self._set_override(user_id=user_id, profile=profile, work_date=current, payload=payload)
            current += timedelta(days=1)
            count += 1
        self.db.flush()
        self._resync_linked_plans(profile)
        self.db.commit()
        invalidate_plans_cache(user_id)
        return count

    def delete_override(self, *, user_id: int, work_date: date) -> None:
        item = self.repo.get_override(user_id=user_id, work_date=work_date)
        if not item:
            raise LookupError("Исключение для дня не найдено")
        profile = self.repo.get_profile(user_id=user_id)
        self.repo.delete_override(item)
        self.db.flush()
        if profile:
            self._resync_linked_plans(profile)
        self.db.commit()
        invalidate_plans_cache(user_id)

    def list_contracts(self, *, user_id: int) -> list[EmploymentContract]:
        return self.repo.list_contracts(user_id=user_id)

    def list_companies(self, *, user_id: int) -> list[dict]:
        contracts = sorted(
            self.repo.list_contracts(user_id=user_id),
            key=lambda item: (item.effective_from, item.id),
        )
        profile = self.repo.get_profile(user_id=user_id)
        companies: dict[str, dict] = {}
        for item in contracts:
            company = (item.company or "").strip()
            if not company:
                continue
            key = company.casefold()
            entry = companies.setdefault(
                key,
                {
                    "company": company,
                    "effective_from": item.effective_from,
                    "effective_to": item.effective_to,
                    "is_current": False,
                    "contract_count": 0,
                    "salary_operation_count": 0,
                    "positions": [],
                    "earnings": {},
                    "periods": [],
                },
            )
            entry["company"] = company
            entry["effective_from"] = min(entry["effective_from"], item.effective_from)
            if item.effective_to is None:
                entry["effective_to"] = None
            elif entry["effective_to"] is not None:
                entry["effective_to"] = max(entry["effective_to"], item.effective_to)
            entry["contract_count"] += 1
            if item.position and item.position not in entry["positions"]:
                entry["positions"].append(item.position)
            entry["periods"].append(
                {
                    "id": int(item.id),
                    "effective_from": item.effective_from,
                    "effective_to": item.effective_to,
                    "position": item.position,
                    "salary_amount": item.salary_amount,
                    "currency": item.currency,
                    "note": item.note,
                }
            )

        latest_contract = contracts[-1] if contracts else None
        profile_company_key = (profile.company or "").strip().casefold() if profile else ""
        for key, entry in companies.items():
            has_open_period = any(period["effective_to"] is None for period in entry["periods"])
            is_latest_profile_company = bool(
                latest_contract
                and (latest_contract.company or "").strip().casefold() == key
                and profile_company_key == key
            )
            entry["is_current"] = has_open_period or is_latest_profile_company
            if entry["is_current"]:
                entry["effective_to"] = None

        salary_operations = [
            operation
            for operation, category_name in self.repo.list_income_operations_with_categories(user_id=user_id)
            if "зарплат" in (category_name or "").casefold()
        ]
        for operation in salary_operations:
            candidates = [
                item
                for item in contracts
                if item.effective_from <= operation.operation_date
                and (item.effective_to is None or item.effective_to >= operation.operation_date)
                and (item.company or "").strip()
            ]
            matched = max(candidates, key=lambda item: (item.effective_from, item.id)) if candidates else None
            if not matched and latest_contract and profile_company_key:
                if operation.operation_date >= latest_contract.effective_from and profile_company_key == (latest_contract.company or "").strip().casefold():
                    matched = latest_contract
            if not matched:
                continue
            entry = companies.get((matched.company or "").strip().casefold())
            if not entry:
                continue
            currency = operation.base_currency or operation.currency
            entry["earnings"][currency] = entry["earnings"].get(currency, Decimal("0.00")) + money_hours(operation.amount)
            entry["salary_operation_count"] += 1

        result = []
        for entry in companies.values():
            entry["earnings"] = [
                {"currency": currency, "amount": amount}
                for currency, amount in sorted(entry["earnings"].items())
            ]
            entry["periods"].sort(key=lambda item: (item["effective_from"], item["id"]), reverse=True)
            result.append(entry)
        return sorted(result, key=lambda item: (item["is_current"], item["effective_from"]), reverse=True)

    def create_contract(self, *, user_id: int, payload: dict) -> EmploymentContract:
        profile = self.repo.get_profile(user_id=user_id) or self.repo.create_profile(user_id=user_id)
        previous_open = None
        if payload.get("effective_to") is None:
            previous_open = self.repo.get_open_contract_before(
                user_id=user_id,
                effective_from=payload["effective_from"],
            )
            if previous_open:
                previous_open.effective_to = payload["effective_from"]
        if self.repo.contracts_overlap(
            user_id=user_id,
            effective_from=payload["effective_from"],
            effective_to=payload.get("effective_to"),
            exclude_id=int(previous_open.id) if previous_open else None,
        ):
            raise ValueError("Период контракта пересекается с существующим")
        item = EmploymentContract(user_id=user_id, work_profile_id=profile.id, **payload)
        self.db.add(item)
        self.db.flush()
        self._sync_profile_from_contracts(profile)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_contract(self, *, user_id: int, contract_id: int, payload: dict) -> EmploymentContract:
        item = self.repo.get_contract(user_id=user_id, contract_id=contract_id)
        if not item:
            raise LookupError("Контракт не найден")
        if self.repo.contracts_overlap(
            user_id=user_id,
            effective_from=payload["effective_from"],
            effective_to=payload.get("effective_to"),
            exclude_id=contract_id,
        ):
            raise ValueError("Период контракта пересекается с существующим")
        for field in (
            "effective_from",
            "effective_to",
            "company",
            "position",
            "salary_amount",
            "currency",
            "note",
        ):
            setattr(item, field, payload.get(field))
        profile = self.repo.get_profile(user_id=user_id)
        self.db.flush()
        if profile:
            self._sync_profile_from_contracts(profile)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_contract(self, *, user_id: int, contract_id: int) -> None:
        item = self.repo.get_contract(user_id=user_id, contract_id=contract_id)
        if not item:
            raise LookupError("Контракт не найден")
        profile = self.repo.get_profile(user_id=user_id)
        self.db.delete(item)
        self.db.flush()
        if profile:
            self._sync_profile_from_contracts(profile)
        self.db.commit()

    def _serialize_profile(self, profile: WorkProfile | None) -> dict:
        if not profile:
            return {
                "id": None,
                "company": None,
                "position": None,
                "employment_start_date": None,
                "standard_hours_per_day": Decimal("8.00"),
                "workday_start_time": time(9, 0),
                "workday_end_time": time(18, 0),
                "lunch_start_time": time(13, 0),
                "lunch_end_time": time(14, 0),
                "workweek_days": [0, 1, 2, 3, 4],
                "country_code": "BY",
                "advance_plan_id": None,
                "salary_plan_id": None,
                "advance_nominal_day": 20,
                "salary_nominal_day": 5,
                "payment_shift_rule": "previous_workday",
            }
        return {
            "id": int(profile.id),
            "company": profile.company,
            "position": profile.position,
            "employment_start_date": profile.employment_start_date,
            "standard_hours_per_day": money_hours(profile.standard_hours_per_day),
            "workday_start_time": profile.workday_start_time,
            "workday_end_time": profile.workday_end_time,
            "lunch_start_time": profile.lunch_start_time,
            "lunch_end_time": profile.lunch_end_time,
            "workweek_days": sorted(parse_workweek_mask(profile.workweek_mask)),
            "country_code": profile.country_code,
            "advance_plan_id": profile.advance_plan_id,
            "salary_plan_id": profile.salary_plan_id,
            "advance_nominal_day": int(profile.advance_nominal_day),
            "salary_nominal_day": int(profile.salary_nominal_day),
            "payment_shift_rule": profile.payment_shift_rule,
        }

    def _set_override(self, *, user_id: int, profile: WorkProfile, work_date: date, payload: dict) -> WorkDayOverride:
        item = self.repo.get_override(user_id=user_id, work_date=work_date)
        if not item:
            item = WorkDayOverride(user_id=user_id, work_profile_id=profile.id, work_date=work_date, status=payload["status"])
            self.db.add(item)
        for field in ("status", "planned_hours", "actual_hours", "credited_hours", "note"):
            if field in payload:
                setattr(item, field, payload[field])
        return item

    def _sync_profile_from_contracts(self, profile: WorkProfile) -> None:
        contracts = self.repo.list_contracts(user_id=profile.user_id)
        today = date.today()
        current = next(
            (
                item
                for item in contracts
                if item.effective_from <= today and (item.effective_to is None or item.effective_to >= today)
            ),
            contracts[0] if contracts else None,
        )
        if not current:
            return
        profile.company = current.company or profile.company
        profile.position = current.position
        employment_start = current.effective_from
        current_company = (current.company or "").strip().casefold()
        if current_company:
            earlier = sorted(
                (
                    item
                    for item in contracts
                    if item.id != current.id
                    and (item.company or "").strip().casefold() == current_company
                    and item.effective_from < employment_start
                ),
                key=lambda item: (item.effective_from, item.id),
                reverse=True,
            )
            for item in earlier:
                if item.effective_to is None or item.effective_to >= employment_start - timedelta(days=1):
                    employment_start = item.effective_from
                else:
                    break
        profile.employment_start_date = employment_start

    def _build_day(
        self,
        *,
        day: date,
        profile_data: dict,
        override: WorkDayOverride | None,
        today: date,
        now: datetime,
    ) -> dict:
        standard = money_hours(profile_data["standard_hours_per_day"])
        baseline = baseline_day(
            day,
            workweek_mask=self._workweek_mask(profile_data["workweek_days"]),
            country_code=profile_data["country_code"],
        )
        baseline_planned = standard if baseline["is_workday"] else Decimal("0.00")
        if baseline["is_workday"] and is_shortened_workday(day, country_code=profile_data["country_code"]):
            baseline_planned = max(Decimal("0.00"), standard - Decimal("1.00"))
        status = override.status if override else baseline["status"]
        planned = money_hours(override.planned_hours) if override and override.planned_hours is not None else baseline_planned
        is_workday = status in WORKING_STATUSES
        if override and status in WORKING_STATUSES and override.planned_hours is None and planned == 0:
            planned = standard
        has_manual_actual = bool(override and override.actual_hours is not None)
        shift_start = datetime.combine(day, profile_data["workday_start_time"], tzinfo=WORK_TIMEZONE)
        shift_end = datetime.combine(day, profile_data["workday_end_time"], tzinfo=WORK_TIMEZONE)
        is_live = bool(
            status in WORKING_STATUSES
            and day == today
            and not has_manual_actual
            and now >= shift_start
            and now < shift_end
        )
        if has_manual_actual:
            actual = money_hours(override.actual_hours)
        elif is_live:
            actual = self._live_worked_hours(day=day, planned=planned, profile_data=profile_data, now=now)
        elif status in WORKING_STATUSES and (
            day < today or (day == today and now >= shift_end)
        ):
            actual = planned
        else:
            actual = Decimal("0.00")
        if override and override.credited_hours is not None:
            credited = money_hours(override.credited_hours)
        elif status in PAID_ABSENCE_STATUSES:
            credited = baseline_planned or standard
        elif status in UNPAID_ABSENCE_STATUSES:
            credited = Decimal("0.00")
        elif day <= today:
            credited = actual
        else:
            credited = Decimal("0.00")
        is_completed = bool(
            actual > 0
            and (
                has_manual_actual
                or day < today
                or (day == today and now >= shift_end)
            )
        )
        if (
            not has_manual_actual
            and (day > today or (day == today and now < shift_start))
        ):
            hours_state = "forecast"
        elif is_live:
            hours_state = "live"
        else:
            hours_state = "actual"
        return {
            "date": day,
            "weekday": day.weekday(),
            "status": status,
            "status_label": STATUS_LABELS.get(status, status),
            "calendar_label": baseline.get("label"),
            "planned_hours": planned,
            "actual_hours": actual,
            "credited_hours": credited,
            "is_workday": is_workday,
            "is_manual": override is not None,
            "is_future": day > today,
            "is_live": is_live,
            "is_completed": is_completed,
            "hours_state": hours_state,
            "note": override.note if override else None,
        }

    @staticmethod
    def _resolve_current_time(
        *,
        today: date | None,
        now: datetime | None,
    ) -> tuple[date, datetime]:
        if now is None:
            local_now = datetime.now(WORK_TIMEZONE)
        elif now.tzinfo is None:
            local_now = now.replace(tzinfo=WORK_TIMEZONE)
        else:
            local_now = now.astimezone(WORK_TIMEZONE)

        if today is not None:
            current_day = today
        elif now is not None:
            current_day = local_now.date()
        else:
            # Keep deterministic date monkeypatches used by service tests while
            # preferring the Belarus calendar day around UTC midnight.
            process_day = date.today()
            current_day = (
                process_day
                if abs((process_day - local_now.date()).days) > 1
                else local_now.date()
            )
        if local_now.date() != current_day:
            local_now = datetime.combine(current_day, time.max, tzinfo=WORK_TIMEZONE)
        return current_day, local_now

    @staticmethod
    def _live_worked_hours(
        *,
        day: date,
        planned: Decimal,
        profile_data: dict,
        now: datetime,
    ) -> Decimal:
        shift_start = datetime.combine(day, profile_data["workday_start_time"], tzinfo=WORK_TIMEZONE)
        shift_end = datetime.combine(day, profile_data["workday_end_time"], tzinfo=WORK_TIMEZONE)
        lunch_start = datetime.combine(day, profile_data["lunch_start_time"], tzinfo=WORK_TIMEZONE)
        lunch_end = datetime.combine(day, profile_data["lunch_end_time"], tzinfo=WORK_TIMEZONE)
        effective_end = min(max(now, shift_start), shift_end)
        worked_seconds = max(0.0, (effective_end - shift_start).total_seconds())
        break_end = min(effective_end, lunch_end)
        break_seconds = max(0.0, (break_end - lunch_start).total_seconds())
        hours = Decimal(str((worked_seconds - break_seconds) / 3600))
        return min(money_hours(hours), money_hours(planned))

    def _create_payment_link_record(
        self,
        *,
        user_id: int,
        role: str,
        source: str,
        operation,
        category_name: str | None,
        plan,
    ) -> WorkPaymentLink:
        operation_amount = money_hours(getattr(operation, "original_amount", None) or 0)
        if operation_amount <= 0:
            operation_amount = money_hours(operation.amount)
        operation_currency = str(operation.currency or "BYN").upper()
        operation_base_amount = money_hours(operation.amount)
        operation_base_currency = str(operation.base_currency or operation.currency or "BYN").upper()

        if plan is not None:
            plan_id = int(plan.id)
        else:
            plan_id = None

        if plan is not None and source == "plan_confirmation":
            forecast_amount = money_hours(getattr(plan, "original_amount", None) or 0)
            if forecast_amount <= 0:
                forecast_amount = money_hours(plan.amount)
            forecast_currency = str(plan.currency or "BYN").upper()
            forecast_base_amount = money_hours(plan.amount)
            forecast_base_currency = str(plan.base_currency or plan.currency or "BYN").upper()
        else:
            forecast_amount = operation_amount
            forecast_currency = operation_currency
            forecast_base_amount = operation_base_amount
            forecast_base_currency = operation_base_currency

        return self.repo.create_payment_link(
            user_id=user_id,
            operation_id=int(operation.id),
            snapshot_operation_id=int(operation.id),
            role=role,
            source=source,
            plan_id=plan_id,
            snapshot_operation_date=operation.operation_date,
            snapshot_original_amount=operation_amount,
            snapshot_currency=operation_currency,
            snapshot_base_amount=operation_base_amount,
            snapshot_base_currency=operation_base_currency,
            snapshot_note=operation.note,
            snapshot_category_name=category_name,
            forecast_amount=forecast_amount,
            forecast_currency=forecast_currency,
            forecast_base_amount=forecast_base_amount,
            forecast_base_currency=forecast_base_currency,
        )

    def _serialize_payment_link_row(self, row) -> dict:
        return self._serialize_payment_link(
            link=row.WorkPaymentLink,
            operation=row.Operation,
            category=row.Category,
        )

    @staticmethod
    def _serialize_payment_link(*, link, operation, category) -> dict:
        if operation is not None:
            amount = money_hours(getattr(operation, "original_amount", None) or 0)
            if amount <= 0:
                amount = money_hours(operation.amount)
            return {
                "link_id": int(link.id),
                "source": link.source,
                "role": link.role,
                "label": PAYMENT_ROLE_LABELS[link.role],
                "plan_id": int(link.plan_id) if link.plan_id is not None else None,
                "operation_id": int(operation.id),
                "source_operation_id": int(link.snapshot_operation_id or operation.id),
                "operation_date": operation.operation_date,
                "amount": amount,
                "currency": str(operation.currency or "BYN").upper(),
                "base_amount": money_hours(operation.amount),
                "base_currency": str(operation.base_currency or operation.currency or "BYN").upper(),
                "note": operation.note,
                "category_name": category.name if category else None,
                "is_deleted": False,
            }
        return {
            "link_id": int(link.id),
            "source": link.source,
            "role": link.role,
            "label": PAYMENT_ROLE_LABELS[link.role],
            "plan_id": int(link.plan_id) if link.plan_id is not None else None,
            "operation_id": None,
            "source_operation_id": (
                int(link.snapshot_operation_id)
                if link.snapshot_operation_id is not None
                else None
            ),
            "operation_date": link.snapshot_operation_date,
            "amount": money_hours(link.snapshot_original_amount),
            "currency": str(link.snapshot_currency or "BYN").upper(),
            "base_amount": money_hours(link.snapshot_base_amount),
            "base_currency": str(link.snapshot_base_currency or link.snapshot_currency or "BYN").upper(),
            "note": link.snapshot_note,
            "category_name": link.snapshot_category_name,
            "is_deleted": True,
        }

    @staticmethod
    def _validate_payment_date_range(*, date_from: date, date_to: date) -> None:
        if date_from < date(2000, 1, 1) or date_to > date(2100, 12, 31):
            raise ValueError("Диапазон выплат должен быть между 01.01.2000 и 31.12.2100")
        if date_to < date_from:
            raise ValueError("Дата окончания не может быть раньше даты начала")
        if (date_to - date_from).days > 3660:
            raise ValueError("История выплат не может превышать 10 лет")

    def _summarize_days(self, days: list[dict]) -> dict:
        return {
            "planned_days": sum(1 for item in days if item["planned_hours"] > 0),
            "completed_days": sum(1 for item in days if item["is_completed"]),
            "planned_hours": sum((item["planned_hours"] for item in days), Decimal("0.00")),
            "actual_hours": sum((item["actual_hours"] for item in days), Decimal("0.00")),
            "credited_hours": sum((item["credited_hours"] for item in days), Decimal("0.00")),
            "vacation_days": sum(1 for item in days if item["status"] == "vacation"),
            "sick_days": sum(1 for item in days if item["status"] in {"sick_paid", "sick_unpaid"}),
            "override_days": sum(1 for item in days if item["is_manual"]),
        }

    def _statistics_months(self, days: list[dict]) -> list[dict]:
        grouped: dict[str, list[dict]] = {}
        for item in days:
            grouped.setdefault(item["date"].strftime("%Y-%m"), []).append(item)
        result = []
        for month, month_days in grouped.items():
            summary = self._summarize_days(month_days)
            result.append({"month": month, **summary})
        return result

    @staticmethod
    def _statistics_bounds(
        *,
        period: str,
        anchor: date,
        date_from: date | None,
        date_to: date | None,
        employment_start: date | None,
        today: date,
    ) -> tuple[date, date]:
        if period == "month":
            return date(anchor.year, anchor.month, 1), date(anchor.year, anchor.month, calendar.monthrange(anchor.year, anchor.month)[1])
        if period == "year":
            return date(anchor.year, 1, 1), date(anchor.year, 12, 31)
        if period == "all_time":
            return employment_start or date(today.year, 1, 1), today
        if period == "custom":
            if not date_from or not date_to:
                raise ValueError("Для произвольного периода нужны обе даты")
            if date_to < date_from:
                raise ValueError("Дата окончания не может быть раньше даты начала")
            if (date_to - date_from).days > 3660:
                raise ValueError("Период статистики не может превышать 10 лет")
            return date_from, date_to
        raise ValueError("period must be one of month, year, all_time, custom")

    def _sync_linked_plan(self, *, profile: WorkProfile, plan, nominal_day: int) -> None:
        overrides = self.repo.list_overrides(
            user_id=profile.user_id,
            date_from=plan.scheduled_date - timedelta(days=40),
            date_to=plan.scheduled_date + timedelta(days=370),
        )
        statuses = {
            row.work_date: row.status
            for row in overrides
            if row.status in PAYROLL_CALENDAR_OVERRIDE_STATUSES
        }
        base_month_index = plan.scheduled_date.year * 12 + (plan.scheduled_date.month - 1)
        candidates = []
        for offset in (-1, 0, 1):
            month_index = base_month_index + offset
            candidate_year = month_index // 12
            candidate_month = (month_index % 12) + 1
            candidate_nominal, candidate_effective = resolve_payment_date(
                candidate_year,
                candidate_month,
                nominal_day,
                workweek_mask=profile.workweek_mask,
                country_code=profile.country_code,
                override_statuses=statuses,
            )
            candidates.append((candidate_nominal, candidate_effective))
        nominal, effective = min(
            candidates,
            key=lambda candidate: abs((candidate[1] - plan.scheduled_date).days),
        )
        year, month = nominal.year, nominal.month
        if effective < date.today() and plan.scheduled_date < date.today():
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
            nominal, effective = resolve_payment_date(
                year,
                month,
                nominal_day,
                workweek_mask=profile.workweek_mask,
                country_code=profile.country_code,
                override_statuses=statuses,
            )
        _ = nominal
        plan.scheduled_date = effective
        plan.recurrence_enabled = True
        plan.recurrence_frequency = "monthly"
        plan.recurrence_interval = 1
        plan.recurrence_weekdays = None
        plan.recurrence_workdays_only = False
        plan.recurrence_month_end = False
        plan.status = "active"
        self.reminders.sync_plan_job(plan)

    def _resync_linked_plans(self, profile: WorkProfile) -> None:
        for plan_id, nominal_day in (
            (profile.advance_plan_id, profile.advance_nominal_day),
            (profile.salary_plan_id, profile.salary_nominal_day),
        ):
            if plan_id:
                plan = self.repo.get_plan(user_id=profile.user_id, plan_id=int(plan_id))
                if plan:
                    self._sync_linked_plan(profile=profile, plan=plan, nominal_day=int(nominal_day))

    @staticmethod
    def _workweek_mask(days: list[int]) -> str:
        return ",".join(str(day) for day in sorted(set(days)))
