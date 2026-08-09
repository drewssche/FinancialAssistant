from datetime import date, datetime
from decimal import Decimal

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
        return self


class WorkProfileOut(BaseModel):
    id: int | None = None
    company: str | None = None
    position: str | None = None
    employment_start_date: date | None = None
    standard_hours_per_day: Decimal
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
    note: str | None = None


class WorkPaymentOut(BaseModel):
    role: str
    label: str
    plan_id: int | None = None
    nominal_date: date
    effective_date: date
    shifted: bool


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
