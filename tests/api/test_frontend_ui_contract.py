from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = REPO_ROOT / "static" / "index.html"
MANIFEST_JS = REPO_ROOT / "static" / "js" / "app-manifest.js"


def test_mobile_table_styles_live_in_dedicated_responsive_module():
    styles = (REPO_ROOT / "static" / "styles.css").read_text(encoding="utf-8")
    tables = (REPO_ROOT / "static" / "css" / "components-tables.css").read_text(encoding="utf-8")
    responsive_tables = (REPO_ROOT / "static" / "css" / "responsive-sm-tables.css").read_text(encoding="utf-8")

    assert '@import url("/static/css/responsive-sm-tables.css?v=20260716j");' in styles
    assert styles.index("responsive-sm-tables.css") < styles.index("responsive-sm-core.css")
    assert "@media (max-width: 640px)" not in tables
    assert ".mobile-card-table thead" in responsive_tables
    assert ".mobile-card-table .table-hierarchy-child-row::before" in responsive_tables
    assert ".mobile-card-table td[data-label]::before" in responsive_tables


def test_prices_discounts_tab_and_context_navigation_contract():
    shell_primary = (REPO_ROOT / "static" / "js" / "templates" / "shell-sections-primary.js").read_text(encoding="utf-8")
    shell = (REPO_ROOT / "static" / "js" / "templates" / "shell.js").read_text(encoding="utf-8")
    manifest = MANIFEST_JS.read_text(encoding="utf-8")
    navigation = (REPO_ROOT / "static" / "js" / "app-section-ui.js").read_text(encoding="utf-8")

    assert 'data-analytics-tab="commerce"' in shell_primary
    assert 'id="analyticsCommercePanel"' in shell_primary
    assert 'data-analytics-commerce-mode="prices"' in shell_primary
    assert 'data-analytics-commerce-mode="discounts"' in shell_primary
    assert 'id="analyticsPriceIncreasesList"' not in shell_primary
    assert 'id="analyticsTopDiscountSavingsList"' not in shell_primary
    assert '"/static/js/app-features-analytics-commerce.js"' in manifest
    assert 'id="sectionBackBtn"' in shell
    assert 'id="sectionBackLabel"' not in shell
    assert 'preserveBackStack' in navigation


def test_section_kpi_cards_and_mobile_debt_search_contract():
    shell_primary = (REPO_ROOT / "static" / "js" / "templates" / "shell-sections-primary.js").read_text(
        encoding="utf-8"
    )
    shell_secondary = (REPO_ROOT / "static" / "js" / "templates" / "shell-sections-secondary.js").read_text(
        encoding="utf-8"
    )
    elements = (REPO_ROOT / "static" / "js" / "app-core-elements.js").read_text(encoding="utf-8")
    debts_render = (REPO_ROOT / "static" / "js" / "app-features-debts-render.js").read_text(encoding="utf-8")
    categories_table = (REPO_ROOT / "static" / "js" / "app-categories-table-ui.js").read_text(encoding="utf-8")
    item_catalog_render = (REPO_ROOT / "static" / "js" / "app-item-catalog-render-coordinator.js").read_text(
        encoding="utf-8"
    )
    responsive_sm = (REPO_ROOT / "static" / "css" / "responsive-sm-core.css").read_text(encoding="utf-8")
    responsive_sm_modals = (REPO_ROOT / "static" / "css" / "responsive-sm-modals.css").read_text(encoding="utf-8")
    components_core = (REPO_ROOT / "static" / "css" / "components-core.css").read_text(encoding="utf-8")
    analytics_calendar = (REPO_ROOT / "static" / "js" / "app-features-analytics-calendar.js").read_text(encoding="utf-8")

    assert 'id="categoriesKpiGrid"' in shell_primary
    assert 'id="itemCatalogKpiGrid"' in shell_secondary
    assert 'id="debtsSectionKpi" class="analytics-kpi-grid section-kpi-grid debts-section-kpi"' in shell_secondary
    assert 'categoriesKpiGrid: document.getElementById("categoriesKpiGrid")' in elements
    assert 'itemCatalogKpiGrid: document.getElementById("itemCatalogKpiGrid")' in elements
    assert "analytics-kpi-card analytics-kpi-negative" in debts_render
    assert "el.categoriesKpiGrid.innerHTML" in categories_table
    assert "visibleCategories" in categories_table
    assert "activeGroupIds.size" in categories_table
    assert "el.itemCatalogKpiGrid.innerHTML" in item_catalog_render
    assert "Средняя последняя цена" not in item_catalog_render
    assert "#debtsSection .debt-toolbar .table-search-input" in responsive_sm
    assert "height: 2.75rem;" in responsive_sm
    assert ".section-kpi-grid" in components_core
    assert "has-left-fade" not in responsive_sm_modals
    assert "has-right-fade" not in responsive_sm_modals
    assert "classList.toggle(\"has-left-fade\"" not in analytics_calendar


