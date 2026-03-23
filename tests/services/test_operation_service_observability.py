from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Category, Operation, User
from app.services.operation_service import OperationService


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    return engine, SessionLocal


def test_create_operation_emits_observability_event(caplog):
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(Category(id=1, user_id=1, kind="expense", name="Еда"))
        db.commit()

        service = OperationService(db)
        with caplog.at_level("INFO", logger="financial_assistant.jobs"):
            created = service.create_operation(
                user_id=1,
                kind="expense",
                amount=Decimal("12.50"),
                operation_date=date(2030, 3, 20),
                category_id=1,
                note="Обед",
            )

        assert created["id"] > 0
        text = caplog.text
        assert "background_job_event component=operation_service event=operation_created" in text
        assert "user_id=1" in text
        assert "kind=expense" in text
        assert "category_id=1" in text
        assert "has_receipt=False" in text
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_update_and_delete_operation_emit_observability_events(caplog):
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(Category(id=1, user_id=1, kind="expense", name="Еда"))
        db.add(
            Operation(
                id=1,
                user_id=1,
                kind="expense",
                amount=Decimal("10.00"),
                operation_date=date(2030, 3, 20),
                category_id=1,
                note="Старое",
            )
        )
        db.commit()

        service = OperationService(db)
        with caplog.at_level("INFO", logger="financial_assistant.jobs"):
            updated = service.update_operation(
                user_id=1,
                operation_id=1,
                updates={"note": "Новое", "amount": Decimal("15.00")},
            )
            service.delete_operation(user_id=1, operation_id=1)

        assert updated["note"] == "Новое"
        text = caplog.text
        assert "background_job_event component=operation_service event=operation_updated" in text
        assert "background_job_event component=operation_service event=operation_deleted" in text
        assert "operation_id=1" in text
        assert "fields_changed=amount,note" in text
        assert "receipt_updated=False" in text
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
