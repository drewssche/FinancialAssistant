import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user_id
from app.core.cache import reset_cache_for_tests
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db
from app.main import app


def _override_current_user_id() -> int:
    return 1


@pytest.fixture
def client():
    reset_cache_for_tests()
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
    reset_cache_for_tests()
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


def test_operations_support_original_currency_and_base_conversion(client: TestClient):
    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "10.00",
            "currency": "USD",
            "fx_rate": "3.30",
            "operation_date": "2026-03-03",
            "note": "usd expense",
        },
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["currency"] == "USD"
    assert payload["base_currency"] == "BYN"
    assert payload["original_amount"] == "10.00"
    assert payload["fx_rate"] == "3.300000"
    assert payload["amount"] == "33.00"

    summary = client.get("/api/v1/operations/summary")
    assert summary.status_code == 200
    assert summary.json()["expense_total"] == "33.00"

    updated = client.patch(
        f"/api/v1/operations/{payload['id']}",
        json={
            "amount": "12.00",
            "currency": "USD",
            "fx_rate": "3.20",
        },
    )
    assert updated.status_code == 200, updated.text
    updated_payload = updated.json()
    assert updated_payload["original_amount"] == "12.00"
    assert updated_payload["amount"] == "38.40"


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


def test_operations_serialize_category_meta_for_operation_and_receipt_items(client: TestClient):
    category_resp = client.post("/api/v1/categories", json={"name": "Еда", "kind": "expense"})
    assert category_resp.status_code == 200
    category_id = category_resp.json()["id"]

    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "operation_date": "2026-03-02",
            "category_id": category_id,
            "note": "кофе и перекус",
            "receipt_items": [
                {
                    "shop_name": "Store",
                    "name": "Кофе",
                    "quantity": "1",
                    "unit_price": "5.00",
                    "category_id": category_id,
                },
            ],
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["category_name"] == "Еда"
    assert payload["receipt_items"][0]["category_name"] == "Еда"

    listed = client.get("/api/v1/operations", params={"page": 1, "page_size": 20})
    assert listed.status_code == 200
    item = listed.json()["items"][0]
    assert item["category_name"] == "Еда"
    assert item["receipt_items"][0]["category_name"] == "Еда"


def test_operations_summary_respects_filters(client: TestClient):
    category_resp = client.post("/api/v1/categories", json={"name": "Еда", "kind": "expense"})
    assert category_resp.status_code == 200
    category_id = category_resp.json()["id"]

    assert client.post(
        "/api/v1/operations",
        json={
            "kind": "income",
            "amount": "1000.00",
            "operation_date": "2026-03-01",
            "note": "salary",
        },
    ).status_code == 201
    assert client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "250.00",
            "operation_date": "2026-03-02",
            "note": "кофе и перекус",
            "category_id": category_id,
        },
    ).status_code == 201

    summary = client.get("/api/v1/operations/summary", params={"q": "еда"})
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["income_total"] == "0"
    assert payload["expense_total"] == "250.00"
    assert payload["balance"] == "-250.00"
    assert payload["total"] == 1


def test_operations_quick_views_filter_list_and_summary(client: TestClient):
    uncategorized = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "25.00",
            "operation_date": "2026-03-01",
            "note": "без категории",
        },
    )
    with_receipt = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "60.00",
            "operation_date": "2026-03-02",
            "note": "с чеком",
            "receipt_items": [
                {"shop_name": "Store", "name": "Milk", "quantity": "1", "unit_price": "60.00"},
            ],
        },
    )
    large = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "150.00",
            "operation_date": "2026-03-03",
            "note": "крупная покупка",
        },
    )
    assert uncategorized.status_code == 201
    assert with_receipt.status_code == 201
    assert large.status_code == 201

    receipt_list = client.get("/api/v1/operations", params={"quick_view": "receipt", "page": 1, "page_size": 20})
    assert receipt_list.status_code == 200
    assert receipt_list.json()["total"] == 1
    assert receipt_list.json()["items"][0]["note"] == "с чеком"

    large_summary = client.get("/api/v1/operations/summary", params={"quick_view": "large"})
    assert large_summary.status_code == 200
    assert large_summary.json()["expense_total"] == "150.00"
    assert large_summary.json()["total"] == 1

    uncategorized_summary = client.get("/api/v1/operations/summary", params={"quick_view": "uncategorized"})
    assert uncategorized_summary.status_code == 200
    assert uncategorized_summary.json()["expense_total"] == "235.00"
    assert uncategorized_summary.json()["total"] == 3


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


