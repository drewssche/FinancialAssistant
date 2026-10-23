import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.db.models import User
from app.main import app


@pytest.mark.parametrize("path", [
    "/preferences", "/operations", "/operations/catalog-products", "/categories",
    "/dashboard/summary", "/plans", "/debts/cards", "/activity", "/admin/users",
])
def test_pending_user_cannot_access_private_data(path):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: User(id=101, display_name="P", status="pending")
    try:
        response = TestClient(app).get("/api/v1" + path)
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
