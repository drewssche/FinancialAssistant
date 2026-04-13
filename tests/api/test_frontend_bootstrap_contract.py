from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = REPO_ROOT / "static" / "index.html"
MANIFEST_JS = REPO_ROOT / "static" / "js" / "app-manifest.js"


def test_index_html_uses_manifest_bootstrap_pair():
    html = INDEX_HTML.read_text(encoding="utf-8")

    script_sources = re.findall(r'<script[^>]+src="([^"]+)"', html)

    assert "/static/js/app-manifest.js" in script_sources
    assert "/static/js/app-bootstrap.js" in script_sources
    assert "/static/js/app-init.js" not in script_sources


def test_manifest_lists_bootstrap_scripts_in_stable_order():
    manifest = MANIFEST_JS.read_text(encoding="utf-8")
    script_sources = re.findall(r'"(/static/js/[^"]+\.js)"', manifest)

    assert script_sources, "frontend script manifest must not be empty"
    assert script_sources[0] == "/static/js/templates/shell-sections-primary.js"
    assert script_sources[-1] == "/static/js/app-init.js"
    assert len(script_sources) == len(set(script_sources)), "frontend script manifest must not contain duplicates"
    assert "/static/js/app-init-registry.js" in script_sources
    assert script_sources.index("/static/js/app-init-registry.js") < script_sources.index("/static/js/app-init-core.js")


def test_app_init_uses_bootstrap_registry_with_global_fallback():
    app_init = (REPO_ROOT / "static" / "js" / "app-init.js").read_text(encoding="utf-8")

    assert 'getBootstrapModule?.("core")' in app_init
    assert 'getBootstrapModule?.("features")' in app_init
    assert 'getBootstrapModule?.("startup")' in app_init
    assert "|| window.App.initCore" in app_init


def test_runtime_registry_is_loaded_before_feature_modules():
    manifest = MANIFEST_JS.read_text(encoding="utf-8")
    script_sources = re.findall(r'"(/static/js/[^"]+\.js)"', manifest)

    registry_index = script_sources.index("/static/js/app-runtime-registry.js")
    assert registry_index < script_sources.index("/static/js/app-features-dashboard.js")
    assert registry_index < script_sources.index("/static/js/app-features-session-auth.js")
    assert registry_index < script_sources.index("/static/js/app-features-session.js")
    assert registry_index < script_sources.index("/static/js/app-features.js")
    assert script_sources.index("/static/js/app-categories-ui-coordinator.js") < script_sources.index(
        "/static/js/app-categories-table-ui.js"
    )
    assert script_sources.index("/static/js/app-categories-section-coordinator.js") < script_sources.index(
        "/static/js/app-init-features-catalog.js"
    )
    assert script_sources.index("/static/js/app-debts-ui-coordinator.js") < script_sources.index(
        "/static/js/app-init-features-debts.js"
    )
    assert script_sources.index("/static/js/app-analytics-ui-coordinator.js") < script_sources.index(
        "/static/js/app-init-features-analytics.js"
    )
    assert script_sources.index("/static/js/app-picker-ui-coordinator.js") < script_sources.index(
        "/static/js/app-init-features-pickers.js"
    )
    assert script_sources.index("/static/js/app-item-catalog-ui-coordinator.js") < script_sources.index(
        "/static/js/app-init-features-catalog.js"
    )
    assert script_sources.index("/static/js/app-item-catalog-section-coordinator.js") < script_sources.index(
        "/static/js/app-features-item-catalog.js"
    )
    assert script_sources.index("/static/js/app-item-catalog-render-coordinator.js") < script_sources.index(
        "/static/js/app-features-item-catalog.js"
    )
    assert script_sources.index("/static/js/app-item-catalog-section-coordinator.js") < script_sources.index(
        "/static/js/app-init-features-catalog.js"
    )
    assert script_sources.index("/static/js/app-analytics-hover-coordinator.js") < script_sources.index(
        "/static/js/app-init-features-analytics.js"
    )
    assert script_sources.index("/static/js/app-analytics-hover-state-coordinator.js") < script_sources.index(
        "/static/js/app-features-analytics-highlights-ui.js"
    )
    assert script_sources.index("/static/js/app-analytics-breakdown-ui-coordinator.js") < script_sources.index(
        "/static/js/app-features-analytics-highlights-ui.js"
    )
    assert script_sources.index("/static/js/app-analytics-breakdown-visibility-coordinator.js") < script_sources.index(
        "/static/js/app-features-analytics-highlights-ui.js"
    )
    assert script_sources.index("/static/js/app-analytics-breakdown-snapshot-coordinator.js") < script_sources.index(
        "/static/js/app-features-analytics-highlights-ui.js"
    )


def test_runtime_registry_registrations_exist_for_key_modules():
    runtime_files = [
        REPO_ROOT / "static" / "js" / "app-features-session-preferences.js",
        REPO_ROOT / "static" / "js" / "app-features-session-auth.js",
        REPO_ROOT / "static" / "js" / "app-features-session.js",
        REPO_ROOT / "static" / "js" / "app-features-dashboard.js",
        REPO_ROOT / "static" / "js" / "app-features-admin.js",
        REPO_ROOT / "static" / "js" / "app-features-debts.js",
        REPO_ROOT / "static" / "js" / "app-features-analytics.js",
        REPO_ROOT / "static" / "js" / "app-features-plans.js",
        REPO_ROOT / "static" / "js" / "app-features-item-catalog.js",
        REPO_ROOT / "static" / "js" / "app-features-operations.js",
        REPO_ROOT / "static" / "js" / "app-features-operation-modal.js",
    ]

    contents = "\n".join(path.read_text(encoding="utf-8") for path in runtime_files)

    assert 'registerRuntimeModule?.("session-preferences"' in contents
    assert 'registerRuntimeModule?.("session-auth"' in contents
    assert 'registerRuntimeModule?.("session"' in contents
    assert 'registerRuntimeModule?.("dashboard"' in contents
    assert 'registerRuntimeModule?.("admin"' in contents
    assert 'registerRuntimeModule?.("debts"' in contents
    assert 'registerRuntimeModule?.("analytics"' in contents
    assert 'registerRuntimeModule?.("plans"' in contents
    assert 'registerRuntimeModule?.("item-catalog"' in contents
    assert 'registerRuntimeModule?.("operations"' in contents
    assert 'registerRuntimeModule?.("operation-modal"' in contents


