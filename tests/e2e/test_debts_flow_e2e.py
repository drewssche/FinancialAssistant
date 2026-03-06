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
def page_with_debts_api_mock():
    preferences = {
        "preferences_version": 1,
        "data": {
            "dashboard": {"period": "day", "custom_date_from": "", "custom_date_to": ""},
            "operations": {"filters": {"kind": "", "q": ""}},
            "ui": {"active_section": "dashboard", "timezone": "Europe/Moscow"},
        },
    }

    debt_cards = [
        {
            "counterparty_id": 1,
            "counterparty": "Анна",
            "principal_total": "100.00",
            "repaid_total": "0.00",
            "outstanding_total": "100.00",
            "status": "active",
            "nearest_due_date": "2026-03-10",
            "debts": [
                {
                    "id": 9001,
                    "counterparty_id": 1,
                    "direction": "lend",
                    "principal": "100.00",
                    "repaid_total": "0.00",
                    "outstanding_total": "100.00",
                    "start_date": "2026-03-05",
                    "due_date": "2026-03-10",
                    "note": "Тест",
                    "created_at": "2026-03-05T10:00:00Z",
                    "repayments": [],
                }
            ],
        }
    ]
    next_debt_id = 9010

    def json_response(route, payload: dict | list, status: int = 200):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    def handler(route, request):
        nonlocal next_debt_id
        parsed = urlparse(request.url)
        path = parsed.path
        query = parse_qs(parsed.query)
        method = request.method.upper()

        if path == "/api/v1/auth/dev" and method == "POST":
            return json_response(route, {"access_token": "e2e-token", "token_type": "bearer"})

        if path == "/api/v1/users/me" and method == "GET":
            return json_response(route, {"id": 1, "display_name": "Debt User", "username": "debt_user"})

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
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})

        if path == "/api/v1/debts/cards" and method == "GET":
            include_closed = (query.get("include_closed") or ["false"])[0] == "true"
            if include_closed:
                return json_response(route, debt_cards)
            only_active = [item for item in debt_cards if item["status"] == "active"]
            return json_response(route, only_active)

        if path == "/api/v1/debts" and method == "POST":
            payload = json.loads(request.post_data or "{}")
            counterparty = payload["counterparty"]
            principal = f"{float(payload['principal']):.2f}"
            new_debt = {
                "id": next_debt_id,
                "counterparty_id": next_debt_id,
                "direction": payload.get("direction", "lend"),
                "principal": principal,
                "repaid_total": "0.00",
                "outstanding_total": principal,
                "start_date": payload.get("start_date"),
                "due_date": payload.get("due_date"),
                "note": payload.get("note"),
                "created_at": "2026-03-05T10:00:00Z",
                "repayments": [],
            }
            next_debt_id += 1
            debt_cards.append(
                {
                    "counterparty_id": new_debt["counterparty_id"],
                    "counterparty": counterparty,
                    "principal_total": principal,
                    "repaid_total": "0.00",
                    "outstanding_total": principal,
                    "status": "active",
                    "nearest_due_date": payload.get("due_date"),
                    "debts": [new_debt],
                }
            )
            return json_response(route, new_debt, status=201)

        if path.startswith("/api/v1/debts/") and path.endswith("/repayments") and method == "POST":
            payload = json.loads(request.post_data or "{}")
            debt_id = int(path.split("/")[-2])
            amount = float(payload["amount"])
            for card in debt_cards:
                for debt in card["debts"]:
                    if debt["id"] != debt_id:
                        continue
                    repaid_total = float(debt["repaid_total"]) + amount
                    principal = float(debt["principal"])
                    outstanding = max(0.0, principal - repaid_total)
                    debt["repaid_total"] = f"{repaid_total:.2f}"
                    debt["outstanding_total"] = f"{outstanding:.2f}"
                    debt.setdefault("repayments", []).insert(
                        0,
                        {
                            "id": 1,
                            "debt_id": debt_id,
                            "amount": f"{amount:.2f}",
                            "repayment_date": payload["repayment_date"],
                            "note": payload.get("note"),
                            "created_at": "2026-03-05T10:00:00Z",
                        },
                    )
                    card["repaid_total"] = debt["repaid_total"]
                    card["outstanding_total"] = debt["outstanding_total"]
                    if outstanding <= 0:
                        card["status"] = "closed"
                    return json_response(route, debt["repayments"][0], status=201)
            return json_response(route, {"detail": "Debt not found"}, status=404)

        if path.startswith("/api/v1/debts/") and method == "PATCH":
            debt_id = int(path.split("/")[-1])
            payload = json.loads(request.post_data or "{}")
            for card in debt_cards:
                for debt in card["debts"]:
                    if debt["id"] != debt_id:
                        continue
                    if "counterparty" in payload:
                        card["counterparty"] = payload["counterparty"]
                    if "direction" in payload:
                        debt["direction"] = payload["direction"]
                    if "principal" in payload:
                        debt["principal"] = f"{float(payload['principal']):.2f}"
                    if "start_date" in payload:
                        debt["start_date"] = payload["start_date"]
                    if "due_date" in payload:
                        debt["due_date"] = payload["due_date"]
                    if "note" in payload:
                        debt["note"] = payload["note"]
                    repaid_total = float(debt["repaid_total"])
                    principal = float(debt["principal"])
                    debt["outstanding_total"] = f"{max(0.0, principal - repaid_total):.2f}"
                    card["principal_total"] = debt["principal"]
                    card["outstanding_total"] = debt["outstanding_total"]
                    return json_response(route, debt)
            return json_response(route, {"detail": "Debt not found"}, status=404)

        if path.startswith("/api/v1/debts/") and method == "DELETE":
            debt_id = int(path.split("/")[-1])
            for idx, card in enumerate(list(debt_cards)):
                debts = card.get("debts", [])
                rest = [item for item in debts if item["id"] != debt_id]
                if len(rest) != len(debts):
                    if rest:
                        card["debts"] = rest
                    else:
                        debt_cards.pop(idx)
                    return json_response(route, {}, status=204)
            return json_response(route, {"detail": "Debt not found"}, status=404)

        return json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")

        page = browser.new_page()
        page.route("**/api/v1/**", handler)
        try:
            yield page
        finally:
            browser.close()


