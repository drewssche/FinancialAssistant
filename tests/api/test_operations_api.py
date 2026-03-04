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


def test_operations_crud_and_filters(client: TestClient):
    created_income = client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "1000.00",
            "operation_date": "2026-03-01",
            "note": "salary",
        },
    )
    assert created_income.status_code == 201

    created_expense = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "5.00",
            "operation_date": "2026-03-02",
            "note": "coffee",
        },
    )
    assert created_expense.status_code == 201
    expense_id = created_expense.json()["id"]

    filtered = client.get("/api/v1/operations", params={"kind": "expense", "page": 1, "page_size": 10})
    assert filtered.status_code == 200
    filtered_data = filtered.json()
    assert filtered_data["total"] == 1
    assert len(filtered_data["items"]) == 1
    assert filtered_data["items"][0]["note"] == "coffee"

    updated = client.patch(
        f"/api/v1/operations/{expense_id}",
        json={"note": "coffee shop", "amount": "7.50"},
    )
    assert updated.status_code == 200
    assert updated.json()["note"] == "coffee shop"
    assert updated.json()["amount"] == "7.50"

    fetched = client.get(f"/api/v1/operations/{expense_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == expense_id

    removed = client.delete(f"/api/v1/operations/{expense_id}")
    assert removed.status_code == 204

    not_found = client.get(f"/api/v1/operations/{expense_id}")
    assert not_found.status_code == 404


def test_operations_reject_invalid_date_range(client: TestClient):
    response = client.get(
        "/api/v1/operations",
        params={
            "date_from": "2026-03-10",
            "date_to": "2026-03-01",
        },
    )
    assert response.status_code == 400
    assert "date_from" in response.json()["detail"]
