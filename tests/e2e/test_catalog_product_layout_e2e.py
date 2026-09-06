from __future__ import annotations

import json
from urllib.parse import urlparse

import pytest

from tests.e2e.test_receipt_picker_store_scope_e2e import (
    _login,
    page_with_receipt_api_mock as page_with_receipt_api_mock,
    static_server_url as static_server_url,
)

sync_api = pytest.importorskip("playwright.sync_api")
expect = sync_api.expect


@pytest.fixture()
def catalog_page(request):
    page = request.getfixturevalue("page_with_receipt_api_mock")
    static_url = request.getfixturevalue("static_server_url")
    products = [{
        "id": i, "name": "Крабовые палочки Санта Бремор Ролл яйцо/грибы 180г " * 3,
        "category_id": 101, "category_name": "Рыба/Морепродукты", "brand_id": 202,
        "brand_name": "Очень длинное название бренда", "offers_count": 1, "sources_count": 1,
        "last_used_at": "2026-09-06T21:26:35.469774Z", "offers": [{
            "id": 500 + i, "template_id": 500 + i, "source_name": "Green", "source_id": 304,
            "name": "Очень длинное название предложения " * 5, "latest_unit_price": "12.99",
            "latest_price_date": "2026-09-06", "use_count": 5,
        }],
    } for i in range(401, 431)]

    def handler(route, request):
        path = urlparse(request.url).path
        if path.endswith("/merge-candidates"):
            payload = {"items": [], "total": 0}
        elif path.endswith("/401"):
            payload = products[0]
        else:
            payload = {"items": products, "total": len(products), "page": 1, "page_size": 100}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    page.route("**/api/v1/operations/catalog-products**", handler)
    page.route("**/api/v1/operations/catalog-products/**", handler)
    page.goto(f"{static_url}/static/index.html")
    page.evaluate("() => { window.Telegram = { WebApp: { initData: 'mock-init-data', ready() {}, expand() {} } }; }")
    _login(page)
    page.evaluate("window.App.getRuntimeModule('navigation').switchSection('item_catalog')")
    expect(page.locator('[data-catalog-product-id="401"]')).to_be_visible()
    return page


@pytest.mark.e2e
@pytest.mark.parametrize("viewport_width", [1280, 390])
def test_product_long_pickers_repeat_open_scroll_and_do_not_move_background(catalog_page, viewport_width, tmp_path):
    page = catalog_page
    page.set_viewport_size({"width": viewport_width, "height": 900})
    page.evaluate("""async () => {
      await window.App.getRuntimeModule('item-brands').ensureItemBrandsLoaded();
      window.App.state.categories = Array.from({length: 160}, (_, i) => ({id: 101 + i,
        name: `Категория продуктов ${i}`, kind: 'expense', icon: '🍔'}));
      window.App.state.itemBrands = Array.from({length: 160}, (_, i) => ({id: 202 + i,
        name: `Бренд продуктов ${i}`, accent_color: '#35B8D4'}));
      await window.App.getRuntimeModule('catalog-products').openEditor(401);
      window.__pickerScrollListeners = new Set();
      const add = window.addEventListener.bind(window), remove = window.removeEventListener.bind(window);
      window.addEventListener = (type, callback, options) => {
        if (type === 'scroll') window.__pickerScrollListeners.add(callback);
        add(type, callback, options);
      };
      window.removeEventListener = (type, callback, options) => {
        if (type === 'scroll') window.__pickerScrollListeners.delete(callback);
        remove(type, callback, options);
      };
    }""")
    for kind in ("Brand", "Category"):
        input_node = page.locator(f"#catalogProduct{kind}Search")
        picker = page.locator(f"#catalogProduct{kind}Picker")
        for _ in range(4):
            input_node.click()
            expect(picker).to_be_visible()
            # Let mobile focus scrolling and the follow-up positioning frame finish.
            page.wait_for_timeout(450)
            rect = picker.bounding_box()
            anchor = input_node.bounding_box()
            assert rect["height"] <= 421
            assert rect["y"] + rect["height"] <= anchor["y"] or rect["y"] >= anchor["y"] + anchor["height"]
            assert page.evaluate("window.__pickerScrollListeners.size") == 1
            background = page.evaluate("[window.scrollY, document.querySelector('#catalogProductModal .modal-card').scrollTop]")
            picker.hover()
            page.mouse.wheel(0, 250)
            page.wait_for_function(f"document.querySelector('#catalogProduct{kind}Picker').scrollTop > 50")
            page.wait_for_timeout(100)
            assert picker.evaluate("node => node.scrollTop") > 50
            # At both boundaries the wheel must not scroll the modal or the page.
            for edge, delta in (("node.scrollHeight", 700), ("0", -700)):
                picker.evaluate(f"node => node.scrollTop = {edge}")
                page.mouse.wheel(0, delta)
                page.wait_for_timeout(100)
                assert page.evaluate("[window.scrollY, document.querySelector('#catalogProductModal .modal-card').scrollTop]") == background
            page.locator("#catalogProductName").click()
            expect(picker).to_be_hidden()
            assert page.evaluate("window.__pickerScrollListeners.size") == 0
        input_node.click()
        for query in ("пр", "прод", "продукт", "продуктов"):
            input_node.fill(query)
            expect(picker).to_be_visible()
            assert page.evaluate("window.__pickerScrollListeners.size") == 1
        page.screenshot(path=str(tmp_path / f"product-{kind}-{viewport_width}.png"))
        picker.locator('[data-product-meta-id]').nth(4).click()
        expect(picker).to_be_hidden()
        input_node.click()
        expect(picker).to_be_visible()
        input_node.press("Escape")
        expect(picker).to_be_hidden()
        expect(page.locator("#catalogProductModal")).to_be_visible()


