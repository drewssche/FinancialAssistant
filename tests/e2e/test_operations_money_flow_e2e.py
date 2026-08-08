from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

sync_api = pytest.importorskip("playwright.sync_api", reason="playwright is not installed")


@pytest.fixture(scope="module")
def static_server_url() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    process = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=str(repo_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                break
        except Exception:
            time.sleep(0.1)
    else:
        process.terminate()
        process.wait(timeout=5)
        raise RuntimeError("Static server did not start in time")

    try:
        yield url
    finally:
        process.terminate()
        process.wait(timeout=5)


@pytest.fixture()
def page_with_money_flow_api_mock():
    preferences = {
        "preferences_version": 1,
        "data": {
            "dashboard": {"period": "day", "custom_date_from": "", "custom_date_to": ""},
            "operations": {"mode": "operations", "filters": {"kind": "", "q": "", "source": "all"}, "sort_preset": "date"},
            "ui": {"active_section": "dashboard", "timezone": "Europe/Minsk", "currency": "BYN", "currency_position": "suffix"},
            "currency": {"tracked_currencies": ["USD", "EUR"]},
        },
    }
    metrics = {"last_money_flow_source": "all", "last_money_flow_currency_scope": "all"}
    operations = []
    money_flow_items = [
        {
            "id": "fx:7001",
            "source_kind": "fx",
            "source_id": 7001,
            "flow_direction": "outflow",
            "event_date": "2026-03-06",
            "amount": "31.00",
            "original_amount": "31.00",
            "currency": "BYN",
            "base_currency": "BYN",
            "fx_rate": "1.000000",
            "title": "Покупка USD",
            "subtitle": "За BYN · курс 3.000000",
            "note": "покупка usd",
            "asset_currency": "USD",
            "quote_currency": "BYN",
            "trade_side": "buy",
            "can_open_source": True,
            "open_section": "currency",
            "open_label": "Сделка",
        },
        {
            "id": "debt-repayment:9102",
            "source_kind": "debt",
            "source_id": 9001,
            "flow_direction": "inflow",
            "event_date": "2026-03-04",
            "amount": "30.00",
            "original_amount": "30.00",
            "currency": "BYN",
            "base_currency": "BYN",
            "fx_rate": "1.000000",
            "title": "Мне вернули долг",
            "subtitle": "Иван",
            "note": "частично",
            "counterparty_id": 1,
            "counterparty_name": "Иван",
            "can_open_source": True,
            "open_section": "debts",
            "open_label": "Движения долга",
        },
        {
            "id": "debt-issuance:9101",
            "source_kind": "debt",
            "source_id": 9001,
            "flow_direction": "outflow",
            "event_date": "2026-03-03",
            "amount": "100.00",
            "original_amount": "100.00",
            "currency": "BYN",
            "base_currency": "BYN",
            "fx_rate": "1.000000",
            "title": "Я дал в долг",
            "subtitle": "Иван",
            "note": "на ремонт",
            "counterparty_id": 1,
            "counterparty_name": "Иван",
            "can_open_source": True,
            "open_section": "debts",
            "open_label": "Движения долга",
        },
        {
            "id": "operation:1",
            "source_kind": "operation",
            "source_id": 1,
            "flow_direction": "inflow",
            "event_date": "2026-03-01",
            "amount": "70.00",
            "original_amount": "70.00",
            "currency": "BYN",
            "base_currency": "BYN",
            "fx_rate": "1.000000",
            "title": "Без категории",
            "subtitle": "Обычная операция",
            "note": "salary",
            "source_plan_id": 77,
            "can_open_source": False,
            "receipt_items": [
                {
                    "name": "Кофе",
                    "quantity": "1.000",
                    "unit_price": "20.00",
                    "regular_unit_price": "25.00",
                    "is_discounted": True,
                    "line_total": "20.00",
                    "shop_name": "Кофейня",
                    "category_id": None,
                    "category_name": "Напитки",
                },
                {
                    "name": "Сэндвич",
                    "quantity": "1.000",
                    "unit_price": "20.00",
                    "line_total": "20.00",
                    "shop_name": "Кофейня",
                    "category_id": None,
                    "category_name": "Перекус",
                },
                {
                    "name": "Яблоки",
                    "quantity": "1.000",
                    "unit_price": "30.00",
                    "line_total": "30.00",
                    "shop_name": "Кофейня",
                    "category_id": None,
                    "category_name": "Фрукты",
                },
            ],
        },
        {
            "id": "operation:2",
            "source_kind": "operation",
            "source_id": 2,
            "flow_direction": "outflow",
            "event_date": "2026-03-02",
            "amount": "15.00",
            "original_amount": "5.00",
            "currency": "USD",
            "base_currency": "BYN",
            "fx_rate": "3.000000",
            "title": "Иностранная операция",
            "subtitle": "Обычная операция",
            "note": "foreign",
            "can_open_source": False,
        },
    ]
    debt_cards = [
        {
            "counterparty_id": 1,
            "counterparty": "Иван",
            "principal_total": "100.00",
            "repaid_total": "30.00",
            "outstanding_total": "70.00",
            "status": "active",
            "nearest_due_date": "2026-04-01",
            "debts": [
                {
                    "id": 9001,
                    "counterparty_id": 1,
                    "direction": "lend",
                    "principal": "100.00",
                    "repaid_total": "30.00",
                    "forgiven_total": "0.00",
                    "outstanding_total": "70.00",
                    "start_date": "2026-03-03",
                    "due_date": "2026-04-01",
                    "note": "на ремонт",
                    "created_at": "2026-03-03T10:00:00Z",
                    "issuances": [
                        {"id": 9101, "amount": "100.00", "current_base_amount": "100.00", "issuance_date": "2026-03-03", "note": "на ремонт"},
                    ],
                    "repayments": [
                        {"id": 9102, "amount": "30.00", "current_base_amount": "30.00", "repayment_date": "2026-03-04", "note": "частично"},
                    ],
                    "forgivenesses": [],
                }
            ],
        }
    ]
    currency_overview = {
        "base_currency": "BYN",
        "tracked_currencies": ["USD", "EUR"],
        "total_book_value": "0.00",
        "total_current_value": "0.00",
        "total_result_value": "0.00",
        "total_unrealized_result_value": "0.00",
        "total_realized_result_value": "0.00",
        "total_combined_result_value": "0.00",
        "buy_volume_base": "31.00",
        "sell_volume_base": "0.00",
        "buy_average_rate": "3.000000",
        "sell_average_rate": "0.000000",
        "buy_trades_count": 1,
        "sell_trades_count": 0,
        "active_positions": 1,
        "positions": [],
        "recent_trades": [
            {
                "id": 7001,
                "side": "buy",
                "asset_currency": "USD",
                "quote_currency": "BYN",
                "quantity": "10.00",
                "unit_price": "3.000000",
                "fee": "1.00",
                "trade_date": "2026-03-06",
                "note": "покупка usd",
            }
        ],
        "current_rates": [{"currency": "USD", "rate": "3.1000", "rate_date": "2026-03-27", "source": "nb"}],
    }

    def json_response(route, payload: dict | list, status: int = 200):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    def handler(route, request):
        parsed = urlparse(request.url)
        path = parsed.path
        query = parse_qs(parsed.query)
        method = request.method.upper()

        if path == "/api/v1/auth/telegram" and method == "POST":
            return json_response(route, {"access_token": "e2e-token", "token_type": "bearer"})
        if path == "/api/v1/users/me" and method == "GET":
            return json_response(route, {"id": 1, "display_name": "Money Flow User", "username": "money_flow_user", "status": "approved", "is_admin": False})
        if path == "/api/v1/preferences":
            if method == "GET":
                return json_response(route, preferences)
            if method == "PUT":
                payload = json.loads(request.post_data or "{}")
                preferences["preferences_version"] = payload.get("preferences_version", preferences["preferences_version"])
                preferences["data"] = payload.get("data", preferences["data"])
                return json_response(route, preferences)
        if path == "/api/v1/categories/groups" and method == "GET":
            return json_response(route, [])
        if path == "/api/v1/categories" and method == "GET":
            if "page" in query and "page_size" in query:
                return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
            return json_response(route, [])
        if path == "/api/v1/dashboard/summary" and method == "GET":
            return json_response(route, {"income_total": "0.00", "expense_total": "0.00", "balance": "0.00"})
        if path == "/api/v1/operations" and method == "GET":
            return json_response(route, {"items": operations, "total": len(operations), "page": 1, "page_size": 20})
        if path == "/api/v1/operations/1" and method == "GET":
            return json_response(route, {
                "id": 1,
                "kind": "income",
                "amount": "70.00",
                "original_amount": "70.00",
                "currency": "BYN",
                "base_currency": "BYN",
                "operation_date": "2026-03-01",
                "note": "salary",
                "receipt_items": money_flow_items[3]["receipt_items"],
            })
        if path == "/api/v1/operations/summary" and method == "GET":
            return json_response(route, {"income_total": "0.00", "expense_total": "0.00", "balance": "0.00", "total": 0})
        def filter_money_flow_items(source: str, currency_scope: str):
            items = money_flow_items if source == "all" else [item for item in money_flow_items if item["source_kind"] == source]
            if currency_scope == "base":
                return [item for item in items if item.get("currency") == item.get("base_currency")]
            if currency_scope == "foreign":
                return [item for item in items if item.get("currency") != item.get("base_currency")]
            return items

        if path == "/api/v1/operations/money-flow" and method == "GET":
            source = (query.get("source") or ["all"])[0]
            currency_scope = (query.get("currency_scope") or ["all"])[0]
            metrics["last_money_flow_source"] = source
            metrics["last_money_flow_currency_scope"] = currency_scope
            items = filter_money_flow_items(source, currency_scope)
            return json_response(route, {"items": items, "total": len(items), "page": 1, "page_size": 20})
        if path == "/api/v1/operations/money-flow/summary" and method == "GET":
            source = (query.get("source") or ["all"])[0]
            currency_scope = (query.get("currency_scope") or ["all"])[0]
            items = filter_money_flow_items(source, currency_scope)
            income_total = sum(float(item["amount"]) for item in items if item["flow_direction"] == "inflow")
            expense_total = sum(float(item["amount"]) for item in items if item["flow_direction"] == "outflow")
            return json_response(route, {
                "income_total": f"{income_total:.2f}",
                "expense_total": f"{expense_total:.2f}",
                "balance": f"{income_total - expense_total:.2f}",
                "total": len(items),
            })
        if path == "/api/v1/debts/cards" and method == "GET":
            return json_response(route, debt_cards)
        if path == "/api/v1/currency/overview" and method == "GET":
            return json_response(route, currency_overview)
        if path == "/api/v1/currency/available-balance" and method == "GET":
            return json_response(route, {
                "currency": (query.get("currency") or ["USD"])[0],
                "as_of": (query.get("as_of") or ["2026-03-05"])[0],
                "available_quantity": "100.000000",
                "current_quantity": "100.000000",
            })
        if path == "/api/v1/currency/trades" and method == "GET":
            trades = currency_overview["recent_trades"]
            return json_response(route, {"items": trades, "total": len(trades), "page": 1, "page_size": 20})
        if path == "/api/v1/currency/performance/history" and method == "GET":
            return json_response(route, {
                "base_currency": "BYN",
                "currency": "USD",
                "date_from": "2026-03-01",
                "date_to": "2026-03-31",
                "points": [
                    {
                        "point_date": "2026-03-06",
                        "book_value": "31.00",
                        "current_value": "31.00",
                        "unrealized_result_value": "0.00",
                        "realized_result_value": "0.00",
                        "total_result_value": "0.00",
                    }
                ],
            })
        if path == "/api/v1/test/money-flow-metrics" and method == "GET":
            return json_response(route, metrics)
        return json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")
        page = browser.new_page()
        page.add_init_script(
            """
            window.Telegram = {
              WebApp: {
                initData: "mock-init-data",
                ready() {},
                expand() {},
              }
            };
            """
        )
        page.route("**/api/v1/**", handler)
        try:
            yield page
        finally:
            browser.close()


def _open_app(page, static_server_url: str):
    page.goto(f"{static_server_url}/static/index.html")
    page.evaluate(
        """
        () => {
          window.Telegram = {
            WebApp: {
              initData: "mock-init-data",
              ready() {},
              expand() {},
            }
          };
        }
        """
    )
    page.evaluate("() => window.App.getRuntimeModule('session')?.refreshTelegramLoginUi?.()")
    if page.locator("#loginScreen:not(.hidden)").count():
        try:
            page.click("#telegramLoginBtn", timeout=1200)
        except sync_api.TimeoutError:
            # Telegram auto-login may hide the button between the visibility check and click.
            pass
    page.wait_for_selector("#appShell:not(.hidden)")


@pytest.mark.e2e
def test_operations_period_popover_changes_period(static_server_url: str, page_with_money_flow_api_mock):
    page = page_with_money_flow_api_mock
    _open_app(page, static_server_url)

    page.click("button[data-section='operations']")
    page.wait_for_selector("#operationsSection:not(.hidden)")
    page.locator("#operationsPeriodTrigger").click()
    page.wait_for_selector("#operationsPeriodPopover:not(.hidden)")
    page.locator("#operationsPeriodPopover [data-operations-period-choice='week']").click()
    page.wait_for_function("() => window.App.state.period === 'week'")

    assert page.evaluate("() => window.App.state.period") == "week"
    assert page.evaluate("() => window.App.state.customDateFrom") == ""
    assert page.evaluate("() => window.App.state.customDateTo") == ""


@pytest.mark.e2e
def test_operations_money_flow_mode_supports_source_filter_and_drilldown(static_server_url: str, page_with_money_flow_api_mock):
    page = page_with_money_flow_api_mock
    _open_app(page, static_server_url)

    page.click("button[data-section='operations']")
    page.wait_for_selector("#operationsSection:not(.hidden)")
    assert page.locator("#operationsModeTabs").count() == 0
    page.wait_for_selector("#operationsSourceTabs")
    page.wait_for_selector("#operationsBody tr")

    table_text = page.locator("#operationsBody").inner_text()
    assert "Я дал в долг" in table_text
    assert "Мне вернули долг" in table_text
    assert "FX" in table_text

    page.click("#operationsSourceTabs button[data-operations-source='debt']")
    page.wait_for_function(
        """
        () => document.querySelector('#operationsSourceTabs .segmented-btn.active')?.dataset.operationsSource === 'debt'
        """
    )
    page.wait_for_function(
        """
        async () => {
          const response = await fetch('/api/v1/test/money-flow-metrics');
          const payload = await response.json();
          return payload.last_money_flow_source === 'debt';
        }
        """
    )
    debt_only_text = page.locator("#operationsBody").inner_text()
    assert "Я дал в долг" in debt_only_text
    assert "Покупка USD" not in debt_only_text

    page.click("#operationsSourceTabs button[data-operations-source='all']")
    page.wait_for_function(
        """
        () => document.querySelector('#operationsSourceTabs .segmented-btn.active')?.dataset.operationsSource === 'all'
        """
    )
    page.wait_for_function(
        """
        async () => {
          const response = await fetch('/api/v1/test/money-flow-metrics');
          const payload = await response.json();
          return payload.last_money_flow_source === 'all';
        }
        """
    )
    page.click("#operationsCurrencyScopeTabs button[data-operations-currency-scope='foreign']")
    page.wait_for_function(
        """
        () => document.querySelector('#operationsCurrencyScopeTabs .segmented-btn.active')?.dataset.operationsCurrencyScope === 'foreign'
        """
    )
    page.wait_for_function(
        """
        async () => {
          const response = await fetch('/api/v1/test/money-flow-metrics');
          const payload = await response.json();
          return payload.last_money_flow_currency_scope === 'foreign';
        }
        """
    )
    foreign_only_text = page.locator("#operationsBody").inner_text()
    assert "Иностранная операция" in foreign_only_text
    assert "Я дал в долг" not in foreign_only_text

    page.evaluate(
        """
        () => window.App.actions.openMoneyFlowSource({
          sourceKind: 'debt',
          sourceId: '9001',
          mode: 'history',
        })
        """
    )
    page.wait_for_selector("#debtHistoryModal:not(.hidden)")
    assert "Иван" in page.locator("#debtHistoryModal").inner_text()

    page.evaluate(
        """
        () => window.App.actions.openMoneyFlowSource({
          sourceKind: 'fx',
          sourceId: '7001',
        })
        """
    )
    page.wait_for_selector("#currencySection:not(.hidden)")
    page.wait_for_selector("#createModal:not(.hidden)")
    assert page.locator("#createTitle").inner_text().strip() == "Редактировать валютную сделку"
    assert page.locator("#currencyAsset").input_value() == "USD"


@pytest.mark.e2e
def test_operations_receipt_chip_opens_same_positions_modal_as_kebab(
    static_server_url: str,
    page_with_money_flow_api_mock,
):
    page = page_with_money_flow_api_mock
    _open_app(page, static_server_url)

    page.click("button[data-section='operations']")
    page.wait_for_selector("#operationsSection:not(.hidden)")
    receipt_chip = page.locator(
        "#operationsBody tr[data-money-flow-source='operation'][data-money-flow-source-id='1'] "
        ".operation-category-stack button[data-receipt-view-id='1']"
    )
    receipt_chip.click()

    page.wait_for_selector("#operationReceiptModal:not(.hidden)")
    assert "Кофе" in page.locator("#operationReceiptModal").inner_text()


@pytest.mark.e2e
def test_operation_row_shows_receipt_categories_discount_and_clean_source(
    static_server_url: str,
    page_with_money_flow_api_mock,
):
    page = page_with_money_flow_api_mock
    _open_app(page, static_server_url)

    page.click("button[data-section='operations']")
    page.wait_for_selector("#operationsSection:not(.hidden)")
    row = page.locator(
        "#operationsBody tr[data-money-flow-source='operation'][data-money-flow-source-id='1']"
    )
    context = row.locator('td[data-label="Контекст"]')
    source = row.locator('td[data-label="Источник"]')

    assert "Напитки" in (context.text_content() or "")
    assert "Перекус" in (context.text_content() or "")
    assert "Фрукты" in (context.text_content() or "")
    assert "Скидка чека −6.7%" in (context.text_content() or "")
    assert "Операция" in (source.text_content() or "")
    assert "Из плана #77" in (source.text_content() or "")
    assert "Без категории" not in (source.text_content() or "")


@pytest.mark.e2e
def test_edit_operation_header_exposes_receipt_positions_action(
    static_server_url: str,
    page_with_money_flow_api_mock,
):
    page = page_with_money_flow_api_mock
    _open_app(page, static_server_url)

    page.evaluate(
        """
        async () => {
          const item = await window.App.core.requestJson('/api/v1/operations/1', {
            headers: window.App.core.authHeaders(),
          });
          await window.App.getRuntimeModule('operation-modal').openEditModal(item);
        }
        """
    )
    page.wait_for_selector("#editModal:not(.hidden)")
    expect_positions = page.locator("#editModalReceiptBtn")
    assert expect_positions.is_visible()
    assert expect_positions.get_attribute("title") == "Позиции"

    expect_positions.click()
    page.wait_for_selector("#operationReceiptModal:not(.hidden)")
    assert "Кофе" in page.locator("#operationReceiptModal").inner_text()


@pytest.mark.e2e
def test_old_foreign_operation_can_enable_direct_currency_settlement(
    static_server_url: str,
    page_with_money_flow_api_mock,
):
    page = page_with_money_flow_api_mock
    _open_app(page, static_server_url)

    page.evaluate(
        """
        async () => {
          await window.App.getRuntimeModule('operation-modal').openEditModal({
            id: 42,
            kind: 'expense',
            amount: '60.00',
            original_amount: '20.00',
            currency: 'USD',
            base_currency: 'BYN',
            fx_rate: '3.000000',
            operation_date: '2026-03-05',
            category_id: null,
            note: 'Старая операция в USD',
            receipt_items: [],
            fx_settlement: null,
          });
        }
        """
    )
    page.wait_for_selector("#editModal:not(.hidden)")
    page.click("#editFxSettlementToggle")

    page.wait_for_function("() => document.querySelector('#editFxSettlementBalance')?.textContent.includes('После операции')")
    assert page.locator("#editCurrency").input_value() == "USD"
    assert page.locator("#editFxSettlementAsset").input_value() == "USD"
    assert page.locator("#editFxSettlementQuantity").input_value() == "20.00"
    assert page.locator("#editFxSettlementUnitPrice").input_value() == "3.0000"
    assert page.locator("#editFxSettlementQuantity").get_attribute("readonly") is not None
    assert "80.00 USD" in page.locator("#editFxSettlementBalance").inner_text()

    payload = page.evaluate("() => window.App.getRuntimeModule('operation-modal').getEditFxSettlementPayload()")
    assert payload == {
        "asset_currency": "USD",
        "quantity": "20.00",
        "quote_total": "60.00",
        "unit_price": "3.000000",
        "note": None,
    }

    desktop_geometry = page.evaluate(
        """
        () => {
          const card = document.querySelector('#editModal .modal-card');
          const balance = document.querySelector('#editFxSettlementBalance');
          return {
            pageOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
            cardOverflow: card.scrollWidth > card.clientWidth + 1,
            balanceInside: balance.getBoundingClientRect().right <= card.getBoundingClientRect().right + 1,
          };
        }
        """
    )
    assert desktop_geometry == {"pageOverflow": False, "cardOverflow": False, "balanceInside": True}

    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(100)
    mobile_geometry = page.evaluate(
        """
        () => {
          const card = document.querySelector('#editModal .modal-card');
          const balance = document.querySelector('#editFxSettlementBalance');
          return {
            pageOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
            cardOverflow: card.scrollWidth > card.clientWidth + 1,
            balanceInside: balance.getBoundingClientRect().right <= card.getBoundingClientRect().right + 1,
          };
        }
        """
    )
    assert mobile_geometry == {"pageOverflow": False, "cardOverflow": False, "balanceInside": True}
