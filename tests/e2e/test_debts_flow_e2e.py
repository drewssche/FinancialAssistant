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


def _restore_mock_telegram(page):
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


def _login_via_mock_telegram(page):
    _restore_mock_telegram(page)
    page.evaluate("() => window.App.getRuntimeModule('session')?.refreshTelegramLoginUi?.()")
    try:
        page.locator("#telegramLoginBtn").wait_for(state="visible", timeout=1200)
        page.click("#telegramLoginBtn")
        page.wait_for_selector("#appShell:not(.hidden)")
    except Exception:
        page.wait_for_selector("#appShell:not(.hidden)")


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
                    "forgiven_total": "0.00",
                    "closure_reason": None,
                    "outstanding_total": "100.00",
                    "start_date": "2026-03-05",
                    "due_date": "2026-03-10",
                    "note": "Тест",
                    "created_at": "2026-03-05T10:00:00Z",
                    "repayments": [],
                    "forgivenesses": [],
                    "issuances": [
                        {
                            "id": 1,
                            "debt_id": 9001,
                            "amount": "100.00",
                            "issuance_date": "2026-03-05",
                            "note": "Тест",
                            "created_at": "2026-03-05T10:00:00Z",
                        }
                    ],
                }
            ],
        }
    ]
    next_debt_id = 9010
    forgiveness_calls = []

    def json_response(route, payload: dict | list, status: int = 200):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    def normalize_name(value: str) -> str:
        return " ".join((value or "").split()).casefold()

    def fmt_amount(value: float) -> str:
        return f"{value:.2f}"

    def recalc_debt(debt: dict) -> None:
        principal = float(debt.get("principal") or 0.0)
        repaid = float(debt.get("repaid_total") or 0.0)
        forgiven = float(debt.get("forgiven_total") or 0.0)
        debt["outstanding_total"] = fmt_amount(max(0.0, principal - repaid - forgiven))
        if float(debt["outstanding_total"]) <= 0 and forgiven > 0:
            debt["closure_reason"] = "forgiven"
        elif float(debt["outstanding_total"]) > 0:
            debt["closure_reason"] = None

    def recalc_card(card: dict) -> None:
        principal_total = 0.0
        repaid_total = 0.0
        outstanding_total = 0.0
        nearest_due_date = None
        for debt in card.get("debts", []):
            recalc_debt(debt)
            principal_total += float(debt.get("principal") or 0.0)
            repaid_total += float(debt.get("repaid_total") or 0.0)
            outstanding = float(debt.get("outstanding_total") or 0.0)
            outstanding_total += outstanding
            due_date = debt.get("due_date")
            if outstanding > 0 and due_date:
                nearest_due_date = due_date if nearest_due_date is None else min(nearest_due_date, due_date)
        card["principal_total"] = fmt_amount(principal_total)
        card["repaid_total"] = fmt_amount(repaid_total)
        card["outstanding_total"] = fmt_amount(outstanding_total)
        card["status"] = "active" if outstanding_total > 0 else "closed"
        card["nearest_due_date"] = nearest_due_date

    def find_card_by_counterparty(counterparty: str) -> dict | None:
        wanted = normalize_name(counterparty)
        for card in debt_cards:
            if normalize_name(card.get("counterparty", "")) == wanted:
                return card
        return None

    def find_debt(debt_id: int) -> tuple[dict, dict] | tuple[None, None]:
        for card in debt_cards:
            for debt in card.get("debts", []):
                if debt.get("id") == debt_id:
                    return card, debt
        return None, None

    def remove_empty_cards() -> None:
        debt_cards[:] = [card for card in debt_cards if card.get("debts")]

    def add_issuance(debt: dict, amount: float, issuance_date: str | None, note: str | None = None) -> None:
        issuances = debt.setdefault("issuances", [])
        issuances.insert(
            0,
            {
                "id": len(issuances) + 1,
                "debt_id": debt["id"],
                "amount": fmt_amount(amount),
                "issuance_date": issuance_date,
                "note": note,
                "created_at": "2026-03-05T10:00:00Z",
            },
        )

    for seed_card in debt_cards:
        recalc_card(seed_card)

    def handler(route, request):
        nonlocal next_debt_id
        parsed = urlparse(request.url)
        path = parsed.path
        query = parse_qs(parsed.query)
        method = request.method.upper()

        if path == "/api/v1/auth/telegram" and method == "POST":
            return json_response(route, {"access_token": "e2e-token", "token_type": "bearer"})

        if path == "/api/v1/auth/public-config" and method == "GET":
            return json_response(route, {"telegram_bot_username": "FinanceWeaselBot", "browser_login_available": True})

        if path == "/api/v1/users/me" and method == "GET":
            return json_response(route, {"id": 1, "display_name": "Debt User", "username": "debt_user", "status": "approved", "is_admin": False})

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
            return json_response(
                route,
                {
                    "date_from": "2026-03-01",
                    "date_to": "2026-03-31",
                    "income_total": "0.00",
                    "expense_total": "0.00",
                    "balance": "0.00",
                    "debt_lend_outstanding": "0.00",
                    "debt_borrow_outstanding": "0.00",
                    "debt_net_position": "0.00",
                    "active_debt_cards": 0,
                },
            )

        if path == "/api/v1/dashboard/debts/preview" and method == "GET":
            limit = max(1, int((query.get("limit") or ["6"])[0]))
            for card in debt_cards:
                recalc_card(card)
            only_active = [item for item in debt_cards if item["status"] == "active"]
            return json_response(route, only_active[:limit])

        if path == "/api/v1/dashboard/analytics/calendar" and method == "GET":
            month = (query.get("month") or ["2026-03"])[0]
            return json_response(
                route,
                {
                    "month": month,
                    "month_start": f"{month}-01",
                    "month_end": f"{month}-31",
                    "income_total": "0.00",
                    "expense_total": "0.00",
                    "balance": "0.00",
                    "operations_count": 0,
                    "weeks": [
                        {
                            "week_start": f"{month}-01",
                            "week_end": f"{month}-07",
                            "income_total": "0.00",
                            "expense_total": "0.00",
                            "balance": "0.00",
                            "operations_count": 0,
                            "days": [
                                {
                                    "date": f"{month}-{day:02d}",
                                    "in_month": True,
                                    "income_total": "0.00",
                                    "expense_total": "0.00",
                                    "balance": "0.00",
                                    "operations_count": 0,
                                }
                                for day in range(1, 8)
                            ],
                        }
                    ],
                },
            )

        if path == "/api/v1/dashboard/analytics/trend" and method == "GET":
            return json_response(
                route,
                {
                    "period": (query.get("period") or ["month"])[0],
                    "granularity": (query.get("granularity") or ["day"])[0],
                    "date_from": "2026-03-01",
                    "date_to": "2026-03-07",
                    "income_total": "0.00",
                    "expense_total": "0.00",
                    "balance": "0.00",
                    "operations_count": 0,
                    "prev_income_total": "0.00",
                    "prev_expense_total": "0.00",
                    "prev_balance": "0.00",
                    "prev_operations_count": 0,
                    "income_change_pct": 0.0,
                    "expense_change_pct": 0.0,
                    "balance_change_pct": 0.0,
                    "operations_change_pct": 0.0,
                    "points": [
                        {
                            "bucket_start": "2026-03-01",
                            "bucket_end": "2026-03-01",
                            "label": "01.03.2026",
                            "income_total": "0.00",
                            "expense_total": "0.00",
                            "balance": "0.00",
                            "operations_count": 0,
                        }
                    ],
                },
            )

        if path == "/api/v1/operations" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})

        if path == "/api/v1/test/seed-debts" and method == "POST":
            payload = json.loads(request.post_data or "{}")
            count = max(0, int(payload.get("count", 0)))
            direction = payload.get("direction", "lend")
            principal_amount = float(payload.get("principal", 100.0))
            start_date = payload.get("start_date", "2026-03-05")
            due_date = payload.get("due_date")
            for idx in range(count):
                counterparty = f"Контрагент {idx + 1:02d}"
                principal = fmt_amount(principal_amount)
                new_debt = {
                    "id": next_debt_id,
                    "counterparty_id": next_debt_id,
                    "direction": direction,
                    "principal": principal,
                    "repaid_total": "0.00",
                    "outstanding_total": principal,
                    "start_date": start_date,
                    "due_date": due_date,
                    "note": f"seed debt {idx + 1}",
                    "created_at": "2026-03-05T10:00:00Z",
                    "repayments": [],
                    "issuances": [],
                }
                add_issuance(new_debt, amount=principal_amount, issuance_date=start_date, note=new_debt["note"])
                next_debt_id += 1
                new_card = {
                    "counterparty_id": new_debt["counterparty_id"],
                    "counterparty": counterparty,
                    "principal_total": principal,
                    "repaid_total": "0.00",
                    "outstanding_total": principal,
                    "status": "active",
                    "nearest_due_date": due_date,
                    "debts": [new_debt],
                }
                recalc_card(new_card)
                debt_cards.append(new_card)
            return json_response(route, {"seeded": count}, status=201)

        if path == "/api/v1/test/seed-debt-history" and method == "POST":
            payload = json.loads(request.post_data or "{}")
            debt_id = int(payload.get("debt_id", 0))
            count = max(0, int(payload.get("count", 0)))
            card, debt = find_debt(debt_id)
            if not card or not debt:
                return json_response(route, {"detail": "Debt not found"}, status=404)
            base_idx = len(debt.get("issuances", []))
            for idx in range(count):
                add_issuance(
                    debt,
                    amount=10.0,
                    issuance_date=f"2026-03-{(idx % 28) + 1:02d}",
                    note=f"seed issuance {base_idx + idx + 1}",
                )
            recalc_card(card)
            return json_response(route, {"seeded": count}, status=201)

        if path == "/api/v1/debts/cards" and method == "GET":
            include_closed = (query.get("include_closed") or ["false"])[0] == "true"
            for card in debt_cards:
                recalc_card(card)
            if include_closed:
                return json_response(route, debt_cards)
            only_active = [item for item in debt_cards if item["status"] == "active"]
            return json_response(route, only_active)

        if path == "/api/v1/plans" and method == "GET":
            return json_response(route, {"items": [], "total": 0})

        if path == "/api/v1/plans/history" and method == "GET":
            return json_response(route, {"items": [], "total": 0})

        if path == "/api/v1/debts" and method == "POST":
            payload = json.loads(request.post_data or "{}")
            counterparty = " ".join(str(payload["counterparty"]).split())
            direction = payload.get("direction", "lend")
            principal_amount = float(payload["principal"])
            principal = fmt_amount(principal_amount)
            existing_card = find_card_by_counterparty(counterparty)
            merge_target = None
            if existing_card:
                for debt in existing_card.get("debts", []):
                    if debt.get("direction") == direction and float(debt.get("outstanding_total") or 0.0) > 0:
                        merge_target = debt
                        break
            if merge_target:
                merge_target["principal"] = fmt_amount(float(merge_target["principal"]) + principal_amount)
                recalc_debt(merge_target)
                add_issuance(merge_target, amount=principal_amount, issuance_date=payload.get("start_date"), note=payload.get("note"))
                recalc_card(existing_card)
                return json_response(route, merge_target, status=201)

            new_debt = {
                "id": next_debt_id,
                "counterparty_id": existing_card["counterparty_id"] if existing_card else next_debt_id,
                "direction": direction,
                "principal": principal,
                "repaid_total": "0.00",
                "forgiven_total": "0.00",
                "closure_reason": None,
                "outstanding_total": principal,
                "start_date": payload.get("start_date"),
                "due_date": payload.get("due_date"),
                "note": payload.get("note"),
                "created_at": "2026-03-05T10:00:00Z",
                "repayments": [],
                "forgivenesses": [],
                "issuances": [],
            }
            add_issuance(new_debt, amount=principal_amount, issuance_date=payload.get("start_date"), note=payload.get("note"))
            next_debt_id += 1
            if existing_card:
                existing_card["debts"].append(new_debt)
                recalc_card(existing_card)
            else:
                new_card = {
                    "counterparty_id": new_debt["counterparty_id"],
                    "counterparty": counterparty,
                    "principal_total": principal,
                    "repaid_total": "0.00",
                    "outstanding_total": principal,
                    "status": "active",
                    "nearest_due_date": payload.get("due_date"),
                    "debts": [new_debt],
                }
                recalc_card(new_card)
                debt_cards.append(new_card)
            return json_response(route, new_debt, status=201)

        if path.startswith("/api/v1/debts/") and path.endswith("/repayments") and method == "POST":
            payload = json.loads(request.post_data or "{}")
            debt_id = int(path.split("/")[-2])
            amount = float(payload["amount"])
            card, debt = find_debt(debt_id)
            if card and debt:
                principal = float(debt["principal"])
                repaid_before = float(debt["repaid_total"])
                outstanding_before = max(0.0, principal - repaid_before)
                applied_amount = min(amount, outstanding_before)
                debt["repaid_total"] = fmt_amount(repaid_before + applied_amount)
                recalc_debt(debt)
                repayments = debt.setdefault("repayments", [])
                repayment_record = {
                    "id": len(repayments) + 1,
                    "debt_id": debt_id,
                    "amount": fmt_amount(applied_amount),
                    "repayment_date": payload["repayment_date"],
                    "note": payload.get("note"),
                    "created_at": "2026-03-05T10:00:00Z",
                }
                repayments.insert(0, repayment_record)

                overpay = amount - applied_amount
                if overpay > 0:
                    reverse_direction = "borrow" if debt["direction"] == "lend" else "lend"
                    reverse_debt = None
                    for candidate in card.get("debts", []):
                        if candidate["id"] == debt_id:
                            continue
                        if candidate.get("direction") == reverse_direction and float(candidate.get("outstanding_total") or 0.0) > 0:
                            reverse_debt = candidate
                            break
                    if reverse_debt:
                        reverse_debt["principal"] = fmt_amount(float(reverse_debt["principal"]) + overpay)
                        recalc_debt(reverse_debt)
                        add_issuance(
                            reverse_debt,
                            amount=overpay,
                            issuance_date=payload.get("repayment_date"),
                            note=f"Переплата по долгу #{debt_id}",
                        )
                    else:
                        reverse_id = next_debt_id
                        next_debt_id += 1
                        reverse_debt = {
                            "id": reverse_id,
                            "counterparty_id": debt["counterparty_id"],
                            "direction": reverse_direction,
                            "principal": fmt_amount(overpay),
                            "repaid_total": "0.00",
                            "forgiven_total": "0.00",
                            "closure_reason": None,
                            "outstanding_total": fmt_amount(overpay),
                            "start_date": payload.get("repayment_date"),
                            "due_date": None,
                            "note": f"Переплата по долгу #{debt_id}",
                            "created_at": "2026-03-05T10:00:00Z",
                            "repayments": [],
                            "forgivenesses": [],
                            "issuances": [],
                        }
                        add_issuance(
                            reverse_debt,
                            amount=overpay,
                            issuance_date=payload.get("repayment_date"),
                            note=reverse_debt["note"],
                        )
                        card["debts"].append(reverse_debt)
                recalc_card(card)
                return json_response(route, repayment_record, status=201)
            return json_response(route, {"detail": "Debt not found"}, status=404)

        if path.startswith("/api/v1/debts/") and path.endswith("/forgivenesses") and method == "POST":
            payload = json.loads(request.post_data or "{}")
            debt_id = int(path.split("/")[-2])
            amount = float(payload["amount"])
            forgiveness_calls.append({"debt_id": debt_id, **payload})
            card, debt = find_debt(debt_id)
            if card and debt:
                principal = float(debt["principal"])
                repaid_before = float(debt.get("repaid_total") or 0.0)
                forgiven_before = float(debt.get("forgiven_total") or 0.0)
                outstanding_before = max(0.0, principal - repaid_before - forgiven_before)
                applied_amount = min(amount, outstanding_before)
                debt["forgiven_total"] = fmt_amount(forgiven_before + applied_amount)
                recalc_debt(debt)
                forgivenesses = debt.setdefault("forgivenesses", [])
                forgiveness_record = {
                    "id": len(forgivenesses) + 1,
                    "debt_id": debt_id,
                    "amount": fmt_amount(applied_amount),
                    "forgiven_date": payload["forgiven_date"],
                    "note": payload.get("note"),
                    "created_at": "2026-03-05T10:00:00Z",
                }
                forgivenesses.insert(0, forgiveness_record)
                recalc_card(card)
                return json_response(route, forgiveness_record, status=201)
            return json_response(route, {"detail": "Debt not found"}, status=404)

        if path.startswith("/api/v1/debts/") and method == "PATCH":
            debt_id = int(path.split("/")[-1])
            payload = json.loads(request.post_data or "{}")
            source_card, debt = find_debt(debt_id)
            if source_card and debt:
                target_card = source_card
                if "counterparty" in payload:
                    normalized_counterparty = " ".join(str(payload["counterparty"]).split())
                    matched_card = find_card_by_counterparty(normalized_counterparty)
                    if matched_card and matched_card is not source_card:
                        target_card = matched_card
                    else:
                        source_card["counterparty"] = normalized_counterparty

                if "direction" in payload:
                    debt["direction"] = payload["direction"]
                if "principal" in payload:
                    debt["principal"] = fmt_amount(float(payload["principal"]))
                if "start_date" in payload:
                    debt["start_date"] = payload["start_date"]
                if "due_date" in payload:
                    debt["due_date"] = payload["due_date"]
                if "note" in payload:
                    debt["note"] = payload["note"]
                recalc_debt(debt)

                if target_card is not source_card:
                    merge_target = None
                    for candidate in target_card.get("debts", []):
                        if candidate["id"] == debt["id"]:
                            continue
                        if candidate.get("direction") == debt.get("direction") and float(candidate.get("outstanding_total") or 0.0) > 0:
                            merge_target = candidate
                            break
                    if merge_target:
                        merge_target["principal"] = fmt_amount(float(merge_target["principal"]) + float(debt["principal"]))
                        merge_target["repaid_total"] = fmt_amount(float(merge_target["repaid_total"]) + float(debt["repaid_total"]))
                        merge_target.setdefault("repayments", []).extend(debt.get("repayments", []))
                        merge_target.setdefault("issuances", []).extend(debt.get("issuances", []))
                        recalc_debt(merge_target)
                        source_card["debts"] = [item for item in source_card.get("debts", []) if item["id"] != debt_id]
                        recalc_card(target_card)
                        recalc_card(source_card)
                        remove_empty_cards()
                        return json_response(route, merge_target)

                    source_card["debts"] = [item for item in source_card.get("debts", []) if item["id"] != debt_id]
                    debt["counterparty_id"] = target_card["counterparty_id"]
                    target_card["debts"].append(debt)
                    recalc_card(target_card)
                    recalc_card(source_card)
                    remove_empty_cards()
                    return json_response(route, debt)

                recalc_card(source_card)
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
                        recalc_card(card)
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
            page._forgiveness_calls = forgiveness_calls
            yield page
        finally:
            browser.close()


