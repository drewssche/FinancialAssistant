from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Category, PlanOperation, User, UserPreference
from app.services.plan_service import PlanService


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    return engine, SessionLocal


def test_create_plan_emits_creation_and_sync_events(caplog):
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "plans": {"reminders_enabled": True, "reminder_time": "09:00"},
                    "ui": {"timezone": "UTC"},
                },
            )
        )
        db.add(Category(id=1, user_id=1, kind="expense", name="Еда"))
        db.commit()

        service = PlanService(db)
        with caplog.at_level("INFO", logger="financial_assistant.jobs"):
            created = service.create_plan(
                user_id=1,
                kind="expense",
                amount=Decimal("15.00"),
                scheduled_date=date(2030, 3, 20),
                category_id=1,
                note="План",
                receipt_items=[{"name": "Хлеб", "quantity": "1", "unit_price": "15.00"}],
            )

        assert created["id"] > 0
        text = caplog.text
        assert "background_job_event component=plan_service event=plan_item_templates_synced" in text
        assert "background_job_event component=plan_service event=plan_reminder_sync_requested" in text
        assert "action=create" in text
        assert "background_job_event component=plan_service event=plan_created" in text
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_skip_plan_emits_completion_and_sync_events(caplog):
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "plans": {"reminders_enabled": True, "reminder_time": "09:00"},
                    "ui": {"timezone": "UTC"},
                },
            )
        )
        db.add(
            PlanOperation(
                id=1,
                user_id=1,
                kind="expense",
                amount="10.00",
                scheduled_date=date(2030, 3, 20),
                note="План",
                status="active",
                recurrence_enabled=False,
            )
        )
        db.commit()

        service = PlanService(db)
        with caplog.at_level("INFO", logger="financial_assistant.jobs"):
            result = service.skip_plan(user_id=1, plan_id=1)

        assert result["status"] == "skipped"
        text = caplog.text
        assert "background_job_event component=plan_service event=plan_reminder_sync_requested" in text
        assert "action=skip" in text
        assert "background_job_event component=plan_service event=plan_completed" in text
        assert "event_type=skipped" in text
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
