from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


WORK_STATUSES = (
    "workday|vacation|sick_paid|sick_unpaid|company_day_off|day_off|"
    "unpaid_leave|transferred_workday|overtime|holiday|weekend"
)


class WorkProfileUpdate(BaseModel):
    company: str | None = Field(default=None, max_length=160)
    position: str | None = Field(default=None, max_length=160)
    employment_start_date: date | None = None
    standard_hours_per_day: Decimal = Field(default=Decimal("8.00"), gt=0, le=24)
    workday_start_time: time = time(9, 0)
    workday_end_time: time = time(18, 0)
    lunch_start_time: time = time(13, 0)
    lunch_end_time: time = time(14, 0)
    workweek_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    advance_plan_id: int | None = None
    salary_plan_id: int | None = None
    advance_nominal_day: int = Field(default=20, ge=1, le=31)
    salary_nominal_day: int = Field(default=5, ge=1, le=31)

    @model_validator(mode="after")
    def validate_plan_links(self):
        if self.advance_plan_id and self.advance_plan_id == self.salary_plan_id:
            raise ValueError("Планы аванса и зарплаты должны быть разными")
        if not self.workweek_days or any(day < 0 or day > 6 for day in self.workweek_days):
            raise ValueError("workweek_days must contain values from 0 to 6")
        if not (
            self.workday_start_time
            < self.lunch_start_time
            < self.lunch_end_time
            < self.workday_end_time
        ):
            raise ValueError("Рабочее время должно идти в порядке: начало, обед, конец обеда, конец дня")
        shift_minutes = (
            self.workday_end_time.hour * 60
            + self.workday_end_time.minute
            - self.workday_start_time.hour * 60
            - self.workday_start_time.minute
        )
        lunch_minutes = (
            self.lunch_end_time.hour * 60
            + self.lunch_end_time.minute
            - self.lunch_start_time.hour * 60
            - self.lunch_start_time.minute
        )
        net_hours = Decimal(shift_minutes - lunch_minutes) / Decimal(60)
        if self.standard_hours_per_day > net_hours:
            raise ValueError("Норма часов не может превышать длительность смены без обеда")
        return self


class WorkProfileOut(BaseModel):
    id: int | None = None
    company: str | None = None
    position: str | None = None
    employment_start_date: date | None = None
    standard_hours_per_day: Decimal
    workday_start_time: time = time(9, 0)
    workday_end_time: time = time(18, 0)
    lunch_start_time: time = time(13, 0)
    lunch_end_time: time = time(14, 0)
    workweek_days: list[int]
    country_code: str = "BY"
    advance_plan_id: int | None = None
    salary_plan_id: int | None = None
    advance_nominal_day: int = 20
    salary_nominal_day: int = 5
    payment_shift_rule: str = "previous_workday"


class WorkDayOverrideIn(BaseModel):
    status: str = Field(pattern=f"^({WORK_STATUSES})$")
    planned_hours: Decimal | None = Field(default=None, ge=0, le=24)
    actual_hours: Decimal | None = Field(default=None, ge=0, le=24)
    credited_hours: Decimal | None = Field(default=None, ge=0, le=24)
    note: str | None = Field(default=None, max_length=500)


class WorkDayRangeOverrideIn(WorkDayOverrideIn):
    date_from: date
    date_to: date

    @model_validator(mode="after")
    def validate_range(self):
        if self.date_to < self.date_from:
            raise ValueError("Дата окончания не может быть раньше даты начала")
        if (self.date_to - self.date_from).days > 366:
            raise ValueError("Диапазон не может превышать 367 дней")
        return self


class WorkDayOut(BaseModel):
    date: date
    weekday: int
    status: str
    status_label: str
    calendar_label: str | None = None
    planned_hours: Decimal
    actual_hours: Decimal
    credited_hours: Decimal
    is_workday: bool
    is_manual: bool
    is_future: bool
    is_live: bool = False
    is_completed: bool = False
    hours_state: str = "actual"
    note: str | None = None


