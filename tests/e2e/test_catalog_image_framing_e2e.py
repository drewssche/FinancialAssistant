from email.parser import BytesParser
from io import BytesIO
import json
import re

import pytest
from PIL import Image

from tests.e2e.test_receipt_picker_store_scope_e2e import (
    _login,
    page_with_receipt_api_mock as page_with_receipt_api_mock,
    static_server_url as static_server_url,
)

sync_api = pytest.importorskip("playwright.sync_api")
expect = sync_api.expect
DEFAULT = {"mode": "contain", "zoom": 1, "offset_x": 0, "offset_y": 0}
OWNERS = [
    ("item-brand", "brand", "item-brands", "itemBrandModal", "item-brands", "openItemBrandModal"),
    ("catalog-product", "product", "catalog-products", "catalogProductModal", "catalog-products", "openEditor"),
    ("item-template", "template", "item-templates", "itemTemplateModal", "item-catalog", "openItemTemplateModal"),
    ("item-source", "source", "item-sources", "sourceGroupModal", "item-catalog", "openSourceGroupModal"),
]


@pytest.fixture
def image_page(request):
    page = request.getfixturevalue("page_with_receipt_api_mock")
    static_url = request.getfixturevalue("static_server_url")
    image = BytesIO()
    Image.new("RGB", (400, 100), "#258cd7").save(image, format="PNG")
    bag = {"frame": dict(DEFAULT), "uploads": [], "raw": image.getvalue()}

    def media_handler(route, req):
        if req.url.endswith("/framing"):
            route.fulfill(json={"framing": bag["frame"], "width": 400, "height": 100})
        else:
            route.fulfill(content_type="image/png", body=bag["raw"])

    def upload_handler(route, req):
        message = BytesParser().parsebytes(b"Content-Type: " + req.headers["content-type"].encode() + b"\r\n\r\n" + req.post_data_buffer)
        fields = {part.get_param("name", header="content-disposition"): part.get_payload(decode=True) for part in message.get_payload()}
        bag["frame"] = json.loads(fields["framing"])
        bag["uploads"].append({"url": req.url, "fields": fields})
        route.fulfill(json={"id": 501, "name": "Логотип", "image_id": 9901})

    page.route("**/api/v1/operations/media/**", media_handler)
    page.route(re.compile(r"/api/v1/operations/(item-brands|catalog-products|item-templates|item-sources)/\d+/image$"), upload_handler)
    page.goto(f"{static_url}/static/index.html")
    page.evaluate("() => { window.Telegram = { WebApp: { initData: 'mock-init-data', ready() {}, expand() {} } }; }")
    _login(page)
    return page, bag


