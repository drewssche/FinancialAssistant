from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OperationItemTemplate(Base):
    __tablename__ = "operation_item_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    shop_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    shop_name_ci: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("item_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(Text)
    name_ci: Mapped[str] = mapped_column(String(255), index=True)
    last_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("item_brands.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    image_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_media_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    use_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recommendation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    recommendation_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="manual", server_default="manual")
    recommendation_interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommendation_base_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
        default=Decimal("1.000"),
        server_default="1.000",
    )
    recommendation_next_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    recommendation_snoozed_until: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