def test_period_control_popovers_have_wide_floating_layout():
    picker_utils = (REPO_ROOT / "static" / "js" / "app-picker-utils.js").read_text(encoding="utf-8")
    overlays_css = (REPO_ROOT / "static" / "css" / "components-overlays.css").read_text(encoding="utf-8")

    assert "Math.min(360, Math.max(320, viewportWidth - margin * 2))" in picker_utils
    assert "Math.min(isControlPopover && !sizesToContent ? 320 : 168, preferredWidth)" in picker_utils
    assert 'const ownerModal = anchor.closest(".modal:not(.hidden)");' in picker_utils
    assert "Math.max(220, (Number.isFinite(ownerModalZIndex) ? ownerModalZIndex : 0) + 2)" in picker_utils
    assert 'const alignToAnchorStart = popover.classList.contains("category-icon-popover");' in picker_utils
    assert ".period-control-popover .settings-picker-option" in overlays_css
    assert "white-space: nowrap" in overlays_css


def test_byn_uses_compact_currency_symbol_in_frontend_formatters():
    core_utils = (REPO_ROOT / "static" / "js" / "app-core-utils.js").read_text(encoding="utf-8")
    tokens_css = (REPO_ROOT / "static" / "css" / "tokens.css").read_text(encoding="utf-8")
    modal_templates = (REPO_ROOT / "static" / "js" / "templates" / "modals.js").read_text(encoding="utf-8")
    secondary_templates = (REPO_ROOT / "static" / "js" / "templates" / "shell-sections-secondary.js").read_text(encoding="utf-8")
    primary_templates = (REPO_ROOT / "static" / "js" / "templates" / "shell-sections-primary.js").read_text(encoding="utf-8")
    core_css = (REPO_ROOT / "static" / "css" / "components-core.css").read_text(encoding="utf-8")
    controls_css = (REPO_ROOT / "static" / "css" / "components-controls.css").read_text(encoding="utf-8")

    assert '@font-face {\n  font-family: "nbrb";' in tokens_css
    assert 'url("/static/fonts/nbrb.woff2") format("woff2")' in tokens_css
    assert 'unicode-range: U+E901;' in tokens_css
    assert 'font-feature-settings: "liga"' in tokens_css
    assert 'BYN: { symbol: "\\uE901" }' in core_utils
    assert '--money-font-family: "nbrb", "Noto Sans", "DejaVu Sans", "Segoe UI Symbol", "Segoe UI", Tahoma, sans-serif;' in tokens_css
    assert '--ui-font-family: "nbrb", "Segoe UI", Tahoma, "Noto Sans", "DejaVu Sans", sans-serif;' in tokens_css
    assert 'font-family: var(--ui-font-family);' in tokens_css
    assert 'RU: "RUB"' in core_utils
    assert "function normalizeCurrencyCode" in core_utils
    assert "function formatCurrencySymbol" in core_utils
    assert r"`${formatted}\u00A0${cfg.symbol}`" in core_utils
    assert '<option value="BYN">BYN (\\uE901)</option>' in modal_templates
    assert "Пример: 1 234,56&nbsp;\\uE901" in secondary_templates
    assert 'id="plansFinancialValue" class="plans-financial-kpi-value">0,00&nbsp;\\uE901' in secondary_templates
    assert 'id="analyticsIncomeDelta">0&nbsp;\\uE901' in primary_templates
    assert "button,\ninput," not in controls_css
    assert "button {\n  font-family: var(--ui-font-family);\n}" in controls_css
    assert "font-family: var(--ui-font-family);" in controls_css
    assert "text-rendering: geometricPrecision" in core_css
    assert "руб." not in core_utils


