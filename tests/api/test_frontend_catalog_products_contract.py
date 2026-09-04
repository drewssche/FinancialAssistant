from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_catalog_products_are_the_default_catalog_view_with_source_view_preserved():
    shell = _read("static/js/templates/shell-sections-secondary.js")
    state = _read("static/js/app-core-state.js")
    catalog = _read("static/js/app-features-item-catalog.js")

    assert shell.index('data-item-catalog-view="products"') < shell.index('data-item-catalog-view="sources"')
    assert shell.index('data-item-catalog-view="sources"') < shell.index('data-item-catalog-view="brands"')
    assert 'id="catalogProductsView"' in shell
    assert 'id="itemCatalogPositionsView"' in shell
    assert 'id="addCatalogProductBtn"' not in shell
    assert 'itemCatalogView: "products"' in state
    assert 'activeView !== "sources"' in catalog
    assert 'getRuntimeModule?.("catalog-products")?.load?.' in catalog


def test_catalog_product_runtime_covers_crud_merge_candidates_and_offer_actions():
    feature = _read("static/js/app-features-catalog-products.js")
    modals = _read("static/js/templates/modals-item-catalog.js")
    media = _read("static/js/app-catalog-media.js")

    assert '"/api/v1/operations/catalog-products"' in feature
    assert '`/api/v1/operations/catalog-products/${id}`' in feature
    assert 'method: id ? "PATCH" : "POST"' in feature
    assert 'catalog-products/merge-candidates?limit=500' in feature
    assert 'JSON.stringify({ source_product_ids: sourceIds })' in feature
    assert '/offers/${templateId}/detach' in feature
    for action in ("history", "operations", "edit", "detach"):
        assert f'data-product-offer-action="{action}"' in feature
    assert "target_product" in feature and "source_product" in feature and "candidate?.products" in feature
    assert "source_conflicts" in feature
    assert "productOfferSummary" in feature
    assert 'class="catalog-product-merge-sources"' in feature
    assert 'class="catalog-product-candidate-products"' in feature
    assert '|| "Без источника"' in feature
    assert 'id="catalogProductModal"' in modals
    assert 'id="catalogProductMergeModal"' in modals
    assert 'maxlength="160"' in modals
    assert 'product: "catalog-products"' in media
    assert 'commitPicker?.("catalog-product", "product"' in feature


def test_receipt_picker_uses_one_product_and_resolves_source_offer_without_overwriting_manual_price():
    pickers = _read("static/js/app-features-operation-modal-receipt-pickers.js")
    interactions = _read("static/js/app-features-operation-modal-receipt-interactions.js")
    receipt = _read("static/js/app-features-operation-modal-receipt.js")
    plans = _read("static/js/app-features-plans.js")

    assert "rebuildReceiptProductHints" in pickers
    assert 'data-receipt-product-id="${item.product_id}"' in pickers
    assert '`/api/v1/operations/catalog-products?${params.toString()}`' in pickers
    assert "selectedSourceId ? null" in pickers
    assert "matchingProducts.find((item) => receiptProductOfferForSource(item, shopName, sourceId))" in pickers
    assert "Number(right.sourceMatch) - Number(left.sourceMatch)" in pickers
    assert "rowItem.product_id = productId" in interactions
    assert "rowItem.name = normalizeReceiptName(offer?.name" in interactions
    assert "if (!rowItem.price_touched)" in interactions
    assert "price_touched:" in receipt
    assert "category_touched: Boolean(seed.category_touched)" in receipt
    assert receipt.count("category_touched: Boolean(item.category_touched)") == 2
    assert 'updateReceiptItemField(draftId, "category_id"' in interactions
    assert "preserveProduct: keepProduct" in receipt
    assert "...(Number(item.product_id) > 0 ? { product_id: Number(item.product_id) } : {})" in receipt
    assert "product_id: row.product_id || null" in plans


def test_analytics_and_operations_drill_down_by_canonical_product():
    analytics = _read("static/js/app-features-analytics-positions.js")
    analytics_actions = _read("static/js/app-features-analytics.js")
    operations = _read("static/js/app-features-operations.js")

    assert "`product:${Number(item.product_id)}`" in analytics
    assert 'data-position-product-id="${item.product_id || ""}"' in analytics
    assert 'data-dashboard-position-product-id="${item.product_id || ""}"' in analytics
    assert "operationsProductFilterId = Number(productId || 0) || null" in analytics_actions
    assert 'params.set("product_id", String(state.operationsProductFilterId))' in operations
    assert "async function openOperationsForProduct" in operations
    assert 'hasProduct ? "Товар" : "Позиция"' in operations
