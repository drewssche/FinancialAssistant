import calendar
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.cache import invalidate_plans_cache
from app.db.models import EmploymentContract, WorkDayOverride, WorkProfile
from app.repositories.work_repo import WorkRepository
from app.services.plan_reminder_service import PlanReminderService
from app.services.work_calendar import (
    baseline_day,
    holiday_name,
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


class WorkService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = WorkRepository(db)
        self.reminders = PlanReminderService(db)

    def get_profile(self, *, user_id: int) -> dict:
        return self._serialize_profile(self.repo.get_profile(user_id=user_id))

    def update_profile(self, *, user_id: int, payload: dict) -> dict:
        profile = self.repo.get_profile(user_id=user_id) or self.repo.create_profile(user_id=user_id)
        for field in ("company", "position", "employment_start_date", "standard_hours_per_day"):
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

    def get_month(self, *, user_id: int, year: int, month: int, today: date | None = None) -> dict:
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
        current_day = today or date.today()
        days = [
            self._build_day(
                day=date(year, month, day_number),
                profile_data=profile_data,
                override=overrides.get(date(year, month, day_number)),
                today=current_day,
            )
            for day_number in range(1, end.day + 1)
        ]
        statuses = {
            row.work_date: row.status
            for row in rows
            if row.status in PAYROLL_CALENDAR_OVERRIDE_STATUSES
        }
        payments = []
        for role, label, plan_key, nominal_key in (
            ("salary", "Основная часть", "salary_plan_id", "salary_nominal_day"),
            ("advance", "Аванс", "advance_plan_id", "advance_nominal_day"),
        ):
            nominal, effective = resolve_payment_date(
                year,
                month,
                profile_data[nominal_key],
                workweek_mask=self._workweek_mask(profile_data["workweek_days"]),
                country_code=profile_data["country_code"],
                override_statuses=statuses,
            )
            payments.append(
                {
                    "role": role,
                    "label": label,
                    "plan_id": profile_data[plan_key],
                    "nominal_date": nominal,
                    "effective_date": effective,
                    "shifted": nominal != effective,
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

    def create_contract(self, *, user_id: int, payload: dict) -> EmploymentContract:
        profile = self.repo.get_profile(user_id=user_id) or self.repo.create_profile(user_id=user_id)
        if self.repo.contracts_overlap(
            user_id=user_id,
            effective_from=payload["effective_from"],
            effective_to=payload.get("effective_to"),
        ):
            raise ValueError("Период контракта пересекается с существующим")
        item = EmploymentContract(user_id=user_id, work_profile_id=profile.id, **payload)
        self.db.add(item)
        profile.company = payload.get("company") or profile.company
        profile.position = payload.get("position") or profile.position
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_contract(self, *, user_id: int, contract_id: int) -> None:
        item = self.repo.get_contract(user_id=user_id, contract_id=contract_id)
        if not item:
            raise LookupError("Контракт не найден")
        self.db.delete(item)
        self.db.commit()

    def _serialize_profile(self, profile: WorkProfile | None) -> dict:
        if not profile:
            return {
                "id": None,
                "company": None,
                "position": None,
                "employment_start_date": None,
                "standard_hours_per_day": Decimal("8.00"),
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

    def _build_day(self, *, day: date, profile_data: dict, override: WorkDayOverride | None, today: date) -> dict:
        standard = money_hours(profile_data["standard_hours_per_day"])
        baseline = baseline_day(
            day,
            workweek_mask=self._workweek_mask(profile_data["workweek_days"]),
            country_code=profile_data["country_code"],
        )
        baseline_planned = standard if baseline["is_workday"] else Decimal("0.00")
        if baseline["is_workday"] and holiday_name(day + timedelta(days=1), country_code=profile_data["country_code"]):
            baseline_planned = max(Decimal("0.00"), standard - Decimal("1.00"))
        status = override.status if override else baseline["status"]
        planned = money_hours(override.planned_hours) if override and override.planned_hours is not None else baseline_planned
        is_workday = status in WORKING_STATUSES
        if override and status in WORKING_STATUSES and override.planned_hours is None and planned == 0:
            planned = standard
        if override and override.actual_hours is not None:
            actual = money_hours(override.actual_hours)
        elif status in WORKING_STATUSES and day <= today:
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
            "note": override.note if override else None,
        }

    def _summarize_days(self, days: list[dict]) -> dict:
        return {
            "planned_days": sum(1 for item in days if item["planned_hours"] > 0),
            "completed_days": sum(1 for item in days if item["actual_hours"] > 0),
            "planned_hours": sum((item["planned_hours"] for item in days), Decimal("0.00")),
            "actual_hours": sum((item["actual_hours"] for item in days), Decimal("0.00")),
            "credited_hours": sum((item["credited_hours"] for item in days), Decimal("0.00")),
            "vacation_days": sum(1 for item in days if item["status"] == "vacation"),
            "sick_days": sum(1 for item in days if item["status"] in {"sick_paid", "sick_unpaid"}),
            "override_days": sum(1 for item in days if item["is_manual"]),
        }

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
