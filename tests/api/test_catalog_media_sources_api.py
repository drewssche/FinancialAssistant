from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import get_current_user_id
from app.main import app
from app.services.catalog_media_service import CatalogMediaService
from app.services.catalog_media_service import (
    CatalogMediaTooLargeError,
    CatalogMediaValidationError,
)
from tests.api.test_operations_api import _client_lifecycle


@pytest.fixture
def client():
    yield from _client_lifecycle()


def _png(*, size: tuple[int, int] = (320, 180), color=(40, 120, 220, 255)) -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _upload(
    client: TestClient,
    url: str,
    payload: bytes | None = None,
    content_type: str = "image/png",
):
    return client.put(
        url,
        files={"file": ("catalog.png", payload or _png(), content_type)},
    )


def test_item_sources_are_stable_entities_and_rename_linked_history(client: TestClient):
    template = client.post(
        "/api/v1/operations/item-templates",
        json={"shop_name": "  Green  ", "name": "Молоко"},
    )
    assert template.status_code == 201, template.text
    template_payload = template.json()
    source_id = template_payload["source_id"]
    assert source_id is not None
    assert template_payload["source_name"] == "Green"

    sources = client.get("/api/v1/operations/item-sources", params={"page_size": 500})
    assert sources.status_code == 200, sources.text
    assert sources.json()["items"] == [
        {
            **sources.json()["items"][0],
            "id": source_id,
            "name": "Green",
            "image_id": None,
            "is_archived": False,
            "positions_count": 1,
        }
    ]

    operation = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "operation_date": "2026-09-04",
            "receipt_items": [
                {
                    "template_id": template_payload["id"],
                    "source_id": source_id,
                    "shop_name": "Green",
                    "name": "Молоко",
                    "quantity": "1",
                    "unit_price": "3.20",
                }
            ],
        },
    )
    assert operation.status_code == 201, operation.text
    plan = client.post(
        "/api/v1/plans",
        json={
            "kind": "expense",
            "scheduled_date": "2026-10-04",
            "receipt_items": [
                {
                    "template_id": template_payload["id"],
                    "source_id": source_id,
                    "shop_name": "Green",
                    "name": "Молоко",
                    "quantity": "1",
                    "unit_price": "3.20",
                }
            ],
        },
    )
    assert plan.status_code == 201, plan.text

    renamed = client.patch(
        f"/api/v1/operations/item-sources/{source_id}",
        json={"name": "Green Supermarket"},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["id"] == source_id
    assert renamed.json()["name"] == "Green Supermarket"

    current_template = client.get(
        f"/api/v1/operations/item-templates/{template_payload['id']}"
    )
    assert current_template.status_code == 200, current_template.text
    assert current_template.json()["shop_name"] == "Green Supermarket"
    assert current_template.json()["source_name"] == "Green Supermarket"

    current_operation = client.get(f"/api/v1/operations/{operation.json()['id']}")
    assert current_operation.status_code == 200, current_operation.text
    receipt = current_operation.json()["receipt_items"][0]
    assert receipt["shop_name"] == "Green Supermarket"
    assert receipt["source_id"] == source_id
    assert receipt["source_name"] == "Green Supermarket"
    current_plan = client.get(f"/api/v1/plans/{plan.json()['id']}")
    assert current_plan.status_code == 200, current_plan.text
    assert current_plan.json()["receipt_items"][0]["shop_name"] == "Green Supermarket"
    assert current_plan.json()["receipt_items"][0]["source_name"] == "Green Supermarket"

    removed = client.delete(f"/api/v1/operations/item-sources/{source_id}")
    assert removed.status_code == 204, removed.text
    active_sources = client.get("/api/v1/operations/item-sources")
    assert active_sources.json()["total"] == 0
    active_templates = client.get(
        "/api/v1/operations/item-templates", params={"page_size": 100}
    )
    assert active_templates.json()["total"] == 0
    historical_operation = client.get(f"/api/v1/operations/{operation.json()['id']}")
    assert (
        historical_operation.json()["receipt_items"][0]["source_name"]
        == "Green Supermarket"
    )

    historical_row = historical_operation.json()["receipt_items"][0]
    round_trip = client.patch(
        f"/api/v1/operations/{operation.json()['id']}",
        json={
            "note": "Историческая строка проверена",
            "receipt_items": [
                {
                    "template_id": historical_row["template_id"],
                    "source_id": historical_row["source_id"],
                    "shop_name": historical_row["shop_name"],
                    "name": historical_row["name"],
                    "quantity": historical_row["quantity"],
                    "unit_price": historical_row["unit_price"],
                    "category_id": historical_row["category_id"],
                }
            ],
        },
    )
    assert round_trip.status_code == 200, round_trip.text
    assert round_trip.json()["receipt_items"][0]["source_id"] == source_id
    assert client.get("/api/v1/operations/item-sources").json()["total"] == 0


def test_catalog_images_propagate_to_receipts_replace_and_delete(client: TestClient):
    source = client.post(
        "/api/v1/operations/item-sources", json={"name": "Green"}
    ).json()
    brand = client.post(
        "/api/v1/operations/item-brands",
        json={"name": "Vici", "accent_color": "#225588"},
    ).json()
    template_response = client.post(
        "/api/v1/operations/item-templates",
        json={
            "source_id": source["id"],
            "name": "Крабовые палочки",
            "brand_id": brand["id"],
        },
    )
    assert template_response.status_code == 201, template_response.text
    template = template_response.json()

    source_image = _upload(
        client, f"/api/v1/operations/item-sources/{source['id']}/image"
    )
    brand_image = _upload(client, f"/api/v1/operations/item-brands/{brand['id']}/image")
    item_image = _upload(
        client, f"/api/v1/operations/item-templates/{template['id']}/image"
    )
    assert (
        source_image.status_code
        == brand_image.status_code
        == item_image.status_code
        == 200
    )
    source_image_id = source_image.json()["image_id"]
    brand_image_id = brand_image.json()["image_id"]
    item_image_id = item_image.json()["image_id"]
    assert len({source_image_id, brand_image_id, item_image_id}) == 3

    thumb = client.get(f"/api/v1/operations/media/{item_image_id}/thumb")
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/webp"
    assert "immutable" in thumb.headers["cache-control"]
    assert thumb.headers["x-content-type-options"] == "nosniff"
    with Image.open(BytesIO(thumb.content)) as rendered:
        assert rendered.format == "WEBP"
        assert rendered.width <= 160 and rendered.height <= 160

    cached = client.get(
        f"/api/v1/operations/media/{item_image_id}/thumb",
        headers={"If-None-Match": thumb.headers["etag"]},
    )
    assert cached.status_code == 304
    assert cached.content == b""

    operation = client.post(
        "/api/v1/operations",
        json={
            "kind": "expense",
            "operation_date": "2026-09-04",
            "receipt_items": [
                {
                    "template_id": template["id"],
                    "source_id": source["id"],
                    "brand_id": brand["id"],
                    "shop_name": "Green",
                    "name": "Крабовые палочки",
                    "quantity": "1",
                    "unit_price": "5.39",
                }
            ],
        },
    )
    assert operation.status_code == 201, operation.text
    receipt = operation.json()["receipt_items"][0]
    assert receipt["item_image_id"] == item_image_id
    assert receipt["brand_image_id"] == brand_image_id
    assert receipt["source_image_id"] == source_image_id

    replacement = _upload(
        client,
        f"/api/v1/operations/item-templates/{template['id']}/image",
        _png(size=(80, 240), color=(220, 80, 40, 255)),
    )
    assert replacement.status_code == 200, replacement.text
    replacement_id = replacement.json()["image_id"]
    assert replacement_id != item_image_id
    assert (
        client.get(f"/api/v1/operations/media/{item_image_id}/thumb").status_code == 404
    )
    refreshed = client.get(f"/api/v1/operations/{operation.json()['id']}").json()
    assert refreshed["receipt_items"][0]["item_image_id"] == replacement_id

    deleted = client.delete(f"/api/v1/operations/item-templates/{template['id']}/image")
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["image_id"] is None
    assert (
        client.get(f"/api/v1/operations/media/{replacement_id}/detail").status_code
        == 404
    )


def test_catalog_image_validation_and_user_isolation(client: TestClient):
    source = client.post(
        "/api/v1/operations/item-sources", json={"name": "Store"}
    ).json()
    image_url = f"/api/v1/operations/item-sources/{source['id']}/image"

    wrong_mime = _upload(client, image_url, content_type="image/jpeg")
    assert wrong_mime.status_code == 400
    assert "does not match" in wrong_mime.json()["detail"]

    corrupt = _upload(client, image_url, payload=b"not an image")
    assert corrupt.status_code == 400

    svg = _upload(client, image_url, payload=b"<svg/>", content_type="image/svg+xml")
    assert svg.status_code == 400

    too_large = _upload(
        client, image_url, payload=b"0" * (CatalogMediaService.MAX_UPLOAD_BYTES + 1)
    )
    assert too_large.status_code == 413

    uploaded = _upload(client, image_url)
    assert uploaded.status_code == 200
    asset_id = uploaded.json()["image_id"]
    app.dependency_overrides[get_current_user_id] = lambda: 2
    assert client.get(f"/api/v1/operations/media/{asset_id}/thumb").status_code == 404
    assert _upload(client, image_url).status_code == 404


def test_image_processing_applies_exif_orientation_and_strips_metadata():
    source = Image.new("RGB", (40, 20), (90, 150, 210))
    exif = Image.Exif()
    exif[274] = 6
    exif[315] = "private author"
    input_buffer = BytesIO()
    source.save(input_buffer, format="JPEG", exif=exif)

    processed = CatalogMediaService.process_image(
        raw=input_buffer.getvalue(),
        content_type="image/jpeg",
    )
    with Image.open(BytesIO(processed.detail_bytes)) as detail:
        assert detail.size == (20, 40)
        assert not detail.getexif()


def test_image_processing_rejects_animation_and_pixel_bombs(monkeypatch):
    animated = BytesIO()
    Image.new("RGB", (4, 4), "red").save(
        animated,
        format="WEBP",
        save_all=True,
        append_images=[Image.new("RGB", (4, 4), "blue")],
        duration=100,
        loop=0,
    )
    with pytest.raises(CatalogMediaValidationError, match="Animated"):
        CatalogMediaService.process_image(
            raw=animated.getvalue(), content_type="image/webp"
        )

    monkeypatch.setattr(CatalogMediaService, "MAX_PIXELS", 100)
    with pytest.raises(CatalogMediaTooLargeError, match="20 megapixels"):
        CatalogMediaService.process_image(
            raw=_png(size=(11, 10)), content_type="image/png"
        )
