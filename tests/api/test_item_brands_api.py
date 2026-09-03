from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.main import app
from tests.api.test_operations_api import _client_lifecycle, _override_current_user_id


def _create_brand(client: TestClient, name: str, color: str | None = None) -> dict:
    payload = {"name": name}
    if color is not None:
        payload["accent_color"] = color
    response = client.post("/api/v1/operations/item-brands", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_item_brand_crud_archive_reactivate_merge_and_template_filter():
    lifecycle = _client_lifecycle()
    client = next(lifecycle)
    try:
        vici = _create_brand(client, "  Vici  ", "#12abef")
        assert vici["name"] == "Vici"
        assert vici["accent_color"] == "#12ABEF"
        assert vici["positions_count"] == 0

        duplicate = client.post(
            "/api/v1/operations/item-brands",
            json={"name": "vICI"},
        )
        assert duplicate.status_code == 400

        template = client.post(
            "/api/v1/operations/item-templates",
            json={"shop_name": "Green", "name": "Крабовые палочки", "brand_id": vici["id"]},
        )
        assert template.status_code == 201, template.text
        assert template.json()["brand_id"] == vici["id"]
        assert template.json()["brand_name"] == "Vici"

        filtered = client.get(
            "/api/v1/operations/item-templates",
            params={"brand_id": vici["id"], "page_size": 100},
        )
        assert filtered.status_code == 200
        assert filtered.json()["total"] == 1

        renamed = client.patch(
            f"/api/v1/operations/item-brands/{vici['id']}",
            json={"name": "VICI Foods", "accent_color": None},
        )
        assert renamed.status_code == 200
        assert renamed.json()["positions_count"] == 1
        assert renamed.json()["accent_color"] is None

        target = _create_brand(client, "Seafood")
        merged = client.post(
            f"/api/v1/operations/item-brands/{vici['id']}/merge",
            json={"target_brand_id": target["id"]},
        )
        assert merged.status_code == 200, merged.text
        assert merged.json()["reassigned_positions"] == 1
        assert merged.json()["brand"]["positions_count"] == 1

        archived = client.get(
            "/api/v1/operations/item-brands",
            params={"include_archived": True, "page_size": 100},
        )
        assert archived.status_code == 200
        archived_vici = next(item for item in archived.json()["items"] if item["id"] == vici["id"])
        assert archived_vici["is_archived"] is True

        deleted = client.delete(f"/api/v1/operations/item-brands/{target['id']}")
        assert deleted.status_code == 204
        active = client.get("/api/v1/operations/item-brands", params={"page_size": 100})
        assert active.status_code == 200
        assert active.json()["total"] == 0

        restored = client.post(
            "/api/v1/operations/item-brands",
            json={"name": "seaFOOD", "accent_color": "#001122"},
        )
        assert restored.status_code == 201
        assert restored.json()["id"] == target["id"]
        assert restored.json()["positions_count"] == 1
    finally:
        client.close()
        try:
            next(lifecycle)
        except StopIteration:
            pass


def test_archived_brand_can_only_round_trip_on_its_existing_catalog_position():
    lifecycle = _client_lifecycle()
    client = next(lifecycle)
    try:
        brand = _create_brand(client, "Legacy", "#445566")
        linked = client.post(
            "/api/v1/operations/item-templates",
            json={"shop_name": "Store", "name": "Linked", "brand_id": brand["id"]},
        )
        assert linked.status_code == 201, linked.text
        linked_id = linked.json()["id"]
        unrelated = client.post(
            "/api/v1/operations/item-templates",
            json={"shop_name": "Store", "name": "Unrelated"},
        )
        assert unrelated.status_code == 201, unrelated.text

        assert client.delete(f"/api/v1/operations/item-brands/{brand['id']}").status_code == 204

        unchanged = client.patch(
            f"/api/v1/operations/item-templates/{linked_id}",
            json={"name": "Linked renamed", "brand_id": brand["id"]},
        )
        assert unchanged.status_code == 200, unchanged.text
        assert unchanged.json()["brand_id"] == brand["id"]
        assert unchanged.json()["brand_name"] == "Legacy"

        rejected = client.patch(
            f"/api/v1/operations/item-templates/{unrelated.json()['id']}",
            json={"brand_id": brand["id"]},
        )
        assert rejected.status_code == 400
        assert rejected.json()["detail"] == "Brand not found"

        cleared = client.patch(
            f"/api/v1/operations/item-templates/{linked_id}",
            json={"brand_id": None},
        )
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["brand_id"] is None
        cannot_restore = client.patch(
            f"/api/v1/operations/item-templates/{linked_id}",
            json={"brand_id": brand["id"]},
        )
        assert cannot_restore.status_code == 400
    finally:
        client.close()
        try:
            next(lifecycle)
        except StopIteration:
            pass


def test_item_template_brand_bulk_update_is_atomic_and_records_each_change():
    lifecycle = _client_lifecycle()
    client = next(lifecycle)
    try:
        initial = _create_brand(client, "Initial")
        target = _create_brand(client, "Target", "#225588")
        templates = []
        for name in ("First", "Second"):
            created = client.post(
                "/api/v1/operations/item-templates",
                json={"shop_name": "Store", "name": name, "brand_id": initial["id"]},
            )
            assert created.status_code == 201, created.text
            templates.append(created.json())

        updated = client.post(
            "/api/v1/operations/item-templates/bulk-brand",
            json={
                "template_ids": [templates[0]["id"], templates[1]["id"], templates[0]["id"]],
                "brand_id": target["id"],
            },
        )
        assert updated.status_code == 200, updated.text
        assert updated.json() == {"updated": 2}

        catalog = client.get("/api/v1/operations/item-templates", params={"page_size": 100})
        assert catalog.status_code == 200
        by_id = {item["id"]: item for item in catalog.json()["items"]}
        assert {by_id[item["id"]]["brand_id"] for item in templates} == {target["id"]}
        assert {by_id[item["id"]]["brand_name"] for item in templates} == {"Target"}

        for item in templates:
            journal = client.get(
                "/api/v1/activity",
                params={"entity_type": "item_template", "entity_id": item["id"], "page_size": 20},
            )
            assert journal.status_code == 200
            bulk_events = [
                event
                for event in journal.json()["items"]
                if event["title"] == "Бренд позиции каталога изменён"
            ]
            assert len(bulk_events) == 1
            assert bulk_events[0]["metadata"]["bulk"] is True
            assert [change["field"] for change in bulk_events[0]["changes"]] == ["brand_id"]

        cleared = client.post(
            "/api/v1/operations/item-templates/bulk-brand",
            json={"template_ids": [item["id"] for item in templates], "brand_id": None},
        )
        assert cleared.status_code == 200, cleared.text
        assert cleared.json() == {"updated": 2}
    finally:
        client.close()
        try:
            next(lifecycle)
        except StopIteration:
            pass


def test_item_template_brand_bulk_update_validates_whole_user_scope_and_active_brand_before_writes():
    lifecycle = _client_lifecycle()
    client = next(lifecycle)
    try:
        initial = _create_brand(client, "Initial")
        target = _create_brand(client, "Target")
        own = client.post(
            "/api/v1/operations/item-templates",
            json={"shop_name": "Store", "name": "Own", "brand_id": initial["id"]},
        )
        assert own.status_code == 201, own.text

        app.dependency_overrides[get_current_user_id] = lambda: 2
        foreign_template = client.post(
            "/api/v1/operations/item-templates",
            json={"shop_name": "Other", "name": "Foreign"},
        )
        assert foreign_template.status_code == 201, foreign_template.text
        foreign_brand = _create_brand(client, "Foreign brand")
        app.dependency_overrides[get_current_user_id] = _override_current_user_id

        rejected_scope = client.post(
            "/api/v1/operations/item-templates/bulk-brand",
            json={
                "template_ids": [own.json()["id"], foreign_template.json()["id"]],
                "brand_id": target["id"],
            },
        )
        assert rejected_scope.status_code == 404

        rejected_foreign_brand = client.post(
            "/api/v1/operations/item-templates/bulk-brand",
            json={"template_ids": [own.json()["id"]], "brand_id": foreign_brand["id"]},
        )
        assert rejected_foreign_brand.status_code == 400
        assert rejected_foreign_brand.json()["detail"] == "Brand not found"

        archived = _create_brand(client, "Archived")
        assert client.delete(f"/api/v1/operations/item-brands/{archived['id']}").status_code == 204
        rejected_archived = client.post(
            "/api/v1/operations/item-templates/bulk-brand",
            json={"template_ids": [own.json()["id"]], "brand_id": archived["id"]},
        )
        assert rejected_archived.status_code == 400
        assert rejected_archived.json()["detail"] == "Brand not found"

        catalog = client.get("/api/v1/operations/item-templates", params={"page_size": 100})
        own_after = next(item for item in catalog.json()["items"] if item["id"] == own.json()["id"])
        assert own_after["brand_id"] == initial["id"]
    finally:
        app.dependency_overrides[get_current_user_id] = _override_current_user_id
        client.close()
        try:
            next(lifecycle)
        except StopIteration:
            pass


def test_reactivating_item_template_with_another_brand_invalidates_operation_cache():
    lifecycle = _client_lifecycle()
    client = next(lifecycle)
    try:
        initial = _create_brand(client, "Old brand")
        target = _create_brand(client, "New brand")
        operation = client.post(
            "/api/v1/operations",
            json={
                "kind": "expense",
                "amount": "4.00",
                "operation_date": "2026-03-10",
                "receipt_items": [
                    {
                        "shop_name": "Store",
                        "name": "Cached item",
                        "brand_id": initial["id"],
                        "quantity": "1",
                        "unit_price": "4.00",
                    }
                ],
            },
        )
        assert operation.status_code == 201, operation.text
        template_id = operation.json()["receipt_items"][0]["template_id"]
        assert client.delete(f"/api/v1/operations/item-templates/{template_id}").status_code == 204

        cached = client.get("/api/v1/operations", params={"page_size": 100})
        assert cached.status_code == 200
        assert cached.json()["items"][0]["receipt_items"][0]["brand_name"] == "Old brand"

        reactivated = client.post(
            "/api/v1/operations/item-templates",
            json={"shop_name": "Store", "name": "Cached item", "brand_id": target["id"]},
        )
        assert reactivated.status_code == 201, reactivated.text
        assert reactivated.json()["id"] == template_id
        assert reactivated.json()["brand_id"] == target["id"]

        refreshed = client.get("/api/v1/operations", params={"page_size": 100})
        assert refreshed.status_code == 200
        assert refreshed.json()["items"][0]["receipt_items"][0]["brand_name"] == "New brand"
    finally:
        client.close()
        try:
            next(lifecycle)
        except StopIteration:
            pass


def test_brand_is_live_in_operations_and_plans_and_brand_filters_work():
    lifecycle = _client_lifecycle()
    client = next(lifecycle)
    try:
        brand = _create_brand(client, "Vici", "#2277AA")
        operation = client.post(
            "/api/v1/operations",
            json={
                "kind": "expense",
                "amount": "5.00",
                "operation_date": "2026-03-05",
                "receipt_items": [
                    {
                        "shop_name": "Green",
                        "name": "Крабовые палочки",
                        "brand_id": brand["id"],
                        "quantity": "1",
                        "unit_price": "5.00",
                    }
                ],
            },
        )
        assert operation.status_code == 201, operation.text
        operation_id = operation.json()["id"]
        receipt = operation.json()["receipt_items"][0]
        template_id = receipt["template_id"]
        assert (receipt["brand_id"], receipt["brand_name"], receipt["brand_accent_color"]) == (
            brand["id"],
            "Vici",
            "#2277AA",
        )

        plan = client.post(
            "/api/v1/plans",
            json={
                "kind": "expense",
                "scheduled_date": "2026-04-05",
                "receipt_items": [
                    {
                        "template_id": template_id,
                        "shop_name": "Green",
                        "name": "Крабовые палочки",
                        "quantity": "1",
                        "unit_price": "5.00",
                    }
                ],
            },
        )
        assert plan.status_code == 201, plan.text
        plan_id = plan.json()["id"]
        assert plan.json()["receipt_items"][0]["brand_name"] == "Vici"

        renamed = client.patch(
            f"/api/v1/operations/item-brands/{brand['id']}",
            json={"name": "Vici Group", "accent_color": "#AA5500"},
        )
        assert renamed.status_code == 200
        historical = client.get(f"/api/v1/operations/{operation_id}")
        planned = client.get(f"/api/v1/plans/{plan_id}")
        assert historical.json()["receipt_items"][0]["brand_name"] == "Vici Group"
        assert historical.json()["receipt_items"][0]["brand_accent_color"] == "#AA5500"
        assert planned.json()["receipt_items"][0]["brand_name"] == "Vici Group"

        recommendation_settings = client.patch(
            f"/api/v1/operations/item-templates/{template_id}",
            json={
                "recommendation_enabled": True,
                "recommendation_mode": "manual",
                "recommendation_interval_days": 30,
                "recommendation_base_quantity": "1",
            },
        )
        assert recommendation_settings.status_code == 200, recommendation_settings.text
        recommendations = client.get("/api/v1/operations/item-recommendations")
        managed_recommendations = client.get("/api/v1/operations/item-recommendations/manage")
        assert recommendations.status_code == 200
        assert managed_recommendations.status_code == 200
        recommendation = next(item for item in recommendations.json() if item["template_id"] == template_id)
        managed = next(item for item in managed_recommendations.json() if item["template_id"] == template_id)
        assert recommendation["brand_name"] == "Vici Group"
        assert recommendation["brand_accent_color"] == "#AA5500"
        assert managed["brand_id"] == brand["id"]

        for path in ("/api/v1/operations", "/api/v1/operations/money-flow"):
            filtered = client.get(path, params={"brand_id": brand["id"], "page_size": 100})
            assert filtered.status_code == 200, filtered.text
            assert filtered.json()["total"] == 1
        summary = client.get("/api/v1/operations/summary", params={"brand_id": brand["id"]})
        assert summary.status_code == 200
        assert summary.json()["expense_total"] == "5.00"

        preserved = client.patch(
            f"/api/v1/operations/{operation_id}",
            json={
                "receipt_items": [
                    {
                        "template_id": template_id,
                        "shop_name": "Green",
                        "name": "Крабовые палочки",
                        "quantity": "1",
                        "unit_price": "5.00",
                    }
                ]
            },
        )
        assert preserved.status_code == 200, preserved.text
        assert preserved.json()["receipt_items"][0]["brand_id"] == brand["id"]

        cleared = client.patch(
            f"/api/v1/operations/{operation_id}",
            json={
                "receipt_items": [
                    {
                        "template_id": template_id,
                        "brand_id": None,
                        "shop_name": "Green",
                        "name": "Крабовые палочки",
                        "quantity": "1",
                        "unit_price": "5.00",
                    }
                ]
            },
        )
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["receipt_items"][0]["brand_id"] is None
        assert client.get(f"/api/v1/plans/{plan_id}").json()["receipt_items"][0]["brand_id"] is None
    finally:
        client.close()
        try:
            next(lifecycle)
        except StopIteration:
            pass


def test_receipt_edit_round_trips_archived_brand_and_reactivates_archived_template():
    lifecycle = _client_lifecycle()
    client = next(lifecycle)
    try:
        brand = _create_brand(client, "Legacy")
        operation = client.post(
            "/api/v1/operations",
            json={
                "kind": "expense",
                "amount": "3.00",
                "operation_date": "2026-03-05",
                "receipt_items": [
                    {
                        "shop_name": "Store",
                        "name": "Legacy item",
                        "brand_id": brand["id"],
                        "quantity": "1",
                        "unit_price": "3.00",
                    }
                ],
            },
        )
        assert operation.status_code == 201, operation.text
        operation_id = operation.json()["id"]
        template_id = operation.json()["receipt_items"][0]["template_id"]

        assert client.delete(f"/api/v1/operations/item-brands/{brand['id']}").status_code == 204
        assert client.delete(f"/api/v1/operations/item-templates/{template_id}").status_code == 204

        rejected_assignment = client.post(
            "/api/v1/operations",
            json={
                "kind": "expense",
                "amount": "2.00",
                "operation_date": "2026-03-06",
                "receipt_items": [
                    {
                        "name": "Another item",
                        "brand_id": brand["id"],
                        "quantity": "1",
                        "unit_price": "2.00",
                    }
                ],
            },
        )
        assert rejected_assignment.status_code == 400

        updated = client.patch(
            f"/api/v1/operations/{operation_id}",
            json={
                "receipt_items": [
                    {
                        "template_id": template_id,
                        "brand_id": brand["id"],
                        "shop_name": "Store",
                        "name": "Legacy item",
                        "quantity": "1",
                        "unit_price": "3.00",
                    }
                ]
            },
        )
        assert updated.status_code == 200, updated.text
        receipt = updated.json()["receipt_items"][0]
        assert receipt["brand_id"] == brand["id"]
        assert receipt["brand_name"] == "Legacy"

        templates = client.get(
            "/api/v1/operations/item-templates",
            params={"brand_id": brand["id"], "page_size": 100},
        )
        assert templates.status_code == 200
        assert templates.json()["total"] == 1
    finally:
        client.close()
        try:
            next(lifecycle)
        except StopIteration:
            pass


def test_plan_confirmation_keeps_template_brand_on_created_operation():
    lifecycle = _client_lifecycle()
    client = next(lifecycle)
    try:
        brand = _create_brand(client, "Plan brand", "#336699")
        template = client.post(
            "/api/v1/operations/item-templates",
            json={"shop_name": "Store", "name": "Planned item", "brand_id": brand["id"]},
        )
        assert template.status_code == 201, template.text
        template_id = template.json()["id"]

        plan = client.post(
            "/api/v1/plans",
            json={
                "kind": "expense",
                "scheduled_date": "2026-03-05",
                "receipt_items": [
                    {
                        "template_id": template_id,
                        "shop_name": "Store",
                        "name": "Planned item",
                        "quantity": "1",
                        "unit_price": "5.00",
                    }
                ],
            },
        )
        assert plan.status_code == 201, plan.text

        confirmed = client.post(f"/api/v1/plans/{plan.json()['id']}/confirm")
        assert confirmed.status_code == 200, confirmed.text
        receipt = confirmed.json()["operation"]["receipt_items"][0]
        assert receipt["template_id"] == template_id
        assert receipt["brand_id"] == brand["id"]
        assert receipt["brand_name"] == "Plan brand"
        assert receipt["brand_accent_color"] == "#336699"
    finally:
        client.close()
        try:
            next(lifecycle)
        except StopIteration:
            pass


def test_brand_metrics_and_analytics_allocate_foreign_receipts_in_base_currency():
    lifecycle = _client_lifecycle()
    client = next(lifecycle)
    try:
        first = _create_brand(client, "First", "#112233")
        second = _create_brand(client, "Second", "#445566")
        foreign = client.post(
            "/api/v1/operations",
            json={
                "kind": "expense",
                "amount": "10.00",
                "currency": "EUR",
                "fx_rate": "3.500000",
                "operation_date": "2026-03-05",
                "receipt_items": [
                    {"name": "A1", "brand_id": first["id"], "quantity": "1", "unit_price": "2.00"},
                    {"name": "A2", "brand_id": first["id"], "quantity": "1", "unit_price": "3.00"},
                    {"name": "B1", "brand_id": second["id"], "quantity": "1", "unit_price": "5.00"},
                ],
            },
        )
        assert foreign.status_code == 201, foreign.text
        ordinary = client.post(
            "/api/v1/operations",
            json={
                "kind": "expense",
                "amount": "10.00",
                "operation_date": "2026-03-06",
                "receipt_items": [
                    {"name": "A3", "brand_id": first["id"], "quantity": "1", "unit_price": "6.00"},
                    {"name": "B2", "brand_id": second["id"], "quantity": "1", "unit_price": "6.00"},
                ],
            },
        )
        assert ordinary.status_code == 201, ordinary.text
        non_receipt = client.post(
            "/api/v1/operations",
            json={"kind": "expense", "amount": "100.00", "operation_date": "2026-03-07"},
        )
        assert non_receipt.status_code == 201

        brands = client.get("/api/v1/operations/item-brands", params={"page_size": 100})
        assert brands.status_code == 200
        by_id = {item["id"]: item for item in brands.json()["items"]}
        assert by_id[first["id"]]["positions_count"] == 3
        assert by_id[first["id"]]["purchases_count"] == 2
        assert by_id[first["id"]]["spent_total"] == "22.50"
        assert by_id[second["id"]]["positions_count"] == 2
        assert by_id[second["id"]]["purchases_count"] == 2
        assert by_id[second["id"]]["spent_total"] == "22.50"

        highlights = client.get(
            "/api/v1/dashboard/analytics/highlights",
            params={"month": "2026-03", "category_breakdown_level": "brand"},
        )
        assert highlights.status_code == 200, highlights.text
        payload = highlights.json()
        assert payload["category_breakdown_level"] == "brand"
        assert payload["receipt_amount_total"] == "45.00"
        assert payload["branded_amount_total"] == "45.00"
        assert payload["unbranded_amount_total"] == "0.00"
        assert payload["brand_coverage_pct"] == 100.0
        breakdown = {item["brand_id"]: item for item in payload["category_breakdown"]}
        assert breakdown[first["id"]]["total_amount"] == "22.50"
        assert breakdown[first["id"]]["positions_count"] == 3
        assert breakdown[first["id"]]["purchases_count"] == 2
        assert breakdown[second["id"]]["total_amount"] == "22.50"
        assert sum(float(item["share_pct"]) for item in breakdown.values()) == 100.0
    finally:
        client.close()
        try:
            next(lifecycle)
        except StopIteration:
            pass


def test_brand_analytics_has_unbranded_receipt_bucket_but_excludes_plain_operations():
    lifecycle = _client_lifecycle()
    client = next(lifecycle)
    try:
        brand = _create_brand(client, "Covered")
        receipt = client.post(
            "/api/v1/operations",
            json={
                "kind": "expense",
                "amount": "10.00",
                "operation_date": "2026-03-08",
                "receipt_items": [
                    {"name": "Known", "brand_id": brand["id"], "quantity": "1", "unit_price": "4.00"},
                    {"name": "Unknown", "quantity": "1", "unit_price": "6.00"},
                ],
            },
        )
        plain = client.post(
            "/api/v1/operations",
            json={"kind": "expense", "amount": "90.00", "operation_date": "2026-03-09"},
        )
        assert receipt.status_code == 201
        assert plain.status_code == 201

        highlights = client.get(
            "/api/v1/dashboard/analytics/highlights",
            params={"month": "2026-03", "category_breakdown_level": "brand"},
        )
        assert highlights.status_code == 200, highlights.text
        payload = highlights.json()
        assert payload["expense_total"] == "100.00"
        assert payload["receipt_amount_total"] == "10.00"
        assert payload["branded_amount_total"] == "4.00"
        assert payload["unbranded_amount_total"] == "6.00"
        assert payload["brand_coverage_pct"] == 40.0
        assert {item["category_name"] for item in payload["category_breakdown"]} == {
            "Covered",
            "Без бренда",
        }
    finally:
        client.close()
        try:
            next(lifecycle)
        except StopIteration:
            pass


def test_brand_metrics_and_breakdown_never_allocate_negative_rounding_remainder():
    lifecycle = _client_lifecycle()
    client = next(lifecycle)
    try:
        brands = [_create_brand(client, f"Tiny brand {index}") for index in range(1, 5)]
        created = client.post(
            "/api/v1/operations",
            json={
                "kind": "expense",
                "amount": "0.02",
                "operation_date": "2026-03-10",
                "receipt_items": [
                    {
                        "name": f"Tiny item {index}",
                        "brand_id": brand["id"],
                        "quantity": "1",
                        "unit_price": "0.01",
                    }
                    for index, brand in enumerate(brands, start=1)
                ],
            },
        )
        assert created.status_code == 201, created.text

        listed = client.get("/api/v1/operations/item-brands", params={"page_size": 100})
        assert listed.status_code == 200, listed.text
        metrics_by_id = {item["id"]: item for item in listed.json()["items"]}
        metric_amounts = [Decimal(metrics_by_id[brand["id"]]["spent_total"]) for brand in brands]
        assert metric_amounts == [Decimal("0.01"), Decimal("0.01"), Decimal("0.00"), Decimal("0.00")]
        assert sum(metric_amounts, start=Decimal("0")) == Decimal("0.02")
        assert all(amount >= 0 for amount in metric_amounts)

        highlights = client.get(
            "/api/v1/dashboard/analytics/highlights",
            params={"month": "2026-03", "category_breakdown_level": "brand"},
        )
        assert highlights.status_code == 200, highlights.text
        payload = highlights.json()
        breakdown_by_id = {item["brand_id"]: item for item in payload["category_breakdown"]}
        breakdown_amounts = [Decimal(breakdown_by_id[brand["id"]]["total_amount"]) for brand in brands]
        assert breakdown_amounts == [Decimal("0.01"), Decimal("0.01"), Decimal("0.00"), Decimal("0.00")]
        assert sum(breakdown_amounts, start=Decimal("0")) == Decimal("0.02")
        assert all(amount >= 0 for amount in breakdown_amounts)
        assert payload["receipt_amount_total"] == "0.02"
        assert payload["branded_amount_total"] == "0.02"
        assert payload["unbranded_amount_total"] == "0.00"
    finally:
        client.close()
        try:
            next(lifecycle)
        except StopIteration:
            pass
