from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = REPO_ROOT / "static" / "index.html"
MANIFEST_JS = REPO_ROOT / "static" / "js" / "app-manifest.js"


def test_activity_journal_modal_is_available_in_frontend_templates():
    modals = (REPO_ROOT / "static" / "js" / "templates" / "modals.js").read_text(encoding="utf-8")
    modals_item_catalog = (REPO_ROOT / "static" / "js" / "templates" / "modals-item-catalog.js").read_text(encoding="utf-8")
    shell_primary = (REPO_ROOT / "static" / "js" / "templates" / "shell-sections-primary.js").read_text(encoding="utf-8")
    shell_secondary = (REPO_ROOT / "static" / "js" / "templates" / "shell-sections-secondary.js").read_text(encoding="utf-8")
    shell = (REPO_ROOT / "static" / "js" / "templates" / "shell.js").read_text(encoding="utf-8")
    activity = (REPO_ROOT / "static" / "js" / "app-activity.js").read_text(encoding="utf-8")
    usage = (REPO_ROOT / "static" / "js" / "app-usage.js").read_text(encoding="utf-8")
    overlays = (REPO_ROOT / "static" / "css" / "components-overlays.css").read_text(encoding="utf-8")
    item_modal = (REPO_ROOT / "static" / "js" / "templates" / "modals-item-catalog.js").read_text(
        encoding="utf-8"
    )
    elements = (REPO_ROOT / "static" / "js" / "app-core-elements.js").read_text(encoding="utf-8")
    session_auth = (REPO_ROOT / "static" / "js" / "app-features-session-auth.js").read_text(encoding="utf-8")
    init_core = (REPO_ROOT / "static" / "js" / "app-init-core.js").read_text(encoding="utf-8")
    core_actions = (REPO_ROOT / "static" / "js" / "app-core-actions.js").read_text(encoding="utf-8")
    init_features = (REPO_ROOT / "static" / "js" / "app-init-features.js").read_text(encoding="utf-8")
    activity_center_css = (REPO_ROOT / "static" / "css" / "components-activity-center.css").read_text(encoding="utf-8")
    styles = (REPO_ROOT / "static" / "styles.css").read_text(encoding="utf-8")

    assert 'id="activityModal"' in modals
    assert 'id="activityCenterToggleBtn"' in shell
    assert 'class="activity-rail"' in shell
    assert 'id="activityCenterDrawer"' in shell
    assert 'id="activityCenterList"' in shell
    assert 'id="activityCenterAllBtn"' in shell
    assert 'id="usageModal"' in modals
    assert 'id="activityList"' in modals
    assert 'id="usageList"' in modals
    assert 'id="closeActivityModalBtn"' in modals
    assert 'id="closeUsageModalBtn"' in modals
    for button_id in (
        "createModalActivityBtn",
        "editModalReceiptBtn",
        "editModalActivityBtn",
        "editGroupActivityBtn",
        "editCategoryActivityBtn",
    ):
        assert f'id="{button_id}"' in modals
        assert f'{button_id}: document.getElementById("{button_id}")' in elements
    assert 'id="itemTemplateActivityBtn"' in modals_item_catalog
    assert 'id="itemTemplateUsageBtn"' in modals_item_catalog
    assert 'id="itemTemplateHistoryBtn"' in modals_item_catalog
    assert 'id="sourceGroupCreateItemBtn"' in modals_item_catalog
    assert 'id="editGroupCreateCategoryBtn"' in modals
    assert 'itemTemplateActivityBtn: document.getElementById("itemTemplateActivityBtn")' in elements
    assert 'itemTemplateUsageBtn: document.getElementById("itemTemplateUsageBtn")' in elements
    assert 'itemTemplateHistoryBtn: document.getElementById("itemTemplateHistoryBtn")' in elements
    assert 'sourceGroupCreateItemBtn: document.getElementById("sourceGroupCreateItemBtn")' in elements
    assert 'editGroupCreateCategoryBtn: document.getElementById("editGroupCreateCategoryBtn")' in elements
    assert 'id="dashboardCurrencyActivityBtn"' in shell_primary
    assert 'id="currencyPortfolioActivityBtn"' in shell_secondary
    assert 'dashboardCurrencyActivityBtn: document.getElementById("dashboardCurrencyActivityBtn")' in elements
    assert 'currencyPortfolioActivityBtn: document.getElementById("currencyPortfolioActivityBtn")' in elements
    assert 'activityModal: document.getElementById("activityModal")' in elements
    assert 'usageModal: document.getElementById("usageModal")' in elements
    assert "function configureActivityButton" in activity
    assert "function loadRecentActivity" in activity
    assert "function openActivityEntity" in activity
    assert 'actionButton(item.id, "restore"' in activity
    assert 'document.addEventListener("app:activity-changed"' in activity
    assert 'new CustomEvent("app:activity-changed"' in core_actions
    assert "dataset.toastActivity" in core_actions
    assert 'button[data-toast-activity]' in init_features
    assert ".activity-center-drawer" in activity_center_css
    assert "@media (max-width: 900px)" in activity_center_css
    assert "@media (hover: none), (pointer: coarse)" in activity_center_css
    assert '@import url("/static/css/components-activity-center.css?v=20260720f");' in styles
    assert "function configureUsageButton" in usage
    assert "/api/v1/operations/money-flow?" in usage
    assert "item_template_id" in usage
    assert "matchingReceiptItem?.category_name" in usage
    assert "data-usage-operation-id" in usage
    assert "openMoneyFlowSource" in usage
    assert "closeUsageModal();\n    await getOperationsFeature().openMoneyFlowSource" not in usage
    assert "captureUsageReturnContext(resolvedId);" in usage
    assert "handleNestedOperationClosed" in usage
    assert 'document.addEventListener("app:activity-changed", markUsageForRefresh);' in usage
    assert "core.bringModalToFront?.(el.activityModal);" in activity
    assert "core.bringModalToFront?.(el.usageModal);" in usage
    assert "#usageModal {\n  z-index: 180;" in overlays
    assert ".modal.modal-front" in overlays
    assert ".usage-event.is-context-selected" in overlays
    assert 'modal-medium item-template-modal-card' in item_modal
    assert "headers: core.authHeaders()" in activity
    assert "auth: true" not in activity
    assert '"currency_portfolio"' in session_auth
    assert 'getRuntimeModule?.("activity")' in init_core
    assert 'getRuntimeModule?.("usage")' in init_core
    assert "bindActivityUi" in init_core
    assert "bindUsageUi" in init_core
    assert "core.getTopVisibleModal?.()" in init_core
    core_js = (REPO_ROOT / "static" / "js" / "app-core.js").read_text(encoding="utf-8")
    assert "function bringModalToFront(modal)" in core_js
    assert "function getTopVisibleModal()" in core_js
    assert "function installModalStackObserver()" in core_js
    assert "modalStackCounter = 0;" in core_js
    assert 'attributeFilter: ["class"]' in core_js
    assert "core.installModalStackObserver?.();" in init_core