@pytest.mark.e2e
@pytest.mark.parametrize("owner", OWNERS, ids=[row[0] for row in OWNERS])
@pytest.mark.parametrize("width", [1280, 390])
def test_image_fit_zoom_drag_reset_and_save_on_all_cards(image_page, owner, width, tmp_path):
    page, bag = image_page
    picker_name, owner_type, endpoint, modal_id, module, method = owner
    page.set_viewport_size({"width": width, "height": 1000})
    page.evaluate("([module, method]) => window.App.getRuntimeModule(module)[method]()", [module, method])
    root = page.locator(f'[data-catalog-image-picker="{picker_name}"]')
    expect(root).to_be_visible()
    expect(root.locator("[data-image-framing-controls]")).to_be_hidden()
    root.locator("input[type=file]").set_input_files({"name": "wide-logo.png", "mimeType": "image/png", "buffer": bag["raw"]})
    slider = root.locator("[data-image-zoom]")
    expect(slider).to_be_enabled()
    preview = root.locator("[data-catalog-image-preview]")
    img = preview.locator("img")
    expect(preview.locator(".catalog-media-fallback")).to_be_hidden()
    expect(root.locator('[data-image-fit="contain"]')).to_have_attribute("aria-pressed", "true")
    assert abs(img.bounding_box()["width"] / img.bounding_box()["height"] - 4) < .01
    assert abs(img.bounding_box()["width"] - preview.bounding_box()["width"]) < 3
    assert slider.bounding_box()["height"] <= 26
    root.locator('[data-image-fit="cover"]').click()
    assert abs(img.bounding_box()["height"] - preview.bounding_box()["height"]) < 3
    slider.focus()
    slider.press("End")
    expect(root.locator("[data-image-zoom-value]")).to_have_text("400%")
    root.locator("[data-image-framing-reset]").click()
    expect(root.locator("[data-image-zoom-value]")).to_have_text("100%")
    preview.scroll_into_view_if_needed()
    box = preview.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] / 2 + 15, box["y"] + box["height"] / 2 + 10, steps=5)
    page.mouse.up()
    assert float(img.evaluate("node => node.style.left").removesuffix("%")) > 55
    assert float(img.evaluate("node => node.style.top").removesuffix("%")) > 55
    expect(root.locator("[data-catalog-image-status]")).to_contain_text("после сохранения")
    assert bag["uploads"] == []
    # Keyboard panning and reset remain available without pointer dragging.
    root.locator("[data-image-framing-reset]").click()
    preview.focus()
    preview.press("ArrowRight")
    preview.press("Shift+ArrowUp")
    assert img.evaluate("node => node.style.left") == "52.5%"
    assert img.evaluate("node => node.style.top") == "42.5%"
    assert page.locator(f"#{modal_id} .modal-card").evaluate("node => node.scrollWidth <= node.clientWidth + 1")
    page.screenshot(path=str(tmp_path / f"image-{picker_name}-{width}.png"))
    page.evaluate("([name, type]) => window.App.getRuntimeModule('catalog-media').commitPicker(name, type, 501)", [picker_name, owner_type])
    assert len(bag["uploads"]) == 1
    upload = bag["uploads"][0]
    assert upload["url"].endswith(f"/{endpoint}/501/image")
    assert upload["fields"]["file"] == bag["raw"]
    assert bag["frame"] == {**DEFAULT, "offset_x": .05, "offset_y": -.15}
    expect(slider).to_be_enabled()
    expect(img).to_have_css("left", re.compile(r".+px"))
    page.wait_for_function("name => document.querySelector(`[data-catalog-image-picker='${name}'] img`).style.left === '52.5%'", arg=picker_name)
    # A framing-only save must not upload/recompress the original file again.
    root.locator("[data-image-framing-reset]").click()
    page.evaluate("([name, type]) => window.App.getRuntimeModule('catalog-media').commitPicker(name, type, 501)", [picker_name, owner_type])
    assert len(bag["uploads"]) == 2
    assert "file" not in bag["uploads"][1]["fields"]
    assert bag["frame"] == DEFAULT


@pytest.mark.e2e
def test_brand_existing_frame_cancel_and_real_form_save(image_page):
    page, bag = image_page
    frame = {"mode": "cover", "zoom": 1.75, "offset_x": .2, "offset_y": -.3}
    bag["frame"] = frame
    brand = {"id": 501, "name": "Широкий логотип", "image_id": 9900, "accent_color": "#7aa8ff"}
    page.route("**/api/v1/operations/item-brands/501", lambda route: route.fulfill(json=brand))
    page.evaluate("brand => window.App.getRuntimeModule('item-brands').openItemBrandModal(brand)", brand)
    root = page.locator('[data-catalog-image-picker="item-brand"]')
    expect(root.locator("[data-image-zoom-value]")).to_have_text("175%")
    expect(root.locator("[data-image-zoom]")).to_be_enabled()
    root.locator("[data-image-framing-reset]").click()
    page.click("#closeItemBrandModalBtn")
    assert bag["uploads"] == []
    page.evaluate("brand => window.App.getRuntimeModule('item-brands').openItemBrandModal(brand)", brand)
    expect(root.locator("[data-image-zoom-value]")).to_have_text("175%")
    root.locator("[data-image-framing-reset]").click()
    page.click("#submitItemBrandBtn")
    expect(page.locator("#itemBrandModal")).to_be_hidden()
    assert len(bag["uploads"]) == 1
    assert "file" not in bag["uploads"][0]["fields"]
    assert bag["frame"] == DEFAULT
