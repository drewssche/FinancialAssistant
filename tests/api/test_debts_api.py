import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user_id
from app.core.cache import reset_cache_for_tests
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db
from app.main import app


def _override_current_user_id() -> int:
    return 1


@pytest.fixture
def client():
    reset_cache_for_tests()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = _override_current_user_id

    db = testing_session()
    db.add(User(id=1, display_name="Tester", status="active"))
    db.commit()
    db.close()

    test_client = TestClient(app)
    yield test_client

    reset_cache_for_tests()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_debts_create_and_list_cards(client: TestClient):
    created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Иван",
            "direction": "lend",
            "principal": "500.00",
            "start_date": "2026-03-05",
            "due_date": "2026-03-30",
            "note": "На ремонт",
        },
    )
    assert created.status_code == 201

    cards = client.get("/api/v1/debts/cards")
    assert cards.status_code == 200
    payload = cards.json()
    assert len(payload) == 1
    assert payload[0]["counterparty"] == "Иван"
    assert payload[0]["status"] == "active"
    assert payload[0]["outstanding_total"] == "500.00"
    assert payload[0]["debts"][0]["repayments"] == []


def test_edit_closed_debt_repayment_updates_one_movement_and_cashflow(client: TestClient):
    debt = client.post("/api/v1/debts", json={
        "counterparty": "Дима", "direction": "lend", "principal": "50.00",
        "start_date": "2026-09-03", "note": "Комментарий долга",
    }).json()
    first = client.post(f"/api/v1/debts/{debt['id']}/repayments", json={
        "amount": "28.00", "repayment_date": "2026-09-04", "note": "Первый платёж",
    }).json()
    second = client.post(f"/api/v1/debts/{debt['id']}/repayments", json={
        "amount": "22.00", "repayment_date": "2026-09-05",
    }).json()
    assert client.get("/api/v1/debts/cards").json() == []
    client.get("/api/v1/operations/money-flow")  # warm cashflow caches
    url = f"/api/v1/debts/{debt['id']}/movements/repayment/{second['id']}"
    detail = client.get(url)
    assert detail.status_code == 200
    assert detail.json()["counterparty"] == "Дима"
    assert detail.json()["amount"] == "22.00"
    edited = client.patch(url, json={"amount": "20.00", "event_date": "2026-09-06", "note": "Уточнено"})
    assert edited.status_code == 200
    card = client.get("/api/v1/debts/cards").json()[0]
    assert card["status"] == "active"
    assert card["outstanding_total"] == "2.00"
    repayments = {item["id"]: item for item in card["debts"][0]["repayments"]}
    assert len(repayments) == 2
    assert repayments[first["id"]]["amount"] == "28.00"
    assert repayments[second["id"]]["repayment_date"] == "2026-09-06"
    flows = client.get("/api/v1/operations/money-flow").json()["items"]
    row = next(item for item in flows if item["id"] == f"debt-repayment:{second['id']}")
    assert row["amount"] == "20.00"
    assert row["note"] == "Уточнено"
    assert client.get("/api/v1/operations").json()["total"] == 0
    # Clearing the movement note must not bring back the parent debt note.
    assert client.patch(url, json={"amount": "22.00", "event_date": "2026-09-05", "note": None}).status_code == 200
    row = next(item for item in client.get("/api/v1/operations/money-flow").json()["items"]
               if item["id"] == f"debt-repayment:{second['id']}")
    assert row["note"] is None
    assert client.get("/api/v1/debts/cards").json() == []


def test_edit_debt_issuance_adjusts_principal_without_creating_another_issuance(client: TestClient):
    debt = client.post("/api/v1/debts", json={
        "counterparty": "Иван", "direction": "borrow", "principal": "50.00",
        "currency": "EUR", "start_date": "2026-09-03",
    }).json()
    issuance = debt["issuances"][0]
    url = f"/api/v1/debts/{debt['id']}/movements/issuance/{issuance['id']}"
    assert client.get(url).json()["currency"] == "EUR"
    edited = client.patch(url, json={"amount": "55.00", "event_date": "2026-09-02", "note": "Уточнение"})
    assert edited.status_code == 200
    # No EUR/BYN rate is seeded in this test; inspect the native-currency values.
    updated = client.get("/api/v1/debts/cards?include_closed=true").json()[0]["debts"][0]
    assert updated["principal"] == "55.00"
    assert updated["original_principal"] == "55.00"
    assert updated["start_date"] == "2026-09-02"
    assert len(updated["issuances"]) == 1
    assert updated["issuances"][0]["id"] == issuance["id"]
    assert updated["issuances"][0]["amount"] == "55.00"


