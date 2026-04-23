from fastapi.testclient import TestClient

from app.main import app


def test_health_response_exposes_request_id_header():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


def test_request_id_header_is_preserved_when_provided_by_client():
    client = TestClient(app)

    response = client.get("/health", headers={"X-Request-ID": "req-123"})

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "req-123"


def test_frontend_entrypoint_and_scripts_revalidate_after_deploy():
    client = TestClient(app)

    index_response = client.get("/")
    script_response = client.get("/static/js/app-features-dashboard.js")

    assert index_response.status_code == 200
    assert index_response.headers.get("Cache-Control") == "no-cache"
    assert script_response.status_code == 200
    assert script_response.headers.get("Cache-Control") == "no-cache"


def test_api_request_completion_is_logged_with_request_context(caplog):
    client = TestClient(app)

    with caplog.at_level("INFO", logger="financial_assistant.api"):
        response = client.get("/health", headers={"X-Request-ID": "req-log"})

    assert response.status_code == 200
    messages = [record.getMessage() for record in caplog.records if record.name == "financial_assistant.api"]
    assert any("api_request_completed" in message for message in messages)
    assert any("path=/health" in message for message in messages)
    assert any("status_code=200" in message for message in messages)
    assert any("request_id=req-log" in message for message in messages)
