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
    mixed = client.get(f"{ops}/purpose-tags/summary", params={"tag": tag}).json()
    assert mixed["converted"] is True
    assert mixed["balances"] == {"BYN": {"income": 0, "expense": 22.30, "net": -22.30}}
    single = client.get(f"{ops}/purpose-tags/summary", params={"tag": whole}).json()
    assert single["converted"] is False
    assert single["balances"] == {"USD": {"income": 0, "expense": 10, "net": -10}}


def test_tag_balance_includes_income_and_excludes_unconfirmed_plans(client):
    ops = "/api/v1/operations"
    tag = "др-2026"

    def post(url, **fields):
        response = client.post(url, json={"tags": [tag], **fields})
        assert response.status_code == 201, response.text
        return response.json()

    def summary():
        return client.get(f"{ops}/purpose-tags/summary", params={"tag": "#ДР-2026"}).json()

    gift = post(ops, kind="income", operation_date="2026-11-20", amount="100.00", note="Подарок")
    post("/api/v1/plans", kind="income", scheduled_date="2026-11-22", amount="25.00")
    post("/api/v1/plans", kind="expense", scheduled_date="2026-11-23", amount="30.00")
    result = summary()
    assert result["balances"]["BYN"] == {"income": 100, "expense": 0, "net": 100}
    assert result["received"]["entries"][0]["id"] == gift["id"]
    assert result["planned_income"]["totals"] == {"BYN": 25}
    assert result["planned"]["totals"] == {"BYN": 30}
    # The same tag on the parent and one line counts the whole receipt once.
    post(ops, kind="expense", operation_date="2026-11-20", receipt_items=[
        {"name":"Заказ", "quantity":1, "unit_price":"248.25", "tags":[tag]},
        {"name":"Доставка", "quantity":1, "unit_price":"22.49"},
    ])
    assert summary()["balances"]["BYN"] == {"income": 100, "expense": 270.74, "net": -170.74}
    post(ops, kind="income", operation_date="2026-11-21", amount="170.74")
    assert summary()["balances"]["BYN"] == {"income": 270.74, "expense": 270.74, "net": 0}

    from app.api.deps import get_current_user_id
    from app.main import app
    app.dependency_overrides[get_current_user_id] = lambda: 2
    other = summary()
    assert other["balances"] == {} and other["received"]["count"] == other["planned_income"]["count"] == 0


def test_combined_tag_balance_uses_each_operations_saved_rate(client):
    ops = "/api/v1/operations"
    tag = "праздник"
    for fields in (
        {"kind":"income", "amount":"10.00", "currency":"USD", "fx_rate":"3.50", "tags":[tag]},
        {"kind":"expense", "amount":"4.00", "currency":"BYN", "tags":[tag]},
        {"kind":"expense", "currency":"USD", "fx_rate":"3.21", "receipt_items":[
            {"name":"Личная покупка", "unit_price":"9.00", "quantity":1},
            {"name":"Открытка", "unit_price":"0.20", "quantity":1, "tags":[tag]},
            {"name":"Конверт", "unit_price":"0.30", "quantity":1, "tags":[tag]},
        ]},
    ):
        response = client.post(ops, json={"operation_date":"2026-11-20", **fields})
        assert response.status_code == 201, response.text
    result = client.get(f"{ops}/purpose-tags/summary", params={"tag":tag}).json()
    assert result["received"]["totals"] == {"USD": 10}
    assert result["paid"]["totals"] == {"USD": 0.50, "BYN": 4}
    assert result["balances"] == {"BYN":{"income":35, "expense":5.61, "net":29.39}}
    partial = next(row for row in result["paid"]["entries"] if row["currency"] == "USD")
    assert partial["description"] == "Позиций по тегу · 2"


def test_tag_balance_totals_cover_older_entries_and_keep_incompatible_bases_separate(client):
    from datetime import date
    from app.db.models import Operation
    from app.db.session import get_db
    from app.main import app

    session = app.dependency_overrides[get_db]()
    db = next(session)
    try:
        for i in range(31):
            db.add(Operation(user_id=1, operation_date=date(2026, 1, i+1), kind="expense",
                             currency="USD", base_currency="BYN", original_amount=1, amount=3, fx_rate=3, tags=["тег"]))
        db.add(Operation(user_id=1, operation_date=date(2026, 2, 1), kind="income",
                         currency="EUR", base_currency="EUR", original_amount=40, amount=40, fx_rate=1, tags=["тег"]))
        db.commit()
    finally:
        session.close()
    result = client.get("/api/v1/operations/purpose-tags/summary", params={"tag":"тег"}).json()
    assert result["converted"] is False
    assert result["balances"] == {"USD":{"income":0, "expense":31, "net":-31},
                                  "EUR":{"income":40, "expense":0, "net":40}}
    assert result["paid"]["count"] == 31 and len(result["paid"]["entries"]) == 30


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
