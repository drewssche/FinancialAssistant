import json
from urllib.parse import parse_qs, urlparse

import pytest

from tests.e2e.test_catalog_product_layout_e2e import catalog_page as catalog_page
from tests.e2e.test_receipt_picker_store_scope_e2e import (
    page_with_receipt_api_mock as page_with_receipt_api_mock,
    static_server_url as static_server_url,
)

sync_api = pytest.importorskip("playwright.sync_api")
expect = sync_api.expect


@pytest.mark.e2e
def test_product_sort_keeps_offers_attached_and_resize_independent(request):
    page = request.getfixturevalue("catalog_page")
    page.set_viewport_size({"width": 1280, "height": 900})
    page.evaluate("""() => {
      const products = window.App.state.catalogProducts;
      products.splice(3);
      products.forEach((p, i) => {
        p.name = ['Яблоко', 'Арбуз', 'Банан'][i];
        p.min_unit_price = [12, 2, null][i];
        p.last_used_at = ['2026-01-30T12:00:00Z', '2026-02-01T09:00:00Z', null][i];
      });
    }""")
    table = page.locator(".catalog-products-table")
    page.locator('[data-toggle-catalog-product="401"]').click()
    price = table.locator('th[data-sort-key="min_unit_price"]')
    price.locator("button").click()
    rows = table.locator("tbody > tr.catalog-product-row")
    expect(rows.first).to_have_attribute("data-catalog-product-id", "402")
    expect(rows.last).to_have_attribute("data-catalog-product-id", "403")
    expect(price).to_have_attribute("aria-sort", "ascending")
    assert page.locator('[data-catalog-product-id="401"]').evaluate(
        "row => row.nextElementSibling.classList.contains('catalog-product-offer-row')"
    )
    price.locator("button").press("Enter")
    expect(rows.first).to_have_attribute("data-catalog-product-id", "401")
    expect(rows.last).to_have_attribute("data-catalog-product-id", "403")
    expect(price).to_have_attribute("aria-sort", "descending")
    dates = table.locator('th[data-sort-key="last_used_at"]')
    dates.locator("button").click()
    expect(rows.first).to_have_attribute("data-catalog-product-id", "401")
    dates.locator("button").click()
    expect(rows.first).to_have_attribute("data-catalog-product-id", "402")
    name = table.locator('th[data-sort-key="name"]')
    name.locator("button").click()
    expect(rows.first).to_have_attribute("data-catalog-product-id", "402")
    grip = name.locator(".catalog-column-resizer")
    grip.click()
    grip.press("ArrowRight")
    expect(name).to_have_attribute("aria-sort", "ascending")
    # Switching away/back re-renders without losing the selected ordering.
    page.evaluate("window.App.getRuntimeModule('catalog-products').render()")
    expect(rows.first).to_have_attribute("data-catalog-product-id", "402")
    assert page.evaluate("window.App.getRuntimeModule('table-sort').get('products')") == {"by": "name", "dir": "asc"}


@pytest.mark.e2e
def test_operation_headers_request_global_sort_and_preserve_filters(request):
    page = request.getfixturevalue("catalog_page")
    page.route("**/api/v1/operations/money-flow?**", lambda route: route.fulfill(
        status=200, content_type="application/json", body='{"items":[],"total":0,"page":1,"page_size":20}'))
    page.route("**/api/v1/operations/money-flow/summary?**", lambda route: route.fulfill(
        status=200, content_type="application/json", body='{"income_total":"0","expense_total":"0","total":0}'))
    calls = []
    page.on("request", lambda request: calls.append(parse_qs(urlparse(request.url).query))
            if urlparse(request.url).path == "/api/v1/operations/money-flow" else None)
    page.evaluate("window.App.getRuntimeModule('navigation').switchSection('operations')")
    table = page.locator("#operationsBody").locator("xpath=ancestor::table")
    price = table.locator('th[data-sort-key="amount"]')
    price.locator("button").click()
    page.wait_for_function("document.querySelector('#operationsBody tr') !== null")
    expect(price).to_have_attribute("aria-sort", "ascending")
    page.wait_for_timeout(150)
    assert calls[-1]["sort_by"] == ["amount"]
    assert calls[-1]["sort_dir"] == ["asc"]
    assert calls[-1]["page"] == ["1"]
    price.locator("button").click()
    page.wait_for_timeout(150)
    assert calls[-1]["sort_dir"] == ["desc"]
    table.locator('th[data-sort-key="note"] button').click()
    page.wait_for_timeout(150)
    assert calls[-1]["sort_by"] == ["note"]
    assert calls[-1]["sort_dir"] == ["asc"]
    assert calls[-1]["date_from"] == calls[0]["date_from"]


