from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ItemBrand(Base):
    __tablename__ = "item_brands"
    __table_args__ = (
        UniqueConstraint("user_id", "name_ci", name="uq_item_brands_user_name_ci"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(Text)
    # Unicode case-folding can expand a 160-character display name (for
    # example, `ß` becomes `ss`), so keep room for the canonical key.
    name_ci: Mapped[str] = mapped_column(String(320), index=True)
    accent_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    image_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_media_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
