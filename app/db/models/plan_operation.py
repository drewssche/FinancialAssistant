from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlanOperation(Base):
    __tablename__ = "plan_operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    confirmed_operation_id: Mapped[int | None] = mapped_column(
        ForeignKey("operations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(20), index=True)  # income|expense
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    scheduled_date: Mapped[date] = mapped_column(Date, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), index=True, default="active", server_default="active")
    recurrence_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    recurrence_frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    recurrence_interval: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    recurrence_weekdays: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recurrence_workdays_only: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    recurrence_month_end: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    recurrence_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confirm_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    skip_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reminder_sent_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_skipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
