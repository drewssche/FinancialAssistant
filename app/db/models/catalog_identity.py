from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CatalogVariant(Base):
    __tablename__ = 'catalog_variants'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('catalog_products.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(160))
    sale_unit: Mapped[str | None] = mapped_column(String(8))
    package_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    package_unit: Mapped[str | None] = mapped_column(String(8))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CatalogVariantCode(Base):
    __tablename__ = 'catalog_variant_codes'
    __table_args__ = (UniqueConstraint('user_id', 'gtin14', name='uq_variant_codes_user_gtin'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey('catalog_variants.id', ondelete='CASCADE'), index=True)
    code: Mapped[str] = mapped_column(String(14))
    gtin14: Mapped[str] = mapped_column(String(14))


class CatalogOfferIdentity(Base):
    __tablename__ = 'catalog_offer_identities'
    template_id: Mapped[int] = mapped_column(ForeignKey('operation_item_templates.id', ondelete='CASCADE'), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey('catalog_variants.id', ondelete='SET NULL'), index=True)
    retailer_code: Mapped[str | None] = mapped_column(String(160))
    external_name: Mapped[str | None] = mapped_column(String(320))
    product_url: Mapped[str | None] = mapped_column(String(2048))