def test_operations_filter_by_receipt_item_category(client: TestClient):
    food_category = client.post("/api/v1/categories", json={"name": "Еда", "kind": "expense"})
    assert food_category.status_code == 200
    food_category_id = food_category.json()["id"]

    transport_category = client.post("/api/v1/categories", json={"name": "Транспорт", "kind": "expense"})
    assert transport_category.status_code == 200
    transport_category_id = transport_category.json()["id"]

    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "100.00",
            "operation_date": "2026-03-08",
            "receipt_items": [
                {"name": "Обед", "quantity": "1", "unit_price": "30.00", "category_id": food_category_id},
                {"name": "Такси", "quantity": "1", "unit_price": "70.00", "category_id": transport_category_id},
            ],
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["receipt_items"][0]["category_id"] == food_category_id
    assert payload["receipt_items"][1]["category_id"] == transport_category_id

    filtered = client.get(
        "/api/v1/operations",
        params={"category_id": transport_category_id, "page": 1, "page_size": 10},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1

    summary = client.get("/api/v1/operations/summary", params={"category_id": food_category_id})
    assert summary.status_code == 200
    assert summary.json()["expense_total"] == "100.00"

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


def test_operation_receipt_item_templates_skip_duplicate_price_history(client: TestClient):
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
            "amount": "66.00",
            "operation_date": "2026-03-06",
            "receipt_items": [
                {"shop_name": "Корона", "name": "Пачка Rothmans", "quantity": "10", "unit_price": "6.60"},
            ],
        },
    )
    assert second.status_code == 201

    templates = client.get("/api/v1/operations/item-templates", params={"page": 1, "page_size": 20})
    assert templates.status_code == 200
    template_id = templates.json()["items"][0]["id"]

    history = client.get(f"/api/v1/operations/item-templates/{template_id}/prices")
    assert history.status_code == 200
    history_payload = history.json()
    assert len(history_payload) == 1
    assert history_payload[0]["unit_price"] == "6.60"
    assert history_payload[0]["recorded_at"] == "2026-03-05"


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
            "latest_price_date": "2026-03-05",
        },
    )
    assert created.status_code == 201
    created_payload = created.json()
    template_id = created_payload["id"]
    assert created_payload["shop_name"] == "Соседи"
    assert created_payload["name"] == "Ротманс"
    assert created_payload["latest_unit_price"] == "6.60"
    assert created_payload["latest_price_date"] == "2026-03-05"

    updated = client.patch(
        f"/api/v1/operations/item-templates/{template_id}",
        json={
            "shop_name": "Кафе",
            "name": "Ротманс синий",
            "latest_unit_price": "6.90",
            "latest_price_date": "2026-03-06",
        },
    )
    assert updated.status_code == 200
    updated_payload = updated.json()
    assert updated_payload["shop_name"] == "Кафе"
    assert updated_payload["name"] == "Ротманс синий"
    assert updated_payload["latest_unit_price"] == "6.90"
    assert updated_payload["latest_price_date"] == "2026-03-06"

    history = client.get(f"/api/v1/operations/item-templates/{template_id}/prices")
    assert history.status_code == 200
    history_payload = history.json()
    assert len(history_payload) == 2
    assert history_payload[0]["recorded_at"] == "2026-03-06"
    assert history_payload[0]["unit_price"] == "6.90"
    assert history_payload[1]["unit_price"] == "6.60"


def test_operation_item_template_history_skips_duplicate_manual_price(client: TestClient):
    created = client.post(
        "/api/v1/operations/item-templates",
        json={
            "shop_name": "Соседи",
            "name": "Ротманс",
            "latest_unit_price": "6.60",
            "latest_price_date": "2026-03-05",
        },
    )
    assert created.status_code == 201
    template_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/operations/item-templates/{template_id}",
        json={
            "latest_unit_price": "6.60",
            "latest_price_date": "2026-03-07",
        },
    )
    assert updated.status_code == 200

    history = client.get(f"/api/v1/operations/item-templates/{template_id}/prices")
    assert history.status_code == 200
    history_payload = history.json()
    assert len(history_payload) == 1
    assert history_payload[0]["unit_price"] == "6.60"
    assert history_payload[0]["recorded_at"] == "2026-03-05"