def test_edit_debt_movement_rejects_overpayment_and_wrong_owner(client: TestClient):
    debt = client.post("/api/v1/debts", json={
        "counterparty": "Олег", "direction": "lend", "principal": "50.00", "start_date": "2026-09-01",
    }).json()
    repayment = client.post(f"/api/v1/debts/{debt['id']}/repayments", json={
        "amount": "40.00", "repayment_date": "2026-09-05",
    }).json()
    url = f"/api/v1/debts/{debt['id']}/movements/repayment/{repayment['id']}"
    assert client.patch(url, json={"amount": "51.00", "event_date": "2026-09-05"}).status_code == 400
    issuance_url = f"/api/v1/debts/{debt['id']}/movements/issuance/{debt['issuances'][0]['id']}"
    assert client.patch(issuance_url, json={"amount": "39.00", "event_date": "2026-09-01"}).status_code == 400
    assert client.get(url).json()["amount"] == "40.00"
    assert client.get(issuance_url).json()["amount"] == "50.00"
    for invalid in ("0", "-1", "0.001", "NaN", "Infinity"):
        assert client.patch(url, json={"amount": invalid, "event_date": "2026-09-05"}).status_code == 422
    assert client.get(f"/api/v1/debts/{debt['id'] + 100}/movements/repayment/{repayment['id']}").status_code == 404
    app.dependency_overrides[get_current_user_id] = lambda: 2
    try:
        assert client.get(url).status_code == 404
        assert client.patch(url, json={"amount": "1.00", "event_date": "2026-09-05"}).status_code == 404
    finally:
        app.dependency_overrides[get_current_user_id] = _override_current_user_id


def test_debts_repayment_and_close_card(client: TestClient):
    created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Мария",
            "direction": "borrow",
            "principal": "300.00",
            "start_date": "2026-02-10",
        },
    )
    assert created.status_code == 201
    debt_id = created.json()["id"]

    repaid = client.post(
        f"/api/v1/debts/{debt_id}/repayments",
        json={"amount": "300.00", "repayment_date": "2026-03-01"},
    )
    assert repaid.status_code == 201

    active_cards = client.get("/api/v1/debts/cards")
    assert active_cards.status_code == 200
    assert active_cards.json() == []

    all_cards = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert all_cards.status_code == 200
    payload = all_cards.json()
    assert len(payload) == 1
    assert payload[0]["status"] == "closed"
    assert payload[0]["outstanding_total"] == "0.00"


def test_active_card_keeps_closed_children_available_for_counterparty_history(client: TestClient):
    closed_debt = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Анна",
            "direction": "lend",
            "principal": "100.00",
            "start_date": "2026-03-01",
        },
    )
    assert closed_debt.status_code == 201
    closed_debt_id = closed_debt.json()["id"]
    repayment = client.post(
        f"/api/v1/debts/{closed_debt_id}/repayments",
        json={"amount": "100.00", "repayment_date": "2026-03-02"},
    )
    assert repayment.status_code == 201

    active_debt = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Анна",
            "direction": "lend",
            "principal": "50.00",
            "start_date": "2026-03-03",
        },
    )
    assert active_debt.status_code == 201
    active_debt_id = active_debt.json()["id"]

    cards = client.get("/api/v1/debts/cards")
    assert cards.status_code == 200
    payload = cards.json()
    assert len(payload) == 1
    assert payload[0]["status"] == "active"
    debts_by_id = {item["id"]: item for item in payload[0]["debts"]}
    assert set(debts_by_id) == {closed_debt_id, active_debt_id}
    assert debts_by_id[closed_debt_id]["outstanding_total"] == "0.00"
    assert debts_by_id[active_debt_id]["outstanding_total"] == "50.00"


