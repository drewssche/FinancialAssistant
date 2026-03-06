from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from time import monotonic

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user_id
from app.core.cache import reset_cache_for_tests
from app.core.metrics import get_dashboard_summary_metrics, reset_metrics_for_tests
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db
from app.main import app


@dataclass
class ScenarioResult:
    name: str
    requests: dict[str, int]
    cache_hit_ratio: float
    latency_p50_ms: float
    latency_p95_ms: float


def _bootstrap_client() -> tuple[TestClient, sessionmaker, object]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1

    with session_local() as db:
        db.add(User(id=1, display_name="Scenario", status="active"))
        db.commit()

    return TestClient(app), session_local, engine


def _seed_data(client: TestClient) -> None:
    for idx in range(20):
        payload = {
            "kind": "income" if idx % 4 == 0 else "expense",
            "amount": f"{120 + idx * 3:.2f}",
            "operation_date": date(2026, 2 + (idx % 2), 1 + (idx % 20)).isoformat(),
            "note": f"seed op {idx}",
        }
        response = client.post("/api/v1/operations", json=payload)
        assert response.status_code == 201, response.text

    for payload in [
        {
            "counterparty": "Иван",
            "direction": "lend",
            "principal": "800.00",
            "start_date": "2026-03-01",
            "note": "ремонт",
        },
        {
            "counterparty": "Мария",
            "direction": "borrow",
            "principal": "450.00",
            "start_date": "2026-03-02",
            "note": "аренда",
        },
    ]:
        response = client.post("/api/v1/debts", json=payload)
        assert response.status_code == 201, response.text


def _collect(name: str) -> ScenarioResult:
    metrics = get_dashboard_summary_metrics()
    return ScenarioResult(
        name=name,
        requests=metrics.get("endpoint_request_totals", {}),
        cache_hit_ratio=float(metrics.get("cache_hit_ratio", 0.0)),
        latency_p50_ms=float(metrics.get("latency_total", {}).get("p50_ms", 0.0)),
        latency_p95_ms=float(metrics.get("latency_total", {}).get("p95_ms", 0.0)),
    )


def _reset_runtime() -> None:
    reset_cache_for_tests()
    reset_metrics_for_tests()


class FrontReadThroughCache:
    def __init__(self) -> None:
        self._items: dict[str, tuple[float, object]] = {}

    def get(self, key: str, ttl_ms: int) -> object | None:
        item = self._items.get(key)
        if not item:
            return None
        ts, payload = item
        age_ms = (monotonic() - ts) * 1000
        if age_ms > ttl_ms:
            self._items.pop(key, None)
            return None
        return payload

    def set(self, key: str, payload: object) -> None:
        self._items[key] = (monotonic(), payload)

    def invalidate(self, prefix: str) -> None:
        for key in list(self._items.keys()):
            if key.startswith(f"{prefix}:"):
                self._items.pop(key, None)


def _frontend_get(
    client: TestClient,
    cache: FrontReadThroughCache | None,
    key: str,
    ttl_ms: int,
    path: str,
    params: dict,
):
    if cache:
        cached = cache.get(key, ttl_ms)
        if cached is not None:
            return cached
    response = client.get(path, params=params)
    assert response.status_code == 200, response.text
    payload = response.json()
    if cache:
        cache.set(key, payload)
    return payload


def _scenario_dashboard_open(client: TestClient) -> ScenarioResult:
    _reset_runtime()
    assert client.get("/api/v1/dashboard/summary", params={"period": "month"}).status_code == 200
    assert client.get("/api/v1/debts/cards", params={"include_closed": False}).status_code == 200
    assert client.get("/api/v1/operations", params={"page": 1, "page_size": 8}).status_code == 200
    return _collect("Open Dashboard")


def _scenario_operations_search(client: TestClient) -> ScenarioResult:
    _reset_runtime()
    assert (
        client.get(
            "/api/v1/operations",
            params={"page": 1, "page_size": 20, "sort_by": "operation_date", "sort_dir": "desc", "q": "seed op 1"},
        ).status_code
        == 200
    )
    return _collect("Operations Search")


def _scenario_create_operation(client: TestClient) -> ScenarioResult:
    _reset_runtime()
    response = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "amount": "321.00",
            "operation_date": "2026-03-06",
            "note": "scenario create",
        },
    )
    assert response.status_code == 201, response.text
    assert client.get("/api/v1/dashboard/summary", params={"period": "month"}).status_code == 200
    assert client.get("/api/v1/operations", params={"page": 1, "page_size": 20}).status_code == 200
    assert client.get("/api/v1/operations", params={"page": 1, "page_size": 8}).status_code == 200
    return _collect("Create Operation + Refresh")


