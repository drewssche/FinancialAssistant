"""Retailer observations are independent of purchase prices and receipt history."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CatalogWatch(Base):
    __tablename__ = 'catalog_watches'
    product_id: Mapped[int] = mapped_column(ForeignKey('catalog_products.id', ondelete='CASCADE'), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CatalogOfferWatch(Base):
    __tablename__ = 'catalog_offer_watches'
    template_id: Mapped[int] = mapped_column(ForeignKey('operation_item_templates.id', ondelete='CASCADE'), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('catalog_products.id', ondelete='CASCADE'), index=True)
    url: Mapped[str] = mapped_column(String(2048))
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_check_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, server_default=func.now())
    error: Mapped[str | None] = mapped_column(String(300))


class CatalogPriceEvent(Base):
    __tablename__ = 'catalog_price_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('catalog_products.id', ondelete='CASCADE'), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey('operation_item_templates.id', ondelete='CASCADE'), index=True)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    telegram_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
