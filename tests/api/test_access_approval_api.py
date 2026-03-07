from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.db.models import User
from app.main import app


def test_pending_user_cannot_access_preferences():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: User(id=101, display_name="P", status="pending")
    client = TestClient(app)
    response = client.get("/api/v1/preferences")
    assert response.status_code == 403
    assert "approved" in response.json()["detail"].lower()
    app.dependency_overrides.clear()
