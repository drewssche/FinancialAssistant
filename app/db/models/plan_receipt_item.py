from decimal import Decimal

from sqlalchemy import JSON, Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlanReceiptItem(Base):
    __tablename__ = "plan_receipt_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan_operations.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("operation_item_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    shop_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    variant_snapshot: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    sale_unit: Mapped[str | None] = mapped_column(String(8), nullable=True)
    package_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    package_unit: Mapped[str | None] = mapped_column(String(8), nullable=True)
    name: Mapped[str] = mapped_column(String(160))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    is_discounted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    regular_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    discount_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    discount_mode: Mapped[str | None] = mapped_column(String(8), nullable=True)
    discount_value: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True)
    line_subtotal: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
