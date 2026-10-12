from datetime import date, datetime
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CatalogPackageReplacement(Base):
    __tablename__ = 'catalog_package_replacements'
    __table_args__ = (
        UniqueConstraint('user_id', 'old_variant_id', name='uq_replacement_old'),
        UniqueConstraint('user_id', 'new_variant_id', name='uq_replacement_new'),
        CheckConstraint('old_variant_id != new_variant_id', name='ck_replacement_distinct'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('catalog_products.id', ondelete='CASCADE'), index=True)
    old_variant_id: Mapped[int] = mapped_column(ForeignKey('catalog_variants.id', ondelete='CASCADE'))
    new_variant_id: Mapped[int] = mapped_column(ForeignKey('catalog_variants.id', ondelete='CASCADE'))
    effective_date: Mapped[date] = mapped_column(Date)
    old_snapshot: Mapped[dict] = mapped_column(JSON)
    new_snapshot: Mapped[dict] = mapped_column(JSON)
    note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
