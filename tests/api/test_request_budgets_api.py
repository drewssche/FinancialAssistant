from datetime import date
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user_id
from app.core.cache import reset_cache_for_tests
from app.core.metrics import get_http_request_totals, reset_metrics_for_tests
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db
from app.main import app

_DOCS_REQUEST_BUDGETS_PATH = Path(__file__).resolve().parents[2] / "docs" / "REQUEST_BUDGETS.md"


def _load_request_budgets() -> dict[str, dict[str, int]]:
    content = _DOCS_REQUEST_BUDGETS_PATH.read_text(encoding="utf-8")
    start_marker = "<!-- REQUEST_BUDGETS_JSON_START -->"
    end_marker = "<!-- REQUEST_BUDGETS_JSON_END -->"
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    assert start_idx >= 0 and end_idx > start_idx, "REQUEST_BUDGETS markers not found in docs/REQUEST_BUDGETS.md"
    block = content[start_idx + len(start_marker) : end_idx]
    json_start = block.find("{")
    json_end = block.rfind("}")
    assert json_start >= 0 and json_end > json_start, "REQUEST_BUDGETS json block is invalid"
    payload = json.loads(block[json_start : json_end + 1])
    assert isinstance(payload, dict), "REQUEST_BUDGETS payload must be an object"
    return payload


REQUEST_BUDGETS = _load_request_budgets()


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
    db.add(User(id=1, display_name="Budget", status="active"))
    db.commit()
    db.close()

    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def reset_runtime_metrics():
    reset_cache_for_tests()
    reset_metrics_for_tests()
    yield
    reset_cache_for_tests()
    reset_metrics_for_tests()


def _seed_minimal_data(client: TestClient) -> None:
    for idx in range(8):
        response = client.post(
            "/api/v1/operations",
            json={
                "kind": "income" if idx % 2 == 0 else "expense",
                "amount": f"{100 + idx:.2f}",
                "operation_date": date(2026, 3, 1 + idx).isoformat(),
                "note": f"seed {idx}",
            },
        )
        assert response.status_code == 201
    response = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Иван",
            "direction": "lend",
            "principal": "500.00",
            "start_date": "2026-03-01",
            "note": "seed debt",
        },
    )
    assert response.status_code == 201


def _run_section_switch_flow(client: TestClient, with_front_cache: bool) -> None:
    flow = [
        ("operations:list", "/api/v1/operations", {"page": 1, "page_size": 20, "sort_by": "operation_date", "sort_dir": "desc"}),
        ("debts:cards", "/api/v1/debts/cards", {"include_closed": False}),
        ("categories:groups", "/api/v1/categories/groups", {}),
        ("categories:catalog", "/api/v1/categories", {}),
        ("categories:table", "/api/v1/categories", {"page": 1, "page_size": 20}),
        ("operations:list", "/api/v1/operations", {"page": 1, "page_size": 20, "sort_by": "operation_date", "sort_dir": "desc"}),
        ("debts:cards", "/api/v1/debts/cards", {"include_closed": False}),
        ("categories:groups", "/api/v1/categories/groups", {}),
        ("categories:catalog", "/api/v1/categories", {}),
        ("categories:table", "/api/v1/categories", {"page": 1, "page_size": 20}),
    ]
    front_cache: dict[str, object] = {}
    for cache_key, path, params in flow:
        if with_front_cache and cache_key in front_cache:
            continue
        response = client.get(path, params=params)
        assert response.status_code == 200
        if with_front_cache:
            front_cache[cache_key] = response.json()


def _assert_budget(totals: dict[str, int], scenario_key: str) -> None:
    budget = REQUEST_BUDGETS[scenario_key]
    for endpoint, ceiling in budget.items():
        assert totals.get(endpoint, 0) <= ceiling


def test_request_budget_open_dashboard(client: TestClient):
    _seed_minimal_data(client)
    reset_cache_for_tests()
    reset_metrics_for_tests()

    assert client.get("/api/v1/dashboard/summary", params={"period": "month"}).status_code == 200
    assert client.get("/api/v1/debts/cards", params={"include_closed": False}).status_code == 200
    assert client.get("/api/v1/operations", params={"page": 1, "page_size": 8}).status_code == 200

    totals = get_http_request_totals()
    _assert_budget(totals, "open_dashboard")


def test_request_budget_operations_search(client: TestClient):
    _seed_minimal_data(client)
    reset_cache_for_tests()
    reset_metrics_for_tests()

    response = client.get(
        "/api/v1/operations",
        params={"page": 1, "page_size": 20, "sort_by": "operation_date", "sort_dir": "desc", "q": "seed 1"},
    )
    assert response.status_code == 200

    totals = get_http_request_totals()
    _assert_budget(totals, "operations_search")


def test_request_budget_create_operation_refresh_flow(client: TestClient):
    _seed_minimal_data(client)
    reset_cache_for_tests()
    reset_metrics_for_tests()

    created = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "333.00",
            "operation_date": "2026-03-06",
            "note": "budget create",
        },
    )
    assert created.status_code == 201
    assert client.get("/api/v1/dashboard/summary", params={"period": "month"}).status_code == 200
    assert client.get("/api/v1/operations", params={"page": 1, "page_size": 20}).status_code == 200
    assert client.get("/api/v1/operations", params={"page": 1, "page_size": 8}).status_code == 200

    totals = get_http_request_totals()
    _assert_budget(totals, "create_operation_refresh")


def test_request_budget_debts_search(client: TestClient):
    _seed_minimal_data(client)
    reset_cache_for_tests()
    reset_metrics_for_tests()

    response = client.get("/api/v1/debts/cards", params={"include_closed": False, "q": "иван"})
    assert response.status_code == 200

    totals = get_http_request_totals()
    _assert_budget(totals, "debts_search")


def test_request_budget_section_switch_no_front_cache(client: TestClient):
    _seed_minimal_data(client)
    reset_cache_for_tests()
    reset_metrics_for_tests()

    _run_section_switch_flow(client, with_front_cache=False)

    totals = get_http_request_totals()
    _assert_budget(totals, "section_switch_no_front_cache")


def test_request_budget_section_switch_front_cache_ttl(client: TestClient):
    _seed_minimal_data(client)
    reset_cache_for_tests()
    reset_metrics_for_tests()

    _run_section_switch_flow(client, with_front_cache=True)

    totals = get_http_request_totals()
    _assert_budget(totals, "section_switch_front_cache_ttl")