def test_debts_add_issuance_increases_existing_debt(client: TestClient):
    created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Мария",
            "direction": "borrow",
            "principal": "300.00",
            "start_date": "2026-02-10",
        },
    )
    assert created.status_code == 201
    debt_id = created.json()["id"]

    added = client.post(
        f"/api/v1/debts/{debt_id}/issuances",
        json={"amount": "125.50", "issuance_date": "2026-02-20", "note": "Долг вырос"},
    )
    assert added.status_code == 201
    assert added.json()["amount"] == "125.50"
    assert added.json()["issuance_date"] == "2026-02-20"

    cards = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert cards.status_code == 200
    payload = cards.json()
    debt = payload[0]["debts"][0]
    assert debt["principal"] == "425.50"
    assert debt["outstanding_total"] == "425.50"
    assert [item["amount"] for item in debt["issuances"]] == ["125.50", "300.00"]
    assert debt["issuances"][0]["note"] == "Долг вырос"


def test_debts_forgiveness_closes_debt_with_forgiven_reason(client: TestClient):
    created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Ольга",
            "direction": "lend",
            "principal": "250.00",
            "start_date": "2026-03-10",
        },
    )
    assert created.status_code == 201
    debt_id = created.json()["id"]

    forgiven = client.post(
        f"/api/v1/debts/{debt_id}/forgivenesses",
        json={"amount": "250.00", "forgiven_date": "2026-03-20", "note": "Списал без возврата"},
    )
    assert forgiven.status_code == 201
    assert forgiven.json()["amount"] == "250.00"

    active_cards = client.get("/api/v1/debts/cards")
    assert active_cards.status_code == 200
    assert active_cards.json() == []

    all_cards = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert all_cards.status_code == 200
    payload = all_cards.json()
    assert payload[0]["status"] == "closed"
    debt = payload[0]["debts"][0]
    assert debt["closure_reason"] == "forgiven"
    assert debt["outstanding_total"] == "0.00"
    assert debt["forgiven_total"] == "250.00"
    assert len(debt["forgivenesses"]) == 1
    assert debt["forgivenesses"][0]["note"] == "Списал без возврата"


def test_debts_repayment_overpay_creates_reverse_debt(client: TestClient):
    created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Петр",
            "direction": "lend",
            "principal": "100.00",
            "start_date": "2026-01-01",
        },
    )
    assert created.status_code == 201
    debt_id = created.json()["id"]

    response = client.post(
        f"/api/v1/debts/{debt_id}/repayments",
        json={"amount": "120.00", "repayment_date": "2026-01-15"},
    )
    assert response.status_code == 201
    assert response.json()["amount"] == "100.00"

    cards = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert cards.status_code == 200
    payload = cards.json()
    assert len(payload) == 1
    debts = payload[0]["debts"]
    directions = sorted([item["direction"] for item in debts])
    assert directions == ["borrow", "lend"]
    reverse = next(item for item in debts if item["direction"] == "borrow")
    assert reverse["principal"] == "20.00"
    assert reverse["outstanding_total"] == "20.00"


def test_debts_update_and_delete(client: TestClient):
    created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Сергей",
            "direction": "lend",
            "principal": "450.00",
            "start_date": "2026-02-01",
            "due_date": "2026-04-01",
            "note": "Черновик",
        },
    )
    assert created.status_code == 201
    debt_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/debts/{debt_id}",
        json={
            "counterparty": "Сергей П.",
            "principal": "500.00",
            "note": "Обновлено",
        },
    )
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["principal"] == "500.00"
    assert payload["note"] == "Обновлено"

    deleted = client.delete(f"/api/v1/debts/{debt_id}")
    assert deleted.status_code == 204

    cards = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert cards.status_code == 200
    assert all(debt["id"] != debt_id for card in cards.json() for debt in card["debts"])


