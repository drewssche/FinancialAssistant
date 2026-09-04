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


@pytest.fixture
def client():
    reset_cache_for_tests()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        class_=Session,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    with testing_session() as db:
        db.add_all(
            [
                User(id=1, display_name="Tester", status="active"),
                User(id=2, display_name="Other tester", status="active"),
            ]
        )
        db.commit()

    yield TestClient(app)

    reset_cache_for_tests()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _source(client: TestClient, name: str) -> int:
    response = client.post("/api/v1/operations/item-sources", json={"name": name})
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def _category(client: TestClient, name: str) -> int:
    response = client.post(
        "/api/v1/categories",
        json={"name": name, "kind": "expense"},
    )
    assert response.status_code == 200, response.text
    return int(response.json()["id"])


def _brand(client: TestClient, name: str) -> int:
    response = client.post(
        "/api/v1/operations/item-brands",
        json={"name": name},
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def _operation(
    client: TestClient,
    *,
    product_id: int,
    source_id: int,
    name: str,
    price: str,
    operation_date: str,
    category_id: int | None = None,
) -> dict:
    item = {
        "product_id": product_id,
        "source_id": source_id,
        "name": name,
        "quantity": "1",
        "unit_price": price,
    }
    payload = {
        "kind": "expense",
        "operation_date": operation_date,
        "receipt_items": [item],
    }
    if category_id is not None:
        payload["category_id"] = category_id
        item["category_id"] = category_id
    response = client.post(
        "/api/v1/operations",
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_receipts_create_source_offers_and_filter_by_canonical_product(
    client: TestClient,
):
    green_id = _source(client, "Green")
    euroopt_id = _source(client, "Евроопт")
    product_response = client.post(
        "/api/v1/operations/catalog-products",
        json={"name": "Сырок клубника 40 г"},
    )
    assert product_response.status_code == 201, product_response.text
    product_id = int(product_response.json()["id"])

    green_purchase = _operation(
        client,
        product_id=product_id,
        source_id=green_id,
        name="Сырок клубника 40г",
        price="0.82",
        operation_date="2026-09-02",
    )
    euroopt_purchase = _operation(
        client,
        product_id=product_id,
        source_id=euroopt_id,
        name="Сырок с печеньем клубника 40 г",
        price="0.81",
        operation_date="2026-09-03",
    )

    green_item = green_purchase["receipt_items"][0]
    euroopt_item = euroopt_purchase["receipt_items"][0]
    assert green_item["product_id"] == product_id
    assert euroopt_item["product_id"] == product_id
    assert green_item["product_name"] == "Сырок клубника 40 г"
    assert green_item["template_id"] != euroopt_item["template_id"]

    product = client.get(
        f"/api/v1/operations/catalog-products/{product_id}"
    ).json()
    assert product["offers_count"] == 2
    assert product["sources_count"] == 2
    assert product["use_count"] == 2

    filtered = client.get(
        "/api/v1/operations",
        params={"product_id": product_id, "page_size": 100},
    )
    assert filtered.status_code == 200, filtered.text
    assert filtered.json()["total"] == 2
    assert {
        int(item["receipt_items"][0]["product_id"])
        for item in filtered.json()["items"]
    } == {product_id}

    searched = client.get(
        "/api/v1/operations",
        params={"q": "Сырок клубника 40 г", "page_size": 100},
    )
    assert searched.status_code == 200, searched.text
    assert searched.json()["total"] == 2

    money_flow = client.get(
        "/api/v1/operations/money-flow",
        params={"product_id": product_id, "page_size": 100},
    )
    assert money_flow.status_code == 200, money_flow.text
    assert money_flow.json()["total"] == 2

    summary = client.get(
        "/api/v1/operations/summary",
        params={"product_id": product_id},
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["expense_total"] == "1.63"
    assert summary.json()["total"] == 2


def test_position_analytics_groups_offers_by_product_and_plan_exposes_linkage(
    client: TestClient,
):
    green_id = _source(client, "Green")
    euroopt_id = _source(client, "Евроопт")
    product = client.post(
        "/api/v1/operations/catalog-products",
        json={"name": "Один канонический товар"},
    ).json()
    product_id = int(product["id"])
    _operation(
        client,
        product_id=product_id,
        source_id=green_id,
        name="Название Green",
        price="2.00",
        operation_date="2026-09-02",
    )
    _operation(
        client,
        product_id=product_id,
        source_id=euroopt_id,
        name="Название Евроопт",
        price="3.00",
        operation_date="2026-09-03",
    )

    analytics = client.get(
        "/api/v1/dashboard/analytics/positions",
        params={"period": "month", "anchor": "2026-09-04"},
    )
    assert analytics.status_code == 200, analytics.text
    rows = analytics.json()["positions"]
    assert len(rows) == 1
    assert rows[0]["product_id"] == product_id
    assert rows[0]["template_id"] is None
    assert rows[0]["name"] == "Один канонический товар"
    assert rows[0]["shop_name"] is None
    assert rows[0]["source_names"] == ["Green", "Евроопт"]
    assert rows[0]["sources_count"] == 2
    assert rows[0]["purchases_count"] == 2
    assert rows[0]["amount_total"] == "5.00"

    plan = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "scheduled_date": "2026-10-01",
            "receipt_items": [
                {
                    "product_id": product_id,
                    "source_id": green_id,
                    "name": "Название Green",
                    "quantity": "1",
                    "unit_price": "2.10",
                }
            ],
        },
    )
    assert plan.status_code == 201, plan.text
    plan_item = plan.json()["receipt_items"][0]
    assert plan_item["product_id"] == product_id
    assert plan_item["product_name"] == "Один канонический товар"


def test_legacy_offer_brand_edit_updates_canonical_product_and_all_offers(
    client: TestClient,
):
    green_id = _source(client, "Green")
    euroopt_id = _source(client, "Евроопт")
    first_brand = client.post(
        "/api/v1/operations/item-brands",
        json={"name": "Первый"},
    ).json()
    second_brand = client.post(
        "/api/v1/operations/item-brands",
        json={"name": "Второй"},
    ).json()
    product = client.post(
        "/api/v1/operations/catalog-products",
        json={"name": "Товар", "brand_id": first_brand["id"]},
    ).json()
    product_id = int(product["id"])

    offers = []
    for source_id, name in ((green_id, "Товар G"), (euroopt_id, "Товар E")):
        response = client.post(
            "/api/v1/operations/item-templates",
            json={"product_id": product_id, "source_id": source_id, "name": name},
        )
        assert response.status_code == 201, response.text
        offers.append(response.json())

    updated = client.patch(
        f"/api/v1/operations/item-templates/{offers[0]['id']}",
        json={"brand_id": second_brand["id"]},
    )
    assert updated.status_code == 200, updated.text
    refreshed_product = client.get(
        f"/api/v1/operations/catalog-products/{product_id}"
    ).json()
    assert refreshed_product["brand_id"] == second_brand["id"]
    assert {offer["brand_id"] for offer in refreshed_product["offers"]} == {
        second_brand["id"]
    }
    searched = client.get(
        "/api/v1/operations/catalog-products",
        params={"q": "Второй"},
    )
    assert searched.status_code == 200, searched.text
    assert [item["id"] for item in searched.json()["items"]] == [product_id]


def test_product_category_update_propagates_to_operation_plan_and_parents(
    client: TestClient,
):
    old_category_id = _category(client, "Старая категория")
    new_category_id = _category(client, "Новая категория")
    source_id = _source(client, "Green")
    product = client.post(
        "/api/v1/operations/catalog-products",
        json={"name": "Товар с категорией", "category_id": old_category_id},
    ).json()
    product_id = int(product["id"])
    operation = _operation(
        client,
        product_id=product_id,
        source_id=source_id,
        name="Товар Green",
        price="4.20",
        operation_date="2026-09-02",
        category_id=old_category_id,
    )
    plan = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "scheduled_date": "2026-10-01",
            "category_id": old_category_id,
            "receipt_items": [
                {
                    "product_id": product_id,
                    "source_id": source_id,
                    "name": "Товар Green",
                    "category_id": old_category_id,
                    "quantity": "1",
                    "unit_price": "4.20",
                }
            ],
        },
    )
    assert plan.status_code == 201, plan.text
    archived_offer = client.delete(
        f"/api/v1/operations/item-templates/"
        f"{operation['receipt_items'][0]['template_id']}"
    )
    assert archived_offer.status_code == 204, archived_offer.text

    updated = client.patch(
        f"/api/v1/operations/catalog-products/{product_id}",
        json={"category_id": new_category_id},
    )
    assert updated.status_code == 200, updated.text

    refreshed_operation = client.get(
        f"/api/v1/operations/{operation['id']}"
    ).json()
    assert refreshed_operation["category_id"] == new_category_id
    assert refreshed_operation["receipt_items"][0]["category_id"] == new_category_id
    refreshed_plan = client.get(f"/api/v1/plans/{plan.json()['id']}").json()
    assert refreshed_plan["category_id"] == new_category_id
    assert refreshed_plan["receipt_items"][0]["category_id"] == new_category_id


