"""Private delivery state, never part of general browser preferences."""
from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class FinancialReportRecipient(Base):
    __tablename__ = 'financial_report_recipients'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    email_address: Mapped[str | None] = mapped_column(String(254), nullable=True)
    activated_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    pending_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    code_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    code_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_code_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    code_day: Mapped[date | None] = mapped_column(Date, nullable=True)
    code_day_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
