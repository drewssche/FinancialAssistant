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


def _json_response(route, payload: dict | list, status: int = 200):
    route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))


def _set_mock_telegram(page):
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


@pytest.mark.e2e
def test_login_screen_prefers_mini_app_copy_and_hides_manual_button_without_initdata(static_server_url: str):
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")
        page = browser.new_page()

        def handler(route, request):
            parsed = urlparse(request.url)
            path = parsed.path
            if path == "/api/v1/auth/public-config":
                return _json_response(
                    route,
                    {"telegram_bot_username": None, "browser_login_available": False},
                )
            return _json_response(route, {"detail": f"Unhandled mock route: {request.method} {path}"}, status=404)

        page.route("**/api/v1/**", handler)
        try:
            page.goto(f"{static_server_url}/static/index.html")
            expect_hidden = page.locator("#telegramLoginBtn")
            expect_hidden.wait_for(state="hidden")
            assert page.locator("#loginTelegramHint").text_content() == (
                "Вход без Telegram Mini App сейчас недоступен. Откройте приложение внутри Telegram "
                "или настройте TELEGRAM_BOT_USERNAME для browser login."
            )
        finally:
            browser.close()


@pytest.mark.e2e
def test_sidebar_user_handle_falls_back_to_telegram_id_when_username_missing(static_server_url: str):
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")
        page = browser.new_page()

        def handler(route, request):
            parsed = urlparse(request.url)
            path = parsed.path
            query = parse_qs(parsed.query)
            method = request.method.upper()

            if path == "/api/v1/auth/public-config":
                return _json_response(
                    route,
                    {"telegram_bot_username": None, "browser_login_available": False},
                )
            if path == "/api/v1/auth/telegram" and method == "POST":
                return _json_response(route, {"access_token": "e2e-token", "token_type": "bearer"})
            if path == "/api/v1/users/me" and method == "GET":
                return _json_response(
                    route,
                    {
                        "id": 1,
                        "display_name": "No Username User",
                        "username": None,
                        "telegram_id": "550011",
                        "status": "approved",
                        "is_admin": False,
                    },
                )
            if path == "/api/v1/preferences":
                if method == "GET":
                    return _json_response(
                        route,
                        {
                            "preferences_version": 1,
                            "data": {
                                "dashboard": {"period": "day", "custom_date_from": "", "custom_date_to": ""},
                                "operations": {"filters": {"kind": "", "q": ""}},
                                "ui": {"active_section": "dashboard", "timezone": "Europe/Moscow"},
                            },
                        },
                    )
                if method == "PUT":
                    return _json_response(route, {"preferences_version": 1, "data": {}})
            if path == "/api/v1/categories/groups" and method == "GET":
                return _json_response(route, [])
            if path == "/api/v1/categories" and method == "GET":
                if "page" in query and "page_size" in query:
                    return _json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
                return _json_response(route, [])
            if path == "/api/v1/dashboard/summary" and method == "GET":
                return _json_response(
                    route,
                    {
                        "income_total": "0.00",
                        "expense_total": "0.00",
                        "balance": "0.00",
                        "debt_lend_total": "0.00",
                        "debt_borrow_total": "0.00",
                        "debt_net_total": "0.00",
                    },
                )
            if path == "/api/v1/dashboard/operations" and method == "GET":
                return _json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
            if path == "/api/v1/dashboard/analytics" and method == "GET":
                return _json_response(route, {"points": [], "summary": {}})
            if path == "/api/v1/operations" and method == "GET":
                return _json_response(route, {"items": [], "total": 0, "page": 1, "page_size": 20})
            if path == "/api/v1/debts/cards" and method == "GET":
                return _json_response(route, [])
            return _json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

        _set_mock_telegram(page)
        page.route("**/api/v1/**", handler)
        try:
            page.goto(f"{static_server_url}/static/index.html")
            _restore_mock_telegram(page)
            page.evaluate("() => window.App.getRuntimeModule('session')?.refreshTelegramLoginUi?.()")
            assert page.locator("#telegramLoginBtn").text_content() == "Войти через Telegram Mini App"
            page.locator("#telegramLoginBtn").wait_for(state="visible")
            page.click("#telegramLoginBtn")
            page.wait_for_selector("#appShell:not(.hidden)")
            assert page.locator("#userHandle").text_content() == "ID 550011"
        finally:
            browser.close()


