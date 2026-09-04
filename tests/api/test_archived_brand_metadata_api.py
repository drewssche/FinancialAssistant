from fastapi.testclient import TestClient

from tests.api.test_operations_api import _client_lifecycle


def _create_brand(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/operations/item-brands",
        json={"name": "Исторический бренд", "accent_color": "#445566"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_archived_brand_status_survives_historical_api_payloads():
    lifecycle = _client_lifecycle()
    client = next(lifecycle)
    try:
        brand = _create_brand(client)
        operation = client.post(
            "/api/v1/operations",
            json={
                "kind": "expense",
                "amount": "5.00",
                "operation_date": "2026-03-05",
                "receipt_items": [
                    {
                        "shop_name": "Green",
                        "name": "Историческая позиция",
                        "brand_id": brand["id"],
                        "quantity": "1",
                        "unit_price": "5.00",
                    }
                ],
            },
        )
        assert operation.status_code == 201, operation.text
        operation_id = operation.json()["id"]
        template_id = operation.json()["receipt_items"][0]["template_id"]

        plan = client.post(
            "/api/v1/plans",
            json={
                "kind": "expense",
                "scheduled_date": "2026-04-05",
                "receipt_items": [
                    {
                        "template_id": template_id,
                        "shop_name": "Green",
                        "name": "Историческая позиция",
                        "quantity": "1",
                        "unit_price": "5.00",
                    }
                ],
            },
        )
        assert plan.status_code == 201, plan.text

        assert client.delete(f"/api/v1/operations/item-brands/{brand['id']}").status_code == 204

        detail = client.get(f"/api/v1/operations/item-brands/{brand['id']}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["is_archived"] is True

        historical_receipt = client.get(f"/api/v1/operations/{operation_id}").json()["receipt_items"][0]
        planned_receipt = client.get(f"/api/v1/plans/{plan.json()['id']}").json()["receipt_items"][0]
        assert historical_receipt["brand_is_archived"] is True
        assert planned_receipt["brand_is_archived"] is True

        templates = client.get(
            "/api/v1/operations/item-templates",
            params={"brand_id": brand["id"], "page_size": 100},
        )
        assert templates.status_code == 200, templates.text
        assert templates.json()["items"][0]["brand_is_archived"] is True

        analytics = client.get(
            "/api/v1/dashboard/analytics/highlights",
            params={"month": "2026-03", "category_breakdown_level": "brand"},
        )
        assert analytics.status_code == 200, analytics.text
        brand_bucket = next(
            item
            for item in analytics.json()["category_breakdown"]
            if item["brand_id"] == brand["id"]
        )
        assert brand_bucket["brand_is_archived"] is True
    finally:
        client.close()
        try:
            next(lifecycle)
        except StopIteration:
            pass
