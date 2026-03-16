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
def page_with_api_mock():
    preferences = {
        "preferences_version": 1,
        "data": {
            "dashboard": {"period": "day", "custom_date_from": "", "custom_date_to": ""},
            "operations": {"filters": {"kind": "", "q": ""}},
            "ui": {"active_section": "dashboard", "timezone": "Europe/Moscow"},
        },
    }

    category_groups = [
        {
            "id": 201,
            "name": "Базовые траты",
            "kind": "expense",
            "accent_color": "#ff8a3d",
        },
    ]

    categories = [
        {
            "id": 101,
            "name": "Еда",
            "icon": "🍔",
            "kind": "expense",
            "group_id": 201,
            "group_name": "Базовые траты",
            "group_icon": None,
            "group_accent_color": "#ff8a3d",
            "is_system": False,
        },
        {
            "id": 102,
            "name": "Зарплата",
            "icon": "💰",
            "kind": "income",
            "group_id": None,
            "group_name": None,
            "group_icon": None,
            "group_accent_color": None,
            "is_system": False,
        },
    ]

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
            return json_response(route, {"id": 1, "display_name": "E2E User", "username": "e2e_user", "status": "approved", "is_admin": False})

        if path == "/api/v1/preferences":
            if method == "GET":
                return json_response(route, preferences)
            if method == "PUT":
                payload = json.loads(request.post_data or "{}")
                preferences["preferences_version"] = payload.get("preferences_version", preferences["preferences_version"])
                preferences["data"] = payload.get("data", preferences["data"])
                return json_response(route, preferences)

        if path == "/api/v1/categories/groups" and method == "GET":
            return json_response(route, category_groups)

        if path == "/api/v1/categories" and method == "GET":
            if "page" in query and "page_size" in query:
                return json_response(route, {"items": categories, "total": len(categories), "page": 1, "page_size": 20})
            return json_response(route, categories)

        if path == "/api/v1/dashboard/summary" and method == "GET":
            return json_response(route, {"income_total": "0.00", "expense_total": "0.00", "balance": "0.00"})

        if path == "/api/v1/debts/cards" and method == "GET":
            return json_response(route, [])

        if path == "/api/v1/operations" and method == "GET":
            return json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})

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


@pytest.mark.e2e
def test_operation_category_search_renders_single_chip_without_duplicates(static_server_url: str, page_with_api_mock):
    page = page_with_api_mock
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
    page.evaluate("() => window.App.featureSession.refreshTelegramLoginUi()")

    page.click("#telegramLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")

    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")

    page.fill("#opCategorySearch", "еда")
    page.wait_for_timeout(200)

    chips = page.locator("#opCategoryQuick button[data-category-id], #opCategoryAll button[data-category-id]")
    assert chips.count() == 1
    assert "Еда" in chips.first.inner_text()


@pytest.mark.e2e
def test_operation_category_popover_closes_on_outside_click(static_server_url: str, page_with_api_mock):
    page = page_with_api_mock
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
    page.evaluate("() => window.App.featureSession.refreshTelegramLoginUi()")

    page.click("#telegramLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")
    page.click("#addOperationCta")
    page.wait_for_selector("#createModal:not(.hidden)")

    page.click("#opCategorySearch")
    page.wait_for_selector("#createCategoryPickerBlock:not(.hidden)")

    page.click("#opNote")
    page.wait_for_timeout(100)

    assert page.locator("#createCategoryPickerBlock").is_hidden()


@pytest.mark.e2e
def test_mobile_create_category_modal_keeps_kind_switch_above_sticky_cta(static_server_url: str, page_with_api_mock):
    page = page_with_api_mock
    page.set_viewport_size({"width": 390, "height": 844})
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
    page.evaluate("() => window.App.featureSession.refreshTelegramLoginUi()")

    page.click("#telegramLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")

    page.click("#mobileNavToggleBtn")
    page.click("button[data-section='categories']")
    page.wait_for_selector("#categoriesSection:not(.hidden)")
    page.click("#addCategoryCta")
    page.wait_for_selector("#createCategoryModal:not(.hidden)")
    page.fill("#categoryName", "Продукты")
    page.focus("#categoryGroupSearch")
    page.wait_for_timeout(150)

    geometry = page.evaluate(
        """
        () => {
          const kindSwitch = document.querySelector('#createCategoryKind');
          const footer = document.querySelector('#createCategoryModal .modal-footer');
          const modalCard = document.querySelector('#createCategoryModal .modal-card');
          if (!kindSwitch || !footer || !modalCard) {
            return null;
          }
          const kindRect = kindSwitch.getBoundingClientRect();
          const footerRect = footer.getBoundingClientRect();
          const modalRect = modalCard.getBoundingClientRect();
          return {
            kindTop: kindRect.top,
            kindBottom: kindRect.bottom,
            footerTop: footerRect.top,
            footerBottom: footerRect.bottom,
            modalBottom: modalRect.bottom,
          };
        }
        """
    )

    assert geometry is not None
    assert geometry["kindTop"] >= 0
    assert geometry["kindBottom"] <= geometry["footerTop"] + 2
    assert geometry["footerBottom"] <= geometry["modalBottom"] + 2


@pytest.mark.e2e
def test_mobile_edit_category_modal_keeps_group_field_above_sticky_cta(static_server_url: str, page_with_api_mock):
    page = page_with_api_mock
    page.set_viewport_size({"width": 390, "height": 844})
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
    page.evaluate("() => window.App.featureSession.refreshTelegramLoginUi()")

    page.click("#telegramLoginBtn")
    page.wait_for_selector("#appShell:not(.hidden)")

    page.click("#mobileNavToggleBtn")
    page.click("button[data-section='categories']")
    page.wait_for_selector("#categoriesSection:not(.hidden)")
    page.click("button[data-edit-category-id='101']")
    page.wait_for_selector("#editCategoryModal:not(.hidden)")
    page.focus("#editCategoryGroupSearch")
    page.wait_for_timeout(150)

    geometry = page.evaluate(
        """
        () => {
          const groupField = document.querySelector('#editCategoryGroupField');
          const footer = document.querySelector('#editCategoryModal .modal-footer');
          const modalCard = document.querySelector('#editCategoryModal .modal-card');
          if (!groupField || !footer || !modalCard) {
            return null;
          }
          const groupRect = groupField.getBoundingClientRect();
          const footerRect = footer.getBoundingClientRect();
          const modalRect = modalCard.getBoundingClientRect();
          return {
            groupTop: groupRect.top,
            groupBottom: groupRect.bottom,
            footerTop: footerRect.top,
            footerBottom: footerRect.bottom,
            modalBottom: modalRect.bottom,
          };
        }
        """
    )

    assert geometry is not None
    assert geometry["groupTop"] >= 0
    assert geometry["groupBottom"] <= geometry["footerTop"] + 2
    assert geometry["footerBottom"] <= geometry["modalBottom"] + 2
