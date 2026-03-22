from fastapi.testclient import TestClient
from app.core.cache import reset_cache_for_tests

from tests.api.test_operations_api import client


def test_plans_crud_confirm_and_history(client: TestClient):
    reset_cache_for_tests()
    category_resp = client.post("/api/v1/categories", json={"name": "Магазин", "kind": "expense"})
    assert category_resp.status_code == 200
    category_id = category_resp.json()["id"]

    created = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "scheduled_date": "2026-03-15",
            "category_id": category_id,
            "note": "Список покупок",
            "receipt_items": [
                {"shop_name": "Соседи", "name": "Хлеб", "quantity": "2", "unit_price": "1.50"},
                {"shop_name": "Соседи", "name": "Молоко", "quantity": "1", "unit_price": "2.30"},
            ],
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["amount"] == "5.30"
    assert payload["status"] in {"upcoming", "due", "overdue"}
    assert len(payload["receipt_items"]) == 2
    plan_id = payload["id"]

    listed = client.get("/api/v1/plans")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    updated = client.patch(
        f"/api/v1/plans/{plan_id}",
        json={
            "note": "Большой список покупок",
            "amount": "6.00",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["note"] == "Большой список покупок"
    assert updated.json()["amount"] == "6.00"

    confirmed = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert confirmed.status_code == 200
    confirm_payload = confirmed.json()
    assert confirm_payload["operation"]["amount"] == "6.00"
    assert confirm_payload["plan"]["status"] == "confirmed"
    assert confirm_payload["plan"]["confirmed_operation_id"] == confirm_payload["operation"]["id"]

    operations = client.get("/api/v1/operations", params={"page": 1, "page_size": 20})
    assert operations.status_code == 200
    assert operations.json()["total"] == 1
    assert operations.json()["items"][0]["note"] == "Большой список покупок"

    history = client.get("/api/v1/plans/history")
    assert history.status_code == 200
    history_payload = history.json()
    assert history_payload["total"] == 1
    assert history_payload["items"][0]["event_type"] == "confirmed"
    assert history_payload["items"][0]["operation_id"] == confirm_payload["operation"]["id"]
    assert history_payload["items"][0]["effective_date"] == "2026-03-15"
    assert history_payload["items"][0]["category_name"] == "Магазин"


def test_recurring_plan_skip_and_confirm_advance_schedule(client: TestClient):
    reset_cache_for_tests()
    created = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "amount": "120.00",
            "scheduled_date": "2026-03-10",
            "note": "Коммуналка",
            "recurrence_enabled": True,
            "recurrence_frequency": "monthly",
            "recurrence_interval": 1,
        },
    )
    assert created.status_code == 201
    plan_id = created.json()["id"]

    skipped = client.post(f"/api/v1/plans/{plan_id}/skip")
    assert skipped.status_code == 200
    skipped_payload = skipped.json()
    assert skipped_payload["skip_count"] == 1
    assert skipped_payload["scheduled_date"] == "2026-04-10"
    assert skipped_payload["status"] in {"upcoming", "due", "overdue"}

    confirmed = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert confirmed.status_code == 200
    confirmed_payload = confirmed.json()
    assert confirmed_payload["plan"]["confirm_count"] == 1
    assert confirmed_payload["plan"]["scheduled_date"] == "2026-05-10"
    assert confirmed_payload["operation"]["operation_date"] == "2026-04-10"

    history = client.get("/api/v1/plans/history")
    assert history.status_code == 200
    history_items = history.json()["items"]
    assert [item["event_type"] for item in history_items[:2]] == ["confirmed", "skipped"]
    assert history_items[0]["effective_date"] == "2026-04-10"
    assert history_items[1]["effective_date"] == "2026-03-10"


def test_plan_rejects_invalid_recurrence_and_deletes(client: TestClient):
    reset_cache_for_tests()
    invalid = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "amount": "10.00",
            "scheduled_date": "2026-03-10",
            "recurrence_enabled": True,
            "recurrence_interval": 1,
        },
    )
    assert invalid.status_code == 400

    created = client.post(
        "/api/v1/plans",
        json={
            "kind": "income",
            "amount": "300.00",
            "scheduled_date": "2026-03-11",
            "note": "Подработка",
        },
    )
    assert created.status_code == 201
    plan_id = created.json()["id"]

    removed = client.delete(f"/api/v1/plans/{plan_id}")
    assert removed.status_code == 204

    missing = client.get(f"/api/v1/plans/{plan_id}")
    assert missing.status_code == 404


def test_weekly_plan_supports_multiple_weekdays(client: TestClient):
    reset_cache_for_tests()
    created = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "amount": "20.00",
            "scheduled_date": "2026-03-09",
            "note": "Спортзал",
            "recurrence_enabled": True,
            "recurrence_frequency": "weekly",
            "recurrence_interval": 1,
            "recurrence_weekdays": [0, 2, 4],
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["recurrence_weekdays"] == [0, 2, 4]
    assert "Пн" in payload["recurrence_label"]
    assert "Ср" in payload["recurrence_label"]
    plan_id = payload["id"]

    skipped = client.post(f"/api/v1/plans/{plan_id}/skip")
    assert skipped.status_code == 200
    assert skipped.json()["scheduled_date"] == "2026-03-11"

    confirmed = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["operation"]["operation_date"] == "2026-03-11"
    assert confirmed.json()["plan"]["scheduled_date"] == "2026-03-13"