@pytest.mark.e2e
def test_brands_sort_numeric_and_remember_direction(request):
    page = request.getfixturevalue("catalog_page")
    page.click('[data-item-catalog-view="brands"]')
    page.evaluate("""() => {
      window.App.state.itemBrands = [
        {id: 991, name: 'Яблоко', positions_count: 12},
        {id: 992, name: 'Арбуз', positions_count: 2},
        {id: 993, name: 'Банан', positions_count: 0},
      ];
      window.App.getRuntimeModule('item-brands').renderItemBrands();
    }""")
    table = page.locator(".item-brands-table")
    rows = table.locator("tbody tr")
    count = table.locator('th[data-sort-key="positions_count"]')
    count.locator("button").click()
    expect(rows.first).to_have_attribute("data-item-brand-id", "993")
    count.locator("button").press("Space")
    expect(rows.first).to_have_attribute("data-item-brand-id", "991")
    expect(count).to_have_attribute("aria-sort", "descending")
    # Re-render after another action preserves the choice, without adding listeners.
    page.evaluate("window.App.getRuntimeModule('item-brands').renderItemBrands()")
    count.locator("button").click()
    expect(rows.first).to_have_attribute("data-item-brand-id", "993")
    assert table.locator(".table-sort-button").count() == 5


@pytest.mark.e2e
def test_grouped_catalog_and_categories_sort_inside_their_groups(request):
    page = request.getfixturevalue("catalog_page")
    page.click('[data-item-catalog-view="sources"]')
    page.evaluate("""() => {
      window.App.state.itemCatalogItems = [
        {id: 901, name: 'Яблоко', shop_name: 'Green', latest_unit_price: 12},
        {id: 902, name: 'Арбуз', shop_name: 'Green', latest_unit_price: 2},
        {id: 903, name: 'Банан', shop_name: 'Санта', latest_unit_price: 4},
      ];
      window.App.getRuntimeModule('item-catalog').refreshItemCatalogView();
    }""")
    table = page.locator("#itemCatalogBody").locator("xpath=ancestor::table")
    table.locator('th[data-sort-key="price"] button').click()
    rows = table.locator("[data-item-template-row]")
    expect(rows.first).to_have_attribute("data-item-template-open-id", "903")
    expect(rows.nth(1)).to_have_attribute("data-item-template-open-id", "902")
    expect(rows.nth(2)).to_have_attribute("data-item-template-open-id", "901")
    table.locator('th[data-sort-key="price"] button').click()
    expect(rows.first).to_have_attribute("data-item-template-open-id", "901")
    expect(rows.nth(1)).to_have_attribute("data-item-template-open-id", "902")
    groups = [{"id": 991, "name": "Продукты", "kind": "expense"}]
    categories = [
        {"id": 992, "name": "Яблоки", "kind": "expense", "group_id": 991, "group_name": "Продукты"},
        {"id": 993, "name": "Арбузы", "kind": "expense", "group_id": 991, "group_name": "Продукты"},
    ]
    page.route("**/api/v1/categories/groups", lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps(groups)))
    page.route("**/api/v1/categories", lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps(categories)))
    page.evaluate("window.App.core.invalidateUiRequestCache('categories')")
    page.evaluate("window.App.getRuntimeModule('navigation').switchSection('categories')")
    expect(page.locator('#categoriesBody [data-category-id="993"]')).to_be_visible()
    table = page.locator("#categoriesBody").locator("xpath=ancestor::table")
    table.locator('th[data-sort-key="name"] button').click()
    rows = table.locator('tr[data-item-type="category"]')
    expect(rows.first).to_have_attribute("data-category-id", "993")
    table.locator('th[data-sort-key="name"] button').click()
    expect(rows.first).to_have_attribute("data-category-id", "992")
    expect(rows.first).to_have_attribute("data-group-id", "991")
