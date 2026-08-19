from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import (
    AuthIdentity,
    PlanOperation,
    PlanOperationEvent,
    PlanReminderJob,
    User,
    UserPreference,
)
from app.repositories.currency_repo import CurrencyRepository
from app.services.telegram_plan_reminder_bot_service import TelegramPlanReminderBotService


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return engine, SessionLocal


def test_list_due_deliveries_builds_ready_to_send_payload():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="100500", username="tester"))
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
                scheduled_date=date.today(),
                note="Напомнить",
                status="active",
                recurrence_enabled=False,
            )
        )
        db.add(
            PlanReminderJob(
                id=1,
                plan_id=1,
                user_id=1,
                scheduled_for=datetime.now(timezone.utc),
                status="pending",
            )
        )
        db.commit()

        deliveries = TelegramPlanReminderBotService(db).list_due_deliveries()

        assert len(deliveries) == 1
        delivery = deliveries[0]
        assert delivery.chat_id == "100500"
        assert delivery.text.startswith("🧾 План к подтверждению")
        assert "💸 Расход 10.00" in delivery.text
        assert "План к подтверждению" in delivery.text
        assert delivery.reply_markup == {
            "inline_keyboard": [[{"text": "Подтвердить", "callback_data": "planc:1"}]]
        }
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_plan_reminder_shows_bank_sale_quote_and_base_amount(monkeypatch):
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="100500", username="tester"))
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
                amount=Decimal("229.00"),
                original_amount=Decimal("229.00"),
                currency="EUR",
                base_currency="BYN",
                fx_rate_source="bank",
                fx_bank_code="technobank",
                fx_bank_channel="cash",
                fx_rate_kind="sell",
                fx_payment_mode="direct_conversion",
                scheduled_date=date.today(),
                note="Подписка",
                status="active",
                recurrence_enabled=False,
            )
        )
        db.add(
            PlanReminderJob(
                id=1,
                plan_id=1,
                user_id=1,
                scheduled_for=datetime.now(timezone.utc),
                status="pending",
            )
        )
        db.commit()
        now = datetime.now(timezone.utc)
        quote = SimpleNamespace(
            bank_code="technobank",
            bank_name="Технобанк",
            currency="EUR",
            base_currency="BYN",
            scale=1,
            buy_rate=Decimal("3.49"),
            sell_rate=Decimal("3.53"),
            channel="cash",
            location_name="Минск",
            quoted_at=now,
            fetched_at=now,
        )
        monkeypatch.setattr(CurrencyRepository, "get_bank_rate", lambda _repo, **_kwargs: quote)

        service = TelegramPlanReminderBotService(db)
        delivery = service.list_due_deliveries()[0]

        assert "229.00 EUR → 808.37 BYN" in delivery.text
        assert "Технобанк · продажа банком · наличные" in delivery.text
        assert "3.530000 BYN за 1 EUR" in delivery.text
        service.mark_delivery_sent(delivery)
        event = db.query(PlanOperationEvent).one()
        assert event.original_amount == Decimal("229.00")
        assert event.currency == "EUR"
        assert event.amount == Decimal("808.37")
        assert event.fx_rate == Decimal("3.530000")
        assert event.fx_bank_code == "technobank"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_mark_delivery_sent_delegates_to_plan_reminder_service():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="100500", username="tester"))
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
                scheduled_date=date.today(),
                note="Напомнить",
                status="active",
                recurrence_enabled=False,
            )
        )
        db.add(
            PlanReminderJob(
                id=1,
                plan_id=1,
                user_id=1,
                scheduled_for=datetime.now(timezone.utc),
                status="pending",
            )
        )
        db.commit()

        service = TelegramPlanReminderBotService(db)
        delivery = service.list_due_deliveries()[0]
        service.mark_delivery_sent(delivery)

        jobs = db.query(PlanReminderJob).order_by(PlanReminderJob.id.asc()).all()
        assert jobs[0].status == "sent"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_delivery_claim_prevents_duplicate_sender_and_can_be_released():
    engine, SessionLocal = _make_session()
    db = SessionLocal()
    try:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(AuthIdentity(user_id=1, provider="telegram", provider_user_id="100500", username="tester"))
        db.add(UserPreference(user_id=1, preferences_version=1, data={"plans": {"reminders_enabled": True}, "ui": {"timezone": "UTC"}}))
        db.add(PlanOperation(id=1, user_id=1, kind="expense", amount="10.00", scheduled_date=date.today(), status="active"))
        db.add(PlanReminderJob(id=1, plan_id=1, user_id=1, scheduled_for=datetime.now(timezone.utc), status="pending"))
        db.commit()

        service = TelegramPlanReminderBotService(db)
        candidate = service.list_due_deliveries()[0]
        claimed = service.claim_delivery(candidate)
        assert claimed is not None
        assert db.get(PlanReminderJob, 1).status == "sending"
        assert service.claim_delivery(candidate) is None

        service.release_delivery(claimed)
        assert db.get(PlanReminderJob, 1).status == "pending"
        assert service.claim_delivery(candidate) is not None
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
