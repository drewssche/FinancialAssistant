from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AuthIdentity, User
from app.services.debt_service import DebtService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Debt User", status="approved"))
        db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="100500", username="debt_user"))
        db.commit()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_add_repayment_notifies_owner_only_when_debt_closes(db_session: Session, monkeypatch):
    service = DebtService(db_session)
    debt, _ = service.create_debt(
        user_id=1,
        counterparty="Мария",
        direction="borrow",
        principal=Decimal("300.00"),
        start_date=date(2026, 3, 1),
    )
    sent: list[dict] = []
    monkeypatch.setattr(
        "app.services.debt_service.notify_debt_repaid_owner",
        lambda **kwargs: sent.append(kwargs),
    )

    service.add_repayment(
        user_id=1,
        debt_id=debt.id,
        amount=Decimal("100.00"),
        repayment_date=date(2026, 3, 10),
    )
    assert sent == []

    service.add_repayment(
        user_id=1,
        debt_id=debt.id,
        amount=Decimal("200.00"),
        repayment_date=date(2026, 3, 23),
        note="Финальный платёж",
    )

    assert len(sent) == 1
    assert sent[0]["owner_telegram_id"] == "100500"
    assert sent[0]["debt_id"] == debt.id
    assert sent[0]["counterparty"] == "Мария"
    assert sent[0]["direction"] == "borrow"
    assert sent[0]["amount"] == Decimal("200.00")


def test_add_repayment_skips_notification_without_owner_telegram_id(db_session: Session, monkeypatch):
    db_session.query(AuthIdentity).delete()
    db_session.commit()
    service = DebtService(db_session)
    debt, _ = service.create_debt(
        user_id=1,
        counterparty="Иван",
        direction="lend",
        principal=Decimal("150.00"),
        start_date=date(2026, 3, 1),
    )
    sent: list[dict] = []
    monkeypatch.setattr(
        "app.services.debt_service.notify_debt_repaid_owner",
        lambda **kwargs: sent.append(kwargs),
    )

    service.add_repayment(
        user_id=1,
        debt_id=debt.id,
        amount=Decimal("150.00"),
        repayment_date=date(2026, 3, 23),
    )

    assert sent == []
