from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_catalog_media_runtime_uses_authenticated_bounded_blob_cache():
    manifest = _read("static/js/app-manifest.js")
    media = _read("static/js/app-catalog-media.js")
    styles = _read("static/styles.css")

    assert manifest.index('"/static/js/app-catalog-media.js"') < manifest.index(
        '"/static/js/app-features-operation-modal-receipt-pickers.js"'
    )
    assert "MAX_OBJECT_URLS = 160" in media
    assert "IntersectionObserver" in media
    assert "MutationObserver" in media
    assert "Authorization: `Bearer ${state.token}`" in media
    assert "URL.createObjectURL(blob)" in media
    assert "URL.revokeObjectURL" in media
    assert 'cache: "force-cache"' in media
    assert '@import url("/static/css/components-catalog-media.css?v=20260904d");' in styles


def test_all_catalog_entities_offer_image_picker_and_media_mutations():
    modals = _read("static/js/templates/modals-item-catalog.js")
    media = _read("static/js/app-catalog-media.js")
    brands = _read("static/js/app-features-item-brands.js")
    items = _read("static/js/app-features-item-catalog-modal.js")
    sources = _read("static/js/app-features-item-catalog-sources.js")

    for picker_name in ("item-template", "item-brand", "item-source"):
        assert f'data-catalog-image-picker="{picker_name}"' in modals
    assert 'accept="image/jpeg,image/png,image/webp"' in modals
    assert 'brand: "item-brands"' in media
    assert 'template: "item-templates"' in media
    assert 'source: "item-sources"' in media
    assert 'commitPicker?.("item-brand", "brand"' in brands
    assert 'commitPicker?.(\n          "item-template",\n          "template"' in items
    assert '"item-source",\n          "source"' in sources


def test_thumbnails_and_nested_item_card_are_wired_through_receipt_surfaces():
    receipt = _read("static/js/app-features-operation-modal-receipt.js")
    pickers = _read("static/js/app-features-operation-modal-receipt-pickers.js")
    interactions = _read("static/js/app-features-operation-modal-receipt-interactions.js")
    display = _read("static/js/app-features-operations-display.js")
    item_modal = _read("static/js/app-features-item-catalog-modal.js")
    media = _read("static/js/app-catalog-media.js")

    assert 'data-open-receipt-template-card="${Number(item.template_id)}"' in receipt
    assert "renderThumb?.(item.image_id" in pickers
    assert "renderThumb?.(getReceiptSourceMeta(shopName)?.image_id" in pickers
    assert 'button[data-open-receipt-template-card]' in interactions
    assert 'data-open-receipt-template-card="${Number(row.template_id)}"' in display
    assert "async function openItemTemplateCard(templateId)" in media
    assert "core.bringModalToFront?.(modal);" in media
    assert "applySavedTemplateToReceiptDrafts" in receipt
    assert 'for (const mode of ["create", "edit"])' in receipt
    assert "applySavedTemplateToReceiptDrafts?.(savedItem)" in item_modal
    assert "refreshOpenReceiptTemplate?.(savedItem)" in item_modal


def test_brand_rows_use_shared_kebab_with_delete_wording():
    brands = _read("static/js/app-features-item-brands.js")

    assert "core.renderInlineKebabMenu?.(`item-brand-${id}`" in brands
    assert 'data-edit-item-brand-id="${id}"' in brands
    assert 'data-delete-item-brand-id="${id}"' in brands
    assert ">Удалить</button>" in brands
    assert 'const actionLabel = "Удалить"' in brands
    assert "Архивировать" not in brands
    assert "Бренд удалён" in brands


def test_catalog_dense_controls_preserve_special_inputs_and_price_date_space():
    media_styles = _read("static/css/components-catalog-media.css")
    modals = _read("static/js/templates/modals-item-catalog.js")

    assert 'class="form-grid item-template-price-grid"' in modals
    assert "<span>Последняя цена</span>" in modals
    assert "<span>Дата цены</span>" in modals
    assert "grid-template-columns: minmax(11rem, 0.8fr) minmax(17.5rem, 1.2fr)" in media_styles
    assert "@media (max-width: 760px)" in media_styles
    assert ".item-template-price-grid {\n    grid-template-columns: minmax(0, 1fr);" in media_styles
    for input_type in ("checkbox", "radio", "hidden", "file", "color"):
        assert f':not([type="{input_type}"])' in media_styles
    assert "min-height: 2.75rem" in media_styles