def test_item_price_history_supports_safe_deletion_and_immediate_refresh():
    template = (REPO_ROOT / "static" / "js" / "templates" / "modals-item-catalog.js").read_text(
        encoding="utf-8"
    )
    sources = (REPO_ROOT / "static" / "js" / "app-features-item-catalog-sources.js").read_text(
        encoding="utf-8"
    )
    catalog_init = (REPO_ROOT / "static" / "js" / "app-init-features-catalog.js").read_text(
        encoding="utf-8"
    )
    features = (REPO_ROOT / "static" / "js" / "app-features.js").read_text(encoding="utf-8")

    assert 'data-delete-item-template-price-id="${Number(row.id)}"' in sources
    assert "deleteItemTemplatePriceFlow" in sources
    assert "core.bringModalToFront?.(el.itemTemplateHistoryModal);" in sources
    assert "core.markModalClosed?.(el.itemTemplateHistoryModal);" in sources
    assert "Цена в уже сохраненной операции не изменится" in sources
    assert "method: \"DELETE\"" in sources
    assert "applySavedItemCatalogItem?.(savedItem)" in sources
    assert "applySavedReceiptTemplateHint?.(savedItem)" in sources
    assert 'button[data-delete-item-template-price-id]' in catalog_init
    assert "deleteItemTemplatePriceFlow = itemCatalogFeatures.deleteItemTemplatePriceFlow" in features
    assert '<th aria-label="Действия"></th>' in template


