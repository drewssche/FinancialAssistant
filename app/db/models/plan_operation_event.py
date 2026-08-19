from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlanOperationEvent(Base):
    __tablename__ = "plan_operation_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan_operations.id", ondelete="CASCADE"), index=True)
    operation_id: Mapped[int | None] = mapped_column(ForeignKey("operations.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(20), index=True)  # confirmed|skipped|reminded
    kind: Mapped[str] = mapped_column(String(20), index=True)  # income|expense
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    original_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    base_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    fx_rate_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fx_bank_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fx_bank_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fx_bank_channel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fx_rate_kind: Mapped[str | None] = mapped_column(String(8), nullable=True)
    fx_rate_scale: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fx_rate_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    fx_quoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fx_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fx_rate_stale: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fx_payment_mode: Mapped[str | None] = mapped_column(String(24), nullable=True)
    effective_date: Mapped[date] = mapped_column(Date, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