def test_dashboard_navigation_ignores_stale_section_loads():
    section_ui = (REPO_ROOT / "static" / "js" / "app-section-ui.js").read_text(encoding="utf-8")
    dashboard = (REPO_ROOT / "static" / "js" / "app-features-dashboard.js").read_text(encoding="utf-8")

    assert "let sectionSwitchSeq = 0" in section_ui
    assert "const switchSeq = ++sectionSwitchSeq" in section_ui
    assert "if (!isCurrentSwitch())" in section_ui
    assert 'core.setStatus("Не удалось обновить дашборд")' in section_ui
    assert "let dashboardLoadSeq = 0" in dashboard
    assert "const loadSeq = ++dashboardLoadSeq" in dashboard
    assert 'state.activeSection === "dashboard"' in dashboard
    assert "if (!isCurrentDashboardLoad())" in dashboard


def test_hot_paths_use_local_action_getters_instead_of_direct_global_calls():
    section_ui = (REPO_ROOT / "static" / "js" / "app-section-ui.js").read_text(encoding="utf-8")
    session_auth = (REPO_ROOT / "static" / "js" / "app-features-session-auth.js").read_text(encoding="utf-8")
    analytics = (REPO_ROOT / "static" / "js" / "app-features-analytics.js").read_text(encoding="utf-8")
    operations_mutations = (REPO_ROOT / "static" / "js" / "app-features-operations-mutations.js").read_text(encoding="utf-8")
    categories_data = (REPO_ROOT / "static" / "js" / "app-categories-data.js").read_text(encoding="utf-8")
    plans = (REPO_ROOT / "static" / "js" / "app-features-plans.js").read_text(encoding="utf-8")
    features = (REPO_ROOT / "static" / "js" / "app-features.js").read_text(encoding="utf-8")
    operations = (REPO_ROOT / "static" / "js" / "app-features-operations.js").read_text(encoding="utf-8")
    item_catalog = (REPO_ROOT / "static" / "js" / "app-features-item-catalog.js").read_text(encoding="utf-8")
    item_catalog_section_coordinator = (
        REPO_ROOT / "static" / "js" / "app-item-catalog-section-coordinator.js"
    ).read_text(encoding="utf-8")
    item_catalog_render_coordinator = (
        REPO_ROOT / "static" / "js" / "app-item-catalog-render-coordinator.js"
    ).read_text(encoding="utf-8")
    item_catalog_ui_coordinator = (REPO_ROOT / "static" / "js" / "app-item-catalog-ui-coordinator.js").read_text(encoding="utf-8")
    dashboard = (REPO_ROOT / "static" / "js" / "app-features-dashboard.js").read_text(encoding="utf-8")
    features = (REPO_ROOT / "static" / "js" / "app-features.js").read_text(encoding="utf-8")
    operations_display = (REPO_ROOT / "static" / "js" / "app-features-operations-display.js").read_text(encoding="utf-8")
    operations_mutations_factory = (REPO_ROOT / "static" / "js" / "app-features-operations-mutations.js").read_text(encoding="utf-8")
    debts_modals = (REPO_ROOT / "static" / "js" / "app-features-debts-modals.js").read_text(encoding="utf-8")
    debts = (REPO_ROOT / "static" / "js" / "app-features-debts.js").read_text(encoding="utf-8")
    admin = (REPO_ROOT / "static" / "js" / "app-features-admin.js").read_text(encoding="utf-8")
    session_preferences = (REPO_ROOT / "static" / "js" / "app-features-session-preferences.js").read_text(encoding="utf-8")
    bulk_ui = (REPO_ROOT / "static" / "js" / "app-bulk-ui.js").read_text(encoding="utf-8")
    categories_ui = (REPO_ROOT / "static" / "js" / "app-categories-ui.js").read_text(encoding="utf-8")
    categories_js = (REPO_ROOT / "static" / "js" / "app-categories.js").read_text(encoding="utf-8")
    categories_table_ui = (REPO_ROOT / "static" / "js" / "app-categories-table-ui.js").read_text(encoding="utf-8")
    bulk_bindings_ops = (REPO_ROOT / "static" / "js" / "app-bulk-bindings-operations.js").read_text(encoding="utf-8")
    picker_utils = (REPO_ROOT / "static" / "js" / "app-picker-utils.js").read_text(encoding="utf-8")
    dashboard_data = (REPO_ROOT / "static" / "js" / "app-dashboard-data.js").read_text(encoding="utf-8")
    item_catalog_modal = (REPO_ROOT / "static" / "js" / "app-features-item-catalog-modal.js").read_text(encoding="utf-8")
    item_catalog_sources = (REPO_ROOT / "static" / "js" / "app-features-item-catalog-sources.js").read_text(encoding="utf-8")
    analytics_calendar = (REPO_ROOT / "static" / "js" / "app-features-analytics-calendar.js").read_text(encoding="utf-8")
    analytics_trend = (REPO_ROOT / "static" / "js" / "app-features-analytics-trend.js").read_text(encoding="utf-8")
    analytics_highlights = (REPO_ROOT / "static" / "js" / "app-features-analytics-highlights.js").read_text(encoding="utf-8")
    analytics_highlights_ui = (REPO_ROOT / "static" / "js" / "app-features-analytics-highlights-ui.js").read_text(encoding="utf-8")
    op_modal = (REPO_ROOT / "static" / "js" / "app-features-operation-modal.js").read_text(encoding="utf-8")
    op_modal_receipt = (REPO_ROOT / "static" / "js" / "app-features-operation-modal-receipt.js").read_text(encoding="utf-8")
    op_modal_receipt_interactions = (REPO_ROOT / "static" / "js" / "app-features-operation-modal-receipt-interactions.js").read_text(encoding="utf-8")
    op_modal_receipt_pickers = (REPO_ROOT / "static" / "js" / "app-features-operation-modal-receipt-pickers.js").read_text(encoding="utf-8")
    op_modal_categories = (REPO_ROOT / "static" / "js" / "app-features-operation-modal-categories.js").read_text(encoding="utf-8")
    op_modal_debt = (REPO_ROOT / "static" / "js" / "app-features-operation-modal-debt-counterparty.js").read_text(encoding="utf-8")
    op_modal_preview = (REPO_ROOT / "static" / "js" / "app-features-operation-modal-preview.js").read_text(encoding="utf-8")
    core_actions = (REPO_ROOT / "static" / "js" / "app-core-actions.js").read_text(encoding="utf-8")
    init_core = (REPO_ROOT / "static" / "js" / "app-init-core.js").read_text(encoding="utf-8")
    init_startup = (REPO_ROOT / "static" / "js" / "app-init-startup.js").read_text(encoding="utf-8")
    init_features = (REPO_ROOT / "static" / "js" / "app-init-features.js").read_text(encoding="utf-8")
    analytics_init = (REPO_ROOT / "static" / "js" / "app-init-features-analytics.js").read_text(encoding="utf-8")
    analytics_coordinator = (REPO_ROOT / "static" / "js" / "app-analytics-ui-coordinator.js").read_text(encoding="utf-8")
    analytics_hover_coordinator = (REPO_ROOT / "static" / "js" / "app-analytics-hover-coordinator.js").read_text(encoding="utf-8")
    analytics_hover_state = (REPO_ROOT / "static" / "js" / "app-analytics-hover-state-coordinator.js").read_text(encoding="utf-8")
    analytics_breakdown_ui = (REPO_ROOT / "static" / "js" / "app-analytics-breakdown-ui-coordinator.js").read_text(encoding="utf-8")
    analytics_breakdown_visibility = (
        REPO_ROOT / "static" / "js" / "app-analytics-breakdown-visibility-coordinator.js"
    ).read_text(encoding="utf-8")
    analytics_breakdown_snapshot = (
        REPO_ROOT / "static" / "js" / "app-analytics-breakdown-snapshot-coordinator.js"
    ).read_text(encoding="utf-8")
    analytics_breakdown_render = (
        REPO_ROOT / "static" / "js" / "app-analytics-breakdown-render-coordinator.js"
    ).read_text(encoding="utf-8")
    bulk_bindings_categories = (
        REPO_ROOT / "static" / "js" / "app-bulk-bindings-categories.js"
    ).read_text(encoding="utf-8")
    bulk_bindings_operations = (
        REPO_ROOT / "static" / "js" / "app-bulk-bindings-operations.js"
    ).read_text(encoding="utf-8")
    pickers_init = (REPO_ROOT / "static" / "js" / "app-init-features-pickers.js").read_text(encoding="utf-8")
    picker_coordinator = (REPO_ROOT / "static" / "js" / "app-picker-ui-coordinator.js").read_text(encoding="utf-8")
    categories_ui_coordinator = (REPO_ROOT / "static" / "js" / "app-categories-ui-coordinator.js").read_text(encoding="utf-8")
    categories_section_coordinator = (REPO_ROOT / "static" / "js" / "app-categories-section-coordinator.js").read_text(encoding="utf-8")
    catalog_init = (REPO_ROOT / "static" / "js" / "app-init-features-catalog.js").read_text(encoding="utf-8")
    debts_ui_coordinator = (REPO_ROOT / "static" / "js" / "app-debts-ui-coordinator.js").read_text(encoding="utf-8")
    debts_init = (REPO_ROOT / "static" / "js" / "app-init-features-debts.js").read_text(encoding="utf-8")

    assert "function getActions()" in section_ui
    assert "function getCategoryActions()" in section_ui
    assert "function getCategoryActions()" in session_auth
    assert "function getNavigationActions()" in session_auth
    assert "function getNavigationActions()" in analytics
    assert "function getActions()" in operations_mutations
    assert "function getOperationModal()" in categories_data
    assert "function getDashboardFeature()" in categories_data
    assert "function getOperationsFeature()" in categories_data
    assert "function getCategoryActions()" in op_modal
    assert "function getCategoryActions()" in operations
    session_feature = (REPO_ROOT / "static" / "js" / "app-features-session.js").read_text(encoding="utf-8")
    assert "function getCategoryActions()" in session_feature
    assert "function getPickerUtils()" in plans
    assert 'getRuntimeModule?.("operation-modal")' in operations
    assert 'getRuntimeModule?.("session")' in item_catalog
    assert "function getBulkUi()" in operations
    assert "function getDashboardData()" in dashboard
    assert "function getDashboardFeature()" in debts
    assert "function getSessionFeature()" in debts
    assert "function getSessionFeature()" in admin
    assert "function getSessionFeature()" in categories_table_ui
    assert "function getCategoriesUiCoordinator()" in categories_table_ui
    assert "function getActions()" in catalog_init
    assert "function getCategoryActions()" in catalog_init
    assert "function getPickerUtils()" in catalog_init
    assert "function getCategoriesUiCoordinator()" in catalog_init
    assert "function getCategoriesSectionCoordinator()" in catalog_init
    assert "function getItemCatalogUiCoordinator()" in catalog_init
    assert "function getItemCatalogSectionCoordinator()" in catalog_init
    assert "function getCategoryActions()" in session_preferences
    assert "function getSessionFeature()" in analytics_highlights_ui
    assert "function getOperationsFeature()" in analytics_highlights
    assert "function getSessionFeature()" in init_core
    assert "function getCategoryActions()" in init_core
    assert "function getCategoryActions()" in init_startup
    assert "function getActions()" in init_startup
    assert "function getCategoryActions()" in bulk_bindings_categories
    assert "function getCategoryActions()" in bulk_bindings_operations
    assert "function getSessionFeature()" in init_startup
    assert "function getTelegramWebApp()" in init_startup
    assert "function getSessionFeature()" in core_actions
    assert "function getDashboardFeature()" in init_core
    assert "function getAnalyticsFeature()" in init_core
    assert "function getOperationsFeature()" in init_core
    assert "function getPlansFeature()" in init_core
    assert "function getItemCatalogFeature()" in init_core
    assert "function getOperationModal()" in init_core
    assert "function getSessionFeature()" in init_features
    assert "function getCategoryActions()" in init_features
    assert "function getDashboardFeature()" in init_features
    assert "function getAnalyticsFeature()" in init_features
    assert "function getOperationsFeature()" in init_features
    assert "function getPlansFeature()" in init_features
    assert "function getItemCatalogFeature()" in init_features
    assert "function getOperationModal()" in init_features
    assert "function getSessionFeature()" in plans
    assert "function getItemCatalogFeature()" in plans
    assert "function getOperationsFeature()" in plans
    assert "function getDashboardFeature()" in plans
    assert "function getAnalyticsFeature()" in plans
    assert "function getAnalyticsFeature()" in operations_mutations_factory
    assert 'getRuntimeModule?.("operations-mutation-factory")' in operations
    assert 'getRuntimeModule?.("operations-display-factory")' in operations
    assert 'registerRuntimeModule?.("operations-display-factory"' in operations_display
    assert 'registerRuntimeModule?.("operations-mutation-factory"' in operations_mutations_factory
    assert 'registerRuntimeModule?.("bulk-ui"' in bulk_ui
    assert 'registerRuntimeModule?.("category-ui"' in categories_ui
    assert 'registerRuntimeModule?.("picker-utils"' in picker_utils
    assert 'getRuntimeModule?.("category-actions")' in section_ui
    assert 'getRuntimeModule?.("category-actions")' in bulk_bindings_categories
    assert 'getRuntimeModule?.("category-actions")' in bulk_bindings_operations
    assert '"setupCategoryIconPickers"' not in features
    assert '"closeIconPopovers"' not in features
    assert '"fillGroupSelect"' not in features
    assert '"populateCategorySelect"' not in features
    assert '"renderCreateGroupPicker"' not in features
    assert '"renderEditGroupPicker"' not in features
    assert '"handleCreateGroupSearchFocus"' not in features
    assert '"handleEditGroupSearchFocus"' not in features
    assert '"selectCreateGroup"' not in features
    assert '"selectEditGroup"' not in features
    assert '"groupCategoryIds"' not in features
    assert '"updateCategoriesBulkUi"' not in features
    assert '"renderCategories"' not in features
    assert 'registerRuntimeModule?.("dashboard-data"' in dashboard_data
    assert 'registerRuntimeModule?.("item-catalog-sources-factory"' in item_catalog_sources
    assert 'registerRuntimeModule?.("item-catalog-modal-factory"' in item_catalog_modal
    assert 'registerRuntimeModule?.("analytics-calendar-module"' in analytics_calendar
    assert 'registerRuntimeModule?.("analytics-trend-module"' in analytics_trend
    assert 'registerRuntimeModule?.("analytics-highlights-module"' in analytics_highlights
    assert 'registerRuntimeModule?.("analytics-highlights-ui"' in analytics_highlights_ui
    assert 'registerRuntimeModule?.("analytics-ui-coordinator"' in analytics_coordinator
    assert 'getRuntimeModule?.("analytics-ui-coordinator")' in analytics_init
    assert "function getCore()" in analytics_init
    assert "function getSessionFeature()" in analytics_init
    assert 'registerRuntimeModule?.("analytics-hover-coordinator"' in analytics_hover_coordinator
    assert 'getRuntimeModule?.("analytics-hover-coordinator")' in analytics_init
    assert 'registerRuntimeModule?.("analytics-hover-state-coordinator"' in analytics_hover_state
    assert 'getRuntimeModule?.("analytics-hover-state-coordinator")' in analytics_highlights_ui
    assert 'registerRuntimeModule?.("analytics-breakdown-ui-coordinator"' in analytics_breakdown_ui
    assert 'getRuntimeModule?.("analytics-breakdown-ui-coordinator")' in analytics_highlights_ui
    assert 'registerRuntimeModule?.("analytics-breakdown-visibility-coordinator"' in analytics_breakdown_visibility
    assert 'getRuntimeModule?.("analytics-breakdown-visibility-coordinator")' in analytics_highlights_ui
    assert 'registerRuntimeModule?.("analytics-breakdown-snapshot-coordinator"' in analytics_breakdown_snapshot
    assert 'getRuntimeModule?.("analytics-breakdown-snapshot-coordinator")' in analytics_highlights_ui
    assert 'registerRuntimeModule?.("analytics-breakdown-render-coordinator"' in analytics_breakdown_render
    assert 'getRuntimeModule?.("analytics-breakdown-render-coordinator")' in analytics_highlights_ui
    assert 'getRuntimeModule?.("analytics-highlights-ui")' in analytics_highlights
    assert "applySegmentedSelection({" in analytics_coordinator
    assert "runPersistedAction({" in analytics_coordinator
    assert "function getCore()" in analytics_coordinator
    assert "function getSessionFeature()" in analytics_coordinator
    assert "bindIndexedHover({" in analytics_hover_coordinator
    assert "applyBreakdownHoverState({" in analytics_hover_state
    assert "bindChartSliceHover({" in analytics_breakdown_ui
    assert "bindListItemHover({" in analytics_breakdown_ui
    assert "hiddenBreakdownKeys({" in analytics_breakdown_visibility
    assert "writeHiddenBreakdownKeys({" in analytics_breakdown_visibility
    assert "toggleCategoryBreakdownVisibility({" in analytics_breakdown_visibility
    assert "showAllCategoryBreakdownItems({" in analytics_breakdown_visibility
    assert "buildCategoryBreakdownSnapshot({" in analytics_breakdown_snapshot
    assert "buildDashboardBreakdownSnapshot({" in analytics_breakdown_snapshot
    assert "renderAnalyticsCategoryBreakdownView({" in analytics_breakdown_render
    assert "renderDashboardBreakdownView({" in analytics_breakdown_render
    assert 'registerRuntimeModule?.("categories-ui-coordinator"' in categories_ui_coordinator
    assert 'registerRuntimeModule?.("categories-section-coordinator"' in categories_section_coordinator
    assert 'getRuntimeModule?.("categories-ui-coordinator")' in categories_table_ui
    assert 'getRuntimeModule?.("categories-ui-coordinator")' in catalog_init
    assert 'getRuntimeModule?.("categories-section-coordinator")' in catalog_init
    assert 'getRuntimeModule?.("category-actions")' in catalog_init
    assert 'getRuntimeModule?.("category-actions")' in pickers_init
    assert 'registerRuntimeModule?.("debts-ui-coordinator"' in debts_ui_coordinator
    assert 'getRuntimeModule?.("debts-ui-coordinator")' in debts_init
    assert "renderGroupedCategoryTable({" in categories_ui_coordinator
    assert "bindCategoryKindTabs({" in categories_section_coordinator
    assert "bindCategorySearch({" in categories_section_coordinator
    assert "bindCategoryCollapseExpand({" in categories_section_coordinator
    assert "bindCategoriesInfiniteObserver({" in categories_section_coordinator
    assert "toggleCollapsedGroupFromEvent({" in categories_ui_coordinator
    assert "openEditCategoryModal({" in categories_ui_coordinator
    assert "closeEditCategoryModal({" in categories_ui_coordinator
    assert "openEditGroupModal({" in categories_ui_coordinator
    assert "closeEditGroupModal({" in categories_ui_coordinator
    assert "handleCategoriesBodyClick({" in categories_ui_coordinator
    assert "toggleCategoriesCardMenu({" in categories_ui_coordinator
    assert "handleDebtsCardsClick({" in debts_ui_coordinator
    assert "toggleDebtMenu({" in debts_ui_coordinator
    assert 'registerRuntimeModule?.("picker-ui-coordinator"' in picker_coordinator
    assert 'registerRuntimeModule?.("item-catalog-ui-coordinator"' in item_catalog_ui_coordinator
    assert 'registerRuntimeModule?.("item-catalog-section-coordinator"' in item_catalog_section_coordinator
    assert 'registerRuntimeModule?.("item-catalog-render-coordinator"' in item_catalog_render_coordinator
    assert 'getRuntimeModule?.("item-catalog-ui-coordinator")' in catalog_init
    assert 'getRuntimeModule?.("item-catalog-section-coordinator")' in catalog_init
    assert 'getRuntimeModule?.("item-catalog-section-coordinator")' in item_catalog
    assert 'getRuntimeModule?.("item-catalog-render-coordinator")' in item_catalog
    assert 'getRuntimeModule?.("picker-ui-coordinator")' in pickers_init
    assert "function getActions()" in pickers_init
    assert "function getCategoryActions()" in pickers_init
    assert "function getCore()" in pickers_init
    assert "function getPickerUtils()" in pickers_init
    assert "function getCore()" in picker_coordinator
    assert "bindSearchPicker({" in picker_coordinator
    assert "bindReceiptList(" in picker_coordinator
    assert "bindDatePickerTriggers()" in pickers_init
    assert "toggleItemCatalogCardMenu({" in item_catalog_ui_coordinator
    assert "handleItemCatalogBodyClick({" in item_catalog_ui_coordinator
    assert "syncItemCatalogControls({" in item_catalog_section_coordinator
    assert "handleItemCatalogGroupToggle({" in item_catalog_section_coordinator
    assert "setItemCatalogSortPreset({" in item_catalog_section_coordinator
    assert "collapseAllItemCatalogGroups({" in item_catalog_section_coordinator
    assert "expandAllItemCatalogGroups({" in item_catalog_section_coordinator
    assert "bindItemCatalogSearch({" in item_catalog_section_coordinator
    assert "bindItemCatalogSortTabs({" in item_catalog_section_coordinator
    assert "bindItemCatalogCollapseExpand({" in item_catalog_section_coordinator
    assert "buildItemCatalogGroups({" in item_catalog_render_coordinator
    assert "renderItemCatalog({" in item_catalog_render_coordinator
    assert 'registerRuntimeModule?.("operation-modal-receipt-picker-factory"' in op_modal_receipt_pickers
    assert "function getActions()" in op_modal_receipt_pickers
    assert "function getCategoryActions()" in op_modal_receipt_pickers
    assert "function getPickerUtils()" in op_modal_receipt_pickers
    assert 'registerRuntimeModule?.("operation-modal-receipt-interactions-factory"' in op_modal_receipt_interactions
    assert 'registerRuntimeModule?.("operation-modal-receipt-factory"' in op_modal_receipt
    assert 'registerRuntimeModule?.("operation-modal-category-factory"' in op_modal_categories
    assert 'registerRuntimeModule?.("operation-modal-debt-counterparty-factory"' in op_modal_debt
    assert 'registerRuntimeModule?.("operation-modal-preview"' in op_modal_preview
    assert 'getRuntimeModule?.("category-ui")' in categories_js
    assert 'registerRuntimeModule?.("category-actions"' in categories_js
    assert "function getCategoryUi()" in categories_js
    assert "function getCategoryData()" in categories_js
    assert "function getActionFacade()" in categories_js
    assert "const publicCategoryActions =" in categories_js
    assert 'getRuntimeModule?.("category-ui")' in categories_data
    assert 'getRuntimeModule?.("operation-modal")' in categories_data
    assert 'getRuntimeModule?.("dashboard")' in categories_data
    assert 'getRuntimeModule?.("operations")' in categories_data
    assert 'getRuntimeModule?.("category-actions")' in op_modal
    assert 'getRuntimeModule?.("bulk-ui")' in bulk_bindings_ops
    assert 'getRuntimeModule?.("dashboard")' in bulk_bindings_ops
    assert 'getRuntimeModule?.("operations")' in bulk_bindings_ops
    assert 'getRuntimeModule?.("item-catalog")' in (REPO_ROOT / "static" / "js" / "app-bulk-bindings-item-catalog.js").read_text(encoding="utf-8")
    assert 'getRuntimeModule?.("item-catalog-modal-factory")' in item_catalog
    assert 'getRuntimeModule?.("item-catalog-sources-factory")' in item_catalog_modal
    assert 'getRuntimeModule?.("dashboard-data")' in plans
    assert 'getRuntimeModule?.("dashboard-data")' in debts_modals
    assert "window.App.core.syncDateFieldValue" not in pickers_init
    assert "window.App.actions.savePreferences" not in analytics_init
    assert "window.App.core.runAction" not in analytics_init
    assert "window.App.core.syncSegmentedActive" not in analytics_init
    assert "window.App.actions.renderTodayLabel" not in init_startup
    assert "window.App.actions.renderTodayLabel" not in session_preferences
    assert "if (actions.renderTodayLabel)" not in session_feature
    assert "const categoryActions = window.App.actions" not in session_auth
    assert "const categoryActions = window.App.actions" not in op_modal
    assert "const categoryActions = window.App.actions" not in operations
    assert "return window.App.actions || {}" not in op_modal
    assert "const highlightsUi = window.App.featureAnalyticsHighlightsUi" not in analytics_highlights
    assert "window.App.featureAnalyticsHighlightsUi =" not in analytics_highlights_ui
    assert "window.App.featureAnalyticsHighlightsUi" not in analytics_highlights
    assert "const { state, el, core, actions } = window.App" not in catalog_init
    assert "Object.assign(window.App.actions," not in categories_js
    assert "Object.assign(getActionFacade()," not in categories_js
    assert "function toggleCardMenu(" not in catalog_init
    assert "let categorySearchDebounceId" not in catalog_init
    assert "let itemCatalogSearchDebounceId" not in catalog_init
    assert "actions.tryAutoTelegramLogin" not in init_startup
    assert "actions.bootstrapApp" not in init_startup
    assert "window.App.actions?.openCreateCategoryModal" not in op_modal_receipt_pickers
    assert 'getRuntimeModule?.("category-actions")' in op_modal_receipt_pickers
    assert 'getRuntimeModule?.("dashboard-data")' in operations_mutations_factory
    assert 'getRuntimeModule?.("dashboard")' in debts
    assert 'getRuntimeModule?.("session")' in debts
    assert 'getRuntimeModule?.("session")' in admin
    assert 'getRuntimeModule?.("session")' in categories_table_ui
    assert 'getRuntimeModule?.("session")' in analytics_highlights_ui
    assert 'getRuntimeModule?.("operations")' in analytics_highlights
    assert 'getRuntimeModule?.("session")' in init_core
    assert 'getRuntimeModule?.("category-actions")' in init_core
    assert 'getRuntimeModule?.("category-actions")' in init_startup
    assert 'getRuntimeModule?.("session")' in core_actions
    assert 'getRuntimeModule?.("dashboard")' in init_core
    assert 'getRuntimeModule?.("analytics")' in init_core
    assert 'getRuntimeModule?.("operations")' in init_core
    assert 'getRuntimeModule?.("plans")' in init_core
    assert 'getRuntimeModule?.("item-catalog")' in init_core
    assert 'getRuntimeModule?.("operation-modal")' in init_core
    assert 'getRuntimeModule?.("dashboard")' in section_ui
    assert 'getRuntimeModule?.("analytics")' in section_ui
    assert 'getRuntimeModule?.("operations")' in section_ui
    assert 'getRuntimeModule?.("plans")' in section_ui
    assert 'getRuntimeModule?.("debts")' in section_ui
    assert 'getRuntimeModule?.("item-catalog")' in section_ui
    assert 'getRuntimeModule?.("admin")' in section_ui
    assert 'getRuntimeModule?.("session")' in section_ui
    assert 'getRuntimeModule?.("session")' in init_features
    assert 'getRuntimeModule?.("category-actions")' in init_features
    assert 'getRuntimeModule?.("dashboard")' in init_features
    assert 'getRuntimeModule?.("analytics")' in init_features
    assert 'getRuntimeModule?.("operations")' in init_features
    assert 'getRuntimeModule?.("plans")' in init_features
    assert 'getRuntimeModule?.("item-catalog")' in init_features
    assert 'getRuntimeModule?.("operation-modal")' in init_features
    assert 'getRuntimeModule?.("session")' in plans
    assert 'getRuntimeModule?.("item-catalog")' in plans
    assert 'getRuntimeModule?.("operations")' in plans
    assert 'getRuntimeModule?.("dashboard")' in plans
    assert 'getRuntimeModule?.("analytics")' in plans
    assert 'getRuntimeModule?.("analytics")' in operations_mutations_factory
    assert 'getRuntimeModule?.("operation-modal")' in debts_modals
    assert 'getRuntimeModule?.("analytics")' in (REPO_ROOT / "static" / "js" / "app-features-session-preferences.js").read_text(encoding="utf-8")
    assert 'getRuntimeModule?.("session-preferences")' in session_auth
    assert 'getRuntimeModule?.("session-preferences")' in (REPO_ROOT / "static" / "js" / "app-features-session.js").read_text(encoding="utf-8")
    assert 'getRuntimeModule?.("session-auth")' in (REPO_ROOT / "static" / "js" / "app-features-session.js").read_text(encoding="utf-8")
    assert 'getRuntimeModule("dashboard")' in features
    assert 'getRuntimeModule("session")' in features
    assert 'getRuntimeModule("operation-modal")' in features
    assert "const publicActionFacade =" in features
    assert "const publicActionFacadeContract = Object.freeze({" in features
    assert "window.App.publicActionFacadeContract =" in features
    assert 'navigation: Object.freeze([' in features
    assert 'debt_batch_orchestration: Object.freeze([' in features
    assert '"switchSection"' in features
    assert '"navigateSectionBack"' in features
    assert '"openDebtRepaymentModal"' in features
    assert '"openBatchCreateModal"' in features
    assert '"openCreateCategoryModal"' not in features
    assert '"closeCreateCategoryModal"' not in features
    assert '"closeEditCategoryModal"' not in features
    assert '"closeEditGroupModal"' not in features
    assert '"openEditCategoryModal"' not in features
    assert '"openEditGroupModal"' not in features
    assert '"loadCategories"' not in features
    assert '"createGroup"' not in features
    assert '"bulkDeleteCategories"' not in features
    assert '"bulkDeleteGroups"' not in features
    assert '"telegramLogin"' not in features
    assert '"updateOperationsBulkUi"' not in features
    assert 'getRuntimeModule?.("analytics-trend-module")' in analytics_highlights
    assert 'getRuntimeModule?.("analytics-calendar-module")' in analytics_highlights
    assert 'getRuntimeModule?.("analytics-trend-module")' in analytics_highlights_ui
    assert 'getRuntimeModule?.("picker-utils")' in init_core
    assert 'getRuntimeModule?.("analytics-highlights-module")' in (REPO_ROOT / "static" / "js" / "app-init-features-analytics.js").read_text(encoding="utf-8")
    assert 'getRuntimeModule?.("operation-modal-receipt-factory")' in op_modal
    assert 'getRuntimeModule?.("operation-modal-category-factory")' in op_modal
    assert 'getRuntimeModule?.("operation-modal-debt-counterparty-factory")' in op_modal
    assert 'getRuntimeModule?.("operation-modal-preview")' in op_modal
    assert "|| window.App.categoryUi" not in categories_js
    assert "|| window.App.operationModal" not in (REPO_ROOT / "static" / "js" / "app-features-session-auth.js").read_text(encoding="utf-8")
    assert "|| window.App.pickerUtils" not in op_modal_receipt_pickers
    assert "window.App.createOperationModalReceiptPickerFeature" not in op_modal_receipt_pickers
    assert "window.App.createOperationModalReceiptInteractionsFeature" not in op_modal_receipt_interactions
    assert "window.App.createOperationModalReceiptFeature" not in op_modal_receipt
    assert "window.App.createOperationModalCategoryFeature" not in op_modal_categories
    assert "window.App.createOperationModalDebtCounterpartyFeature" not in op_modal_debt
    assert "window.App.operationModalPreview" not in op_modal_preview
    assert "|| window.App.bulkUi" not in bulk_bindings_ops
    assert "|| window.App.pickerUtils" not in init_core
    assert "|| window.App.featureAnalyticsModules" not in analytics
    assert "window.App.featureDashboard" not in features
    assert "window.App.featureAnalytics" not in features
    assert "window.App.featureAdmin" not in features
    assert "window.App.featureDebts" not in features
    assert "window.App.featurePlans" not in features
    assert "window.App.featureSession" not in features
    assert "window.App.featureItemCatalog" not in features
    assert "window.App.featureOperations" not in features
    assert "window.App.dashboardData" not in dashboard_data
    assert "window.App.pickerUtils" not in picker_utils
    assert "window.App.bulkUi" not in bulk_ui
    assert "window.App.createOperationsDisplayFeature" not in operations_display
    assert "window.App.createOperationsMutationFeature" not in operations_mutations_factory
    assert "window.App.createItemCatalogModalFeature" not in item_catalog_modal
    assert "window.App.createItemCatalogSourcesFeature" not in item_catalog_sources
    assert "window.App.featureAnalyticsModules" not in analytics_calendar
    assert "window.App.featureAnalyticsModules" not in analytics_trend
    assert "window.App.featureAnalyticsModules" not in analytics_highlights
    assert "window.App.featureAnalyticsModules" not in analytics_highlights_ui
    assert "window.App.featureAnalytics" not in analytics
    assert "window.App.featurePlans" not in plans
    assert "window.App.featureDashboard" not in dashboard
    assert "window.App.featureSession" not in (REPO_ROOT / "static" / "js" / "app-features-session.js").read_text(encoding="utf-8")
    assert "window.App.featureSessionPreferences" not in (REPO_ROOT / "static" / "js" / "app-features-session-preferences.js").read_text(encoding="utf-8")
    assert "window.App.featureSessionAuth" not in session_auth
    assert "window.App.featureItemCatalog" not in item_catalog
    assert "window.App.featureDebts" not in (REPO_ROOT / "static" / "js" / "app-features-debts.js").read_text(encoding="utf-8")
    assert "window.App.featureOperations" not in operations
    assert "window.App.featureDashboard" not in features
    assert "window.App.featureSession" not in features
    assert "window.App.featureItemCatalog" not in features
    assert "window.App.featureDebts" not in features
    assert "window.App.featureAnalytics" not in features
    assert "window.App.dashboardData" not in plans
    assert "window.App.dashboardData" not in debts_modals
    assert "window.App.dashboardData" not in operations_mutations_factory
    assert "window.App.pickerUtils" not in plans
    assert "window.App.pickerUtils" not in item_catalog_modal
    assert "window.App.bulkUi" not in operations
    assert "window.App.actions.loadDashboard" not in section_ui
    assert "actions.loadDashboard(" not in section_ui
    assert "actions.loadDashboardOperations(" not in section_ui
    assert "actions.loadDashboardAnalyticsPreview(" not in section_ui
    assert "actions.loadOperations(" not in section_ui
    assert "actions.loadPlans(" not in section_ui
    assert "actions.loadDebtsCards(" not in section_ui
    assert "actions.loadItemCatalog(" not in section_ui
    assert "actions.loadAnalyticsSection(" not in section_ui
    assert "actions.loadAdminUsers(" not in section_ui
    assert "actions.savePreferences(" not in section_ui
    assert "actions.telegramLogin()" not in init_core
    assert "actions.logout(true)" not in init_core
    assert "actions.openCreateModal()" not in init_core
    assert "actions.openCreatePlan" not in init_core
    assert "actions.setCreateEntryMode(" not in init_core
    assert "actions.openItemTemplateModal()" not in init_core
    assert "actions.openSourceGroupModal()" not in init_core
    assert "actions.closeCreateModal()" not in init_core
    assert "actions.closeEditModal()" not in init_core
    assert "actions.closePeriodCustomModal()" not in init_core
    assert "actions.closeOperationReceiptModal()" not in init_core
    assert "actions.closeItemTemplateModal()" not in init_core
    assert "actions.closeSourceGroupModal()" not in init_core
    assert "actions.closeItemTemplateHistoryModal()" not in init_core
    assert "actions.closeSettingsPickerModal()" not in init_core
    assert "actions.applySettingsPickerValue(" not in init_core
    assert "actions.openSettingsPickerModal(" not in init_core
    assert "actions.saveSettings(" not in init_core
    assert "actions.previewInterfaceSettingsUi()" not in init_core
    assert "actions.savePreferencesDebounced(" not in init_core
    assert "actions.loadDashboard()" not in init_core
    assert "actions.loadDashboardAnalyticsPreview(" not in init_core
    assert "actions.loadDashboardOperations()" not in init_core
    assert "actions.syncSettingsPickerButtons()" not in init_core
    assert "actions.deleteMe()" not in init_core
    assert "actions.setPlansTab(" not in init_core
    assert "actions.setPlansKindFilter(" not in init_core
    assert "actions.setPlansStatusFilter(" not in init_core
    assert "actions.setPlansHistoryEventFilter(" not in init_core
    assert "actions.applyPlansSearch()" not in init_core
    assert "actions.handlePlanActionClick(" not in init_core
    assert "actions.setDashboardPlansPeriod(" not in init_core
    assert "actions.syncPlanRecurrenceUi(" not in init_core
    assert "actions.updateCreatePreview" not in init_core
    assert "actions.togglePlanWeekday(" not in init_core
    assert "actions.telegramLogin" not in init_core
    assert "window.App.actions.logout(false)" not in core_actions
    assert "window.App.actions.switchSection" not in analytics
    assert "window.App.actions.loadDashboardAnalyticsPreview" not in operations_mutations
    assert "window.App.actions.renderCreateCategoryPicker" not in categories_data
    assert "return window.App.actions || {}" not in categories_data
    assert "window.App.pickerUtils?.setPopoverOpen" not in plans
    assert "window.App.bulkUi?.updateOperationsBulkUi?.()" not in operations
    assert "actions.updateOperationsBulkUi" not in operations
    assert "window.App.actions?.loadDashboard" not in debts
    assert "window.App.actions?.savePreferences" not in debts
    assert "window.App.actions.savePreferences" not in admin
    assert "window.App.actions?.savePreferences" not in categories_table_ui
    assert "actions.invalidateAllTimeAnchor(" not in bulk_bindings_ops
    assert "actions.loadDashboard(" not in bulk_bindings_ops
    assert "actions.loadDashboardOperations(" not in bulk_bindings_ops
    assert "actions.loadOperations(" not in bulk_bindings_ops
    assert "actions.getCurrentOperationItems(" not in bulk_bindings_ops
    assert "actions.loadItemCatalog(" not in (REPO_ROOT / "static" / "js" / "app-bulk-bindings-item-catalog.js").read_text(encoding="utf-8")
    assert "actions.submitPlanForm(" not in init_features
    assert "actions.createOperation(" not in init_features
    assert "actions.updateOperation(" not in init_features
    assert "actions.submitItemTemplateForm(" not in init_features
    assert "actions.submitSourceGroupForm(" not in init_features
    assert "actions.openPeriodCustomModal(" not in init_features
    assert "actions.ensureAllTimeBounds(" not in init_features
    assert "actions.savePreferences(" not in init_features
    assert "actions.loadDashboard(" not in init_features
    assert "actions.loadDashboardOperations(" not in init_features
    assert "actions.loadOperations(" not in init_features
    assert "actions.loadDashboardAnalyticsPreview(" not in init_features
    assert "actions.loadAnalyticsSection(" not in init_features
    assert "actions.closePeriodCustomModal(" not in init_features
    assert "actions.invalidateAllTimeAnchor(" not in init_features
    assert "window.App.actions?.savePreferencesDebounced" not in analytics_highlights_ui
    assert "window.App.actions.applyAnalyticsTabUi" not in (REPO_ROOT / "static" / "js" / "app-features-session-preferences.js").read_text(encoding="utf-8")
    assert "window.App.actions?.ensureAllTimeBounds" not in analytics_highlights
    assert "getActions().savePreferencesDebounced" not in plans
    assert "actions.loadItemCatalog" not in plans
    assert "actions.loadOperations" not in plans
    assert "actions.loadDashboard" not in plans
    assert "actions.loadDashboardOperations" not in plans
    assert "actions.loadAnalyticsSection" not in plans
    assert "actions.openOperationReceiptModal" not in plans
    assert "actions.loadDashboardAnalyticsPreview" not in operations_mutations_factory
    assert "actions.loadAnalyticsSection" not in operations_mutations_factory
    assert "window.App.actions?.openCreateModalForDebtEdit" not in debts_modals
