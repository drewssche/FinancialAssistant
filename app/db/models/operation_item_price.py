from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OperationItemPrice(Base):
    __tablename__ = "operation_item_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("operation_item_templates.id", ondelete="CASCADE"),
        index=True,
    )
    source_operation_id: Mapped[int | None] = mapped_column(
        ForeignKey("operations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    recorded_at: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