@pytest.mark.e2e
@pytest.mark.parametrize(
    ("user_status", "expected_message"),
    [
        ("pending", "Заявка отправлена. Ожидайте одобрения администратора"),
        ("rejected", "Доступ отклонен администратором"),
    ],
)
def test_login_keeps_pending_and_rejected_users_out_of_workspace(
    static_server_url: str,
    user_status: str,
    expected_message: str,
):
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")
        page = browser.new_page()

        def handler(route, request):
            parsed = urlparse(request.url)
            path = parsed.path
            method = request.method.upper()

            if path == "/api/v1/auth/public-config":
                return _json_response(
                    route,
                    {"telegram_bot_username": None, "browser_login_available": False},
                )
            if path == "/api/v1/auth/telegram" and method == "POST":
                return _json_response(route, {"access_token": "e2e-token", "token_type": "bearer"})
            if path == "/api/v1/users/me" and method == "GET":
                return _json_response(
                    route,
                    {
                        "id": 1,
                        "display_name": "Blocked User",
                        "username": "blocked_user",
                        "telegram_id": "991122",
                        "status": user_status,
                        "is_admin": False,
                    },
                )
            return _json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

        _set_mock_telegram(page)
        page.route("**/api/v1/**", handler)
        try:
            page.goto(f"{static_server_url}/static/index.html")
            _restore_mock_telegram(page)
            page.evaluate("() => window.App.getRuntimeModule('session')?.refreshTelegramLoginUi?.()")
            page.click("#telegramLoginBtn")
            page.wait_for_selector("#loginScreen:not(.hidden)")
            assert page.locator("#loginAlert").text_content() == expected_message
            assert page.locator("#appShell.hidden").count() == 1
            assert page.evaluate("() => window.localStorage.getItem('access_token')") is None
        finally:
            browser.close()


@pytest.mark.e2e
@pytest.mark.parametrize(
    ("user_status", "expected_message"),
    [
        ("pending", "Заявка отправлена. Ожидайте одобрения администратора"),
        ("rejected", "Доступ отклонен администратором"),
    ],
)
def test_browser_widget_login_keeps_pending_and_rejected_users_out_of_workspace(
    static_server_url: str,
    user_status: str,
    expected_message: str,
):
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")
        page = browser.new_page()

        def handler(route, request):
            parsed = urlparse(request.url)
            path = parsed.path
            method = request.method.upper()

            if path == "/api/v1/auth/public-config":
                return _json_response(
                    route,
                    {"telegram_bot_username": "FinanceWeaselBot", "browser_login_available": True},
                )
            if path == "/api/v1/auth/telegram/browser" and method == "POST":
                return _json_response(route, {"access_token": "browser-token", "token_type": "bearer"})
            if path == "/api/v1/users/me" and method == "GET":
                return _json_response(
                    route,
                    {
                        "id": 2,
                        "display_name": "Browser Blocked User",
                        "username": "browser_blocked",
                        "telegram_id": "771199",
                        "status": user_status,
                        "is_admin": False,
                    },
                )
            return _json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

        page.route("**/api/v1/**", handler)
        try:
            page.goto(f"{static_server_url}/static/index.html")
            page.wait_for_selector("#telegramBrowserLoginWrap:not(.hidden)")
            page.evaluate(
                """
                () => window.onTelegramAuth({
                  id: 771199,
                  first_name: "Browser",
                  username: "browser_blocked",
                  auth_date: Math.floor(Date.now() / 1000),
                  hash: "mock-hash",
                })
                """
            )
            page.wait_for_selector("#loginScreen:not(.hidden)")
            page.wait_for_function(
                "(expected) => document.querySelector('#loginAlert')?.textContent === expected",
                arg=expected_message,
            )
            assert page.locator("#loginAlert").text_content() == expected_message
            assert page.locator("#appShell.hidden").count() == 1
            assert page.evaluate("() => window.localStorage.getItem('access_token')") is None
        finally:
            browser.close()


@pytest.mark.e2e
@pytest.mark.parametrize(
    ("user_status", "expected_message"),
    [
        ("pending", "Заявка отправлена. Ожидайте одобрения администратора"),
        ("rejected", "Доступ отклонен администратором"),
    ],
)
def test_session_restore_keeps_pending_and_rejected_users_on_login_screen(
    static_server_url: str,
    user_status: str,
    expected_message: str,
):
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")
        page = browser.new_page()

        def handler(route, request):
            parsed = urlparse(request.url)
            path = parsed.path
            method = request.method.upper()

            if path == "/api/v1/auth/public-config":
                return _json_response(
                    route,
                    {"telegram_bot_username": None, "browser_login_available": False},
                )
            if path == "/api/v1/users/me" and method == "GET":
                return _json_response(
                    route,
                    {
                        "id": 3,
                        "display_name": "Restored Blocked User",
                        "username": "restored_blocked",
                        "telegram_id": "661133",
                        "status": user_status,
                        "is_admin": False,
                    },
                )
            return _json_response(route, {"detail": f"Unhandled mock route: {method} {path}"}, status=404)

        page.add_init_script("""window.localStorage.setItem("access_token", "restored-token");""")
        page.route("**/api/v1/**", handler)
        try:
            page.goto(f"{static_server_url}/static/index.html")
            page.wait_for_selector("#loginScreen:not(.hidden)")
            assert page.locator("#loginAlert").text_content() == expected_message
            assert page.locator("#appShell.hidden").count() == 1
            assert page.evaluate("() => window.localStorage.getItem('access_token')") is None
        finally:
            browser.close()