def test_context_action_registry_keeps_row_and_modal_actions_explicit():
    registry = (REPO_ROOT / "static" / "js" / "app-context-actions.js").read_text(encoding="utf-8")
    manifest = MANIFEST_JS.read_text(encoding="utf-8")
    item_render = (REPO_ROOT / "static" / "js" / "app-item-catalog-render-coordinator.js").read_text(
        encoding="utf-8"
    )
    category_render = (REPO_ROOT / "static" / "js" / "app-categories-table-ui.js").read_text(encoding="utf-8")
    catalog_init = (REPO_ROOT / "static" / "js" / "app-init-features-catalog.js").read_text(encoding="utf-8")

    assert 'item_template: Object.freeze({' in registry
    assert 'operation: Object.freeze({' in registry
    assert 'modal: Object.freeze(["receipt", "activity"])' in registry
    assert 'modal: Object.freeze(["activity", "usage", "history"])' in registry
    assert 'category_group: Object.freeze({' in registry
    assert 'item_source: Object.freeze({' in registry
    assert 'modal: Object.freeze(["create_child"])' in registry
    assert '"/static/js/app-context-actions.js"' in manifest
    assert 'renderContextActions("item_template", item' in item_render
    assert 'renderContextActions("item_source", group' in item_render
    assert 'renderCategoryContextActions("category_group", group)' in category_render
    assert "el.itemTemplateHistoryBtn?.addEventListener" in catalog_init
    assert "el.sourceGroupCreateItemBtn?.addEventListener" in catalog_init
    assert "el.editGroupCreateCategoryBtn?.addEventListener" in catalog_init
    operations_init = (REPO_ROOT / "static" / "js" / "app-init-features-operations.js").read_text(
        encoding="utf-8"
    )
    assert 'el.editModalReceiptBtn?.addEventListener("click", handleOperationActionClick)' in operations_init


def test_debt_movements_and_add_amount_ui_contract():
    modals_secondary = (REPO_ROOT / "static" / "js" / "templates" / "modals-secondary.js").read_text(encoding="utf-8")
    debts_render = (REPO_ROOT / "static" / "js" / "app-features-debts-render.js").read_text(encoding="utf-8")
    debts_modals = (REPO_ROOT / "static" / "js" / "app-features-debts-modals.js").read_text(encoding="utf-8")
    debts_init = (REPO_ROOT / "static" / "js" / "app-init-features-debts.js").read_text(encoding="utf-8")
    elements = (REPO_ROOT / "static" / "js" / "app-core-elements.js").read_text(encoding="utf-8")
    features = (REPO_ROOT / "static" / "js" / "app-features.js").read_text(encoding="utf-8")

    assert 'id="debtIssuanceModal"' in modals_secondary
    assert 'id="debtIssuanceForm"' in modals_secondary
    assert 'id="issuanceAmount"' in modals_secondary
    assert "Движения долга" in modals_secondary
    assert ">История</button>" not in debts_render
    assert "data-add-debt-issuance-id" in debts_render
    assert "Добавить сумму" in debts_render
    assert "openDebtIssuanceModal" in debts_modals
    assert "submitDebtIssuance" in debts_modals
    assert "/api/v1/debts/${debtId}/issuances" in debts_modals
    assert "updateIssuanceDeltaHint" in debts_init
    assert 'debtIssuanceModal: document.getElementById("debtIssuanceModal")' in elements
    assert "openDebtIssuanceModal" in features


