from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import FxTrade, Operation, User
from app.services.currency_service import CurrencyService
from app.services.operation_service import OperationService
from app.services.dashboard_analytics_timeline import DashboardAnalyticsTimelineService


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


def test_currency_service_treats_linked_trade_as_non_cashflow() -> None:
    db = _build_session()
    try:
        trade = FxTrade(
            user_id=1,
            side="sell",
            asset_currency="USD",
            quote_currency="BYN",
            quantity=Decimal("5.000000"),
            unit_price=Decimal("4.000000"),
            fee=Decimal("0.00"),
            trade_kind="manual",
            linked_operation_id=77,
            trade_date=date(2026, 4, 1),
            note="linked settlement",
        )
        assert CurrencyService.is_cashflow_trade(trade) is False
    finally:
        db.close()


def test_money_flow_excludes_linked_trade_even_if_trade_kind_is_manual() -> None:
    db = _build_session()
    try:
        operation = Operation(
            user_id=1,
            kind="expense",
            amount=Decimal("20.00"),
            original_amount=Decimal("20.00"),
            currency="BYN",
            base_currency="BYN",
            fx_rate=Decimal("1.000000"),
            operation_date=date(2026, 4, 1),
            category_id=None,
            note="receipt fx",
        )
        db.add(operation)
        db.flush()
        db.add(
            FxTrade(
                user_id=1,
                side="sell",
                asset_currency="USD",
                quote_currency="BYN",
                quantity=Decimal("5.000000"),
                unit_price=Decimal("4.000000"),
                fee=Decimal("0.00"),
                trade_kind="manual",
                linked_operation_id=operation.id,
                trade_date=date(2026, 4, 1),
                note="legacy linked settlement",
            )
        )
        db.commit()

        service = OperationService(db)
        items, total = service.list_money_flow(
            user_id=1,
            page=1,
            page_size=20,
            sort_by="operation_date",
            sort_dir="desc",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 1),
            q=None,
            direction=None,
            source=None,
            currency_scope=None,
        )

        assert total == 1
        assert len(items) == 1
        assert items[0]["source_kind"] == "operation"
    finally:
        db.close()


def test_dashboard_cashflow_overlay_excludes_linked_trade_even_if_trade_kind_is_manual() -> None:
    db = _build_session()
    try:
        db.add(
            FxTrade(
                user_id=1,
                side="sell",
                asset_currency="USD",
                quote_currency="BYN",
                quantity=Decimal("5.000000"),
                unit_price=Decimal("4.000000"),
                fee=Decimal("0.00"),
                trade_kind="manual",
                linked_operation_id=123,
                trade_date=date(2026, 4, 1),
                note="legacy linked settlement",
            )
        )
        db.commit()

        timeline = DashboardAnalyticsTimelineService(db, OperationService(db).repo)
        totals = timeline.get_cashflow_totals(
            user_id=1,
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 1),
        )

        assert totals["fx_cashflow_total"] == Decimal("0")
        assert totals["cashflow_total"] == Decimal("0")
        assert totals["fx_events_count"] == 0
        assert totals["cashflow_events_count"] == 0
    finally:
        db.close()
