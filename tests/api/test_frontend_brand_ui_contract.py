from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_catalog_exposes_brand_management_and_assignment_controls():
    shell = _read("static/js/templates/shell-sections-secondary.js")
    modals = _read("static/js/templates/modals-item-catalog.js")
    elements = _read("static/js/app-core-elements.js")

    positions_at = shell.index('data-item-catalog-view="positions"')
    brands_at = shell.index('data-item-catalog-view="brands"')
    assert positions_at < brands_at
    assert 'data-item-catalog-view="recommendations"' not in shell
    assert 'id="itemBrandsView"' in shell
    assert 'id="itemBrandsKpiGrid"' in shell
    assert 'id="itemBrandsSearchQ"' in shell
    assert 'id="itemCatalogBrandFilter"' in shell
    assert 'id="itemCatalogBulkBrand"' in shell
    assert 'id="itemCatalogSelectAll"' in shell

    assert 'id="itemTemplateBrand"' in modals
    assert 'id="itemTemplateBrandSearch"' in modals
    assert 'id="itemBrandModal"' in modals
    assert 'id="itemBrandDetailModal"' in modals
    assert 'id="openItemBrandOperationsBtn"' in modals
    assert 'id="itemBrandName" type="text" maxlength="160"' in modals
    assert 'itemTemplateBrand: document.getElementById("itemTemplateBrand")' in elements
    assert 'itemBrandsView: document.getElementById("itemBrandsView")' in elements


def test_item_brand_runtime_covers_crud_detail_and_bulk_assignment():
    brands = _read("static/js/app-features-item-brands.js")
    catalog = _read("static/js/app-features-item-catalog-modal.js")
    brand_styles = _read("static/css/components-item-brands.css")
    sources = _read("static/js/app-features-item-catalog-sources.js")
    renderer = _read("static/js/app-item-catalog-render-coordinator.js")
    init = _read("static/js/app-init-features-catalog.js")

    assert 'registerRuntimeModule?.("item-brands"' in brands
    assert '"/api/v1/operations/item-brands"' in brands
    assert "loadItemBrands" in brands
    assert "ensureItemBrandsLoaded" in brands
    assert "openItemBrandDetail" in brands
    assert "openOperationsForItemBrand" in brands
    assert "cleanupRuntime" in brands
    assert "brand?.is_archived ?? brand?.brand_is_archived" in brands
    assert 'item-brand-archive-badge">Архивный' in brands
    assert 'editItemBrandFromDetailBtn.classList.toggle("hidden", archived)' in brands
    assert "ensureItemBrandsLoaded().catch" in brands
    assert "`/api/v1/operations/item-brands/${id}`" in brands
    assert '"/api/v1/operations/item-templates/bulk-brand"' in brands
    assert "template_ids: selectedIds, brand_id: brandId" in brands
    assert "Promise.all(selectedIds.map" not in brands
    assert "payload.brand_id = Number(el.itemTemplateBrand" in catalog
    assert "handleItemTemplateBrandPickerClick" in catalog
    assert "itemTemplateBrandSelectionTouched" in catalog
    assert "if (!isEdit || itemTemplateBrandSelectionTouched)" in catalog
    assert "hydrateItemTemplateBrandFields(savedItem)" in catalog
    assert "restoreItemTemplateBrandSearchLabel" in catalog
    assert "getSelectedItemTemplateBrandMeta" in catalog
    assert "linkedArchivedBrand" in catalog
    assert "selected.is_archived ?? selected.brand_is_archived" in catalog
    assert "invalidateItemCatalogDependentCaches?.()" in catalog
    assert "loadItemBrands?.({ force: true })" in catalog
    assert "invalidateItemCatalogDependentCaches?.()" in sources
    assert "loadItemBrands?.({ force: true })" in sources
    assert "state.selectedItemCatalogIds?.delete?.(Number(item.id))" in catalog
    assert "state.selectedItemCatalogIds?.clear?.()" in catalog
    assert "`/api/v1/operations/item-sources/${Number(source.id)}`" in sources
    assert "for (const item of matchedItems)" not in sources
    assert "data-item-catalog-select-id" in renderer
    assert 'data-label="Бренд"' in renderer
    assert "itemBrandsFeature.bind?.()" in init

    hydration = catalog[
        catalog.index("function hydrateItemTemplateBrandFields(item)")
        : catalog.index("function restoreItemTemplateBrandSearchLabel()")
    ]
    assert "const brandMeta =" in hydration
    assert "hydrateItemTemplateBrandFields(item);" not in hydration
    assert "grid-template-columns: auto minmax(0, 1fr) auto" in brand_styles


