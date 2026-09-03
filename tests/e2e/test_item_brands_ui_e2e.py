from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest

from tests.e2e.test_mobile_shell_cards_e2e import (
    _build_handler,
    _login_via_mock_telegram,
    _set_mock_telegram,
    static_server_url as _static_server_url,
)

static_server_url = _static_server_url


sync_api = pytest.importorskip("playwright.sync_api", reason="playwright is not installed")
expect = sync_api.expect


def _json_response(route, payload: dict | list, status: int = 200):
    route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))


@pytest.mark.e2e
def test_brand_catalog_assignment_detail_and_analytics_drilldown(static_server_url: str):
    brands = [
        {
            "id": 1,
            "name": "Vici",
            "accent_color": "#5fd3bc",
            "positions_count": 1,
            "purchases_count": 4,
            "spent_total": "22.40",
            "last_purchase_date": "2026-08-26",
            "is_archived": False,
        },
        {
            "id": 2,
            "name": "Coca-Cola",
            "accent_color": "#fb7185",
            "positions_count": 0,
            "purchases_count": 0,
            "spent_total": "0",
            "last_purchase_date": None,
            "is_archived": False,
        },
    ]
    templates = [
        {
            "id": 1,
            "shop_name": "Green",
            "name": "Крабовые палочки",
            "brand_id": 1,
            "brand_name": "Vici",
            "brand_accent_color": "#5fd3bc",
            "last_category_id": 1,
            "use_count": 4,
            "latest_unit_price": "5.39",
            "latest_price_date": "2026-08-26",
            "last_used_at": "2026-08-26T12:00:00Z",
        },
        {
            "id": 2,
            "shop_name": "Green",
            "name": "Минеральная вода",
            "brand_id": None,
            "brand_name": None,
            "brand_accent_color": None,
            "last_category_id": 1,
            "use_count": 2,
            "latest_unit_price": "1.80",
            "latest_price_date": "2026-08-25",
            "last_used_at": "2026-08-25T12:00:00Z",
        },
        {
            "id": 3,
            "shop_name": "Green",
            "name": "Legacy item",
            "brand_id": 99,
            "brand_name": "Legacy brand",
            "brand_accent_color": "#8899AA",
            "brand_is_archived": True,
            "last_category_id": 1,
            "use_count": 1,
            "latest_unit_price": "2.20",
            "latest_price_date": "2026-08-24",
            "last_used_at": "2026-08-24T12:00:00Z",
        },
    ]
    base_handler = _build_handler("item_catalog")

    def handler(route, request):
        parsed = urlparse(request.url)
        path = parsed.path
        query = parse_qs(parsed.query)
        method = request.method.upper()

        if path == "/api/v1/operations/item-brands" and method == "GET":
            return _json_response(route, {"items": brands, "total": len(brands), "page": 1, "page_size": 100})
        if path == "/api/v1/operations/item-brands" and method == "POST":
            body = json.loads(request.post_data or "{}")
            saved = {
                "id": 3,
                "name": body["name"],
                "accent_color": body["accent_color"],
                "positions_count": 0,
                "purchases_count": 0,
                "spent_total": "0",
                "last_purchase_date": None,
                "is_archived": False,
            }
            brands.append(saved)
            return _json_response(route, saved, status=201)
        if path == "/api/v1/operations/item-brands/99" and method == "GET":
            return _json_response(
                route,
                {
                    "id": 99,
                    "name": "Legacy brand",
                    "accent_color": "#8899AA",
                    "is_archived": True,
                    "positions_count": 1,
                    "purchases_count": 8,
                    "spent_total": "99.90",
                    "last_purchase_date": "2026-08-24",
                },
            )
        if path == "/api/v1/operations/item-templates" and method == "GET":
            brand_id = int(query.get("brand_id", [0])[0] or 0)
            items = [item for item in templates if not brand_id or int(item.get("brand_id") or 0) == brand_id]
            return _json_response(route, {"items": items, "total": len(items), "page": 1, "page_size": 100})
        if path == "/api/v1/operations/item-templates/bulk-brand" and method == "POST":
            body = json.loads(request.post_data or "{}")
            brand_id = body.get("brand_id")
            selected_ids = {int(template_id) for template_id in body.get("template_ids", [])}
            brand = next((entry for entry in brands if int(entry["id"]) == int(brand_id or 0)), None)
            updated = 0
            for item in templates:
                if int(item["id"]) not in selected_ids or item.get("brand_id") == brand_id:
                    continue
                item["brand_id"] = brand_id
                item["brand_name"] = brand["name"] if brand else None
                item["brand_accent_color"] = brand["accent_color"] if brand else None
                updated += 1
            for entry in brands:
                entry["positions_count"] = len(
                    [item for item in templates if int(item.get("brand_id") or 0) == int(entry["id"])]
                )
            return _json_response(route, {"updated": updated})
        if path.startswith("/api/v1/operations/item-templates/") and method == "PATCH":
            template_id = int(path.rsplit("/", 1)[-1])
            body = json.loads(request.post_data or "{}")
            item = next(item for item in templates if int(item["id"]) == template_id)
            for key in ("shop_name", "name", "last_category_id"):
                if key in body:
                    item[key] = body[key]
            if "brand_id" in body:
                item["brand_id"] = body["brand_id"]
                brand = next((entry for entry in brands if int(entry["id"]) == int(item.get("brand_id") or 0)), None)
                item["brand_name"] = brand["name"] if brand else None
                item["brand_accent_color"] = brand["accent_color"] if brand else None
            brands[0]["positions_count"] = len([row for row in templates if row.get("brand_id") == 1])
            return _json_response(route, item)
        if path == "/api/v1/dashboard/analytics/highlights" and method == "GET":
            level = query.get("category_breakdown_level", ["category"])[0]
            breakdown = []
            if level == "brand":
                breakdown = [
                    {
                        "category_id": None,
                        "category_name": "Vici",
                        "category_kind": "expense",
                        "brand_id": 1,
                        "brand_name": "Vici",
                        "brand_accent_color": "#5fd3bc",
                        "brand_is_archived": False,
                        "positions_count": 2,
                        "operations_count": 4,
                        "purchases_count": 4,
                        "total_amount": "22.40",
                        "share_pct": 100,
                    },
                    {
                        "category_id": None,
                        "category_name": "Legacy brand",
                        "category_kind": "expense",
                        "brand_id": 99,
                        "brand_name": "Legacy brand",
                        "brand_accent_color": "#8899AA",
                        "brand_is_archived": True,
                        "positions_count": 1,
                        "operations_count": 1,
                        "purchases_count": 1,
                        "total_amount": "3.00",
                        "share_pct": 0,
                    },
                ]
            return _json_response(
                route,
                {
                    "period": "month",
                    "date_from": "2026-08-01",
                    "date_to": "2026-08-31",
                    "category_breakdown_kind": "expense",
                    "category_breakdown_level": level,
                    "category_breakdown": breakdown,
                    "income_total": "0",
                    "expense_total": "22.40",
                    "balance": "-22.40",
                    "cashflow_total": "-22.40",
                    "operations_count": 4,
                    "receipt_amount_total": "44.80",
                    "branded_amount_total": "22.40",
                    "unbranded_amount_total": "22.40",
                    "brand_coverage_pct": 50,
                    "top_operations": [],
                    "top_categories": [],
                    "anomalies": [],
                    "top_positions": [],
                    "frequent_positions": [],
                    "price_increases": [],
                    "discount_savings_by_type": [],
                    "top_discount_savings": [],
                },
            )
        return base_handler(route, request)

    with sync_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium is not available for Playwright: {exc}")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        _set_mock_telegram(page)
        page.route("**/api/v1/**", handler)
        try:
            page.goto(f"{static_server_url}/static/index.html")
            _login_via_mock_telegram(page)
            page.wait_for_selector("#itemCatalogSection:not(.hidden)")

            page.locator('[data-item-catalog-view="brands"]').click()
            expect(page.locator("#itemBrandsView")).to_be_visible()
            expect(page.locator("#itemBrandsBody")).to_contain_text("Vici")
            expect(page.locator("#itemBrandsKpiGrid")).to_contain_text("Без бренда")

            page.locator('[data-open-item-brand-id="1"]').click()
            expect(page.locator("#itemBrandDetailModal")).to_be_visible()
            expect(page.locator("#itemBrandDetailBody")).to_contain_text("Крабовые палочки")
            page.locator("#closeItemBrandDetailModalBtn").click()

            page.locator("#addItemBrandBtn").click()
            page.locator("#itemBrandName").fill("Bonfesto")
            page.locator('[data-item-brand-color="#c084fc"]').click()
            page.locator("#submitItemBrandBtn").click()
            expect(page.locator("#itemBrandsBody")).to_contain_text("Bonfesto")

            page.locator('[data-item-catalog-view="positions"]').click()
            expect(page.locator('#itemCatalogBody [data-item-template-open-id="1"]')).to_contain_text("Vici")

            page.locator('[data-item-template-open-id="3"]').click()
            expect(page.locator("#itemTemplateModal")).to_be_visible()
            expect(page.locator("#itemTemplateBrandSearch")).to_have_value("Legacy brand")
            expect(page.locator("#itemTemplatePreviewBody")).to_contain_text("Legacy brand")
            page.locator("#itemTemplateBrandSearch").fill("not-a-brand")
            page.locator("#itemTemplateName").fill("Legacy item renamed")
            expect(page.locator("#itemTemplateBrandSearch")).to_have_value("Legacy brand")
            with page.expect_request(
                lambda request: request.method == "PATCH"
                and urlparse(request.url).path == "/api/v1/operations/item-templates/3"
            ) as request_info:
                page.locator("#submitItemTemplateBtn").click()
            saved_body = json.loads(request_info.value.post_data or "{}")
            assert "brand_id" not in saved_body
            expect(page.locator("#itemTemplateBrandSearch")).to_have_value("Legacy brand")
            expect(page.locator("#itemTemplatePreviewBody")).to_contain_text("Legacy brand")
            page.locator("#closeItemTemplateModalBtn").click()

            page.locator('[data-item-catalog-select-id="2"]').check()
            page.locator("#itemCatalogBulkBrand").select_option("1")
            page.locator("#assignSelectedItemBrandBtn").click()
            expect(page.locator('#itemCatalogBody [data-item-template-open-id="2"]')).to_contain_text("Vici")

            # A second atomic assignment changes an existing A -> B relation.
            # Opening a new receipt must reload the invalidated template hints
            # and autofill the freshly assigned brand instead of stale A data.
            page.locator('[data-item-catalog-select-id="1"]').check()
            page.locator("#itemCatalogBulkBrand").select_option("2")
            page.locator("#assignSelectedItemBrandBtn").click()
            expect(page.locator('#itemCatalogBody [data-item-template-open-id="1"]')).to_contain_text("Coca-Cola")

            page.locator('button[data-section="operations"]').click()
            page.locator("#addOperationCta").click()
            page.wait_for_selector("#createModal:not(.hidden)")
            page.locator('#createOperationModeSwitch button[data-operation-mode="receipt"]').click()
            page.wait_for_selector("#opReceiptFields:not(.hidden)")
            receipt_row = page.locator("#receiptItemsList .receipt-item-row").first
            receipt_row.locator('[data-receipt-field="shop_name"]').fill("Green")
            receipt_row.locator('[data-receipt-field="name"]').click()
            page.wait_for_selector(
                '.receipt-item-row:first-child .receipt-name-picker:not(.hidden) button[data-receipt-template-id="1"]'
            )
            receipt_row.locator('button[data-receipt-template-id="1"]').click()
            expect(receipt_row.locator('[data-receipt-field="brand_search"]')).to_have_value("Coca-Cola")
            page.locator("#closeCreateModalBtn").click()

            page.locator('button[data-section="analytics"]').click()
            page.locator('[data-analytics-tab="structure"]').click()
            page.locator('[data-analytics-breakdown-level="brand"]').click()
            expect(page.locator("#analyticsBrandCoverage")).to_contain_text("50.0%")
            page.locator('#analyticsCategoryBreakdownList [data-analytics-brand-id="1"]').click()
            expect(page.locator("#itemBrandDetailModal")).to_be_visible()
            expect(page.locator("#itemBrandDetailKpiGrid")).to_contain_text("22,40")
            page.locator("#closeItemBrandDetailModalBtn").click()

            page.locator('#analyticsCategoryBreakdownList [data-analytics-brand-id="99"]').click()
            expect(page.locator("#itemBrandDetailModal")).to_be_visible()
            expect(page.locator("#itemBrandDetailTitle")).to_contain_text("Архивный")
            expect(page.locator("#editItemBrandFromDetailBtn")).to_be_hidden()
            expect(page.locator("#openItemBrandOperationsBtn")).to_be_visible()
            expect(page.locator("#itemBrandDetailBody")).to_contain_text("Legacy item")
            expect(page.locator("#itemBrandDetailKpiGrid")).to_contain_text("99,90")
            page.locator("#closeItemBrandDetailModalBtn").click()

            page.set_viewport_size({"width": 390, "height": 844})
            page.locator('button[data-section="item_catalog"]').evaluate("node => node.click()")
            page.locator('[data-item-catalog-view="positions"]').click()
            mobile_head = page.locator(".item-catalog-mobile-item-head").first
            expect(mobile_head).to_be_visible()
            checkbox_box = mobile_head.locator(".item-catalog-mobile-item-select").bounding_box()
            title_box = mobile_head.locator(".item-catalog-mobile-item-title").bounding_box()
            menu_box = mobile_head.locator(".mobile-card-kebab-wrap").bounding_box()
            assert checkbox_box and title_box and menu_box
            assert checkbox_box["x"] < title_box["x"] < menu_box["x"]
            assert abs(title_box["y"] - menu_box["y"]) < max(title_box["height"], menu_box["height"])
            assert page_errors == []
        finally:
            browser.close()