def test_debts_merge_same_counterparty_direction_into_active_debt(client: TestClient):
    first = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Надя",
            "direction": "lend",
            "principal": "100.00",
            "start_date": "2026-03-05",
        },
    )
    assert first.status_code == 201
    debt_id = first.json()["id"]

    second = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "надя",
            "direction": "lend",
            "principal": "250.00",
            "start_date": "2026-03-06",
        },
    )
    assert second.status_code == 201
    assert second.json()["id"] == debt_id
    assert second.json()["principal"] == "350.00"
    assert len(second.json()["issuances"]) == 2
    issuance_amounts = sorted([item["amount"] for item in second.json()["issuances"]])
    assert issuance_amounts == ["100.00", "250.00"]

    cards = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert cards.status_code == 200
    payload = cards.json()
    assert len(payload) == 1
    assert len(payload[0]["debts"]) == 1
    assert payload[0]["debts"][0]["principal"] == "350.00"


def test_debts_cards_search_by_counterparty_note_and_direction(client: TestClient):
    client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Олег",
            "direction": "lend",
            "principal": "200.00",
            "start_date": "2026-03-01",
            "note": "На ремонт кухни",
        },
    )
    client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Марина",
            "direction": "borrow",
            "principal": "150.00",
            "start_date": "2026-03-02",
            "note": "Возврат за аренду",
        },
    )

    by_name = client.get("/api/v1/debts/cards", params={"q": "олег", "include_closed": True})
    assert by_name.status_code == 200
    assert [item["counterparty"] for item in by_name.json()] == ["Олег"]

    by_note = client.get("/api/v1/debts/cards", params={"q": "ремонт", "include_closed": True})
    assert by_note.status_code == 200
    assert [item["counterparty"] for item in by_note.json()] == ["Олег"]

    by_direction = client.get("/api/v1/debts/cards", params={"q": "взял", "include_closed": True})
    assert by_direction.status_code == 200
    assert [item["counterparty"] for item in by_direction.json()] == ["Марина"]


def test_debts_cards_cache_is_invalidated_after_mutations(client: TestClient):
    initial = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert initial.status_code == 200
    assert initial.json() == []

    created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Олег",
            "direction": "lend",
            "principal": "200.00",
            "start_date": "2026-03-01",
            "note": "На ремонт кухни",
        },
    )
    assert created.status_code == 201
    debt_id = created.json()["id"]

    after_create = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert after_create.status_code == 200
    assert len(after_create.json()) == 1
    assert after_create.json()[0]["outstanding_total"] == "200.00"

    updated = client.patch(
        f"/api/v1/debts/{debt_id}",
        json={
            "principal": "250.00",
            "note": "Обновлено",
        },
    )
    assert updated.status_code == 200

    after_update = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert after_update.status_code == 200
    assert after_update.json()[0]["outstanding_total"] == "250.00"
    assert after_update.json()[0]["debts"][0]["note"] == "Обновлено"

    repaid = client.post(
        f"/api/v1/debts/{debt_id}/repayments",
        json={"amount": "250.00", "repayment_date": "2026-03-05"},
    )
    assert repaid.status_code == 201

    after_repayment = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert after_repayment.status_code == 200
    assert after_repayment.json()[0]["status"] == "closed"
    assert after_repayment.json()[0]["outstanding_total"] == "0.00"

    deleted = client.delete(f"/api/v1/debts/{debt_id}")
    assert deleted.status_code == 204

    after_delete = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert after_delete.status_code == 200
    assert after_delete.json() == []


def test_debts_support_original_currency_and_live_base_equivalent(client: TestClient):
    rate = client.put(
        "/api/v1/currency/rates/current",
        json={
            "currency": "USD",
            "rate": "3.20",
            "rate_date": "2026-03-28",
            "source": "manual",
        },
    )
    assert rate.status_code == 200

    created = client.post(
        "/api/v1/debts",
        json={
            "counterparty": "Денис",
            "direction": "lend",
            "principal": "100.00",
            "currency": "USD",
            "start_date": "2026-03-05",
            "note": "В долларах",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["currency"] == "USD"
    assert payload["base_currency"] == "BYN"
    assert payload["principal"] == "100.00"
    assert payload["current_rate"] == "3.200000"
    assert payload["current_base_principal"] == "320.00"
    assert payload["current_base_outstanding_total"] == "320.00"

    cards = client.get("/api/v1/debts/cards", params={"include_closed": True})
    assert cards.status_code == 200
    debt = cards.json()[0]["debts"][0]
    assert debt["currency"] == "USD"
    assert debt["current_base_outstanding_total"] == "320.00"