def test_finance_calculator_drawer_is_registered_and_safe_for_mobile():
    manifest = MANIFEST_JS.read_text(encoding="utf-8")
    shell = (REPO_ROOT / "static" / "js" / "templates" / "shell.js").read_text(encoding="utf-8")
    modals = (REPO_ROOT / "static" / "js" / "templates" / "modals.js").read_text(encoding="utf-8")
    styles = (REPO_ROOT / "static" / "styles.css").read_text(encoding="utf-8")
    calculator_css = (REPO_ROOT / "static" / "css" / "components-finance-calculator.css").read_text(encoding="utf-8")
    calculator_js = (REPO_ROOT / "static" / "js" / "app-finance-calculator.js").read_text(encoding="utf-8")
    init_features = (REPO_ROOT / "static" / "js" / "app-init-features.js").read_text(encoding="utf-8")
    index_html = INDEX_HTML.read_text(encoding="utf-8")

    assert "<title>ФинАсист</title>" in index_html
    assert "<h1>ФинАсист</h1>" in index_html
    assert 'id="loginLoading"' in index_html
    assert 'id="loginContent" class="login-content hidden"' in index_html
    assert "/static/favicon.svg?v=2" in index_html
    assert "Проверяем сессию..." in index_html
    assert 'class="login-brand-mark"' in index_html
    assert 'width="52" height="52"' in index_html
    assert '<div class="brand" aria-label="ФинАсист">' in shell
    assert '<img src="/static/favicon.svg?v=2" alt="" width="40" height="40" />' in shell
    assert 'id="sessionStatusRow"' in shell
    assert 'id="sessionStartedLabel"' in shell
    assert 'id="sessionExpiresLabel"' in shell
    assert 'id="sessionRenewedLabel" class="hidden"' in shell
    assert 'id="sessionRefreshBtn"' in shell
    assert 'id="sessionRefreshBtn" class="btn btn-secondary session-renew-btn" type="button" title="Продлить сессию" aria-label="Продлить сессию"><span aria-hidden="true">⟳</span></button>' in shell
    assert 'id="sessionRecoveryOverlay"' in shell
    assert 'id="sessionRecoveryBtn"' in shell
    assert 'id="financeCalculatorToggle"' not in shell
    assert 'id="financeCalculatorDrawer"' in shell
    assert 'id="createFinanceCalculatorToggle"' in modals
    assert 'id="editFinanceCalculatorToggle"' in modals
    assert 'id="createSessionRefreshBtn"' in modals
    assert 'id="editSessionRefreshBtn"' in modals
    assert modals.count('aria-label="Продлить сессию"') >= 2
    assert modals.count("modal-head-icon-btn") >= 8
    assert '<span aria-hidden="true">%</span><span>Калькулятор</span>' not in modals
    assert modals.count('class="modal-action-svg"') == 3
    assert 'data-calculator-mode="discount"' in shell
    assert 'data-calculator-mode="split"' in shell
    assert '"/static/js/app-finance-calculator.js"' in manifest
    assert '@import url("/static/css/components-finance-calculator.css?v=20260716j");' in styles
    assert "registerRuntimeModule?.(\"finance-calculator\"" in calculator_js
    assert "calculateDiscount" in calculator_js
    assert "calculateChange" in calculator_js
    assert "calculateUnit" in calculator_js
    assert "calculateSplit" in calculator_js
    assert "closeIfAttachedToModal" in calculator_js
    assert "modal-attached" in calculator_css
    assert "overflow-x: hidden" in calculator_css
    assert ".segmented.finance-calculator-tabs {" in calculator_css
    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in calculator_css
    assert "getFinanceCalculator().bind?.();" in init_features
    assert "body.finance-calculator-open" in calculator_css
    assert "@media (max-width: 640px)" in calculator_css
    assert "max-height: min(88dvh, 720px)" in calculator_css
    assert '/static/styles.css?v=20260826c' in index_html
    assert '/static/css/components-core.css?v=20260808a' in styles
    assert '/static/css/layout-debts.css?v=20260716j' in styles
    assert '/static/css/components-analytics-summary.css?v=20260826c' in styles
    assert '/static/css/responsive-sm-core.css?v=20260826b' in styles


def test_session_refresh_preserves_runtime_ui_and_retries_unauthorized_requests():
    session_auth = (REPO_ROOT / "static" / "js" / "app-features-session-auth.js").read_text(encoding="utf-8")
    core_actions = (REPO_ROOT / "static" / "js" / "app-core-actions.js").read_text(encoding="utf-8")
    startup = (REPO_ROOT / "static" / "js" / "app-init-startup.js").read_text(encoding="utf-8")

    assert 'fetch("/api/v1/auth/refresh"' in session_auth
    assert "waitForTelegramInitData" in session_auth
    assert 'document.addEventListener("visibilitychange", resume)' in session_auth
    assert 'window.addEventListener("pageshow", resume)' in session_auth
    assert "if (bootstrapPromise) return bootstrapPromise" in session_auth
    assert "await refreshSession({ manual: true })" in session_auth
    assert "state.sessionStartedAt = tokenTimestampIso(claims.session_started_at || claims.iat)" in session_auth
    assert '`Завершится ${expiresAt}`' in session_auth
    assert '`Осталось ${formatRemainingTime(remainingMs)}`' in session_auth
    assert "storeAccessToken(data, { renewed: true })" in session_auth
    assert "operationModal.closeCreateModal()" not in session_auth.split("async function refreshSession", 1)[1].split("function authenticateTelegramInPlace", 1)[0]
    assert "recoverUnauthorized" in core_actions
    assert "getSessionFeature().logout?.(false)" not in core_actions
    assert "skipAuthRecovery: true" in core_actions
    assert "core.showSessionChecking?.();" in startup


def test_analytics_calendar_money_tooltip_uses_app_font_not_native_title():
    analytics_calendar = (REPO_ROOT / "static" / "js" / "app-features-analytics-calendar.js").read_text(encoding="utf-8")
    analytics_css = (REPO_ROOT / "static" / "css" / "components-analytics-summary.css").read_text(encoding="utf-8")

    assert "function bindCalendarTooltipUi()" in analytics_calendar
    assert 'data-analytics-calendar-tooltip="${escapeHtml(dayTooltip)}"' in analytics_calendar
    assert 'title="${escapeHtml(dayTitle)}"' not in analytics_calendar
    assert ".analytics-day-meta {\n  color: #9db0d4;\n  font-family: var(--money-font-family);" in analytics_css


