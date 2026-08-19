from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Operation(Base):
    __tablename__ = "operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)  # income|expense
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    original_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="BYN")
    base_currency: Mapped[str] = mapped_column(String(3), default="BYN")
    fx_rate: Mapped[Decimal] = mapped_column(Numeric(14, 6), default=Decimal("1.000000"))
    # ``fx_rate`` is always normalized to one unit of ``currency``.  The
    # remaining fields are an immutable quote/provenance snapshot; in
    # particular RUB bank quotes may have ``fx_rate_scale == 100``.
    fx_rate_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fx_bank_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fx_bank_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fx_bank_channel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fx_rate_kind: Mapped[str | None] = mapped_column(String(8), nullable=True)
    fx_rate_scale: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    fx_rate_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    fx_quoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fx_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fx_rate_stale: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    fx_payment_mode: Mapped[str] = mapped_column(String(24), default="valuation", server_default="valuation")
    operation_date: Mapped[date] = mapped_column(Date, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
