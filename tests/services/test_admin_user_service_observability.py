from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AuthIdentity, User
from app.services.admin_user_service import AdminUserService, InvalidAdminUserRequestError


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
        db.add_all(
            [
                User(id=1, display_name="Admin", status="approved", created_at=datetime.now(timezone.utc)),
                User(id=2, display_name="Pending User", status="pending", created_at=datetime.now(timezone.utc)),
                User(id=3, display_name="Rejected User", status="rejected", created_at=datetime.now(timezone.utc)),
            ]
        )
        db.add_all(
            [
                AuthIdentity(user_id=1, provider="telegram", provider_user_id="1001", username="admin"),
                AuthIdentity(user_id=2, provider="telegram", provider_user_id="1002", username="pending"),
                AuthIdentity(user_id=3, provider="telegram", provider_user_id="1003", username="rejected"),
            ]
        )
        db.commit()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_admin_user_service_logs_status_change(db_session: Session, caplog: pytest.LogCaptureFixture):
    caplog.set_level("INFO")

    AdminUserService(db_session).update_user_status(user_id=2, next_status="approved", current_admin_id=1)

    text = caplog.text
    assert "admin_notification_event event=admin_user_status_changed" in text
    assert "admin_id=1" in text
    assert "target_user_id=2" in text
    assert "previous_status=pending" in text
    assert "next_status=approved" in text


def test_admin_user_service_logs_already_set_status(db_session: Session, caplog: pytest.LogCaptureFixture):
    caplog.set_level("INFO")

    AdminUserService(db_session).update_user_status(user_id=3, next_status="rejected", current_admin_id=1)

    text = caplog.text
    assert "admin_notification_event event=admin_user_status_already_set" in text
    assert "admin_id=1" in text
    assert "target_user_id=3" in text
    assert "status=rejected" in text


def test_admin_user_service_logs_delete_success(db_session: Session, caplog: pytest.LogCaptureFixture):
    caplog.set_level("INFO")

    AdminUserService(db_session).delete_user(user_id=2, current_admin_id=1)

    text = caplog.text
    assert "admin_notification_event event=admin_user_deleted" in text
    assert "admin_id=1" in text
    assert "target_user_id=2" in text


def test_admin_user_service_logs_blocked_self_action(db_session: Session, caplog: pytest.LogCaptureFixture):
    caplog.set_level("INFO")

    with pytest.raises(InvalidAdminUserRequestError, match="Cannot delete own account"):
        AdminUserService(db_session).delete_user(user_id=1, current_admin_id=1)

    text = caplog.text
    assert "admin_notification_event event=admin_user_self_action_blocked" in text
    assert "admin_id=1" in text
    assert "action=delete" in text
    assert "target_user_id=1" in text