class WorkPaymentOperationOut(BaseModel):
    link_id: int | None = None
    source: Literal["plan_confirmation", "manual", "category_match"]
    label: str | None = None
    operation_id: int | None = None
    source_operation_id: int | None = None
    operation_date: date
    amount: Decimal
    currency: str
    base_amount: Decimal
    base_currency: str
    note: str | None = None
    category_name: str | None = None
    is_deleted: bool = False


class WorkPaymentOut(BaseModel):
    role: str
    label: str
    plan_id: int | None = None
    nominal_date: date
    effective_date: date
    shifted: bool
    forecast_visible: bool = False
    forecast_amount: Decimal | None = None
    forecast_currency: str | None = None
    forecast_base_amount: Decimal | None = None
    forecast_base_currency: str | None = None
    actual_operations: list[WorkPaymentOperationOut] = Field(default_factory=list)


class WorkPaymentHistoryItemOut(WorkPaymentOperationOut):
    role: Literal["salary", "advance"]
    label: str
    plan_id: int | None = None


class WorkPaymentHistoryOut(BaseModel):
    items: list[WorkPaymentHistoryItemOut]
    total: int


class WorkPaymentCandidateOut(BaseModel):
    operation_id: int
    operation_date: date
    amount: Decimal
    currency: str
    base_amount: Decimal
    base_currency: str
    note: str | None = None
    category_name: str | None = None
    is_linked: bool = False
    link_id: int | None = None
    linked_role: Literal["salary", "advance"] | None = None


class WorkPaymentCandidateListOut(BaseModel):
    items: list[WorkPaymentCandidateOut]
    total: int


class WorkPaymentLinkIn(BaseModel):
    operation_id: int = Field(gt=0)
    role: Literal["salary", "advance"]


class WorkMonthSummaryOut(BaseModel):
    planned_days: int
    completed_days: int
    planned_hours: Decimal
    actual_hours: Decimal
    credited_hours: Decimal
    vacation_days: int
    sick_days: int
    override_days: int


class WorkMonthOut(BaseModel):
    year: int
    month: int
    profile: WorkProfileOut
    summary: WorkMonthSummaryOut
    payments: list[WorkPaymentOut]
    payroll_operations: list[WorkPaymentOperationOut] = Field(default_factory=list)
    days: list[WorkDayOut]


class WorkStatisticsMonthOut(BaseModel):
    month: str
    planned_days: int
    completed_days: int
    planned_hours: Decimal
    actual_hours: Decimal
    credited_hours: Decimal
    override_days: int


class WorkStatisticsOut(BaseModel):
    period: str
    date_from: date
    date_to: date
    calendar_days: int
    planned_days: int
    completed_days: int
    planned_hours: Decimal
    actual_hours: Decimal
    credited_hours: Decimal
    future_planned_hours: Decimal
    completion_percent: Decimal
    vacation_days: int
    sick_days: int
    overtime_hours: Decimal
    override_days: int
    months: list[WorkStatisticsMonthOut]


class EmploymentContractIn(BaseModel):
    effective_from: date
    effective_to: date | None = None
    company: str | None = Field(default=None, max_length=160)
    position: str | None = Field(default=None, max_length=160)
    salary_amount: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="BYN", min_length=3, max_length=3)
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("Дата окончания не может быть раньше даты начала")
        return self


class EmploymentContractOut(EmploymentContractIn):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkCompanyEarningOut(BaseModel):
    currency: str
    amount: Decimal


class WorkCompanyPeriodOut(BaseModel):
    id: int
    effective_from: date
    effective_to: date | None = None
    position: str | None = None
    salary_amount: Decimal | None = None
    currency: str
    note: str | None = None


class WorkCompanyOut(BaseModel):
    company: str
    effective_from: date
    effective_to: date | None = None
    is_current: bool = False
    contract_count: int
    salary_operation_count: int
    positions: list[str]
    earnings: list[WorkCompanyEarningOut]
    periods: list[WorkCompanyPeriodOut]
