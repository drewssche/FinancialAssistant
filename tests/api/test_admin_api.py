from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_admin_user, get_current_user
from app.db.base import Base
from app.db.models import AuthIdentity, User
from app.db.session import get_db
from app.main import app


def _override_admin_user() -> User:
    return User(id=900, display_name="Admin", status="approved")


@pytest.fixture
def client_and_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_admin_user] = _override_admin_user

    db = testing_session()
    pending = User(id=1, display_name="Pending User", status="pending", created_at=datetime.now(timezone.utc))
    approved = User(id=2, display_name="Approved User", status="approved", created_at=datetime.now(timezone.utc))
    rejected = User(id=3, display_name="Rejected User", status="rejected", created_at=datetime.now(timezone.utc))
    db.add_all([pending, approved, rejected])
    db.flush()
    db.add_all(
        [
            AuthIdentity(user_id=1, provider="telegram", provider_user_id="101", username="pending"),
            AuthIdentity(user_id=2, provider="telegram", provider_user_id="102", username="approved"),
            AuthIdentity(user_id=3, provider="telegram", provider_user_id="103", username="rejected"),
        ]
    )
    db.commit()
    db.close()

    test_client = TestClient(app)
    yield test_client, testing_session

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_admin_users_list_by_status(client_and_sessionmaker):
    client, _ = client_and_sessionmaker
    response = client.get("/api/v1/admin/users", params={"status_filter": "pending"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "pending"


def test_admin_can_approve_user(client_and_sessionmaker):
    client, testing_session = client_and_sessionmaker
    response = client.patch("/api/v1/admin/users/1/status", json={"status": "approved"})
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    db = testing_session()
    user = db.scalar(select(User).where(User.id == 1))
    db.close()
    assert user is not None
    assert user.status == "approved"


def test_admin_can_delete_user(client_and_sessionmaker):
    client, testing_session = client_and_sessionmaker
    response = client.delete("/api/v1/admin/users/3")
    assert response.status_code == 204

    db = testing_session()
    user = db.scalar(select(User).where(User.id == 3))
    db.close()
    assert user is None


def test_non_admin_cannot_access_admin_users():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: User(id=55, display_name="U", status="approved")
    client = TestClient(app)
    response = client.get("/api/v1/admin/users")
    assert response.status_code == 403
    app.dependency_overrides.clear()
