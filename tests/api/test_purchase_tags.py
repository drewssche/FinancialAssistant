from decimal import Decimal

from tests.api.test_plans_api import client


def test_tagged_plan_confirmation_and_mixed_receipt_totals(client):
    tag = "кофемашина"
    plans, ops = "/api/v1/plans", "/api/v1/operations"
    response = client.post(plans, json={
        "kind": "expense", "scheduled_date": "2026-11-15", "tags": [" ДОМ ", "#дом"],
        "receipt_items": [
            {"name": "Коврик", "shop_name": "WB", "tags": [tag], "quantity": 1, "unit_price": "26.90"},
            {"name": "Футболка", "shop_name": "WB", "quantity": 1, "unit_price": "34.30"},
        ],
    })
    assert response.status_code == 201, response.text
    plan = response.json()
    assert plan["tags"] == ["дом"]
    assert client.get(plans, params={"q": "#" + tag}).json()["total"] == 1
    product_id = plan["receipt_items"][0]["product_id"]
    product = f"{ops}/catalog-products/{product_id}"
    assert plan["receipt_items"][0]["tags"] == [tag]
    assert client.get(product).json()["tags"] == []
    assert client.patch(product, json={"tags": ["новый тег"]}).status_code == 200
    summary = lambda value: client.get(ops + "/purpose-tags/summary", params={"tag": value}).json()
    assert Decimal(str(summary(tag)["planned"]["totals"]["BYN"])) == Decimal("26.90")
    assert Decimal(str(summary("дом")["planned"]["totals"]["BYN"])) == Decimal("61.20")
    confirmed = client.post(f"{plans}/{plan['id']}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    operation = confirmed.json()["operation"]
    assert operation["tags"] == ["дом"]
    assert operation["receipt_items"][0]["tags"] == [tag]
    assert client.get(ops + "/money-flow", params={"q": "#" + tag}).json()["total"] == 1
    assert summary(tag)["planned"]["count"] == 0
    assert Decimal(str(summary(tag)["paid"]["totals"]["BYN"])) == Decimal("26.90")
    assert client.get(plans + "/history", params={"q": "#дом"}).json()["total"] == 1
    assert client.patch(product, json={"tags": ["a,b"]}).status_code == 422


def test_birthday_tag_stays_on_its_purchase_when_the_product_is_bought_again(client):
    ops = "/api/v1/operations"
    tag = "др-2026"
    line = {"name": "Торт", "shop_name": "Green", "quantity": 1, "unit_price": "35.00"}

    def buy(day, item):
        response = client.post(ops, json={"kind": "expense", "operation_date": day, "receipt_items": [item]})
        assert response.status_code == 201, response.text
        return response.json()["receipt_items"][0]

    first = buy("2026-11-15", {**line, "tags": [tag]})
    assert first["tags"] == [tag]
    product = f"{ops}/catalog-products/{first['product_id']}"
    again = buy("2026-11-16", {**line, "template_id": first["template_id"]})
    assert again["product_id"] == first["product_id"]
    assert again["tags"] == []
    assert client.get(product).json()["tags"] == []

    assert client.patch(product, json={"tags": ["выпечка"]}).status_code == 200
    assert buy("2026-11-17", line)["tags"] == ["выпечка"]
    summary = client.get(f"{ops}/purpose-tags/summary", params={"tag": tag}).json()["paid"]
    assert summary["count"] == 1
    assert summary["totals"] == {"BYN": 35}


def test_tag_summary_uses_the_currency_of_the_tagged_amount(client):
    ops = "/api/v1/operations"
    tag = "др-2026"
    whole = "вся оплата"
    legacy = client.post(ops, json={
        "kind": "expense", "operation_date": "2026-01-20", "tags": [whole],
        "receipt_items": [
            {"name": "Десерт", "quantity": 1, "unit_price": "15.10", "tags": [tag, whole]},
            {"name": "Чай", "quantity": 1, "unit_price": "17.00"},
        ],
        "fx_settlement": {"asset_currency": "USD", "quantity": "10", "quote_total": "32.10", "unit_price": "3.21"},
    })
    assert legacy.status_code == 201, legacy.text
    receipt = legacy.json()
    assert (receipt["receipt_currency"], receipt["currency"]) == ("BYN", "USD")
    foreign = client.post(ops, json={
        "kind": "expense", "operation_date": "2026-01-21", "currency": "USD", "fx_rate": "3.20",
        "receipt_items": [{"name": "Свеча", "quantity": 1, "unit_price": "2.25", "tags": [tag]}],
    })
    assert foreign.status_code == 201, foreign.text

    def paid(value):
        result = client.get(f"{ops}/purpose-tags/summary", params={"tag": value})
        assert result.status_code == 200, result.text
        return result.json()["paid"]

    lines = paid(tag)
    assert lines["totals"] == {"BYN": 15.10, "USD": 2.25}
    assert [(r["id"], r["amount"], r["currency"]) for r in lines["entries"]] == [
        (foreign.json()["id"], 2.25, "USD"), (receipt["id"], 15.10, "BYN"),
    ]
    payment = paid(whole)
    assert payment["totals"] == {"USD": 10}
    assert [(r["id"], r["amount"], r["currency"]) for r in payment["entries"]] == [(receipt["id"], 10, "USD")]


def test_standalone_plan_tags_and_legacy_line_update(client):
    plans, ops = "/api/v1/plans", "/api/v1/operations"
    category = client.post("/api/v1/categories", json={"kind":"expense", "name":"Дом"}).json()["id"]
    plan = client.post(plans, json={"kind":"expense", "scheduled_date":"2026-11-15", "amount":10, "category_id":category,
                                    "tags":["ремонт"]}).json()
    assert next(row for row in client.get("/api/v1/categories").json() if row["id"] == category)["used_tags"] == ["ремонт"]
    assert client.patch(f"{plans}/{plan['id']}", json={"note":"Сервис"}).json()["tags"] == ["ремонт"]
    result = client.post(f"{plans}/{plan['id']}/confirm").json()
    assert result["operation"]["tags"] == ["ремонт"]
    line = {"shop_name":"WB", "name":"Салфетки", "tags":["кухня"], "quantity":1, "unit_price":"20.88"}
    purchase = client.post(ops, json={"kind":"expense", "operation_date":"2026-11-14", "receipt_items":[line]}).json()
    line.pop("tags")
    url = f"{ops}/{purchase['id']}"
    assert client.patch(url, json={"receipt_items":[line]}).json()["receipt_items"][0]["tags"] == ["кухня"]
    line["tags"] = []
    assert client.patch(url, json={"receipt_items":[line]}).json()["receipt_items"][0]["tags"] == []


def test_historical_edit_keeps_archived_source_and_other_users_tags_private(client):
    from app.api.deps import get_current_user_id
    from app.main import app

    ops = "/api/v1/operations"
    line = {"name":"Покупка", "shop_name":"Старый источник", "tags":["личное"],
            "quantity":1, "unit_price":"3.00"}
    category_id = client.post("/api/v1/categories", json={"name":"Покупки", "kind":"expense"}).json()["id"]
    purchase = client.post(ops, json={"kind":"expense", "category_id":category_id,
                          "operation_date":"2026-11-14", "receipt_items":[line]}).json()
    row = purchase["receipt_items"][0]
    source = f"{ops}/item-sources/{row['source_id']}"
    assert client.delete(source).is_success
    assert client.patch(f"{ops}/{purchase['id']}", json={"receipt_items":[{**line, "template_id":row["template_id"]}]}).is_success
    offers = client.get(f"{ops}/catalog-products/{row['product_id']}").json()["offers"]
    assert offers == []
    app.dependency_overrides[get_current_user_id] = lambda: 2
    summary = client.get(ops + "/purpose-tags/summary", params={"tag":"личное"}).json()
    assert summary["paid"]["count"] == summary["planned"]["count"] == 0
    assert all("личное" not in c["used_tags"] for c in client.get("/api/v1/categories").json())
