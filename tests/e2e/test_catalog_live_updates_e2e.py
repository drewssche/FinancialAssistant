import json
from urllib.parse import parse_qs, urlparse

import pytest

from tests.e2e.test_receipt_picker_store_scope_e2e import (
    _login,
    page_with_receipt_api_mock as page_with_receipt_api_mock,
    static_server_url as static_server_url,
)

sync_api = pytest.importorskip("playwright.sync_api")
expect = sync_api.expect


@pytest.fixture()
def live_catalog(request):
    page = request.getfixturevalue("page_with_receipt_api_mock")
    static_url = request.getfixturevalue("static_server_url")
    brands = [{"id": 201, "name": "Бабушкина крынка"}, {"id": 202, "name": "Савушкин"}]
    product = {"id": 401, "name": "Сырок 40 г", "brand_id": None, "category_id": 101,
               "offers_count": 2, "sources_count": 2, "offers": [
                   {"id": 501, "source_id": 301, "source_name": "Green", "latest_unit_price": "0.82", "use_count": 1},
                   {"id": 502, "source_id": 302, "source_name": "Санта", "latest_unit_price": "0.81", "use_count": 1},
               ]}
    metrics = {"brand_gets": 0, "patches": 0}

    def respond(route, payload):
        route.fulfill(status=200, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    def brand_rows():
        return [{**brand, "positions_count": int(product["brand_id"] == brand["id"]),
                 "purchases_count": 2 if product["brand_id"] == brand["id"] else 0,
                 "spent_total": "1.63" if product["brand_id"] == brand["id"] else "0",
                 "last_purchase_date": "2026-09-07" if product["brand_id"] == brand["id"] else None,
                 } for brand in brands]

    def offers():
        return [{**offer, "product_id": 401, "name": product["name"], "shop_name": offer["source_name"],
                 "brand_id": product["brand_id"], "brand_name": product.get("brand_name"),
                 "last_category_id": 101} for offer in product["offers"]]

    def handler(route, req):
        path = urlparse(req.url).path
        if path.endswith("merge-candidates"):
            return respond(route, {"items": [], "total": 0})
        if path == "/api/v1/operations/item-brands":
            metrics["brand_gets"] += 1
            return respond(route, {"items": brand_rows(), "total": 2, "page": 1, "page_size": 100})
        if path == "/api/v1/operations/catalog-products/401" and req.method == "PATCH":
            product.update(req.post_data_json)
            product["brand_name"] = next((b["name"] for b in brands if b["id"] == product["brand_id"]), None)
            metrics["patches"] += 1
            return respond(route, {**product, "offers": offers()})
        if path == "/api/v1/operations/catalog-products/401":
            return respond(route, {**product, "offers": offers()})
        if path == "/api/v1/operations/catalog-products":
            return respond(route, {"items": [{**product, "offers": offers()}], "total": 1, "page": 1, "page_size": 100})
        if path == "/api/v1/operations/item-templates":
            query = parse_qs(urlparse(req.url).query).get("q", [""])[0].lower()
            items = [offer for offer in offers() if query in (offer["shop_name"] + " " + offer["name"]).lower()]
            return respond(route, {"items": items, "total": len(items), "page": 1, "page_size": 100})
        route.fallback()

    page.route("**/api/v1/operations/**", handler)
    page.goto(f"{static_url}/static/index.html")
    page.evaluate("window.Telegram = {WebApp: {initData: 'mock-init-data', ready() {}, expand() {}}}")
    _login(page)
    page.evaluate("window.App.getRuntimeModule('navigation').switchSection('item_catalog')")
    expect(page.locator('[data-catalog-product-id="401"]')).to_be_visible()
    return page, product, metrics


@pytest.mark.e2e
def test_assign_reassign_clear_brand_refresh_all_catalog_views(request):
    page, _, metrics = request.getfixturevalue("live_catalog")
    page.click('[data-item-catalog-view="sources"]')
    page.locator("#itemCatalogSearchQ").fill("Green")
    expect(page.locator('[data-item-template-row]')).to_have_count(1)
    page.click('[data-item-catalog-view="brands"]')
    expect(page.locator('[data-item-brand-id="201"] td[data-label="Позиций"]')).to_have_text("0")
    for selected in [201, 202, None]:
        page.click('[data-item-catalog-view="products"]')
        page.locator('[data-catalog-product-id="401"] [data-open-catalog-product="401"]').first.click()
        page.click("#catalogProductBrandSearch")
        page.locator(f'#catalogProductBrandPicker [data-product-meta-id="{selected or ""}"]').click()
        gets_before_save = metrics["brand_gets"]
        page.click("#submitCatalogProductBtn")
        expect(page.locator("#catalogProductModal")).to_be_hidden()
        # Assert refreshed data before opening Brands: switching tabs must not be
        # the only thing that repairs the stale zero counter.
        page.wait_for_function("""selected => window.App.state.itemBrandsLoaded &&
          window.App.state.itemBrands.every(b => b.positions_count === (b.id === selected ? 1 : 0)) &&
          window.App.state.itemCatalogAllItems.length === 2 &&
          window.App.state.itemCatalogAllItems.every(i => i.brand_id === selected)
        """, arg=selected)
        assert metrics["brand_gets"] == gets_before_save + 1
        page.click('[data-item-catalog-view="brands"]')
        for brand in [201, 202]:
            row = page.locator(f'[data-item-brand-id="{brand}"]')
            expect(row.locator('[data-label="Позиций"]')).to_have_text("1" if selected == brand else "0")
            expect(row.locator('[data-label="Покупок"]')).to_have_text("2" if selected == brand else "0")
        expect(page.locator("#itemBrandsKpiGrid article").nth(1).locator("strong")).to_have_text("1" if selected else "0")
        page.click('[data-item-catalog-view="sources"]')
        expected = "Бабушкина крынка" if selected == 201 else "Савушкин" if selected else "Без бренда"
        expect(page.locator('[data-item-template-row] .item-catalog-brand-cell').first).to_have_text(expected)
    assert metrics["patches"] == 3


@pytest.mark.e2e
def test_old_brand_response_cannot_overwrite_metrics_after_product_save(request):
    page, _, _ = request.getfixturevalue("live_catalog")
    page.locator('[data-catalog-product-id="401"] [data-open-catalog-product="401"]').first.click()
    page.evaluate("""() => {
      const core = window.App.core, original = core.requestJson;
      const stale = JSON.parse(JSON.stringify(window.App.state.itemBrands));
      let delayed = false;
      core.requestJson = function(url, options) {
        if (!delayed && url.startsWith('/api/v1/operations/item-brands?')) {
          delayed = true;
          return new Promise(resolve => { window.releaseOldBrands = () => resolve({items: stale, total: stale.length, page_size: 100}); });
        }
        return original.call(this, url, options);
      };
      window.oldBrandLoad = window.App.getRuntimeModule('item-brands').loadItemBrands({force: true});
    }""")
    page.click("#catalogProductBrandSearch")
    page.locator('#catalogProductBrandPicker [data-product-meta-id="201"]').click()
    page.click("#submitCatalogProductBtn")
    page.wait_for_function("window.App.state.itemBrands.find(b => b.id === 201).positions_count === 1")
    page.evaluate("async () => { window.releaseOldBrands(); await window.oldBrandLoad; }")
    assert page.evaluate("window.App.state.itemBrands.find(b => b.id === 201).positions_count") == 1
    assert page.evaluate("window.App.state.itemBrandsLoaded")


@pytest.mark.e2e
def test_source_checkboxes_remain_clickable(request):
    page, _, _ = request.getfixturevalue("live_catalog")
    page.click('[data-item-catalog-view="sources"]')
    checkbox = page.locator('[data-item-catalog-select-id="501"]')
    checkbox.scroll_into_view_if_needed()
    geometry = checkbox.evaluate("""input => {
      const r = input.getBoundingClientRect(), td = input.closest('td'), style = getComputedStyle(input);
      return {input: r.toJSON(), cell: td.getBoundingClientRect().toJSON(), pointer: style.pointerEvents,
        target: document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2)?.outerHTML,
        hit: document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2) === input};
    }""")
    assert geometry["hit"], json.dumps(geometry)
    checkbox.check()
    expect(page.locator("#itemCatalogSelectedCount")).to_have_text("Выбрано: 1")


@pytest.mark.e2e
@pytest.mark.parametrize("view,width", [(v, w) for v in ["brands", "sources"] for w in [1024, 1280, 1920]])
def test_catalog_tabs_resize_persist_and_reset_without_sorting(request, view, width):
    page, _, _ = request.getfixturevalue("live_catalog")
    page.set_viewport_size({"width": width, "height": 900})
    page.click(f'[data-item-catalog-view="{view}"]')
    is_brand = view == "brands"
    table = page.locator(".item-brands-table" if is_brand else ".item-catalog-table")
    reset = page.locator("#resetItemBrandWidthsBtn" if is_brand else "#resetItemCatalogWidthsBtn")
    expect(table).to_be_visible()
    grips = table.locator(".catalog-column-resizer")
    expect(grips).to_have_count(5)
    grips.first.scroll_into_view_if_needed()
    original = table.locator("col").evaluate_all("nodes => nodes.map(n => n.style.width)")
    box = grips.first.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] / 2 + 35, box["y"] + box["height"] / 2, steps=8)
    page.mouse.up()
    changed = table.locator("col").evaluate_all("nodes => nodes.map(n => n.style.width)")
    assert changed != original, table.evaluate("t => ({width: t.clientWidth, rect: t.getBoundingClientRect().toJSON()})")
    assert abs(sum(float(w.rstrip("%")) for w in changed) - 100) < 0.01
    expect(table.locator('th[aria-sort="ascending"], th[aria-sort="descending"]')).to_have_count(0)
    assert table.evaluate("t => t.getBoundingClientRect().right <= innerWidth && t.scrollWidth <= t.clientWidth + 2")
    page.reload()
    page.wait_for_selector("#appShell:not(.hidden)")
    page.evaluate("window.App.getRuntimeModule('navigation').switchSection('item_catalog')")
    page.click(f'[data-item-catalog-view="{view}"]')
    expect(table).to_be_visible()
    assert table.locator("col").evaluate_all("nodes => nodes.map(n => n.style.width)") == changed
    reset.click()
    assert table.locator("col").evaluate_all("nodes => nodes.map(n => n.style.width)") == original
    grips.first.focus()
    grips.first.press("ArrowRight")
    assert table.locator("col").evaluate_all("nodes => nodes.map(n => n.style.width)") != original
    grips.first.dblclick()
    assert table.locator("col").evaluate_all("nodes => nodes.map(n => n.style.width)") == original
