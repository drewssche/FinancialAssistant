from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkPaymentLink(Base):
    __tablename__ = "work_payment_links"
    __table_args__ = (
        CheckConstraint("role IN ('salary', 'advance')", name="ck_work_payment_links_role"),
        CheckConstraint(
            "source IN ('plan_confirmation', 'manual')",
            name="ck_work_payment_links_source",
        ),
        UniqueConstraint("user_id", "operation_id", name="uq_work_payment_links_user_operation"),
        UniqueConstraint(
            "user_id",
            "snapshot_operation_id",
            name="uq_work_payment_links_user_snapshot_operation",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    operation_id: Mapped[int | None] = mapped_column(
        ForeignKey("operations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Legacy events whose operation was deleted before this table existed have
    # already lost the id through their SET NULL foreign key.
    snapshot_operation_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(20), index=True)
    source: Mapped[str] = mapped_column(String(24), index=True)
    # This is deliberately a snapshot rather than a foreign key. Payroll history
    # must survive deleting or replacing the recurring plan.
    plan_id: Mapped[int | None] = mapped_column(nullable=True, index=True)

    snapshot_operation_date: Mapped[date] = mapped_column(Date, index=True)
    snapshot_original_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    snapshot_currency: Mapped[str] = mapped_column(String(3))
    snapshot_base_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    snapshot_base_currency: Mapped[str] = mapped_column(String(3))
    snapshot_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_category_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # A separate plan snapshot freezes the forecast displayed for a payroll
    # period once the corresponding payment has actually happened.
    forecast_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    forecast_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    forecast_base_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    forecast_base_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
