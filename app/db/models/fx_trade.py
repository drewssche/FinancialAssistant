from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FxTrade(Base):
    __tablename__ = "fx_trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    side: Mapped[str] = mapped_column(String(10), index=True)  # buy|sell
    asset_currency: Mapped[str] = mapped_column(String(3), index=True)
    quote_currency: Mapped[str] = mapped_column(String(3), index=True, default="BYN")
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