def test_analytics_structure_supports_brand_breakdown_and_drilldown():
    shell = _read("static/js/templates/shell-sections-primary.js")
    shared = _read("static/js/app-features-analytics-shared.js")
    snapshot = _read("static/js/app-analytics-breakdown-snapshot-coordinator.js")
    renderer = _read("static/js/app-analytics-breakdown-render-coordinator.js")
    init = _read("static/js/app-init-features-analytics.js")

    assert 'data-analytics-breakdown-level="brand"' in shell
    assert 'id="analyticsBrandCoverage"' in shell
    assert 'return "Структура по брендам"' in shared
    assert "`brand:${item.brand_id}`" in shared
    assert "brand_accent_color" in snapshot
    assert "brand_coverage_pct" in renderer
    assert 'data-analytics-brand-id' in renderer
    assert 'data-analytics-brand-archived' in renderer
    assert "brand_is_archived: card.dataset.analyticsBrandArchived === \"true\"" in init
    assert 'getRuntimeModule?.("item-brands")?.openItemBrandDetail' in init


def test_catalog_cleanup_drops_user_scoped_brand_and_template_state():
    catalog = _read("static/js/app-features-item-catalog.js")

    cleanup = catalog[catalog.index("function cleanupItemCatalogRuntime()") : catalog.index("function refreshItemCatalogView()")]
    assert 'getRuntimeModule?.("item-brands")?.cleanupRuntime?.()' in cleanup
    assert "state.itemCatalogItems = []" in cleanup
    assert "state.itemCatalogAllItems = []" in cleanup
    assert "state.receiptTemplateHints = []" in cleanup
    assert "state.itemBrands = []" in cleanup
    assert "state.itemBrandsLoaded = false" in cleanup
    assert "state.selectedItemCatalogIds = new Set()" in cleanup
    assert 'state.itemCatalogView = "positions"' in cleanup
    assert 'state.itemCatalogBrandFilter = "all"' in cleanup


def test_brand_mutations_invalidate_every_dependent_frontend_cache():
    catalog = _read("static/js/app-features-item-catalog.js")
    brands = _read("static/js/app-features-item-brands.js")

    invalidator = catalog[
        catalog.index("function invalidateItemCatalogDependentCaches()")
        : catalog.index("async function fetchItemCatalogPages")
    ]
    for prefix in (
        "item-catalog",
        "item-brands",
        "op:receipt:templates",
        "operations",
        "plans",
        "analytics",
        "dashboard:highlights",
    ):
        assert f'"{prefix}"' in invalidator
    assert "state.receiptTemplateHints = []" in invalidator
    assert "state.itemBrandsLoaded = false" in invalidator
    assert brands.count("invalidateBrandDependentCaches();") >= 3


def test_receipt_brand_search_does_not_persist_an_unconfirmed_draft_choice():
    receipt = _read("static/js/app-features-operation-modal-receipt.js")
    interactions = _read("static/js/app-features-operation-modal-receipt-interactions.js")
    pickers = _read("static/js/app-features-operation-modal-receipt-pickers.js")

    assert "item.brand_touched || item.brand_id" not in receipt
    assert receipt.count("...(item.brand_touched ? { brand_id:") == 2
    assert "The text box is only a search query" in receipt
    assert 'currentInput.value = normalizeReceiptName(item?.brand_name || "")' in interactions

    enter_branch = interactions[
        interactions.index('if (field === "brand_search") {', interactions.index("function handleReceiptItemsListKeydown"))
        : interactions.index('if (field === "category_search") {', interactions.index("function handleReceiptItemsListKeydown"))
    ]
    assert "upsertLocalReceiptTemplate" not in enter_branch
    assert 'rawQuery.toLowerCase() === normalizeReceiptName(rowItem.brand_name || "").toLowerCase()' in pickers


def test_operation_and_plan_mutations_refresh_receipt_brand_hints():
    operation_mutations = _read("static/js/app-features-operations-mutations.js")
    plans = _read("static/js/app-features-plans.js")

    assert "itemCatalogFeature.invalidateItemCatalogDependentCaches();" in operation_mutations
    assert "itemCatalogFeature.invalidateItemCatalogDependentCaches();" in plans
    assert "state.receiptTemplateHints = []" in operation_mutations
    assert "state.receiptTemplateHints = []" in plans


def test_brand_filters_have_distinct_all_kind_keys_and_survive_back_navigation():
    shared = _read("static/js/app-features-analytics-shared.js")
    snapshot = _read("static/js/app-analytics-breakdown-snapshot-coordinator.js")
    analytics = _read("static/js/app-features-analytics.js")
    navigation = _read("static/js/app-section-ui.js")

    assert 'selectedKind === "all" ? `${brandKey}:${item.category_kind || "expense"}` : brandKey' in shared
    assert "breakdownItemKey(selectedLevel, normalizedItem, selectedKind)" in snapshot
    assert analytics.count("clearOperationsBrandFilter();") == 4
    assert "operationsBrandFilterId: state.operationsBrandFilterId" in navigation
    assert "operationsBrandFilterName: state.operationsBrandFilterName" in navigation
    assert "state.operationsBrandFilterId = snapshot.operationsBrandFilterId ?? null" in navigation
    assert 'state.operationsBrandFilterName = snapshot.operationsBrandFilterName || ""' in navigation
