from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Debt(Base):
    __tablename__ = "debts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    counterparty_id: Mapped[int] = mapped_column(ForeignKey("debt_counterparties.id", ondelete="CASCADE"), index=True)
    direction: Mapped[str] = mapped_column(String(10), index=True)  # lend|borrow
    principal: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    original_principal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    currency: Mapped[str] = mapped_column(String(8), default="BYN", index=True)
    base_currency: Mapped[str] = mapped_column(String(8), default="BYN")
    closure_reason: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