def test_monthly_plan_can_stick_to_last_day_of_month(client: TestClient):
    reset_cache_for_tests()
    created = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "amount": "50.00",
            "scheduled_date": "2026-01-31",
            "note": "Подписка",
            "recurrence_enabled": True,
            "recurrence_frequency": "monthly",
            "recurrence_interval": 1,
            "recurrence_month_end": True,
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["recurrence_month_end"] is True
    assert "последний день месяца" in payload["recurrence_label"]
    plan_id = payload["id"]

    skipped = client.post(f"/api/v1/plans/{plan_id}/skip")
    assert skipped.status_code == 200
    assert skipped.json()["scheduled_date"] == "2026-02-28"

    confirmed = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["operation"]["operation_date"] == "2026-02-28"
    assert confirmed.json()["plan"]["scheduled_date"] == "2026-03-31"


def test_plan_rejects_invalid_weekday_values(client: TestClient):
    reset_cache_for_tests()
    invalid = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "amount": "10.00",
            "scheduled_date": "2026-03-10",
            "recurrence_enabled": True,
            "recurrence_frequency": "weekly",
            "recurrence_interval": 1,
            "recurrence_weekdays": [1, 8],
        },
    )
    assert invalid.status_code == 400


def test_daily_plan_can_repeat_on_workdays_only(client: TestClient):
    reset_cache_for_tests()
    created = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "amount": "15.00",
            "scheduled_date": "2026-03-13",
            "note": "Кофе в офисе",
            "recurrence_enabled": True,
            "recurrence_frequency": "daily",
            "recurrence_interval": 1,
            "recurrence_workdays_only": True,
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["recurrence_workdays_only"] is True
    assert payload["recurrence_label"] == "По будням"
    plan_id = payload["id"]

    skipped = client.post(f"/api/v1/plans/{plan_id}/skip")
    assert skipped.status_code == 200
    assert skipped.json()["scheduled_date"] == "2026-03-16"

    confirmed = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["operation"]["operation_date"] == "2026-03-16"
    assert confirmed.json()["plan"]["scheduled_date"] == "2026-03-17"


def test_income_plan_receipt_items_appear_in_item_catalog_before_confirm(client: TestClient):
    reset_cache_for_tests()
    category_resp = client.post("/api/v1/categories", json={"name": "Зарплата", "kind": "income"})
    assert category_resp.status_code == 200
    category_id = category_resp.json()["id"]

    created = client.post(
        "/api/v1/plans",
        json={
            "kind": "income",
            "scheduled_date": "2026-03-20",
            "category_id": category_id,
            "note": "Получка",
            "receipt_items": [
                {"shop_name": "Получка", "name": "Оклад", "quantity": "1", "unit_price": "1500.00"},
            ],
        },
    )
    assert created.status_code == 201

    catalog = client.get("/api/v1/operations/item-templates", params={"page": 1, "page_size": 20, "q": "Получка"})
    assert catalog.status_code == 200
    payload = catalog.json()
    assert payload["total"] >= 1
    assert any(item["shop_name"] == "Получка" and item["name"] == "Оклад" for item in payload["items"])


def test_item_catalog_backfills_from_existing_plan_receipt_items(client: TestClient):
    reset_cache_for_tests()
    category_resp = client.post("/api/v1/categories", json={"name": "Фриланс", "kind": "income"})
    assert category_resp.status_code == 200
    category_id = category_resp.json()["id"]

    created = client.post(
        "/api/v1/plans",
        json={
            "kind": "income",
            "scheduled_date": "2026-03-21",
            "category_id": category_id,
            "note": "Старый план",
            "receipt_items": [
                {"shop_name": "Подработка", "name": "Проект", "quantity": "1", "unit_price": "800.00"},
            ],
        },
    )
    assert created.status_code == 201

    cleared = client.delete("/api/v1/operations/item-templates")
    assert cleared.status_code == 200
    assert cleared.json()["deleted"] >= 1

    catalog = client.get("/api/v1/operations/item-templates", params={"page": 1, "page_size": 20, "q": "Подработка"})
    assert catalog.status_code == 200
    payload = catalog.json()
    assert payload["total"] >= 1
    assert any(item["shop_name"] == "Подработка" and item["name"] == "Проект" for item in payload["items"])


def test_plans_list_and_history_cache_are_invalidated_after_plan_mutation(client: TestClient):
    reset_cache_for_tests()

    created = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "amount": "42.00",
            "scheduled_date": "2026-03-22",
            "note": "Кэшируемый план",
        },
    )
    assert created.status_code == 201
    plan_id = created.json()["id"]

    first_list = client.get("/api/v1/plans")
    assert first_list.status_code == 200
    assert first_list.json()["total"] >= 1

    first_history = client.get("/api/v1/plans/history")
    assert first_history.status_code == 200

    updated = client.patch(f"/api/v1/plans/{plan_id}", json={"note": "Обновлённый кэшируемый план"})
    assert updated.status_code == 200

    second_list = client.get("/api/v1/plans")
    assert second_list.status_code == 200
    assert any(item["note"] == "Обновлённый кэшируемый план" for item in second_list.json()["items"])

    confirmed = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert confirmed.status_code == 200

    second_history = client.get("/api/v1/plans/history")
    assert second_history.status_code == 200
    assert second_history.json()["total"] >= 1
    assert second_history.json()["items"][0]["event_type"] == "confirmed"