def test_analytics_calendar_picker_popover_uses_content_width():
    analytics_template = (REPO_ROOT / "static" / "js" / "templates" / "shell-sections-primary.js").read_text(encoding="utf-8")
    analytics_css = (REPO_ROOT / "static" / "css" / "components-analytics-summary.css").read_text(encoding="utf-8")
    picker_utils = (REPO_ROOT / "static" / "js" / "app-picker-utils.js").read_text(encoding="utf-8")

    assert analytics_template.count("analytics-grid-picker-popover") == 2
    assert ".app-popover.analytics-grid-picker-popover {\n  width: max-content;" in analytics_css
    assert "max-width: calc(100vw - 2rem);" in analytics_css
    assert 'const sizesToContent = popover.classList.contains("analytics-grid-picker-popover");' in picker_utils
    assert ".analytics-calendar-tooltip {\n  font-family: var(--money-font-family);\n}" in analytics_css


def test_analytics_year_view_groups_months_by_quarter_without_extra_api_calls():
    analytics_calendar = (REPO_ROOT / "static" / "js" / "app-features-analytics-calendar.js").read_text(encoding="utf-8")
    analytics_css = (REPO_ROOT / "static" / "css" / "components-analytics-summary.css").read_text(encoding="utf-8")

    assert "function renderAnalyticsYearQuarter" in analytics_calendar
    assert "function summarizeQuarterMonths" in analytics_calendar
    assert "[0, 1, 2, 3]" in analytics_calendar
    assert "months.slice(index * 3, index * 3 + 3)" in analytics_calendar
    assert 'class="analytics-year-quarter"' in analytics_calendar
    assert "квартал</strong>" in analytics_calendar
    assert "analytics-year-quarter-totals" in analytics_calendar
    assert "analytics-year-quarter-months" in analytics_calendar
    assert 'data-analytics-month-anchor="${item.month}"' in analytics_calendar
    assert "/api/v1/dashboard/analytics/calendar/quarter" not in analytics_calendar
    assert ".analytics-year-quarter {" in analytics_css
    assert ".analytics-year-quarter-totals" in analytics_css
    assert "grid-template-columns: repeat(5, minmax(8.5rem, 1fr));" in analytics_css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in analytics_css
    assert "min-width: 980px;" in analytics_css


def test_contextual_create_actions_prefill_category_group_and_item_source():
    categories_table = (REPO_ROOT / "static" / "js" / "app-categories-table-ui.js").read_text(encoding="utf-8")
    categories_ui = (REPO_ROOT / "static" / "js" / "app-categories-ui.js").read_text(encoding="utf-8")
    categories_coordinator = (REPO_ROOT / "static" / "js" / "app-categories-ui-coordinator.js").read_text(
        encoding="utf-8"
    )
    catalog_render = (REPO_ROOT / "static" / "js" / "app-item-catalog-render-coordinator.js").read_text(
        encoding="utf-8"
    )
    catalog_coordinator = (REPO_ROOT / "static" / "js" / "app-item-catalog-ui-coordinator.js").read_text(
        encoding="utf-8"
    )
    catalog_modal = (REPO_ROOT / "static" / "js" / "app-features-item-catalog-modal.js").read_text(
        encoding="utf-8"
    )
    init_catalog = (REPO_ROOT / "static" / "js" / "app-init-features-catalog.js").read_text(encoding="utf-8")
    tables_css = (REPO_ROOT / "static" / "css" / "components-tables.css").read_text(encoding="utf-8")

    assert "data-create-category-group-id" in categories_table
    assert "category-context-create-btn" in categories_table
    assert "Добавить категорию" in categories_table
    assert "const preselectGroupId = options.groupId ? String(options.groupId) : \"\";" in categories_ui
    assert "el.categoryGroup.value = preselectGroupId;" in categories_ui
    assert "openCreateCategoryModalAction?.({ groupId, kind });" in categories_coordinator
    assert "openCreateCategoryModalAction: categoryActions.openCreateCategoryModal" in init_catalog
    assert "data-create-item-template-source-name" in catalog_render
    assert "item-source-context-create-btn" in catalog_render
    assert "Добавить позицию" in catalog_render
    assert "openItemTemplateModalAction?.({ shop_name:" in catalog_coordinator
    assert "!normalizeItemCatalogShopName(item?.shop_name || \"\")" in catalog_modal
    assert ".category-context-create-btn {" in tables_css
    assert ".category-table-group-wrap:hover .category-context-create-btn" in tables_css
    assert ".item-catalog-source-wrap:hover .item-source-context-create-btn" in tables_css


def test_number_inputs_hide_native_spin_buttons():
    controls_css = (REPO_ROOT / "static" / "css" / "components-controls.css").read_text(encoding="utf-8")

    assert 'input[type="number"] {\n  appearance: textfield !important;' in controls_css
    assert "-webkit-appearance: none !important;" in controls_css
    assert "-moz-appearance: textfield !important;" in controls_css
    assert "input[type=\"number\"]::-webkit-outer-spin-button" in controls_css
    assert "input[type=\"number\"]::-webkit-inner-spin-button" in controls_css
    assert "display: none;" in controls_css


