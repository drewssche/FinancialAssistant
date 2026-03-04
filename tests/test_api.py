from __future__ import annotations


def test_create_operation_and_get_day_summary(client):
    create_resp = client.post(
        "/api/operations",
        data={
            "kind": "expense",
            "subcategory": "Продукты и быт",
            "amount": "25.40",
            "occurred_on": "2026-03-02",
            "account": "Карта",
            "comment": "Магазин",
        },
    )
    assert create_resp.status_code == 200
    body = create_resp.json()
    assert body["ok"] is True
    assert body["id"]

    summary_resp = client.get("/api/summary", params={"period": "day", "selected_date": "2026-03-02"})
    assert summary_resp.status_code == 200

    payload = summary_resp.json()["data"]
    assert payload["totals"]["expense"] == 25.4
    assert payload["totals"]["income"] == 0.0
    assert payload["totals"]["balance"] == -25.4
    assert payload["expense_rows"][0]["name"] == "Продукты и быт"


def test_week_summary_aggregates_multiple_operations(client):
    operations = [
        {
            "kind": "income",
            "subcategory": "ЗП",
            "amount": "1500",
            "occurred_on": "2026-03-02",
            "account": "Карта",
            "comment": "",
        },
        {
            "kind": "expense",
            "subcategory": "Коммуналка",
            "amount": "100",
            "occurred_on": "2026-03-03",
            "account": "Карта",
            "comment": "",
        },
        {
            "kind": "expense",
            "subcategory": "Коммуналка",
            "amount": "50",
            "occurred_on": "2026-03-04",
            "account": "Карта",
            "comment": "",
        },
    ]

    for item in operations:
        resp = client.post("/api/operations", data=item)
        assert resp.status_code == 200

    summary_resp = client.get("/api/summary", params={"period": "week", "selected_date": "2026-03-05"})
    assert summary_resp.status_code == 200
    data = summary_resp.json()["data"]

    assert data["totals"]["income"] == 1500.0
    assert data["totals"]["expense"] == 150.0
    assert data["totals"]["balance"] == 1350.0
    assert data["expense_rows"][0]["name"] == "Коммуналка"
    assert data["expense_rows"][0]["amount"] == 150.0


def test_create_operation_validation_error(client):
    resp = client.post(
        "/api/operations",
        data={
            "kind": "expense",
            "subcategory": "Несуществующая",
            "amount": "10",
            "occurred_on": "2026-03-02",
            "account": "Карта",
            "comment": "",
        },
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid subcategory"


def test_edit_operation(client):
    create_resp = client.post(
        "/api/operations",
        data={
            "kind": "expense",
            "subcategory": "Коммуналка",
            "amount": "25",
            "occurred_on": "2026-03-02",
            "account": "Карта",
            "comment": "",
        },
    )
    assert create_resp.status_code == 200
    op_id = create_resp.json()["id"]

    edit_resp = client.put(
        f"/api/operations/{op_id}",
        data={
            "kind": "expense",
            "subcategory": "Коммуналка",
            "amount": "35",
            "occurred_on": "2026-03-02",
            "account": "Карта",
            "comment": "updated",
        },
    )
    assert edit_resp.status_code == 200

    detail_resp = client.get(f"/api/operations/{op_id}")
    assert detail_resp.status_code == 200
    data = detail_resp.json()["data"]
    assert data["amount"] == 35.0
    assert data["comment"] == "updated"


def test_delete_operation(client):
    create_resp = client.post(
        "/api/operations",
        data={
            "kind": "income",
            "subcategory": "ЗП",
            "amount": "100",
            "occurred_on": "2026-03-02",
            "account": "Карта",
            "comment": "",
        },
    )
    assert create_resp.status_code == 200
    op_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/api/operations/{op_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["ok"] is True

    detail_resp = client.get(f"/api/operations/{op_id}")
    assert detail_resp.status_code == 404


def test_category_create_rename_delete(client):
    create_resp = client.post(
        "/api/categories",
        json={"kind": "expense", "name": "Тест категория"},
    )
    assert create_resp.status_code == 200
    category_id = create_resp.json()["data"]["id"]

    rename_resp = client.put(
        f"/api/categories/{category_id}",
        json={"name": "Тест категория 2"},
    )
    assert rename_resp.status_code == 200
    assert rename_resp.json()["data"]["name"] == "Тест категория 2"

    delete_resp = client.delete(f"/api/categories/{category_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["ok"] is True


def test_category_group_create_and_move_category(client):
    groups_resp = client.get("/api/category-groups", params={"kind": "expense"})
    assert groups_resp.status_code == 200
    groups = [g for g in groups_resp.json()["data"] if not g.get("is_virtual")]
    assert len(groups) > 0

    first_group_id = groups[0]["id"]

    create_category_resp = client.post(
        "/api/categories",
        json={"kind": "expense", "name": "Тест перенос", "group_id": first_group_id},
    )
    assert create_category_resp.status_code == 200
    category_id = create_category_resp.json()["data"]["id"]

    create_group_resp = client.post(
        "/api/category-groups",
        json={"kind": "expense", "name": "Тест группа", "color": "#55aaff", "icon": "🧾"},
    )
    assert create_group_resp.status_code == 200
    new_group = create_group_resp.json()["data"]
    new_group_id = new_group["id"]
    assert new_group["icon"] == "🧾"

    move_resp = client.put(
        f"/api/categories/{category_id}",
        json={"group_id": new_group_id},
    )
    assert move_resp.status_code == 200
    assert move_resp.json()["data"]["group_id"] == new_group_id


def test_reorder_groups_and_categories_and_archive(client):
    groups_resp = client.get("/api/category-groups", params={"kind": "expense"})
    assert groups_resp.status_code == 200
    groups = [g for g in groups_resp.json()["data"] if not g.get("is_virtual")]
    assert len(groups) >= 2

    g1 = groups[0]
    g2 = groups[1]

    reorder_groups_resp = client.post(
        "/api/category-groups/reorder",
        json={"kind": "expense", "group_ids": [g2["id"], g1["id"]]},
    )
    assert reorder_groups_resp.status_code == 200

    if len(g1["categories"]) > 0:
        c1 = g1["categories"][0]
        reorder_categories_resp = client.post(
            "/api/categories/reorder",
            json={
                "kind": "expense",
                "items": [{"id": c1["id"], "group_id": g2["id"], "sort_order": 0}],
            },
        )
        assert reorder_categories_resp.status_code == 200

        archive_category_resp = client.put(
            f"/api/categories/{c1['id']}/archive",
            json={"is_archived": True},
        )
        assert archive_category_resp.status_code == 200
        assert archive_category_resp.json()["data"]["is_archived"] is True

    archive_group_resp = client.put(
        f"/api/category-groups/{g1['id']}/archive",
        json={"is_archived": True},
    )
    assert archive_group_resp.status_code == 200
    assert archive_group_resp.json()["data"]["is_archived"] is True


def test_category_can_be_created_and_moved_to_ungrouped(client):
    create_resp = client.post(
        "/api/categories",
        json={"kind": "expense", "name": "Без группы тест", "group_id": None},
    )
    assert create_resp.status_code == 200
    data = create_resp.json()["data"]
    assert data["group_id"] is None

    category_id = data["id"]
    move_resp = client.put(
        f"/api/categories/{category_id}",
        json={"group_id": None},
    )
    assert move_resp.status_code == 200
    assert move_resp.json()["data"]["group_id"] is None
