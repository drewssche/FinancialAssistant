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