def test_debts_mobile_search_and_operations_period_label_contracts():
    layout_forms = (REPO_ROOT / "static" / "css" / "layout-forms.css").read_text(encoding="utf-8")
    responsive_lg = (REPO_ROOT / "static" / "css" / "responsive-lg.css").read_text(encoding="utf-8")
    operations = (REPO_ROOT / "static" / "js" / "app-features-operations.js").read_text(encoding="utf-8")
    skeletons = (REPO_ROOT / "static" / "js" / "app-loading-skeletons.js").read_text(encoding="utf-8")

    assert ".debt-toolbar .table-search-input {\n  flex: 0 1 34rem;" in layout_forms
    assert "#debtsSection .debt-toolbar .table-search-input {\n    flex: 0 0 auto;" in responsive_lg
    assert "function updateOperationsPeriodLabel()" in operations
    assert "updateOperationsPeriodLabel," in operations
    assert "el.operationsPeriodLabel.innerHTML" not in skeletons


def test_dashboard_summary_retry_and_plan_fallback_are_non_blocking():
    dashboard_data = (REPO_ROOT / "static" / "js" / "app-dashboard-data.js").read_text(encoding="utf-8")
    dashboard = (REPO_ROOT / "static" / "js" / "app-features-dashboard.js").read_text(encoding="utf-8")
    skeletons = (REPO_ROOT / "static" / "js" / "app-loading-skeletons.js").read_text(encoding="utf-8")
    plans = (REPO_ROOT / "static" / "js" / "app-features-plans.js").read_text(encoding="utf-8")

    assert "function isRetryableSummaryError(err)" in dashboard_data
    assert "/\\[(500|502|503|504)\\]/.test(message)" in dashboard_data
    assert "await wait(450, options.signal);" in dashboard_data
    assert "Загружаем активные долги…" in skeletons
    assert "Загружаем ближайшие планы…" in skeletons
    assert "data-dashboard-retry" in dashboard
    assert "bindDashboardRetryActions" in dashboard
    assert "data-plans-retry" in plans
    assert "state.plansAllTimeBalance = 0;" in plans
    assert "return 0;" in plans


def test_operations_section_is_money_flow_first_without_bulk_select():
    shell_primary = (REPO_ROOT / "static" / "js" / "templates" / "shell-sections-primary.js").read_text(
        encoding="utf-8"
    )
    state = (REPO_ROOT / "static" / "js" / "app-core-state.js").read_text(encoding="utf-8")
    operations = (REPO_ROOT / "static" / "js" / "app-features-operations.js").read_text(encoding="utf-8")
    init_features = (REPO_ROOT / "static" / "js" / "app-init-features.js").read_text(encoding="utf-8")
    operations_period_controls = (
        REPO_ROOT / "static" / "js" / "app-init-features-operations-period-controls.js"
    ).read_text(encoding="utf-8")
    preferences = (REPO_ROOT / "static" / "js" / "app-features-session-preferences.js").read_text(encoding="utf-8")
    renderers = (REPO_ROOT / "static" / "js" / "app-renderers.js").read_text(encoding="utf-8")
    styles = (REPO_ROOT / "static" / "styles.css").read_text(encoding="utf-8")
    operations_css = (REPO_ROOT / "static" / "css" / "components-operation-controls.css").read_text(encoding="utf-8")
    analytics_css = (REPO_ROOT / "static" / "css" / "components-analytics-summary.css").read_text(encoding="utf-8")

    assert 'operationsMode: "money_flow"' in state
    assert 'id="operationsModeTabs"' not in shell_primary
    assert 'class="operations-controls-grid control-section-grid"' in shell_primary
    assert 'class="control-section operations-period-section"' in shell_primary
    assert 'class="control-section operations-filter-section"' in shell_primary
    assert 'class="control-section operations-sort-section"' in shell_primary
    assert 'id="operationsPeriodTrigger"' in shell_primary
    assert 'id="operationsPeriodControlLabel"' in shell_primary
    assert 'class="segmented hidden" data-period-tabs' in shell_primary
    assert shell_primary.index('id="resetOperationsFiltersBtn"') < shell_primary.index('id="operationsSummaryGrid"')
    assert 'id="operationsQuickActionsCard"' not in shell_primary
    assert 'id="quickFilterExpenseBtn"' not in shell_primary
    assert 'id="quickFilterIncomeBtn"' not in shell_primary
    assert 'id="quickCustomRangeBtn"' not in shell_primary
    assert 'id="operationsSelectAll"' not in shell_primary
    assert 'id="selectVisibleOperationsBtn"' not in shell_primary
    assert 'id="operationsBulkBar"' not in shell_primary
    assert 'id="deleteAllOperationsBtn"' not in shell_primary
    assert "padding: 12px;" in operations_css
    assert "gap: 10px;" in operations_css
    assert ".period-control {" in operations_css
    assert "grid-template-columns: 2.25rem minmax(10rem, 1fr) 2.25rem;" in operations_css
    assert '@import url("/static/css/components-operation-controls.css?v=20260716j");' in styles
    assert styles.index("components-operation-controls.css") < styles.index("components-analytics-summary.css")
    assert ".period-control {" not in analytics_css
    assert ".operations-controls-grid {" not in analytics_css
    assert 'state.operationsMode = "money_flow";' in operations
    assert "data-operations-period-choice" in operations_period_controls
    assert "state.operationsPeriodStepGranularity" in operations_period_controls
    assert "operationsPeriodControls.openQuickPeriodPopover" in init_features
    assert "setOperationsCurrencyScope," in (REPO_ROOT / "static" / "js" / "app-features.js").read_text(encoding="utf-8")
    assert 'mode: "money_flow"' in preferences
    assert 'params.set("item_template_id", String(state.operationsItemTemplateFilterId));' in operations
    assert '<td class="select-col" data-label="Выбор"><span class="muted-small">—</span></td>' not in renderers


