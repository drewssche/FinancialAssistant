from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FxBankRate(Base):
    __tablename__ = "fx_bank_rates"
    __table_args__ = (
        UniqueConstraint(
            "bank_code",
            "currency",
            "base_currency",
            "channel",
            name="uq_fx_bank_rate_bank_currency_channel",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_code: Mapped[str] = mapped_column(String(32), index=True)
    bank_name: Mapped[str] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3), index=True)
    base_currency: Mapped[str] = mapped_column(String(3), default="BYN")
    scale: Mapped[int] = mapped_column(Integer, default=1)
    buy_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    sell_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    channel: Mapped[str] = mapped_column(String(20), default="cash")
    location_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    quoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