def test_operation_item_template_history_cleans_existing_same_day_duplicate_rows(client: TestClient):
    created = client.post(
        "/api/v1/operations/item-templates",
        json={
            "shop_name": "Соседи",
            "name": "Ротманс",
            "latest_unit_price": "6.60",
            "latest_price_date": "2026-03-05",
        },
    )
    assert created.status_code == 201
    template_id = created.json()["id"]

    duplicated = client.patch(
        f"/api/v1/operations/item-templates/{template_id}",
        json={
            "latest_unit_price": "6.60",
            "latest_price_date": "2026-03-05",
        },
    )
    assert duplicated.status_code == 200

    history = client.get(f"/api/v1/operations/item-templates/{template_id}/prices")
    assert history.status_code == 200
    history_payload = history.json()
    assert len(history_payload) == 1
    assert history_payload[0]["unit_price"] == "6.60"
    assert history_payload[0]["recorded_at"] == "2026-03-05"


def test_operation_item_template_latest_price_uses_latest_recorded_date(client: TestClient):
    created = client.post(
        "/api/v1/operations/item-templates",
        json={
            "shop_name": "Соседи",
            "name": "Ротманс",
            "latest_unit_price": "6.60",
            "latest_price_date": "2026-03-05",
        },
    )
    assert created.status_code == 201
    template_id = created.json()["id"]

    older = client.patch(
        f"/api/v1/operations/item-templates/{template_id}",
        json={
            "latest_unit_price": "5.30",
            "latest_price_date": "2024-04-13",
        },
    )
    assert older.status_code == 200
    older_payload = older.json()
    assert older_payload["latest_unit_price"] == "6.60"
    assert older_payload["latest_price_date"] == "2026-03-05"

    history = client.get(f"/api/v1/operations/item-templates/{template_id}/prices")
    assert history.status_code == 200
    history_payload = history.json()
    assert history_payload[0]["recorded_at"] == "2026-03-05"
    assert history_payload[1]["recorded_at"] == "2024-04-13"

    deleted = client.delete(f"/api/v1/operations/item-templates/{template_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/api/v1/operations/item-templates/{template_id}/prices")
    assert missing.status_code == 404


def test_operation_item_template_create_without_price_or_source(client: TestClient):
    created = client.post(
        "/api/v1/operations/item-templates",
        json={
            "name": "USB кабель",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["shop_name"] is None
    assert payload["name"] == "USB кабель"
    assert payload["latest_unit_price"] is None


def test_operation_item_template_create_reactivates_archived_duplicate(client: TestClient):
    created = client.post(
        "/api/v1/operations/item-templates",
        json={
            "shop_name": "Легаси",
            "name": "Ротманс",
            "latest_unit_price": "9.40",
            "latest_price_date": "2026-03-01",
        },
    )
    assert created.status_code == 201
    template_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/operations/item-templates/{template_id}")
    assert deleted.status_code == 204

    recreated = client.post(
        "/api/v1/operations/item-templates",
        json={
            "shop_name": "Легаси",
            "name": "Ротманс",
            "latest_unit_price": "9.50",
        },
    )
    assert recreated.status_code == 201
    payload = recreated.json()
    assert payload["id"] == template_id
    assert payload["shop_name"] == "Легаси"
    assert payload["name"] == "Ротманс"
    assert payload["latest_unit_price"] == "9.50"

    templates = client.get("/api/v1/operations/item-templates", params={"page": 1, "page_size": 20, "q": "Ротманс"})
    assert templates.status_code == 200
    list_payload = templates.json()
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["id"] == template_id


def test_operation_receipt_item_template_reactivates_archived_duplicate(client: TestClient):
    created = client.post(
        "/api/v1/operations/item-templates",
        json={
            "shop_name": "Легаси",
            "name": "Ротманс",
            "latest_unit_price": "9.40",
            "latest_price_date": "2026-03-01",
        },
    )
    assert created.status_code == 201
    template_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/operations/item-templates/{template_id}")
    assert deleted.status_code == 204

    operation = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "9.50",
            "operation_date": "2026-03-07",
            "receipt_items": [
                {"shop_name": "Легаси", "name": "Ротманс", "quantity": "1", "unit_price": "9.50"},
            ],
        },
    )
    assert operation.status_code == 201

    templates = client.get("/api/v1/operations/item-templates", params={"page": 1, "page_size": 20, "q": "Ротманс"})
    assert templates.status_code == 200
    list_payload = templates.json()
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["id"] == template_id
    assert list_payload["items"][0]["shop_name"] == "Легаси"
    assert list_payload["items"][0]["latest_unit_price"] == "9.50"


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