def test_product_merge_propagates_target_category_to_linked_history(
    client: TestClient,
):
    source_category_id = _category(client, "Категория источника")
    target_category_id = _category(client, "Категория цели")
    source_id = _source(client, "Евроопт")
    target_product = client.post(
        "/api/v1/operations/catalog-products",
        json={"name": "Общий товар", "category_id": target_category_id},
    ).json()
    source_product = client.post(
        "/api/v1/operations/catalog-products",
        json={"name": "Старое имя", "category_id": source_category_id},
    ).json()
    operation = _operation(
        client,
        product_id=int(source_product["id"]),
        source_id=source_id,
        name="Предложение Евроопт",
        price="2.50",
        operation_date="2026-09-01",
        category_id=source_category_id,
    )
    plan = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "scheduled_date": "2026-10-02",
            "category_id": source_category_id,
            "receipt_items": [
                {
                    "product_id": source_product["id"],
                    "source_id": source_id,
                    "name": "Предложение Евроопт",
                    "category_id": source_category_id,
                    "quantity": "1",
                    "unit_price": "2.50",
                }
            ],
        },
    )
    assert plan.status_code == 201, plan.text

    merged = client.post(
        f"/api/v1/operations/catalog-products/{target_product['id']}/merge",
        json={"source_product_ids": [source_product["id"]]},
    )
    assert merged.status_code == 200, merged.text

    refreshed_operation = client.get(
        f"/api/v1/operations/{operation['id']}"
    ).json()
    assert refreshed_operation["category_id"] == target_category_id
    assert refreshed_operation["receipt_items"][0]["category_id"] == target_category_id
    refreshed_plan = client.get(f"/api/v1/plans/{plan.json()['id']}").json()
    assert refreshed_plan["category_id"] == target_category_id
    assert refreshed_plan["receipt_items"][0]["category_id"] == target_category_id