@pytest.mark.e2e
def test_create_debt_from_operation_modal(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.goto(f"{static_server_url}/static/index.html")
    page.click("#devLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")

    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    page.click("#addDebtCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.click("#createEntryModeSwitch button[data-entry-mode='debt']")
    page.fill("#debtCounterparty", "Иван")
    page.click("#createDebtDirectionSwitch button[data-debt-direction='lend']")
    page.fill("#debtPrincipal", "250")
    page.fill("#debtStartDate", "2026-03-05")
    page.fill("#debtDueDate", "2026-03-20")
    page.fill("#debtNote", "Новый долг")
    page.click("#submitCreateOperationBtn")

    page.wait_for_selector("#createModal", state="hidden")
    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    assert page.locator("#debtsCards .debt-card h3", has_text="Иван").count() == 1


@pytest.mark.e2e
def test_repayment_moves_debt_to_closed(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.goto(f"{static_server_url}/static/index.html")
    page.click("#devLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")

    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    page.locator("tr:has(button[data-repay-debt-id='9001'])").hover()
    page.click("button[data-repay-debt-id='9001']", force=True)
    page.wait_for_selector("#debtRepaymentModal:not(.hidden)")
    page.fill("#repaymentAmount", "100")
    page.fill("#repaymentDate", "2026-03-06")
    page.click("#submitDebtRepaymentBtn")
    page.wait_for_selector("#debtRepaymentModal", state="hidden")

    assert "Долги не найдены" in page.locator("#debtsCards").inner_text()

    page.click("#debtStatusTabs button[data-debt-status='closed']")
    page.wait_for_timeout(200)
    assert page.locator("#debtsCards .debt-card h3", has_text="Анна").count() == 1


@pytest.mark.e2e
def test_edit_and_delete_debt(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.goto(f"{static_server_url}/static/index.html")
    page.click("#devLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")

    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    page.locator("tr:has(button[data-edit-debt-id='9001'])").hover()
    page.click("button[data-edit-debt-id='9001']", force=True)
    page.wait_for_selector("#createModal:not(.hidden)")
    page.fill("#debtCounterparty", "Анна Обновл.")
    page.fill("#debtPrincipal", "150")
    page.click("#submitCreateOperationBtn")
    page.wait_for_selector("#createModal", state="hidden")
    assert page.locator("#debtsCards .debt-card h3", has_text="Анна Обновл.").count() == 1

    page.locator("tr:has(button[data-delete-debt-id='9001'])").hover()
    page.click("button[data-delete-debt-id='9001']", force=True)
    page.click("#confirmDeleteBtn")
    page.wait_for_timeout(250)
    assert "Долги не найдены" in page.locator("#debtsCards").inner_text()