def test_analytics_global_period_uses_compact_period_control():
    shell_primary = (REPO_ROOT / "static" / "js" / "templates" / "shell-sections-primary.js").read_text(
        encoding="utf-8"
    )
    elements = (REPO_ROOT / "static" / "js" / "app-core-elements.js").read_text(encoding="utf-8")
    analytics_init = (REPO_ROOT / "static" / "js" / "app-init-features-analytics.js").read_text(encoding="utf-8")
    analytics_period_controls = (
        REPO_ROOT / "static" / "js" / "app-init-features-analytics-period-controls.js"
    ).read_text(encoding="utf-8")
    analytics_ui = (REPO_ROOT / "static" / "js" / "app-features-analytics-highlights-ui.js").read_text(
        encoding="utf-8"
    )
    analytics_trend = (REPO_ROOT / "static" / "js" / "app-features-analytics-trend.js").read_text(encoding="utf-8")
    preferences = (REPO_ROOT / "static" / "js" / "app-features-session-preferences.js").read_text(encoding="utf-8")

    assert 'data-period-control="analytics-global"' in shell_primary
    assert 'data-period-control="dashboard-analytics"' in shell_primary
    assert 'data-period-control="analytics-positions"' in shell_primary
    assert 'id="dashboardAnalyticsPeriodTrigger"' in shell_primary
    assert 'id="dashboardAnalyticsPeriodControlLabel"' in shell_primary
    assert 'id="analyticsGlobalPeriodTrigger"' in shell_primary
    assert 'id="analyticsGlobalPeriodControlLabel"' in shell_primary
    assert 'id="dashboardPositionsPanel"' in shell_primary
    assert 'id="dashboardPositionsRanking"' in shell_primary
    assert 'id="openPositionsAnalyticsBtn"' in shell_primary
    assert 'class="segmented hidden" id="dashboardAnalyticsPeriodTabs"' in shell_primary
    assert 'class="segmented hidden" id="analyticsGlobalPeriodTabs"' in shell_primary
    assert "dashboardAnalyticsPeriodTrigger: document.getElementById" in elements
    assert "dashboardAnalyticsPeriodControlLabel: document.getElementById" in elements
    assert "analyticsGlobalPeriodTrigger: document.getElementById" in elements
    assert "analyticsGlobalPeriodControlLabel: document.getElementById" in elements
    assert "analyticsPositionsPeriodTrigger: document.getElementById" in elements
    assert "analyticsPositionsPeriodControlLabel: document.getElementById" in elements
    assert "dashboardPositionsPanel: document.getElementById" in elements
    assert "dashboardPositionsRanking: document.getElementById" in elements
    assert "openPositionsAnalyticsBtn: document.getElementById" in elements
    assert 'el.dashboardPositionsPanel.classList.toggle("hidden"' in preferences
    assert 'const periodAttr = scope === "dashboard" ? "dashboard" : "analytics";' in analytics_period_controls
    assert "data-${periodAttr}-period-choice" in analytics_period_controls
    assert "data-analytics-period-choice" in analytics_init
    assert "data-dashboard-period-choice" in analytics_init
    assert "state.analyticsGlobalPeriodStepGranularity" in analytics_period_controls
    assert "periodControls.openQuickPeriodPopover" in analytics_init
    assert "periodControls.shiftDashboardPeriod" in analytics_init
    assert "function shiftDashboardPeriod" in analytics_period_controls
    assert "el.analyticsGlobalPeriodControlLabel.textContent = label;" in analytics_ui
    assert "el.dashboardAnalyticsPeriodControlLabel.textContent" in analytics_ui
    assert "el.analyticsGlobalPeriodControlLabel.textContent = rangeLabel;" in analytics_trend
    assert "if (period !== \"all_time\")" in analytics_trend


def test_currency_kpi_and_settings_support_compact_bank_rates_and_alerts():
    secondary = (
        REPO_ROOT / "static" / "js" / "templates" / "shell-sections-secondary.js"
    ).read_text(encoding="utf-8")
    dashboard = (REPO_ROOT / "static" / "js" / "app-features-dashboard.js").read_text(
        encoding="utf-8"
    )
    preferences = (
        REPO_ROOT / "static" / "js" / "app-features-session-preferences.js"
    ).read_text(encoding="utf-8")

    assert 'name="bankRateBank"' in secondary
    assert 'id="bankCurrencyAlertsList"' in secondary
    assert 'id="addBankCurrencyAlertBtn"' in secondary
    assert 'choiceButton("rate_kind"' in preferences
    assert 'data-bank-alert-threshold="above"' in preferences
    assert 'data-bank-alert-threshold="below"' in preferences
    assert 'data-bank-alert-field="action"' not in preferences
    assert "Покупка" in dashboard
    assert "Продажа" in dashboard
    assert 'itemCurrency === "RUB" ? 100 : 1' in dashboard
    assert "currencyOverview.bank_rates" in dashboard
    assert "collectBankCurrencyAlerts()" in preferences


