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
    activity = (REPO_ROOT / "static" / "js" / "app-activity.js").read_text(encoding="utf-8")
    usage = (REPO_ROOT / "static" / "js" / "app-usage.js").read_text(encoding="utf-8")
    overlays = (REPO_ROOT / "static" / "css" / "components-overlays.css").read_text(encoding="utf-8")
    item_modal = (REPO_ROOT / "static" / "js" / "templates" / "modals-item-catalog.js").read_text(
        encoding="utf-8"
    )
    elements = (REPO_ROOT / "static" / "js" / "app-core-elements.js").read_text(encoding="utf-8")
    session_auth = (REPO_ROOT / "static" / "js" / "app-features-session-auth.js").read_text(encoding="utf-8")
    init_core = (REPO_ROOT / "static" / "js" / "app-init-core.js").read_text(encoding="utf-8")

    assert 'id="activityModal"' in modals
    assert 'id="usageModal"' in modals
    assert 'id="activityList"' in modals
    assert 'id="usageList"' in modals
    assert 'id="closeActivityModalBtn"' in modals
    assert 'id="closeUsageModalBtn"' in modals
    for button_id in (
        "createModalActivityBtn",
        "editModalActivityBtn",
        "editGroupActivityBtn",
        "editCategoryActivityBtn",
    ):
        assert f'id="{button_id}"' in modals
        assert f'{button_id}: document.getElementById("{button_id}")' in elements
    assert 'id="itemTemplateActivityBtn"' in modals_item_catalog
    assert 'id="itemTemplateUsageBtn"' in modals_item_catalog
    assert 'itemTemplateActivityBtn: document.getElementById("itemTemplateActivityBtn")' in elements
    assert 'itemTemplateUsageBtn: document.getElementById("itemTemplateUsageBtn")' in elements
    assert 'id="dashboardCurrencyActivityBtn"' in shell_primary
    assert 'id="currencyPortfolioActivityBtn"' in shell_secondary
    assert 'dashboardCurrencyActivityBtn: document.getElementById("dashboardCurrencyActivityBtn")' in elements
    assert 'currencyPortfolioActivityBtn: document.getElementById("currencyPortfolioActivityBtn")' in elements
    assert 'activityModal: document.getElementById("activityModal")' in elements
    assert 'usageModal: document.getElementById("usageModal")' in elements
    assert "function configureActivityButton" in activity
    assert "function configureUsageButton" in usage
    assert "/api/v1/operations/money-flow?" in usage
    assert "item_template_id" in usage
    assert "matchingReceiptItem?.category_name" in usage
    assert "data-usage-operation-id" in usage
    assert "openMoneyFlowSource" in usage
    assert "core.bringModalToFront?.(el.activityModal);" in activity
    assert "core.bringModalToFront?.(el.usageModal);" in usage
    assert "#usageModal {\n  z-index: 180;" in overlays
    assert ".modal.modal-front" in overlays
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
    source_edit_block = item_sources.split("if (originalName)", 1)[1].split("writeItemCatalogSourceGroups([...groups", 1)[0]
    assert "closeSourceGroupModal();" not in source_edit_block
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


def test_receipt_discount_ui_uses_discount_copy_and_prefills_regular_price():
    receipt = (REPO_ROOT / "static" / "js" / "app-features-operation-modal-receipt.js").read_text(encoding="utf-8")

    assert ">Скидка</button>" in receipt
    assert "title=\"Скидка, купон, промокод или бонусы\"" in receipt
    assert 'type="text" inputmode="decimal" data-receipt-field="unit_price"' in receipt
    assert 'data-receipt-field="regular_unit_price"' in receipt
    assert "receipt-price-label-chip" in receipt
    assert "Цена покупки" in receipt
    assert "Обычная цена" in receipt
    assert 'data-receipt-discount-type="${entry.value}"' in receipt
    assert "Акция" in receipt
    assert "Купон" in receipt
    assert "Баллы" in receipt
    assert "if (latestPrice > 0)" in receipt
    assert "latestPrice > asMoney(item.unit_price || 0)" not in receipt