@pytest.mark.e2e
def test_create_debt_from_operation_modal(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.goto(f"{static_server_url}/static/index.html")
    _login_via_mock_telegram(page)

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
    _login_via_mock_telegram(page)

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
def test_debt_history_action_closes_popover_before_modal(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.goto(f"{static_server_url}/static/index.html")
    _login_via_mock_telegram(page)

    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    page.click("button[data-table-menu-trigger='debt-9001']")
    page.wait_for_selector(".table-kebab-popover[data-table-menu='debt-9001']:not(.hidden)")
    page.click("button[data-history-debt-id='9001']")
    page.wait_for_selector("#debtHistoryModal:not(.hidden)")

    assert page.locator(".table-kebab-popover[data-table-menu='debt-9001']").is_hidden()


@pytest.mark.e2e
def test_dashboard_debt_actions_load_full_debt_cache_before_open(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.goto(f"{static_server_url}/static/index.html")
    _login_via_mock_telegram(page)

    page.wait_for_selector("button[data-dashboard-history-debt-id='9001']")
    page.click("button[data-dashboard-history-debt-id='9001']")
    page.wait_for_selector("#debtHistoryModal:not(.hidden)")
    assert "Начальная сумма" in page.locator("#debtHistoryItems").inner_text()

    page.click("#closeDebtHistoryModalBtn")
    page.wait_for_selector("#debtHistoryModal", state="hidden")
    page.click("button[data-dashboard-repay-debt-id='9001']")
    page.wait_for_selector("#debtRepaymentModal:not(.hidden)")
    assert page.locator("#repaymentDebtId").input_value() == "9001"


@pytest.mark.e2e
def test_repayment_presets_fill_amount_from_current_outstanding(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.goto(f"{static_server_url}/static/index.html")
    _login_via_mock_telegram(page)

    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    page.locator("tr:has(button[data-repay-debt-id='9001'])").hover()
    page.click("button[data-repay-debt-id='9001']", force=True)
    page.wait_for_selector("#debtRepaymentModal:not(.hidden)")

    page.click("#repaymentPresetRow button[data-repayment-preset='0.25']")
    assert page.locator("#repaymentAmount").input_value() == "25.00"

    page.click("#repaymentPresetRow button[data-repayment-preset='0.5']")
    assert page.locator("#repaymentAmount").input_value() == "50.00"

    page.click("#repaymentPresetRow button[data-repayment-preset='1']")
    assert page.locator("#repaymentAmount").input_value() == "100.00"


@pytest.mark.e2e
def test_mobile_repayment_modal_keeps_amount_field_above_sticky_cta(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{static_server_url}/static/index.html")
    _login_via_mock_telegram(page)

    page.click("#mobileNavToggleBtn")
    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    page.evaluate("window.App.actions.openDebtRepaymentModal(9001)")
    page.wait_for_selector("#debtRepaymentModal:not(.hidden)")
    page.fill("#repaymentAmount", "50")
    page.fill("#repaymentDate", "2026-03-06")
    page.fill("#repaymentNote", "Мобильная проверка")
    page.wait_for_timeout(200)

    geometry = page.evaluate(
        """
        () => {
          const amountField = document.querySelector('#repaymentAmountField');
          const footer = document.querySelector('#debtRepaymentModal .modal-footer');
          if (!amountField || !footer) {
            return null;
          }
          const amountRect = amountField.getBoundingClientRect();
          const footerRect = footer.getBoundingClientRect();
          return {
            amountTop: amountRect.top,
            amountBottom: amountRect.bottom,
            footerTop: footerRect.top,
            footerBottom: footerRect.bottom,
          };
        }
        """
    )

    assert geometry is not None
    assert geometry["amountTop"] < geometry["footerTop"]
    assert geometry["amountBottom"] <= geometry["footerTop"] + 2


@pytest.mark.e2e
def test_debts_cards_infinite_scroll_loads_next_batch(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.goto(f"{static_server_url}/static/index.html")
    _login_via_mock_telegram(page)

    page.evaluate(
        """
        async () => {
          const response = await fetch('/api/v1/test/seed-debts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count: 54, direction: 'lend', principal: 120, start_date: '2026-03-05' }),
          });
          if (!response.ok) {
            throw new Error('seed failed');
          }
        }
        """
    )

    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    page.evaluate("window.App.core.invalidateUiRequestCache('debts')")
    page.evaluate("window.App.actions.loadDebtsCards({ force: true })")
    initial_count = page.locator("#debtsCards .debt-card").count()
    assert 20 <= initial_count < 55
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_function(f"document.querySelectorAll('#debtsCards .debt-card').length > {initial_count}")


@pytest.mark.e2e
def test_debt_history_infinite_scroll_loads_next_batch(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.goto(f"{static_server_url}/static/index.html")
    _login_via_mock_telegram(page)

    page.evaluate(
        """
        async () => {
          const response = await fetch('/api/v1/test/seed-debt-history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ debt_id: 9001, count: 70 }),
          });
          if (!response.ok) {
            throw new Error('seed history failed');
          }
        }
        """
    )

    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    page.evaluate("window.App.core.invalidateUiRequestCache('debts')")
    page.evaluate("window.App.actions.loadDebtsCards({ force: true })")
    page.evaluate("window.App.actions.openDebtHistoryModal(9001)")
    page.wait_for_selector("#debtHistoryModal:not(.hidden)")
    initial_count = page.locator("#debtHistoryItems .debt-history-event").count()
    assert 20 <= initial_count < 71
    page.evaluate(
        """
        () => {
          const list = document.getElementById('debtHistoryList');
          if (list) {
            list.scrollTo(0, list.scrollHeight);
          }
        }
        """
    )
    page.wait_for_function(f"document.querySelectorAll('#debtHistoryItems .debt-history-event').length > {initial_count}")


@pytest.mark.e2e
def test_mobile_debt_history_modal_keeps_scroll_region_visible(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{static_server_url}/static/index.html")
    _login_via_mock_telegram(page)

    page.evaluate(
        """
        async () => {
          const response = await fetch('/api/v1/test/seed-debt-history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ debt_id: 9001, count: 40 }),
          });
          if (!response.ok) {
            throw new Error('seed history failed');
          }
        }
        """
    )

    page.click("#mobileNavToggleBtn")
    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    page.evaluate("window.App.core.invalidateUiRequestCache('debts')")
    page.evaluate("window.App.actions.loadDebtsCards({ force: true })")
    page.evaluate("window.App.actions.openDebtHistoryModal(9001)")
    page.wait_for_selector("#debtHistoryModal:not(.hidden)")
    page.wait_for_timeout(150)

    geometry = page.evaluate(
        """
        () => {
          const list = document.querySelector('#debtHistoryList');
          const modalCard = document.querySelector('#debtHistoryModal .modal-card');
          const items = document.querySelectorAll('#debtHistoryItems .debt-history-event');
          if (!list || !modalCard || !items.length) {
            return null;
          }
          const listRect = list.getBoundingClientRect();
          const modalRect = modalCard.getBoundingClientRect();
          return {
            listTop: listRect.top,
            listBottom: listRect.bottom,
            modalTop: modalRect.top,
            modalBottom: modalRect.bottom,
            itemsCount: items.length,
            scrollHeight: list.scrollHeight,
            clientHeight: list.clientHeight,
          };
        }
        """
    )

    assert geometry is not None
    assert geometry["itemsCount"] > 0
    assert geometry["listTop"] >= geometry["modalTop"]
    assert geometry["listBottom"] <= geometry["modalBottom"] + 2
    assert geometry["scrollHeight"] >= geometry["clientHeight"]


@pytest.mark.e2e
def test_debt_history_uses_directional_event_labels(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.goto(f"{static_server_url}/static/index.html")
    _login_via_mock_telegram(page)

    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    page.locator("tr:has(button[data-repay-debt-id='9001'])").hover()
    page.click("button[data-repay-debt-id='9001']", force=True)
    page.wait_for_selector("#debtRepaymentModal:not(.hidden)")
    page.fill("#repaymentAmount", "10")
    page.fill("#repaymentDate", "2026-03-06")
    page.click("#submitDebtRepaymentBtn")
    page.wait_for_selector("#debtRepaymentModal", state="hidden")

    page.evaluate("window.App.actions.openDebtHistoryModal(9001)")
    page.wait_for_selector("#debtHistoryModal:not(.hidden)")
    assert page.locator("#debtHistoryItems .debt-history-event strong", has_text="Погашение: мне вернули").count() >= 1


@pytest.mark.e2e
def test_edit_and_delete_debt(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.goto(f"{static_server_url}/static/index.html")
    _login_via_mock_telegram(page)

    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    page.evaluate("window.App.actions.openEditDebtModal(9001)")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.fill("#debtCounterparty", "Анна Обновл.")
    page.fill("#debtPrincipal", "150")
    page.click("#submitCreateOperationBtn")
    page.wait_for_selector("#createModal", state="hidden")
    assert page.locator("#debtsCards .debt-card h3", has_text="Анна Обновл.").count() == 1

    page.evaluate("window.App.actions.deleteDebtFlow(9001)")
    page.wait_for_selector("#confirmModal:not(.hidden)")
    page.click("#confirmDeleteBtn")
    page.wait_for_timeout(250)
    assert "Долги не найдены" in page.locator("#debtsCards").inner_text()


@pytest.mark.e2e
def test_overpay_creates_reverse_direction_debt(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.goto(f"{static_server_url}/static/index.html")
    _login_via_mock_telegram(page)

    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    page.locator("tr:has(button[data-repay-debt-id='9001'])").hover()
    page.click("button[data-repay-debt-id='9001']", force=True)
    page.wait_for_selector("#debtRepaymentModal:not(.hidden)")
    page.fill("#repaymentAmount", "120")
    page.fill("#repaymentDate", "2026-03-06")
    page.click("#submitDebtRepaymentBtn")
    page.wait_for_selector("#debtRepaymentModal", state="hidden")

    card = page.locator("#debtsCards .debt-card", has_text="Анна")
    card.wait_for()
    assert card.locator("tr:has-text('Я взял')").count() == 1
    assert card.locator("tr:has-text('20,00 BYN')").count() >= 1


@pytest.mark.e2e
def test_edit_counterparty_name_merges_with_existing_card(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.goto(f"{static_server_url}/static/index.html")
    _login_via_mock_telegram(page)

    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    page.click("#addDebtCta")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.click("#createEntryModeSwitch button[data-entry-mode='debt']")
    page.fill("#debtCounterparty", "Борис")
    page.click("#createDebtDirectionSwitch button[data-debt-direction='lend']")
    page.fill("#debtPrincipal", "250")
    page.fill("#debtStartDate", "2026-03-05")
    page.click("#submitCreateOperationBtn")
    page.wait_for_selector("#createModal", state="hidden")
    assert page.locator("#debtsCards .debt-card h3", has_text="Борис").count() == 1

    page.evaluate("window.App.actions.openEditDebtModal(9001)")
    page.wait_for_selector("#createModal:not(.hidden)")
    page.fill("#debtCounterparty", "борис")
    page.click("#submitCreateOperationBtn")
    page.wait_for_selector("#createModal", state="hidden")

    page.wait_for_timeout(200)
    assert page.locator("#debtsCards .debt-card h3", has_text="Анна").count() == 0
    boris_card = page.locator("#debtsCards .debt-card", has_text="Борис")
    assert boris_card.count() == 1
    assert boris_card.locator("tbody tr").count() == 1
    assert boris_card.locator("tbody tr:has-text('350,00 BYN')").count() >= 1


@pytest.mark.e2e
def test_dashboard_debts_toggle_applies_without_page_reload(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.goto(f"{static_server_url}/static/index.html")
    _login_via_mock_telegram(page)

    page.click("button[data-section='settings']")
    page.wait_for_selector("#settingsSection:not(.hidden)")
    page.uncheck("#showDashboardDebtsToggle")
    page.click("#saveSettingsBtn")
    page.wait_for_timeout(200)

    page.click("button[data-section='dashboard']")
    page.wait_for_selector("#dashboardSection:not(.hidden)")
    assert page.locator("#dashboardDebtsPanel").evaluate("el => el.classList.contains('hidden')") is True

    page.click("button[data-section='settings']")
    page.wait_for_selector("#settingsSection:not(.hidden)")
    page.check("#showDashboardDebtsToggle")
    page.click("#saveSettingsBtn")
    page.wait_for_timeout(200)

    page.click("button[data-section='dashboard']")
    page.wait_for_selector("#dashboardSection:not(.hidden)")
    assert page.locator("#dashboardDebtsPanel").evaluate("el => el.classList.contains('hidden')") is False
    assert page.locator("#dashboardDebtsList").inner_text().find("Анна") != -1


@pytest.mark.e2e
def test_forgiveness_flow_closes_debt_with_forgiven_request(static_server_url: str, page_with_debts_api_mock):
    page = page_with_debts_api_mock
    page.goto(f"{static_server_url}/static/index.html")
    _login_via_mock_telegram(page)

    page.click("button[data-section='debts']")
    page.wait_for_selector("#debtsSection:not(.hidden)")
    page.evaluate("window.App.getRuntimeModule('debts').openDebtForgivenessModal(9001)")
    page.wait_for_selector("#confirmModal:not(.hidden)")
    assert page.locator("#confirmDeleteBtn").inner_text() in {"Простить остаток", "Подтвердить списание"}
    assert page.locator("#confirmCancelBtn").inner_text() in {"Не прощать", "Оставить долг"}
    page.click("#confirmDeleteBtn")
    page.wait_for_selector("#confirmModal", state="hidden")

    assert len(getattr(page, "_forgiveness_calls", [])) == 1
    assert getattr(page, "_forgiveness_calls", [])[0]["debt_id"] == 9001
    assert getattr(page, "_forgiveness_calls", [])[0]["amount"] == "100.00"
    assert getattr(page, "_forgiveness_calls", [])[0]["note"] is None
    assert "Долги не найдены" in page.locator("#debtsCards").inner_text()
