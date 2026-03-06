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


def test_debts_create_and_list_cards(client: TestClient):
    created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Иван",
            "direction": "lend",
            "principal": "500.00",
            "start_date": "2026-03-05",
            "due_date": "2026-03-30",
            "note": "На ремонт",
        },
    )
    assert created.status_code == 201

    cards = client.get("/api/v1/debts/cards")
    assert cards.status_code == 200
    payload = cards.json()
    assert len(payload) == 1
    assert payload[0]["counterparty"] == "Иван"
    assert payload[0]["status"] == "active"
    assert payload[0]["outstanding_total"] == "500.00"
    assert payload[0]["debts"][0]["repayments"] == []


def test_debts_repayment_and_close_card(client: TestClient):
    created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Мария",
            "direction": "borrow",
            "principal": "300.00",
            "start_date": "2026-02-10",
        },
    )
    assert created.status_code == 201
    debt_id = created.json()["id"]

    repaid = client.post(
        f"/api/v1/debts/{debt_id}/repayments",
        json={"amount": "300.00", "repayment_date": "2026-03-01"},
    )
    assert repaid.status_code == 201

    active_cards = client.get("/api/v1/debts/cards")
    assert active_cards.status_code == 200
    assert active_cards.json() == []

    all_cards = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert all_cards.status_code == 200
    payload = all_cards.json()
    assert len(payload) == 1
    assert payload[0]["status"] == "closed"
    assert payload[0]["outstanding_total"] == "0.00"


def test_debts_repayment_overpay_creates_reverse_debt(client: TestClient):
    created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Петр",
            "direction": "lend",
            "principal": "100.00",
            "start_date": "2026-01-01",
        },
    )
    assert created.status_code == 201
    debt_id = created.json()["id"]

    response = client.post(
        f"/api/v1/debts/{debt_id}/repayments",
        json={"amount": "120.00", "repayment_date": "2026-01-15"},
    )
    assert response.status_code == 201
    assert response.json()["amount"] == "100.00"

    cards = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert cards.status_code == 200
    payload = cards.json()
    assert len(payload) == 1
    debts = payload[0]["debts"]
    directions = sorted([item["direction"] for item in debts])
    assert directions == ["borrow", "lend"]
    reverse = next(item for item in debts if item["direction"] == "borrow")
    assert reverse["principal"] == "20.00"
    assert reverse["outstanding_total"] == "20.00"


def test_debts_update_and_delete(client: TestClient):
    created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Сергей",
            "direction": "lend",
            "principal": "450.00",
            "start_date": "2026-02-01",
            "due_date": "2026-04-01",
            "note": "Черновик",
        },
    )
    assert created.status_code == 201
    debt_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/debts/{debt_id}",
        json={
            "counterparty": "Сергей П.",
            "principal": "500.00",
            "note": "Обновлено",
        },
    )
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["principal"] == "500.00"
    assert payload["note"] == "Обновлено"

    deleted = client.delete(f"/api/v1/debts/{debt_id}")
    assert deleted.status_code == 204

    cards = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert cards.status_code == 200
    assert all(debt["id"] != debt_id for card in cards.json() for debt in card["debts"])


def test_debts_merge_same_counterparty_direction_into_active_debt(client: TestClient):
    first = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Надя",
            "direction": "lend",
            "principal": "100.00",
            "start_date": "2026-03-05",
        },
    )
    assert first.status_code == 201
    debt_id = first.json()["id"]

    second = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "надя",
            "direction": "lend",
            "principal": "250.00",
            "start_date": "2026-03-06",
        },
    )
    assert second.status_code == 201
    assert second.json()["id"] == debt_id
    assert second.json()["principal"] == "350.00"
    assert len(second.json()["issuances"]) == 2

    cards = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert cards.status_code == 200
    payload = cards.json()
    assert len(payload) == 1
    assert len(payload[0]["debts"]) == 1
    assert payload[0]["debts"][0]["principal"] == "350.00"