@pytest.mark.e2e
@pytest.mark.parametrize("viewport_width", [1024, 1280, 1920, 390])
def test_product_columns_fit_resize_persist_and_reset(catalog_page, viewport_width, tmp_path):
    page = catalog_page
    page.set_viewport_size({"width": viewport_width, "height": 1000})
    table = page.locator(".catalog-products-table")
    table.scroll_into_view_if_needed()
    def geometry():
        return table.evaluate("""node => {
          const wrap = node.closest('.table-wrap');
          return {table: node.getBoundingClientRect().width, width: wrap.clientWidth, scroll: wrap.scrollWidth,
            columns: [...node.querySelectorAll('thead th')].map(n => n.getBoundingClientRect().width)};
        }""")
    initial = geometry()
    page.screenshot(path=str(tmp_path / f"catalog-{viewport_width}.png"))
    assert initial["scroll"] <= initial["width"] + 1, table.evaluate("""node => ({
      table: node.getBoundingClientRect().toJSON(),
      cells: [...node.querySelectorAll('thead th, tbody tr:first-child td')].map(n => ({text:n.textContent.slice(0,50), width:n.clientWidth, scroll:n.scrollWidth}))
    })""")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    if viewport_width == 390:
        expect(page.locator("#resetCatalogProductWidthsBtn")).to_be_hidden()
        return
    assert initial["columns"][1] < initial["table"] * .32
    handle = table.locator(".catalog-column-resizer").first
    box = handle.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] / 2 - 55, box["y"] + box["height"] / 2, steps=8)
    page.mouse.up()
    resized = geometry()
    assert resized["columns"][1] < initial["columns"][1] - 5
    assert resized["scroll"] <= resized["width"] + 1
    assert abs(resized["table"] - initial["table"]) < 1
    page.click("#refreshCatalogProductsBtn")
    assert abs(geometry()["columns"][1] - resized["columns"][1]) < 1
    # Preferences survive a real reload, not just a re-render of the table.
    page.reload()
    page.evaluate("() => { window.Telegram = { WebApp: { initData: 'mock-init-data', ready() {}, expand() {} } }; }")
    _login(page)
    page.evaluate("window.App.getRuntimeModule('navigation').switchSection('item_catalog')")
    expect(table).to_be_visible()
    assert abs(geometry()["columns"][1] - resized["columns"][1]) < 1
    handle.focus()
    handle.press("ArrowRight")
    assert geometry()["columns"][1] > resized["columns"][1] + 5
    handle.dblclick()
    assert abs(geometry()["columns"][1] - initial["columns"][1]) < 1
    handle.press("ArrowLeft")
    page.click("#resetCatalogProductWidthsBtn")
    assert abs(geometry()["columns"][1] - initial["columns"][1]) < 1
    page.locator('[data-toggle-catalog-product="401"]').click()
    assert geometry()["scroll"] <= geometry()["width"] + 1
