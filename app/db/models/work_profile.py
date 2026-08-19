from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkProfile(Base):
    __tablename__ = "work_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    company: Mapped[str | None] = mapped_column(String(160), nullable=True)
    position: Mapped[str | None] = mapped_column(String(160), nullable=True)
    employment_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    standard_hours_per_day: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("8.00"), server_default="8.00")
    workday_start_time: Mapped[time] = mapped_column(Time, default=time(9, 0), server_default="09:00:00")
    workday_end_time: Mapped[time] = mapped_column(Time, default=time(18, 0), server_default="18:00:00")
    lunch_start_time: Mapped[time] = mapped_column(Time, default=time(13, 0), server_default="13:00:00")
    lunch_end_time: Mapped[time] = mapped_column(Time, default=time(14, 0), server_default="14:00:00")
    workweek_mask: Mapped[str] = mapped_column(String(32), default="0,1,2,3,4", server_default="0,1,2,3,4")
    country_code: Mapped[str] = mapped_column(String(2), default="BY", server_default="BY")
    advance_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("plan_operations.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    salary_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("plan_operations.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    advance_nominal_day: Mapped[int] = mapped_column(Integer, default=20, server_default="20")
    salary_nominal_day: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    payment_shift_rule: Mapped[str] = mapped_column(
        String(32), default="previous_workday", server_default="previous_workday"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EmploymentContract(Base):
    __tablename__ = "employment_contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    work_profile_id: Mapped[int] = mapped_column(ForeignKey("work_profiles.id", ondelete="CASCADE"), index=True)
    effective_from: Mapped[date] = mapped_column(Date, index=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    company: Mapped[str | None] = mapped_column(String(160), nullable=True)
    position: Mapped[str | None] = mapped_column(String(160), nullable=True)
    salary_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="BYN", server_default="BYN")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkDayOverride(Base):
    __tablename__ = "work_day_overrides"
    __table_args__ = (UniqueConstraint("user_id", "work_date", name="uq_work_day_overrides_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    work_profile_id: Mapped[int] = mapped_column(ForeignKey("work_profiles.id", ondelete="CASCADE"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    planned_hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    actual_hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    credited_hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