def test_currency_digest_settings_support_seven_day_chart_preference():
    secondary = (
        REPO_ROOT / "static" / "js" / "templates" / "shell-sections-secondary.js"
    ).read_text(encoding="utf-8")
    elements = (REPO_ROOT / "static" / "js" / "app-core-elements.js").read_text(encoding="utf-8")
    preferences = (
        REPO_ROOT / "static" / "js" / "app-features-session-preferences.js"
    ).read_text(encoding="utf-8")

    assert 'id="currencyDigestChartToggle" type="checkbox" checked' in secondary
    assert "Добавлять график курсов за последние 7 дней" in secondary
    assert 'currencyDigestChartToggle: document.getElementById("currencyDigestChartToggle")' in elements
    assert "telegram_digest_chart_enabled: true" in preferences
    assert "getMergedCurrencyPrefs().telegram_digest_chart_enabled !== false" in preferences
    assert "el.currencyDigestChartToggle.disabled = !el.currencyDigestToggle.checked" in preferences
    assert "telegram_digest_chart_enabled: el.currencyDigestChartToggle" in preferences


def test_currency_digest_manual_send_buttons_are_available_in_all_currency_views():
    primary = (
        REPO_ROOT / "static" / "js" / "templates" / "shell-sections-primary.js"
    ).read_text(encoding="utf-8")
    secondary = (
        REPO_ROOT / "static" / "js" / "templates" / "shell-sections-secondary.js"
    ).read_text(encoding="utf-8")
    elements = (REPO_ROOT / "static" / "js" / "app-core-elements.js").read_text(encoding="utf-8")

    assert 'id="dashboardSendCurrencyDigestBtn" class="btn btn-secondary btn-xs"' in primary
    assert 'id="analyticsSendCurrencyDigestBtn" class="btn btn-secondary btn-xs"' in primary
    assert 'id="currencySendDigestBtn" class="btn btn-secondary"' in secondary
    assert primary.count("Отправить дайджест") == 2
    assert secondary.count("Отправить дайджест") == 1
    assert 'dashboardSendCurrencyDigestBtn: document.getElementById("dashboardSendCurrencyDigestBtn")' in elements
    assert 'currencySendDigestBtn: document.getElementById("currencySendDigestBtn")' in elements
    assert 'analyticsSendCurrencyDigestBtn: document.getElementById("analyticsSendCurrencyDigestBtn")' in elements


def test_currency_analytics_supports_bank_history_comparison_controls():
    primary = (
        REPO_ROOT / "static" / "js" / "templates" / "shell-sections-primary.js"
    ).read_text(encoding="utf-8")
    elements = (REPO_ROOT / "static" / "js" / "app-core-elements.js").read_text(encoding="utf-8")
    currency = (
        REPO_ROOT / "static" / "js" / "app-features-analytics-currency.js"
    ).read_text(encoding="utf-8")
    chart = (
        REPO_ROOT / "static" / "js" / "app-features-analytics-currency-chart.js"
    ).read_text(encoding="utf-8")
    analytics_css = (
        REPO_ROOT / "static" / "css" / "components-analytics-summary.css"
    ).read_text(encoding="utf-8")

    assert 'data-analytics-currency-chart-mode="banks"' in primary
    assert 'id="analyticsCurrencyChartCurrencyTabs"' in primary
    assert 'id="analyticsCurrencyChartLegend"' in primary
    assert 'id="analyticsCurrencyChartShowAllBtn"' in primary
    assert 'id="analyticsCurrencyChartCoverage"' in primary
    assert "analyticsCurrencyChartBankOptions: document.getElementById" in elements
    assert "analyticsCurrencyChartShowAllBtn: document.getElementById" in elements
    assert "/api/v1/currency/bank-rates/history?" in currency
    assert "/api/v1/currency/bank-rates/history/fill?" in currency
    assert "/api/v1/currency/bank-rates/history/fill/status" in currency
    assert 'params.append("bank_code", code)' in currency
    assert 'String(currency || "").toUpperCase() === "RUB" ? 100 : 1' in currency
    assert "buildNbrbChartSeries" in currency
    assert "data-analytics-chart-series-toggle" in currency
    assert "renderCurrentChartSnapshot" in currency
    assert 'buy: { label: "Покупка банком"' in currency
    assert 'sell: { label: "Продажа банком"' in currency
    assert "new Date(Date.UTC(year, month - 1, day))" in currency
    assert "setUTCDate" in currency
    assert "Promise.allSettled" in currency
    assert "requestSequence !== currencyChartLoadSequence" in currency
    assert 'state.analyticsCurrencyChartMode !== "banks"' in currency
    assert "dataset.originalText = idleText" in currency
    assert 'item?.capability === "accumulating" || item?.capability === "unavailable"' in currency
    assert "renderComparison" in chart
    assert 'createTooltipHost(svgNode, "comparison")' in chart
    assert '"analytics-chart-tooltip-currency-comparison"' in chart
    assert 'stroke-dasharray="${escapeHtml(series.dashArray)}"' in chart
    assert 'data-marker-shape="${escapeHtml(series.markerShape || "circle")}"' in chart
    assert ".currency-chart-legend-bank.is-unavailable" in analytics_css
    assert ".currency-chart-legend-series.is-sell > i::after" in analytics_css
    assert ".analytics-chart-tooltip.analytics-chart-tooltip-currency-comparison" in analytics_css


