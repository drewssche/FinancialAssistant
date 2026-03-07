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


def test_operations_search_by_note_category_and_kind_ru(client: TestClient):
    category_resp = client.post("/api/v1/categories", json={"name": "Еда", "kind": "expense"})
    assert category_resp.status_code == 200
    category_id = category_resp.json()["id"]

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
            "amount": "250.00",
            "operation_date": "2026-03-02",
            "note": "кофе и перекус",
            "category_id": category_id,
        },
    )
    assert created_expense.status_code == 201

    by_note = client.get("/api/v1/operations", params={"q": "кофе", "page": 1, "page_size": 20})
    assert by_note.status_code == 200
    assert by_note.json()["total"] == 1
    assert by_note.json()["items"][0]["kind"] == "expense"

    by_category = client.get("/api/v1/operations", params={"q": "еда", "page": 1, "page_size": 20})
    assert by_category.status_code == 200
    assert by_category.json()["total"] == 1
    assert by_category.json()["items"][0]["category_id"] == category_id

    by_kind_ru = client.get("/api/v1/operations", params={"q": "расход", "page": 1, "page_size": 20})
    assert by_kind_ru.status_code == 200
    assert by_kind_ru.json()["total"] == 1
    assert by_kind_ru.json()["items"][0]["kind"] == "expense"


def test_operation_receipt_items_autofill_amount_and_discrepancy(client: TestClient):
    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "operation_date": "2026-03-07",
            "note": "чек",
            "receipt_items": [
                {"shop_name": "Корона", "name": "Пачка Rothmans", "quantity": "10", "unit_price": "6.60"},
                {"shop_name": "Корона", "name": "Кофе", "quantity": "1", "unit_price": "3.40"},
            ],
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["amount"] == "69.40"
    assert payload["receipt_total"] == "69.40"
    assert payload["receipt_discrepancy"] == "0.00"
    assert len(payload["receipt_items"]) == 2
    assert payload["receipt_items"][0]["shop_name"] == "Корона"

    operation_id = payload["id"]
    updated = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={
            "amount": "70.00",
            "receipt_items": [
                {"shop_name": "Корона", "name": "Пачка Rothmans", "quantity": "10", "unit_price": "6.60"},
                {"shop_name": "Корона", "name": "Кофе", "quantity": "1", "unit_price": "3.40"},
            ],
        },
    )
    assert updated.status_code == 200
    updated_payload = updated.json()
    assert updated_payload["amount"] == "70.00"
    assert updated_payload["receipt_total"] == "69.40"
    assert updated_payload["receipt_discrepancy"] == "0.60"


def test_operation_receipt_item_templates_and_price_history(client: TestClient):
    first = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "66.00",
            "operation_date": "2026-03-05",
            "receipt_items": [
                {"shop_name": "Корона", "name": "Пачка Rothmans", "quantity": "10", "unit_price": "6.60"},
            ],
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "68.00",
            "operation_date": "2026-03-06",
            "receipt_items": [
                {"shop_name": "Корона", "name": "Пачка Rothmans", "quantity": "10", "unit_price": "6.80"},
            ],
        },
    )
    assert second.status_code == 201

    templates = client.get("/api/v1/operations/item-templates", params={"page": 1, "page_size": 20})
    assert templates.status_code == 200
    tpl_payload = templates.json()
    assert tpl_payload["total"] == 1
    assert tpl_payload["items"][0]["shop_name"] == "Корона"
    assert tpl_payload["items"][0]["name"] == "Пачка Rothmans"
    assert tpl_payload["items"][0]["use_count"] == 2
    assert tpl_payload["items"][0]["latest_unit_price"] == "6.80"

    template_id = tpl_payload["items"][0]["id"]
    history = client.get(f"/api/v1/operations/item-templates/{template_id}/prices")
    assert history.status_code == 200
    history_payload = history.json()
    assert len(history_payload) >= 2
    assert history_payload[0]["unit_price"] == "6.80"
    assert history_payload[1]["unit_price"] == "6.60"


def test_operation_rejects_missing_amount_when_receipt_is_empty(client: TestClient):
    response = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "operation_date": "2026-03-07",
            "note": "empty",
            "receipt_items": [],
        },
    )
    assert response.status_code == 400
    assert "amount is required" in response.json()["detail"]


def test_operation_item_templates_are_scoped_by_shop(client: TestClient):
    first = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "6.60",
            "operation_date": "2026-03-06",
            "receipt_items": [
                {"shop_name": "Корона", "name": "Ротманс", "quantity": "1", "unit_price": "6.60"},
            ],
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "6.90",
            "operation_date": "2026-03-06",
            "receipt_items": [
                {"shop_name": "Евроопт", "name": "Ротманс", "quantity": "1", "unit_price": "6.90"},
            ],
        },
    )
    assert second.status_code == 201

    templates = client.get("/api/v1/operations/item-templates", params={"page": 1, "page_size": 20, "q": "Ротманс"})
    assert templates.status_code == 200
    payload = templates.json()
    assert payload["total"] == 2
    shops = {item["shop_name"] for item in payload["items"]}
    assert shops == {"Корона", "Евроопт"}


def test_operation_item_templates_crud(client: TestClient):
    created = client.post(
        "/api/v1/operations/item-templates",
        json={
            "shop_name": "Соседи",
            "name": "Ротманс",
            "latest_unit_price": "6.60",
        },
    )
    assert created.status_code == 201
    created_payload = created.json()
    template_id = created_payload["id"]
    assert created_payload["shop_name"] == "Соседи"
    assert created_payload["name"] == "Ротманс"
    assert created_payload["latest_unit_price"] == "6.60"

    updated = client.patch(
        f"/api/v1/operations/item-templates/{template_id}",
        json={
            "shop_name": "Кафе",
            "name": "Ротманс синий",
            "latest_unit_price": "6.90",
        },
    )
    assert updated.status_code == 200
    updated_payload = updated.json()
    assert updated_payload["shop_name"] == "Кафе"
    assert updated_payload["name"] == "Ротманс синий"
    assert updated_payload["latest_unit_price"] == "6.90"

    history = client.get(f"/api/v1/operations/item-templates/{template_id}/prices")
    assert history.status_code == 200
    history_payload = history.json()
    assert len(history_payload) == 2
    assert history_payload[0]["unit_price"] == "6.90"
    assert history_payload[1]["unit_price"] == "6.60"

    deleted = client.delete(f"/api/v1/operations/item-templates/{template_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/api/v1/operations/item-templates/{template_id}/prices")
    assert missing.status_code == 404


def test_operation_item_templates_delete_all(client: TestClient):
    one = client.post(
        "/api/v1/operations/item-templates",
        json={"shop_name": "Соседи", "name": "Ротманс", "latest_unit_price": "6.60"},
    )
    assert one.status_code == 201
    two = client.post(
        "/api/v1/operations/item-templates",
        json={"shop_name": "Кафе", "name": "Кофе", "latest_unit_price": "4.50"},
    )
    assert two.status_code == 201

    deleted = client.delete("/api/v1/operations/item-templates")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] == 2

    templates = client.get("/api/v1/operations/item-templates", params={"page": 1, "page_size": 20})
    assert templates.status_code == 200
    assert templates.json()["total"] == 0