def test_operation_item_templates_cache_is_invalidated_by_template_and_receipt_mutations(client: TestClient):
    initial = client.get("/api/v1/operations/item-templates", params={"page": 1, "page_size": 20})
    assert initial.status_code == 200
    assert initial.json()["total"] == 0

    created = client.post(
        "/api/v1/operations/item-templates",
        json={
            "shop_name": "Соседи",
            "name": "Кофе",
            "latest_unit_price": "4.50",
            "latest_price_date": "2026-03-05",
        },
    )
    assert created.status_code == 201
    template_id = created.json()["id"]

    after_create = client.get("/api/v1/operations/item-templates", params={"page": 1, "page_size": 20})
    assert after_create.status_code == 200
    assert after_create.json()["total"] == 1
    assert after_create.json()["items"][0]["latest_unit_price"] == "4.50"

    first_history = client.get(f"/api/v1/operations/item-templates/{template_id}/prices")
    assert first_history.status_code == 200
    assert len(first_history.json()) == 1

    operation = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "4.80",
            "operation_date": "2026-03-06",
            "receipt_items": [
                {"shop_name": "Соседи", "name": "Кофе", "quantity": "1", "unit_price": "4.80"},
            ],
        },
    )
    assert operation.status_code == 201

    after_receipt = client.get("/api/v1/operations/item-templates", params={"page": 1, "page_size": 20})
    assert after_receipt.status_code == 200
    assert after_receipt.json()["total"] == 1
    assert after_receipt.json()["items"][0]["latest_unit_price"] == "4.80"
    assert after_receipt.json()["items"][0]["use_count"] == 1

    history_after_receipt = client.get(f"/api/v1/operations/item-templates/{template_id}/prices")
    assert history_after_receipt.status_code == 200
    history_payload = history_after_receipt.json()
    assert len(history_payload) == 2
    assert history_payload[0]["unit_price"] == "4.80"
    assert history_payload[1]["unit_price"] == "4.50"


def test_operations_summary_cache_is_invalidated_after_operation_mutations(client: TestClient):
    initial_summary = client.get("/api/v1/operations/summary")
    assert initial_summary.status_code == 200
    assert initial_summary.json()["total"] == 0

    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "120.00",
            "operation_date": "2026-03-02",
            "note": "cache summary op",
        },
    )
    assert created.status_code == 201
    operation_id = created.json()["id"]

    after_create = client.get("/api/v1/operations/summary")
    assert after_create.status_code == 200
    assert after_create.json()["expense_total"] == "120.00"
    assert after_create.json()["total"] == 1

    updated = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={
            "amount": "150.00",
            "note": "cache summary op updated",
        },
    )
    assert updated.status_code == 200

    after_update = client.get("/api/v1/operations/summary")
    assert after_update.status_code == 200
    assert after_update.json()["expense_total"] == "150.00"
    assert after_update.json()["total"] == 1

    deleted = client.delete(f"/api/v1/operations/{operation_id}")
    assert deleted.status_code == 204

    after_delete = client.get("/api/v1/operations/summary")
    assert after_delete.status_code == 200
    assert after_delete.json()["expense_total"] == "0"
    assert after_delete.json()["total"] == 0


def test_operations_list_cache_is_invalidated_after_operation_mutations(client: TestClient):
    initial_list = client.get(
        "/api/v1/operations",
        params={"page": 1, "page_size": 20, "sort_by": "operation_date", "sort_dir": "desc"},
    )
    assert initial_list.status_code == 200
    assert initial_list.json()["total"] == 0

    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "120.00",
            "operation_date": "2026-03-02",
            "note": "cache list op",
        },
    )
    assert created.status_code == 201
    operation_id = created.json()["id"]

    after_create = client.get(
        "/api/v1/operations",
        params={"page": 1, "page_size": 20, "sort_by": "operation_date", "sort_dir": "desc"},
    )
    assert after_create.status_code == 200
    assert after_create.json()["total"] == 1
    assert after_create.json()["items"][0]["note"] == "cache list op"

    updated = client.patch(
        f"/api/v1/operations/{operation_id}",
        json={
            "amount": "150.00",
            "note": "cache list op updated",
        },
    )
    assert updated.status_code == 200

    after_update = client.get(
        "/api/v1/operations",
        params={"page": 1, "page_size": 20, "sort_by": "operation_date", "sort_dir": "desc"},
    )
    assert after_update.status_code == 200
    assert after_update.json()["total"] == 1
    assert after_update.json()["items"][0]["note"] == "cache list op updated"
    assert after_update.json()["items"][0]["amount"] == "150.00"

    deleted = client.delete(f"/api/v1/operations/{operation_id}")
    assert deleted.status_code == 204

    after_delete = client.get(
        "/api/v1/operations",
        params={"page": 1, "page_size": 20, "sort_by": "operation_date", "sort_dir": "desc"},
    )
    assert after_delete.status_code == 200
    assert after_delete.json()["total"] == 0