def test_edit_modals_keep_open_after_successful_save():
    operations_mutations = (REPO_ROOT / "static" / "js" / "app-features-operations-mutations.js").read_text(
        encoding="utf-8"
    )
    plans = (REPO_ROOT / "static" / "js" / "app-features-plans.js").read_text(encoding="utf-8")
    categories_data = (REPO_ROOT / "static" / "js" / "app-categories-data.js").read_text(encoding="utf-8")
    item_template_modal = (REPO_ROOT / "static" / "js" / "app-features-item-catalog-modal.js").read_text(
        encoding="utf-8"
    )
    item_sources = (REPO_ROOT / "static" / "js" / "app-features-item-catalog-sources.js").read_text(
        encoding="utf-8"
    )
    init_core = (REPO_ROOT / "static" / "js" / "app-init-core.js").read_text(encoding="utf-8")
    renderers = (REPO_ROOT / "static" / "js" / "app-renderers.js").read_text(encoding="utf-8")

    assert "if (!isEditDebt) {\n          state.editDebtCreateId = null;\n          closeCreateModal();" in operations_mutations
    assert "if (!isEditTrade) {\n          state.editCurrencyTradeId = null;" in operations_mutations
    assert "async function updateOperation" in operations_mutations
    update_operation_block = operations_mutations.split("async function updateOperation", 1)[1].split(
        "async function deleteOperationFlow", 1
    )[0]
    assert "closeEditModal();" not in update_operation_block
    assert "if (planId <= 0) {\n      operationModal.closeCreateModal();" in plans
    assert "categoryUi.closeEditCategoryModal();" not in categories_data
    assert "categoryUi.closeEditGroupModal();" not in categories_data
    assert "if (!isEdit) {\n        closeItemTemplateModal();" in item_template_modal
    source_submit_block = item_sources.split("async function submitSourceGroupForm", 1)[1].split(
        "async function deleteItemSourceFlow", 1
    )[0]
    assert "if (!isEdit) {\n        closeSourceGroupModal();" in source_submit_block
    assert "function closeVisibleModalOnEscape" in init_core
    assert "getOperationModal().closeEditModal" in init_core
    assert 'data-activity-entity-type="operation"' in renderers
    assert 'data-activity-entity-type="debt"' in renderers
    assert 'data-activity-entity-type="currency_trade"' in renderers


def test_receipt_line_total_live_update_keeps_currency_symbol():
    receipt = (REPO_ROOT / "static" / "js" / "app-features-operation-modal-receipt.js").read_text(encoding="utf-8")
    interactions = (
        REPO_ROOT / "static" / "js" / "app-features-operation-modal-receipt-interactions.js"
    ).read_text(encoding="utf-8")

    assert "formatReceiptMoney(value, mode = \"create\", options = {})" in receipt
    assert "formatReceiptMoney," in receipt
    assert "formatReceiptMoney," in interactions
    assert "${formatReceiptMoney(receiptLineTotal(updated.item), mode)}" in interactions
    assert "receiptLineTotal(updated.item), { withCurrency: false }" not in interactions
    assert "syncReceiptNumericInputs(mode);" in receipt
    assert 'renderReceiptSummary(mode, { amountValue: total });' in receipt


def test_receipt_discount_ui_uses_discount_copy_and_prefills_regular_price():
    receipt = (REPO_ROOT / "static" / "js" / "app-features-operation-modal-receipt.js").read_text(encoding="utf-8")

    assert "receiptDiscountToggleLabel(item)" in receipt
    assert "Скидка −${Number(percent.toFixed(1))}%" in receipt
    assert 'return "Скидка —%"' in receipt
    assert "title=\"Скидка, купон, промокод или бонусы\"" in receipt
    assert 'type="text" inputmode="decimal" data-receipt-field="unit_price"' in receipt
    assert 'data-receipt-field="regular_unit_price"' in receipt
    assert "receipt-item-row-discounted" in receipt
    assert "receipt-price-label-chip" not in receipt
    assert 'data-receipt-discount-type="${entry.value}"' in receipt
    assert "Акция" in receipt
    assert "Купон" in receipt
    assert "Баллы" in receipt
    assert "if (latestPrice > 0)" in receipt
    assert "latestPrice > asMoney(item.unit_price || 0)" not in receipt