def test_operation_receipt_edits_update_only_explicit_canonical_metadata(
    client: TestClient,
):
    old_category_id = _category(client, "Исходная категория операции")
    receipt_category_id = _category(client, "Категория строки операции")
    old_brand_id = _brand(client, "Исходный бренд операции")
    new_brand_id = _brand(client, "Новый бренд операции")
    green_id = _source(client, "Green")
    euroopt_id = _source(client, "Евроопт")
    product = client.post(
        "/api/v1/operations/catalog-products",
        json={
            "name": "Товар операции",
            "brand_id": old_brand_id,
            "category_id": old_category_id,
        },
    ).json()
    product_id = int(product["id"])
    offers = []
    for source_id, name in (
        (green_id, "Товар операции Green"),
        (euroopt_id, "Товар операции Евроопт"),
    ):
        response = client.post(
            "/api/v1/operations/item-templates",
            json={"product_id": product_id, "source_id": source_id, "name": name},
        )
        assert response.status_code == 201, response.text
        offers.append(response.json())

    sibling_operation = _operation(
        client,
        product_id=product_id,
        source_id=euroopt_id,
        name="Товар операции Евроопт",
        price="2.30",
        operation_date="2026-09-03",
        category_id=old_category_id,
    )
    sibling_plan = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "scheduled_date": "2026-10-03",
            "category_id": old_category_id,
            "receipt_items": [
                {
                    "template_id": offers[1]["id"],
                    "product_id": product_id,
                    "source_id": euroopt_id,
                    "category_id": old_category_id,
                    "name": "Товар операции Евроопт",
                    "quantity": "1",
                    "unit_price": "2.30",
                }
            ],
        },
    )
    assert sibling_plan.status_code == 201, sibling_plan.text

    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "operation_date": "2026-09-04",
            "receipt_items": [
                {
                    "template_id": offers[0]["id"],
                    "product_id": product_id,
                    "source_id": green_id,
                    "brand_id": new_brand_id,
                    "category_id": receipt_category_id,
                    "name": "Товар операции Green",
                    "quantity": "1",
                    "unit_price": "2.40",
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["receipt_items"][0]["category_id"] == receipt_category_id

    refreshed = client.get(
        f"/api/v1/operations/catalog-products/{product_id}"
    ).json()
    assert refreshed["brand_id"] == new_brand_id
    assert refreshed["category_id"] == old_category_id
    assert {offer["brand_id"] for offer in refreshed["offers"]} == {new_brand_id}
    assert {offer["last_category_id"] for offer in refreshed["offers"]} == {
        old_category_id
    }

    updated = client.patch(
        f"/api/v1/operations/{created.json()['id']}",
        json={
            "receipt_items": [
                {
                    "template_id": offers[0]["id"],
                    "product_id": product_id,
                    "source_id": green_id,
                    "brand_id": old_brand_id,
                    "category_id": receipt_category_id,
                    "category_touched": True,
                    "name": "Товар операции Green",
                    "quantity": "1",
                    "unit_price": "2.40",
                }
            ]
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["receipt_items"][0]["category_id"] == receipt_category_id

    refreshed = client.get(
        f"/api/v1/operations/catalog-products/{product_id}"
    ).json()
    assert refreshed["brand_id"] == old_brand_id
    assert refreshed["category_id"] == receipt_category_id
    assert {offer["brand_id"] for offer in refreshed["offers"]} == {old_brand_id}
    assert {offer["last_category_id"] for offer in refreshed["offers"]} == {
        receipt_category_id
    }
    refreshed_sibling_operation = client.get(
        f"/api/v1/operations/{sibling_operation['id']}"
    ).json()
    assert refreshed_sibling_operation["category_id"] == receipt_category_id
    assert (
        refreshed_sibling_operation["receipt_items"][0]["category_id"]
        == receipt_category_id
    )
    refreshed_sibling_plan = client.get(
        f"/api/v1/plans/{sibling_plan.json()['id']}"
    ).json()
    assert refreshed_sibling_plan["category_id"] == receipt_category_id
    assert (
        refreshed_sibling_plan["receipt_items"][0]["category_id"]
        == receipt_category_id
    )


def test_plan_receipt_edits_follow_canonical_metadata_touch_semantics(
    client: TestClient,
):
    old_category_id = _category(client, "Исходная категория плана")
    receipt_category_id = _category(client, "Категория строки плана")
    old_brand_id = _brand(client, "Исходный бренд плана")
    new_brand_id = _brand(client, "Новый бренд плана")
    source_id = _source(client, "Санта")
    product = client.post(
        "/api/v1/operations/catalog-products",
        json={
            "name": "Товар плана",
            "brand_id": old_brand_id,
            "category_id": old_category_id,
        },
    ).json()
    product_id = int(product["id"])
    offer_response = client.post(
        "/api/v1/operations/item-templates",
        json={
            "product_id": product_id,
            "source_id": source_id,
            "name": "Товар плана Санта",
        },
    )
    assert offer_response.status_code == 201, offer_response.text
    offer_id = int(offer_response.json()["id"])
    receipt_item = {
        "template_id": offer_id,
        "product_id": product_id,
        "source_id": source_id,
        "brand_id": new_brand_id,
        "category_id": receipt_category_id,
        "name": "Товар плана Санта",
        "quantity": "1",
        "unit_price": "3.10",
    }

    created = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "scheduled_date": "2026-10-04",
            "receipt_items": [receipt_item],
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["receipt_items"][0]["category_id"] == receipt_category_id
    refreshed = client.get(
        f"/api/v1/operations/catalog-products/{product_id}"
    ).json()
    assert refreshed["brand_id"] == new_brand_id
    assert refreshed["category_id"] == old_category_id

    updated = client.patch(
        f"/api/v1/plans/{created.json()['id']}",
        json={
            "receipt_items": [
                {
                    **receipt_item,
                    "brand_id": old_brand_id,
                    "category_touched": True,
                }
            ]
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["receipt_items"][0]["category_id"] == receipt_category_id
    refreshed = client.get(
        f"/api/v1/operations/catalog-products/{product_id}"
    ).json()
    assert refreshed["brand_id"] == old_brand_id
    assert refreshed["category_id"] == receipt_category_id
    assert refreshed["offers"][0]["brand_id"] == old_brand_id
    assert refreshed["offers"][0]["last_category_id"] == receipt_category_id


def test_receipt_category_snapshot_cannot_reference_another_users_category(
    client: TestClient,
):
    app.dependency_overrides[get_current_user_id] = lambda: 2
    foreign_category_id = _category(client, "Чужая категория")
    app.dependency_overrides[get_current_user_id] = lambda: 1

    response = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "operation_date": "2026-09-04",
            "receipt_items": [
                {
                    "category_id": foreign_category_id,
                    "name": "Товар с чужой категорией",
                    "quantity": "1",
                    "unit_price": "1.00",
                }
            ],
        },
    )
    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Category not found"
