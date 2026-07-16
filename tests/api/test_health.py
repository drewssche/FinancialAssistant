from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

import app.main as main_module
from app.main import app, readiness_check


def test_health_check():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_requires_current_database_revision(monkeypatch):
    class ReadyDb:
        def execute(self, _statement):
            return None

        def scalar(self, _statement):
            return "head-1"

    monkeypatch.setattr(main_module, "expected_database_revision", "head-1")
    assert readiness_check(ReadyDb()) == {
        "status": "ready",
        "database": "ok",
        "revision": "head-1",
    }


def test_readiness_reports_database_failure_without_details():
    class FailedDb:
        def execute(self, _statement):
            raise OperationalError("SELECT 1", {}, RuntimeError("connection failed"))

    response = readiness_check(FailedDb())
    assert response.status_code == 503
    assert b'"database":"unavailable"' in response.body
