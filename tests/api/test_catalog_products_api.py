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
        db.add(User(id=1, display_name="Tester", status="active"))
        db.commit()

    yield TestClient(app)

    reset_cache_for_tests()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _source(client: TestClient, name: str) -> int:
    response = client.post("/api/v1/operations/item-sources", json={"name": name})
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def _offer(
    client: TestClient,
    *,
    source_id: int,
    name: str,
    price: str,
    product_id: int | None = None,
) -> dict:
    payload = {
        "source_id": source_id,
        "name": name,
        "latest_unit_price": price,
        "latest_price_date": "2026-09-04",
    }
    if product_id is not None:
        payload["product_id"] = product_id
    response = client.post("/api/v1/operations/item-templates", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_product_aggregates_source_offers_and_latest_prices(client: TestClient):
    green_id = _source(client, "Green")
    euroopt_id = _source(client, "Евроопт")
    created = client.post(
        "/api/v1/operations/catalog-products",
        json={"name": "Сырок клубника 40 г"},
    )
    assert created.status_code == 201, created.text
    product_id = int(created.json()["id"])

    _offer(
        client,
        product_id=product_id,
        source_id=green_id,
        name="Сырок клубника 40г",
        price="0.82",
    )
    _offer(
        client,
        product_id=product_id,
        source_id=euroopt_id,
        name="Сырок с печеньем клубника 40 г",
        price="0.81",
    )

    response = client.get(f"/api/v1/operations/catalog-products/{product_id}")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["offers_count"] == 2
    assert payload["sources_count"] == 2
    assert payload["min_unit_price"] == "0.81"
    assert payload["max_unit_price"] == "0.82"
    assert {item["source_name"] for item in payload["offers"]} == {
        "Green",
        "Евроопт",
    }
    assert {item["product_id"] for item in payload["offers"]} == {product_id}


def test_exact_candidates_merge_and_detach_preserve_offer_prices(client: TestClient):
    green_id = _source(client, "Green")
    euroopt_id = _source(client, "Евроопт")
    first = _offer(
        client,
        source_id=green_id,
        name="Один товар 40г",
        price="1.20",
    )
    second = _offer(
        client,
        source_id=euroopt_id,
        name="Один товар 40г",
        price="1.10",
    )
    first_product_id = int(first["product_id"])
    second_product_id = int(second["product_id"])
    assert first_product_id != second_product_id

    candidates = client.get(
        "/api/v1/operations/catalog-products/merge-candidates"
    )
    assert candidates.status_code == 200, candidates.text
    assert candidates.json()["total"] == 1
    assert {
        product["id"] for product in candidates.json()["items"][0]["products"]
    } == {first_product_id, second_product_id}

    merged = client.post(
        f"/api/v1/operations/catalog-products/{first_product_id}/merge",
        json={"source_product_ids": [second_product_id]},
    )
    assert merged.status_code == 200, merged.text
    assert merged.json()["reassigned_offers"] == 1
    assert merged.json()["product"]["offers_count"] == 2

    detached = client.post(
        f"/api/v1/operations/catalog-products/{first_product_id}"
        f"/offers/{second['id']}/detach",
        json={},
    )
    assert detached.status_code == 200, detached.text
    detached_product = detached.json()["product"]
    assert detached_product["offers_count"] == 1
    prices = client.get(
        f"/api/v1/operations/item-templates/{second['id']}/prices"
    )
    assert prices.status_code == 200, prices.text
    assert [item["unit_price"] for item in prices.json()] == ["1.10"]

    archived_offer = client.delete(
        f"/api/v1/operations/item-templates/{second['id']}"
    )
    assert archived_offer.status_code == 204, archived_offer.text
    cannot_detach_archived = client.post(
        f"/api/v1/operations/catalog-products/{detached_product['id']}"
        f"/offers/{second['id']}/detach",
        json={},
    )
    assert cannot_detach_archived.status_code == 404


def test_add_source_to_product_preserves_metadata_and_rejects_duplicate_source(client: TestClient):
    green = _source(client, "Green")
    brand = client.post("/api/v1/operations/item-brands", json={"name": "Молочная страна"}).json()
    product = client.post("/api/v1/operations/catalog-products", json={
        "name": "Сырок клубника 40г", "brand_id": brand["id"],
    }).json()
    url = f"/api/v1/operations/catalog-products/{product['id']}/offers"
    first = client.post(url, json={
        "source_id": green, "latest_unit_price": "0.82", "latest_price_date": "2026-09-03",
    })
    assert first.status_code == 201, first.text
    assert first.json()["product_id"] == product["id"]
    assert first.json()["brand_id"] == brand["id"]
    assert first.json()["name"] == product["name"]
    second = client.post(url, json={"shop_name": "Санта"})
    assert second.status_code == 201, second.text
    assert second.json()["latest_unit_price"] is None
    assert second.json()["use_count"] == 0
    for source_payload in ({"source_id": green}, {"shop_name": " green "}):
        duplicate = client.post(url, json={
            **source_payload, "latest_unit_price": "9.99", "latest_price_date": "2026-09-06",
        })
        assert duplicate.status_code == 400
        assert "уже добавлен" in duplicate.json()["detail"]
    prices = client.get(f"/api/v1/operations/item-templates/{first.json()['id']}/prices").json()
    assert [item["unit_price"] for item in prices] == ["0.82"]
    result = client.get(f"/api/v1/operations/catalog-products/{product['id']}").json()
    assert result["sources_count"] == result["offers_count"] == 2
    assert {offer["product_id"] for offer in result["offers"]} == {product["id"]}
    assert client.get("/api/v1/operations/catalog-products").json()["total"] == 1
    assert client.get("/api/v1/operations").json()["total"] == 0


def test_add_product_source_validates_owner_and_conflicting_legacy_product(client: TestClient):
    green = _source(client, "Green")
    existing = _offer(client, source_id=green, name="Сырок 40г", price="0.82")
    product = client.post("/api/v1/operations/catalog-products", json={"name": "Сырок 40г"}).json()
    url = f"/api/v1/operations/catalog-products/{product['id']}/offers"
    conflict = client.post(url, json={"source_id": green})
    assert conflict.status_code == 400
    assert "объедините" in conflict.json()["detail"]
    assert client.get(f"/api/v1/operations/item-templates/{existing['id']}").json()["product_id"] == existing["product_id"]
    assert client.post(url, json={}).status_code == 400
    assert client.post(url, json={"shop_name": "Санта", "latest_unit_price": "0.82"}).status_code == 400
    assert client.post(url, json={"shop_name": "Санта", "latest_unit_price": "0"}).status_code == 422
    assert client.get(f"/api/v1/operations/catalog-products/{product['id']}").json()["offers_count"] == 0
    app.dependency_overrides[get_current_user_id] = lambda: 2
    try:
        assert client.post(url, json={"shop_name": "Санта"}).status_code == 404
    finally:
        app.dependency_overrides[get_current_user_id] = lambda: 1


def test_add_product_source_does_not_duplicate_an_existing_offer_with_a_different_name(client: TestClient):
    green = _source(client, "Green")
    product = client.post("/api/v1/operations/catalog-products", json={"name": "Сырок 40г"}).json()
    _offer(client, source_id=green, product_id=product["id"], name="Сырок клубника 40 грамм", price="0.82")
    result = client.post(f"/api/v1/operations/catalog-products/{product['id']}/offers", json={"source_id": green})
    assert result.status_code == 400
    assert client.get(f"/api/v1/operations/catalog-products/{product['id']}").json()["offers_count"] == 1
