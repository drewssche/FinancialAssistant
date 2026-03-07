from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.base import Base
from app.db.models import Operation, User
from app.db.session import get_db
from app.main import app


def _override_current_user():
    return User(id=1, display_name="Tester", status="approved")


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
    app.dependency_overrides[get_current_user] = _override_current_user

    db = testing_session()
    db.add(User(id=1, display_name="Tester", status="active"))
    db.add(Operation(user_id=1, kind="expense", amount="10.00", operation_date=date(2026, 3, 1), note="x"))
    db.commit()
    db.close()

    test_client = TestClient(app)
    yield test_client, testing_session

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_delete_me_removes_user_and_related_data(client_and_sessionmaker):
    client, testing_session = client_and_sessionmaker
    response = client.delete("/api/v1/users/me")
    assert response.status_code == 204

    db = testing_session()
    user = db.scalar(select(User).where(User.id == 1))
    operations = list(db.scalars(select(Operation).where(Operation.user_id == 1)))
    db.close()
    assert user is None
    assert operations == []