def test_debts_section_has_filtered_base_currency_kpi():
    secondary_template = (REPO_ROOT / "static" / "js" / "templates" / "shell-sections-secondary.js").read_text(
        encoding="utf-8"
    )
    elements = (REPO_ROOT / "static" / "js" / "app-core-elements.js").read_text(encoding="utf-8")
    debts_render = (REPO_ROOT / "static" / "js" / "app-features-debts-render.js").read_text(encoding="utf-8")
    debts_css = (REPO_ROOT / "static" / "css" / "layout-debts.css").read_text(encoding="utf-8")

    assert 'id="debtsSectionKpi"' in secondary_template
    assert "debtsSectionKpi: document.getElementById(\"debtsSectionKpi\")" in elements
    assert "function summarizeDebtCards(cards)" in debts_render
    assert "debt.current_base_outstanding_total ?? debt.outstanding_total" in debts_render
    assert "renderDebtsSectionKpi(visibleCards);" in debts_render
    assert "Я должен" in debts_render
    assert "Мне должны" in debts_render
    assert "Чистая позиция" in debts_render
    assert "analytics-kpi-card analytics-kpi-negative" in debts_render
    assert ".debts-section-kpi" in debts_css


def test_debt_status_filter_applies_to_rows_inside_counterparty_cards():
    state = (REPO_ROOT / "static" / "js" / "app-core-state.js").read_text(encoding="utf-8")
    debts = (REPO_ROOT / "static" / "js" / "app-features-debts.js").read_text(encoding="utf-8")
    debts_render = (REPO_ROOT / "static" / "js" / "app-features-debts-render.js").read_text(encoding="utf-8")
    debts_init = (REPO_ROOT / "static" / "js" / "app-init-features-debts.js").read_text(encoding="utf-8")

    assert "expandedDebtClosedCounterpartyIds: new Set()" in state
    assert "function isClosedDebt(debt)" in debts_render
    assert "const activeDebts = allDebts.filter" in debts_render
    assert "const closedDebts = allDebts.filter" in debts_render
    assert "data-debt-closed-toggle-counterparty-id" in debts_render
    assert 'aria-expanded="${closedDebtsExpanded ? "true" : "false"}"' in debts_render
    assert "function toggleDebtClosedRows(counterpartyId)" in debts
    assert "debtCardsRenderer.isClosedDebt(debt)" in debts
    assert "button[data-debt-closed-toggle-counterparty-id]" in debts_init


def test_work_calendar_distinguishes_plan_forecasts_from_payroll_facts():
    work = (REPO_ROOT / "static" / "js" / "app-features-work.js").read_text(encoding="utf-8")
    styles = (REPO_ROOT / "static" / "styles.css").read_text(encoding="utf-8")

    assert "function paymentForecastVisible(item)" in work
    assert "item?.forecast_visible === true" in work
    assert "if (!paymentForecastVisible(item)) return;" in work
    assert "snapshot?.payroll_operations" in work
    assert 'source === "category_match"' in work
    assert "Определено по категории" in work
    assert "function exactDatePayrollOperations(item)" in work
    assert "Получено по категории" in work
    assert "Фактическая выплата не найдена" in work
    assert "payment.label || payment.category_name" in work
    assert "(?:operations|plans|categories)(?:\\/\\d+)?" in work
    assert ".work-payment-card.is-missing" in styles


def test_work_calendar_shows_credited_hours_for_paid_absences():
    work = (REPO_ROOT / "static" / "js" / "app-features-work.js").read_text(encoding="utf-8")
    styles = (REPO_ROOT / "static" / "styles.css").read_text(encoding="utf-8")

    assert 'const PAID_ABSENCE_STATUSES = new Set(["vacation", "sick_paid", "company_day_off"]);' in work
    assert "function renderDayHourChips(item, isToday)" in work
    assert 'workHoursChip("credited", item.is_future ? "К оплате" : "Зачтено", creditedHours)' in work
    assert "if (actualHours > 0)" in work
    assert "actualHours <= 0 || !sameHours(actualHours, creditedHours)" in work
    assert "!sameHours(plannedHours, creditedHours) && !sameHours(plannedHours, actualHours)" in work
    assert ".work-hours-chip-credited" in styles
