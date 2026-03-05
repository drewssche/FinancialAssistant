import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user_id
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db
from app.main import app


def _override_current_user_id() -> int:
    return 1


@pytest.fixture
def client():
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
    app.dependency_overrides[get_current_user_id] = _override_current_user_id

    db = testing_session()
    db.add(User(id=1, display_name="Tester", status="active"))
    db.commit()
    db.close()

    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_categories_create_list_delete(client: TestClient):
    created = client.post("/api/v1/categories", json={"name": "Еда", "kind": "expense"})
    assert created.status_code == 200
    category_id = created.json()["id"]

    listed = client.get("/api/v1/categories")
    assert listed.status_code == 200
    assert any(item["id"] == category_id for item in listed.json())

    deleted = client.delete(f"/api/v1/categories/{category_id}")
    assert deleted.status_code == 204

    listed_after = client.get("/api/v1/categories")
    ids = [item["id"] for item in listed_after.json()]
    assert category_id not in ids


def test_categories_reject_bad_kind(client: TestClient):
    response = client.post("/api/v1/categories", json={"name": "Некорректно", "kind": "other"})
    assert response.status_code == 400
