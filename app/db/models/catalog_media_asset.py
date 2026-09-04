from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CatalogMediaAsset(Base):
    __tablename__ = "catalog_media_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="image/webp", server_default="image/webp"
    )
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    thumb_bytes: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False, deferred=True
    )
    thumb_width: Mapped[int] = mapped_column(Integer, nullable=False)
    thumb_height: Mapped[int] = mapped_column(Integer, nullable=False)
    detail_bytes: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False, deferred=True
    )
    detail_width: Mapped[int] = mapped_column(Integer, nullable=False)
    detail_height: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