def test_plan_and_operation_history_are_linked_without_duplicate_money_flow_rows():
    renderers = (REPO_ROOT / "static" / "js" / "app-renderers.js").read_text(encoding="utf-8")
    operations = (REPO_ROOT / "static" / "js" / "app-features-operations.js").read_text(encoding="utf-8")
    plans_render = (REPO_ROOT / "static" / "js" / "app-features-plans-render.js").read_text(encoding="utf-8")
    plans = (REPO_ROOT / "static" / "js" / "app-features-plans.js").read_text(encoding="utf-8")

    assert 'data-open-source-kind="plan"' in renderers
    assert "Из плана #${Number(item.source_plan_id)}" in renderers
    assert 'openActivityModal?.("plan", resolvedId)' in operations
    assert "data-plan-history-operation-id" in plans_render
    assert "Журнал плана" in plans_render
    assert 'sourceKind: "operation"' in plans


def test_repeat_purchase_recommendations_are_removed_from_frontend():
    modal = (REPO_ROOT / "static" / "js" / "templates" / "modals-item-catalog.js").read_text(encoding="utf-8")
    primary_shell = (REPO_ROOT / "static" / "js" / "templates" / "shell-sections-primary.js").read_text(encoding="utf-8")
    secondary_shell = (REPO_ROOT / "static" / "js" / "templates" / "shell-sections-secondary.js").read_text(encoding="utf-8")
    catalog = (REPO_ROOT / "static" / "js" / "app-features-item-catalog-modal.js").read_text(encoding="utf-8")
    dashboard = (REPO_ROOT / "static" / "js" / "app-features-dashboard.js").read_text(encoding="utf-8")
    manifest = (REPO_ROOT / "static" / "js" / "app-manifest.js").read_text(encoding="utf-8")

    combined = "\n".join((modal, primary_shell, secondary_shell, catalog, dashboard, manifest))
    assert "itemTemplateRecommendation" not in combined
    assert "item-recommendations" not in combined
    assert "data-recommendation" not in combined
    assert "Пора купить снова" not in combined


def test_saved_item_template_is_applied_immediately_to_catalog_and_receipt_hints():
    catalog = (REPO_ROOT / "static/js/app-features-item-catalog.js").read_text(encoding="utf-8")
    modal = (REPO_ROOT / "static/js/app-features-item-catalog-modal.js").read_text(encoding="utf-8")

    assert "function applySavedItemCatalogItem(item)" in catalog
    assert "savedItem = await core.requestJson(url" in modal
    assert "applySavedItemCatalogItem?.(savedItem);" in modal
    assert "applySavedReceiptTemplateHint(savedItem);" in modal
    assert 'core.invalidateUiRequestCache("op:receipt:templates");' in catalog


def test_item_catalog_exposes_category_picker_and_discount_summary():
    modal = (REPO_ROOT / "static/js/templates/modals-item-catalog.js").read_text(encoding="utf-8")
    feature = (REPO_ROOT / "static/js/app-features-item-catalog-modal.js").read_text(encoding="utf-8")
    renderer = (REPO_ROOT / "static/js/app-renderers.js").read_text(encoding="utf-8")
    sources = (REPO_ROOT / "static/js/app-features-item-catalog-sources.js").read_text(encoding="utf-8")

    assert 'id="itemTemplateCategorySearch"' in modal
    assert 'id="itemTemplateCategoryPickerBlock"' in modal
    assert "last_category_id: Number(el.itemTemplateCategory?.value || 0) || null" in feature
    assert "Скидка чека −${Number(discount.percent.toFixed(1))}%" in renderer
    assert 'eventChips.push(renderMetaChip(title, "neutral"))' not in renderer
    assert 'method: "DELETE"' in sources
    assert 'body: JSON.stringify({ shop_name: null })' not in sources


