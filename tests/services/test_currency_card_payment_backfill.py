from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import FxTrade, Operation, User
from app.services.currency_service import CurrencyService


def _build_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    db = testing_session()
    db.add(User(id=1, display_name="Tester", status="active"))
    db.commit()
    return db


def test_backfill_linked_card_payment_trades_links_unique_matching_operation() -> None:
    db = _build_session()
    try:
        created_at = datetime(2026, 4, 2, 12, 0, tzinfo=timezone.utc)
        operation = Operation(
            user_id=1,
            kind="expense",
            amount=Decimal("4.50"),
            original_amount=Decimal("4.50"),
            currency="BYN",
            base_currency="BYN",
            fx_rate=Decimal("1.000000"),
            operation_date=date(2026, 4, 2),
            note="coffee",
            created_at=created_at,
        )
        trade = FxTrade(
            user_id=1,
            side="sell",
            asset_currency="USD",
            quote_currency="BYN",
            quantity=Decimal("1.560000"),
            unit_price=Decimal("2.884615"),
            fee=Decimal("0.00"),
            trade_kind="card_payment",
            linked_operation_id=None,
            trade_date=date(2026, 4, 2),
            note="USD card",
            created_at=created_at + timedelta(seconds=20),
        )
        db.add_all([operation, trade])
        db.commit()

        linked_count = CurrencyService(db).backfill_linked_card_payment_trades()
        db.refresh(trade)

        assert linked_count == 1
        assert trade.linked_operation_id == operation.id
    finally:
        db.close()


def test_backfill_linked_card_payment_trades_skips_ambiguous_matches() -> None:
    db = _build_session()
    try:
        base_time = datetime(2026, 4, 2, 12, 0, tzinfo=timezone.utc)
        operation_one = Operation(
            user_id=1,
            kind="expense",
            amount=Decimal("4.50"),
            original_amount=Decimal("4.50"),
            currency="BYN",
            base_currency="BYN",
            fx_rate=Decimal("1.000000"),
            operation_date=date(2026, 4, 2),
            note="coffee one",
            created_at=base_time,
        )
        operation_two = Operation(
            user_id=1,
            kind="expense",
            amount=Decimal("4.50"),
            original_amount=Decimal("4.50"),
            currency="BYN",
            base_currency="BYN",
            fx_rate=Decimal("1.000000"),
            operation_date=date(2026, 4, 2),
            note="coffee two",
            created_at=base_time + timedelta(seconds=30),
        )
        trade = FxTrade(
            user_id=1,
            side="sell",
            asset_currency="USD",
            quote_currency="BYN",
            quantity=Decimal("1.560000"),
            unit_price=Decimal("2.884615"),
            fee=Decimal("0.00"),
            trade_kind="card_payment",
            linked_operation_id=None,
            trade_date=date(2026, 4, 2),
            note="USD card",
            created_at=base_time + timedelta(seconds=15),
        )
        db.add_all([operation_one, operation_two, trade])
        db.commit()

        linked_count = CurrencyService(db).backfill_linked_card_payment_trades()
        db.refresh(trade)

        assert linked_count == 0
        assert trade.linked_operation_id is None
    finally:
        db.close()
