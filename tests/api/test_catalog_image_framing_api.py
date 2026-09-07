from io import BytesIO
import json

import pytest
from PIL import Image

from app.api.deps import get_current_user_id
from app.main import app
from app.services.catalog_media_service import CatalogMediaService
from tests.api.test_catalog_media_sources_api import _png
from tests.api.test_operations_api import _client_lifecycle


DEFAULT = {"mode": "contain", "zoom": 1.0, "offset_x": 0.0, "offset_y": 0.0}


@pytest.fixture
def client():
    yield from _client_lifecycle()


@pytest.mark.parametrize("owner", ["item-brands", "item-sources", "item-templates", "catalog-products"])
def test_upload_reframe_and_reset_preserve_source_for_every_owner(client, owner):
    entity = client.post(f"/api/v1/operations/{owner}", json={"name": "Логотип"}).json()
    url = f"/api/v1/operations/{owner}/{entity['id']}/image"
    assert client.put(url, data={"framing": "{}"}).status_code == 404
    frame = {"mode": "cover", "zoom": 1.75, "offset_x": -.25, "offset_y": .1}
    upload = client.put(url, files={"file": ("logo.png", _png(size=(800, 200)), "image/png")}, data={"framing": json.dumps(frame)})
    assert upload.status_code == 200, upload.text
    image_id = upload.json()["image_id"]
    detail = client.get(f"/api/v1/operations/media/{image_id}/detail").content
    assert client.get(f"/api/v1/operations/media/{image_id}/framing").json() == {"framing": frame, "width": 800, "height": 200}
    for next_frame in ({**DEFAULT, "zoom": 3, "offset_x": .5}, DEFAULT):
        # No file is sent when adjusting an existing image.
        saved = client.put(url, data={"framing": json.dumps(next_frame)})
        assert saved.status_code == 200, saved.text
        next_id = saved.json()["image_id"]
        assert next_id != image_id
        assert client.get(f"/api/v1/operations/media/{image_id}/detail").status_code == 404
        assert client.get(f"/api/v1/operations/media/{next_id}/detail").content == detail
        assert client.get(f"/api/v1/operations/media/{next_id}/framing").json()["framing"] == next_frame
        image_id = next_id
    with Image.open(BytesIO(client.get(f"/api/v1/operations/media/{image_id}/thumb").content)) as thumb:
        assert thumb.size == (160, 160)
        # An uncropped 4:1 source occupies 160x40, centered in the square.
        assert thumb.convert("RGBA").getbbox() == (0, 60, 160, 100)


@pytest.mark.parametrize("frame", [
    '{', 'null', '[]', '{"mode":"stretch"}', '{"zoom":0.9}', '{"zoom":4.01}',
    '{"zoom":NaN}', '{"offset_x":Infinity}', '{"offset_y":-1.01}',
])
def test_invalid_framing_does_not_replace_image(client, frame):
    brand = client.post("/api/v1/operations/item-brands", json={"name": "Бренд"}).json()
    url = f"/api/v1/operations/item-brands/{brand['id']}/image"
    uploaded = client.put(url, files={"file": ("logo.png", _png(), "image/png")}).json()
    result = client.put(url, data={"framing": frame})
    assert result.status_code == 422, result.text
    assert client.get(f"/api/v1/operations/media/{uploaded['image_id']}/thumb").status_code == 200


def test_framing_read_and_write_are_private(client):
    source = client.post("/api/v1/operations/item-sources", json={"name": "Магазин"}).json()
    url = f"/api/v1/operations/item-sources/{source['id']}/image"
    uploaded = client.put(url, files={"file": ("logo.png", _png(), "image/png")}).json()
    app.dependency_overrides[get_current_user_id] = lambda: 2
    assert client.get(f"/api/v1/operations/media/{uploaded['image_id']}/framing").status_code == 404
    assert client.put(url, data={"framing": "{}"}).status_code == 404


def test_offer_reframing_updates_the_shared_product_and_all_sources(client):
    product = client.post("/api/v1/operations/catalog-products", json={"name": "Сырок 40г"}).json()
    offers = []
    for name in ("Green", "Соседи"):
        source = client.post("/api/v1/operations/item-sources", json={"name": name}).json()
        offer = client.post(f"/api/v1/operations/catalog-products/{product['id']}/offers", json={"source_id": source["id"]})
        assert offer.status_code == 201, offer.text
        offers.append(offer.json())
    url = f"/api/v1/operations/catalog-products/{product['id']}/image"
    uploaded = client.put(url, files={"file": ("photo.png", _png(), "image/png")}).json()
    offer_url = f"/api/v1/operations/item-templates/{offers[0]['id']}/image"
    result = client.put(offer_url, data={"framing": '{"zoom":2}'})
    assert result.status_code == 200, result.text
    new_id = result.json()["image_id"]
    assert new_id != uploaded["image_id"]
    assert client.get(f"/api/v1/operations/catalog-products/{product['id']}").json()["image_id"] == new_id
    for offer in offers:
        assert client.get(f"/api/v1/operations/item-templates/{offer['id']}").json()["image_id"] == new_id


@pytest.mark.parametrize("size, expected", [((400, 100), (0, 60, 160, 100)), ((100, 400), (60, 0, 100, 160)), ((100, 100), (0, 0, 160, 160))])
def test_default_fit_preserves_the_source_aspect_ratio(size, expected):
    image = CatalogMediaService.process_image(raw=_png(size=size), content_type="image/png")
    with Image.open(BytesIO(image.thumb_bytes)) as thumb:
        assert thumb.convert("RGBA").getbbox() == expected
    assert image.framing == DEFAULT


def test_zoom_cover_and_offsets_match_the_preview_coordinate_system():
    raw = _png(size=(400, 100))
    cases = [
        ({"mode": "cover"}, (0, 0, 160, 160)),
        ({"zoom": 2}, (0, 40, 160, 120)),
        ({"offset_x": .5, "offset_y": -.5}, (40, 20, 160, 60)),
        ({"mode": "cover", "zoom": 4}, (0, 0, 160, 160)),
    ]
    for frame, bounds in cases:
        image = CatalogMediaService.process_image(raw=raw, content_type="image/png", framing=frame)
        with Image.open(BytesIO(image.thumb_bytes)) as thumb:
            assert thumb.convert("RGBA").getbbox() == bounds
        with Image.open(BytesIO(image.detail_bytes)) as detail:
            assert detail.size == (400, 100)
