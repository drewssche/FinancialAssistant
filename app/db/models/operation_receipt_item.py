from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OperationReceiptItem(Base):
    __tablename__ = "operation_receipt_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[int] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("operation_item_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    shop_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    is_discounted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    regular_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