def test_reopened_discounted_receipt_uses_purchase_price_for_total_and_discrepancy():
    receipt = (REPO_ROOT / "static" / "js" / "app-features-operation-modal-receipt.js").read_text(encoding="utf-8")
    modal = (REPO_ROOT / "static" / "js" / "app-features-operation-modal.js").read_text(encoding="utf-8")

    assert "return asMoney(asQty(item.quantity) * asMoney(item.unit_price));" in receipt
    assert "regular_unit_price: row.regular_unit_price || 0" in modal
    assert "unit_price: row.unit_price || 0" in modal
    assert "regular_unit_price" not in receipt.split("function receiptLineTotal(item)", 1)[1].split("}", 1)[0]


def test_foreign_operation_and_plan_forms_expose_explicit_fx_policy_contract():
    modals = (REPO_ROOT / "static/js/templates/modals.js").read_text(encoding="utf-8")
    policy = (REPO_ROOT / "static/js/app-features-operation-modal-fx-policy.js").read_text(encoding="utf-8")
    mutations = (REPO_ROOT / "static/js/app-features-operations-mutations.js").read_text(encoding="utf-8")
    plans = (REPO_ROOT / "static/js/app-features-plans.js").read_text(encoding="utf-8")
    plan_render = (REPO_ROOT / "static/js/app-features-plans-render.js").read_text(encoding="utf-8")
    preview = (REPO_ROOT / "static/js/app-features-operation-modal-preview.js").read_text(encoding="utf-8")
    manifest = MANIFEST_JS.read_text(encoding="utf-8")

    for prefix in ("op", "edit"):
        for suffix in (
            "FxRateSourceSwitch",
            "FxBankOptions",
            "FxRateKindSwitch",
            "FxPaymentModeSwitch",
            "FxRateRefreshBtn",
            "FxRateMeta",
            "FxComputedAmount",
        ):
            assert f'id="{prefix}{suffix}"' in modals
    assert "Покупка банком" in modals
    assert "Продажа банком" in modals
    assert "Только пересчитать" in modals
    assert "Пополнить и оплатить" in modals
    assert "С валютного остатка" in modals
    assert 'value="nbrb"' in modals
    assert 'value="valuation"' in modals

    assert '"/static/js/app-features-operation-modal-fx-policy.js"' in manifest
    assert manifest.index("app-features-operation-modal-fx-policy.js") < manifest.index(
        "app-features-operation-modal-currency.js"
    )
    assert "/api/v1/currency/rate-options?${params.toString()}" in policy
    assert "/api/v1/currency/rate-options/refresh?" in policy
    assert 'params.set("as_of", context.operationDate)' in policy
    assert "/api/v1/currency/rates/history/fill?" in policy
    assert "/api/v1/currency/rates/history?${params.toString()}" not in policy
    assert 'params.set("bank_code", context.bankCode)' in policy
    assert 'fx_manual_rate: context.source === "manual"' in policy
    assert "core.resolveRateInput(context.displayRate, 1, 6).formatted" in policy
    assert "fx_bank_channel:" in policy
    assert "uiState[mode].refreshRequested || uiState[mode].policyDirty" in policy
    assert "uiState[mode] === current" in policy
    assert 'if (n.kind?.value === "income" && nextValue !== "valuation")' in policy
    assert 'return {};' in policy

    assert "delete payload.fx_rate;" in mutations
    assert "payload.fx_settlement = null;" in mutations
    assert "...operationModal.getOperationFxPolicyPayload?.(\"create\", { isPlan: true })" in plans
    assert "item?.current_rate ?? item?.fx_rate ?? 0" in plan_render
    assert "item?.current_rate_date || item?.fx_rate_date" in plan_render
    assert "escapeHtml(provenance)" in plan_render
    assert "escapeHtml(provenance)" in preview