def _scenario_debts_search(client: TestClient) -> ScenarioResult:
    _reset_runtime()
    assert client.get("/api/v1/debts/cards", params={"include_closed": False, "q": "иван"}).status_code == 200
    return _collect("Debts Search")


def _scenario_section_switch_no_front_cache(client: TestClient) -> ScenarioResult:
    _reset_runtime()
    flow = [
        ("GET", "/api/v1/operations", {"page": 1, "page_size": 20, "sort_by": "operation_date", "sort_dir": "desc"}),
        ("GET", "/api/v1/debts/cards", {"include_closed": False}),
        ("GET", "/api/v1/categories/groups", {}),
        ("GET", "/api/v1/categories", {}),
        ("GET", "/api/v1/categories", {"page": 1, "page_size": 20}),
        ("GET", "/api/v1/operations", {"page": 1, "page_size": 20, "sort_by": "operation_date", "sort_dir": "desc"}),
        ("GET", "/api/v1/debts/cards", {"include_closed": False}),
        ("GET", "/api/v1/categories/groups", {}),
        ("GET", "/api/v1/categories", {}),
        ("GET", "/api/v1/categories", {"page": 1, "page_size": 20}),
    ]
    for _method, path, params in flow:
        response = client.get(path, params=params)
        assert response.status_code == 200, response.text
    return _collect("Section Switch (No Front Cache)")


def _scenario_section_switch_front_cache(client: TestClient) -> ScenarioResult:
    _reset_runtime()
    cache = FrontReadThroughCache()
    _frontend_get(
        client,
        cache,
        "operations:list:page=1&page_size=20&sort_by=operation_date&sort_dir=desc",
        15000,
        "/api/v1/operations",
        {"page": 1, "page_size": 20, "sort_by": "operation_date", "sort_dir": "desc"},
    )
    _frontend_get(
        client,
        cache,
        "debts:cards:include_closed=false:q=",
        20000,
        "/api/v1/debts/cards",
        {"include_closed": False},
    )
    _frontend_get(
        client,
        cache,
        "categories:groups",
        60000,
        "/api/v1/categories/groups",
        {},
    )
    _frontend_get(
        client,
        cache,
        "categories:catalog",
        60000,
        "/api/v1/categories",
        {},
    )
    _frontend_get(
        client,
        cache,
        "categories:table:page=1&page_size=20",
        45000,
        "/api/v1/categories",
        {"page": 1, "page_size": 20},
    )
    _frontend_get(
        client,
        cache,
        "operations:list:page=1&page_size=20&sort_by=operation_date&sort_dir=desc",
        15000,
        "/api/v1/operations",
        {"page": 1, "page_size": 20, "sort_by": "operation_date", "sort_dir": "desc"},
    )
    _frontend_get(
        client,
        cache,
        "debts:cards:include_closed=false:q=",
        20000,
        "/api/v1/debts/cards",
        {"include_closed": False},
    )
    _frontend_get(
        client,
        cache,
        "categories:groups",
        60000,
        "/api/v1/categories/groups",
        {},
    )
    _frontend_get(
        client,
        cache,
        "categories:catalog",
        60000,
        "/api/v1/categories",
        {},
    )
    _frontend_get(
        client,
        cache,
        "categories:table:page=1&page_size=20",
        45000,
        "/api/v1/categories",
        {"page": 1, "page_size": 20},
    )
    return _collect("Section Switch (Front Cache TTL)")


def main() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    client, session_local, engine = _bootstrap_client()
    try:
        _seed_data(client)
        scenarios = [
            _scenario_dashboard_open(client),
            _scenario_operations_search(client),
            _scenario_create_operation(client),
            _scenario_debts_search(client),
            _scenario_section_switch_no_front_cache(client),
            _scenario_section_switch_front_cache(client),
        ]
        print("# Request Count Per Action (backend)")
        print("")
        print("| Scenario | Request totals | cache_hit_ratio | p50(ms) | p95(ms) |")
        print("| --- | --- | ---: | ---: | ---: |")
        for item in scenarios:
            requests = ", ".join(f"`{k}`={v}" for k, v in sorted(item.requests.items()))
            print(
                f"| {item.name} | {requests or '-'} | {item.cache_hit_ratio:.4f} | "
                f"{item.latency_p50_ms:.3f} | {item.latency_p95_ms:.3f} |"
            )
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


if __name__ == "__main__":
    main()
