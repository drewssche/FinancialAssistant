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


def test_create_category_then_create_operation_with_it(client: TestClient):
    created_category = client.post(
        "/api/v1/categories",
        json={"name": "Еда", "kind": "expense"},
    )
    assert created_category.status_code == 200
    category_id = created_category.json()["id"]

    created_operation = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "111.00",
            "operation_date": "2026-03-04",
            "note": "Обед",
            "category_id": category_id,
        },
    )
    assert created_operation.status_code == 201
    assert created_operation.json()["category_id"] == category_id

    filtered = client.get(
        "/api/v1/operations",
        params={"category_id": category_id, "page": 1, "page_size": 10},
    )
    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["total"] == 1
    assert payload["items"][0]["category_id"] == category_id


def test_group_update_changes_category_group_fields_in_list(client: TestClient):
    created_group = client.post(
        "/api/v1/categories/groups",
        json={"name": "Продукты", "kind": "expense", "accent_color": "#44aa66"},
    )
    assert created_group.status_code == 200
    group_id = created_group.json()["id"]

    created_category = client.post(
        "/api/v1/categories",
        json={"name": "Фрукты", "kind": "expense", "group_id": group_id},
    )
    assert created_category.status_code == 200
    category_id = created_category.json()["id"]

    updated_group = client.patch(
        f"/api/v1/categories/groups/{group_id}",
        json={"name": "Супермаркет", "accent_color": "#229955"},
    )
    assert updated_group.status_code == 200

    listed = client.get("/api/v1/categories")
    assert listed.status_code == 200
    updated_category = next(item for item in listed.json() if item["id"] == category_id)
    assert updated_category["group_id"] == group_id
    assert updated_category["group_name"] == "Супермаркет"
    assert updated_category["group_accent_color"] == "#229955"


def test_deleted_category_restore_preserves_visual_and_statistics_fields(client: TestClient):
    group = client.post(
        "/api/v1/categories/groups",
        json={"name": "Optional", "kind": "expense", "accent_color": "#336699"},
    )
    assert group.status_code == 200, group.text
    category = client.post(
        "/api/v1/categories",
        json={
            "name": "Hidden expense",
            "kind": "expense",
            "group_id": group.json()["id"],
            "icon": "ticket",
            "include_in_statistics": False,
        },
    )
    assert category.status_code == 200, category.text
    category_id = category.json()["id"]
    operation = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "12.00",
            "operation_date": "2026-03-06",
            "category_id": category_id,
        },
    )
    assert operation.status_code == 201, operation.text

    deleted = client.delete(f"/api/v1/categories/{category_id}")
    assert deleted.status_code == 204, deleted.text
    restored = client.post(f"/api/v1/categories/{category_id}/restore")
    assert restored.status_code == 200, restored.text
    payload = restored.json()
    assert payload["id"] == category_id
    assert payload["group_id"] == group.json()["id"]
    assert payload["icon"] == "ticket"
    assert payload["include_in_statistics"] is False

    restored_operation = client.get(f"/api/v1/operations/{operation.json()['id']}")
    assert restored_operation.status_code == 200, restored_operation.text
    assert restored_operation.json()["category_id"] == category_id
    assert client.post(f"/api/v1/categories/{category_id}/restore").status_code == 409
