(() => {
  const { state, el, core } = window.App;
  function getCategoryActions() {
    return window.App.getRuntimeModule?.("category-actions") || {};
  }

  function getSelectedCreateCategoryId() {
    return el.opCategory.value ? Number(el.opCategory.value) : null;
  }
  function getCategoryMetaById(categoryId) {
    if (!categoryId) {
      return null;
    }
    const category = state.categories.find((item) => item.id === categoryId);
    if (!category) {
      return null;
    }
    return {
      id: category.id,
      name: category.name,
      icon: category.icon || category.group_icon || null,
      accent_color: category.group_accent_color || null,
      kind: category.kind,
      group_name: category.group_name || "",
    };
  }

  function getActivityFeature() {
    return window.App.getRuntimeModule?.("activity") || {};
  }

  function setCreateModalActivity(entityType, entityId) {
    getActivityFeature().configureActivityButton?.(el.createModalActivityBtn, entityType, entityId);
  }

  function setEditModalActivity(entityType, entityId) {
    getActivityFeature().configureActivityButton?.(el.editModalActivityBtn, entityType, entityId);
  }
  let getDebtPreviewSnapshot = null;
  const previewModule = window.App.getRuntimeModule?.("operation-modal-preview");
  const preview = previewModule?.build({
    state,
    el,
    core,
    getSelectedCreateCategoryId,
    getCategoryMetaById,
    getDebtPreviewSnapshot: () => (typeof getDebtPreviewSnapshot === "function" ? getDebtPreviewSnapshot() : null),
  });
  const updateDebtDueHint = preview?.updateDebtDueHint || (() => {});
  const getCreateFormPreviewItem = preview?.getCreateFormPreviewItem || (() => ({}));
  const updateCreatePreview = preview?.updateCreatePreview || (() => {});
  const updateEditPreview = preview?.updateEditPreview || (() => {});
  const handleCreatePreviewClick = preview?.handleCreatePreviewClick || (() => {});
  let currencyFeature = {};
  function callCurrencyFeature(method, fallback, args) {
    const fn = currencyFeature?.[method];
    return typeof fn === "function" ? fn(...args) : fallback;
  }
  function setCurrencySide(...args) { return callCurrencyFeature("setCurrencySide", undefined, args); }
  function syncCurrencyTradeFieldUi(...args) { return callCurrencyFeature("syncCurrencyTradeFieldUi", undefined, args); }
  function syncSuggestedCurrencyRate(...args) { return callCurrencyFeature("syncSuggestedCurrencyRate", Promise.resolve(), args); }
  function syncCreateFxSettlementFieldUi(...args) { return callCurrencyFeature("syncCreateFxSettlementFieldUi", undefined, args); }
  function syncEditFxSettlementFieldUi(...args) { return callCurrencyFeature("syncEditFxSettlementFieldUi", undefined, args); }
  function getCreateFxSettlementPayload(...args) { return callCurrencyFeature("getCreateFxSettlementPayload", null, args); }
  function getEditFxSettlementPayload(...args) { return callCurrencyFeature("getEditFxSettlementPayload", null, args); }
  function syncSelectableCurrencyFields(...args) { return callCurrencyFeature("syncSelectableCurrencyFields", undefined, args); }
  function buildSelectableCurrencyList(...args) { return callCurrencyFeature("buildSelectableCurrencyList", [], args); }
  function setOperationFxRateManual(...args) { return callCurrencyFeature("setOperationFxRateManual", undefined, args); }
  function setOperationFxRateHint(...args) { return callCurrencyFeature("setOperationFxRateHint", undefined, args); }
  function getOperationCurrencyContext(...args) { return callCurrencyFeature("getOperationCurrencyContext", null, args); }
  function syncSuggestedOperationFxRate(...args) { return callCurrencyFeature("syncSuggestedOperationFxRate", Promise.resolve(), args); }
  function syncOperationCurrencyFields(...args) { return callCurrencyFeature("syncOperationCurrencyFields", Promise.resolve(), args); }
  function applyDebtCurrencyUi(...args) { return callCurrencyFeature("applyDebtCurrencyUi", undefined, args); }
  function getCurrencyTradeContext(...args) { return callCurrencyFeature("getCurrencyTradeContext", null, args); }
  function markCurrencyRateManual(...args) { return callCurrencyFeature("markCurrencyRateManual", undefined, args); }
  function markCurrencyQuantitySource(...args) { return callCurrencyFeature("markCurrencyQuantitySource", undefined, args); }
  function markCurrencyQuoteSource(...args) { return callCurrencyFeature("markCurrencyQuoteSource", undefined, args); }
  function resetCurrencyRateAutofill(...args) { return callCurrencyFeature("resetCurrencyRateAutofill", undefined, args); }
  function formatTradeRateValue(...args) { return callCurrencyFeature("formatTradeRateValue", "", args); }
  function setAutoComputedField(...args) { return callCurrencyFeature("setAutoComputedField", undefined, args); }
  const createOperationModalReceiptFeature = window.App.getRuntimeModule?.("operation-modal-receipt-factory");
  const receipt = createOperationModalReceiptFeature
    ? createOperationModalReceiptFeature({
      state,
      el,
      core,
      updateCreatePreview,
      updateEditPreview,
      syncCreateFxSettlementFieldUi,
      syncEditFxSettlementFieldUi,
    })
    : {};
  const createReceiptDraft = receipt.createReceiptDraft;
  const clearReceiptItems = receipt.clearReceiptItems || (() => {});
  const setReceiptEnabled = receipt.setReceiptEnabled || (() => {});
  const renderReceiptItems = receipt.renderReceiptItems || (() => {});
  const renderReceiptSummary = receipt.renderReceiptSummary || (() => {});
  const loadReceiptTemplateHints = receipt.loadReceiptTemplateHints || (async () => {});
  const handleReceiptItemsListInput = receipt.handleReceiptItemsListInput || (() => {});
  const handleReceiptItemsListFocusOut = receipt.handleReceiptItemsListFocusOut || (() => {});
  const handleReceiptItemsListFocusIn = receipt.handleReceiptItemsListFocusIn || (() => {});
  const handleReceiptItemsListKeydown = receipt.handleReceiptItemsListKeydown || (() => {});
  const handleReceiptItemsListClick = receipt.handleReceiptItemsListClick || (() => {});
  const handleReceiptOutsidePointer = receipt.handleReceiptOutsidePointer || (() => {});
  const handlePullReceiptTotal = receipt.handlePullReceiptTotal || (() => {});
  const getCreateReceiptPayload = receipt.getCreateReceiptPayload || (() => []);
  const getEditReceiptPayload = receipt.getEditReceiptPayload || (() => []);
  const syncReceiptCategoriesToKind = receipt.syncReceiptCategoriesToKind || (() => {});
  const createOperationModalDebtCounterpartyFeature = window.App.getRuntimeModule?.("operation-modal-debt-counterparty-factory");
  const createOperationModalDebtFeature = window.App.getRuntimeModule?.("operation-modal-debt-factory");

  function isCreateReceiptMode() {
    return el.opOperationMode?.value === "receipt";
  }

  function isEditReceiptMode() {
    return el.editOperationMode?.value === "receipt";
  }
  const createOperationModalCurrencyFeature = window.App.getRuntimeModule?.("operation-modal-currency-factory");
  currencyFeature = createOperationModalCurrencyFeature
    ? createOperationModalCurrencyFeature({
      state,
      el,
      core,
      updateCreatePreview,
      updateEditPreview,
      renderReceiptSummary,
      getCreateReceiptPayload,
      getEditReceiptPayload,
      isCreateReceiptMode,
      isEditReceiptMode,
    })
    : {};
  const debtCounterpartyFeature = createOperationModalDebtCounterpartyFeature
    ? createOperationModalDebtCounterpartyFeature({
      state,
      el,
      core,
      getCurrentDebtEditId: () => Number(state.editDebtCreateId || 0),
      getCurrentDebtDirection: () => (el.debtDirection?.value === "borrow" ? "borrow" : "lend"),
      getCurrentDebtCurrency: () => String(el.debtCurrency?.value || (core.getCurrencyConfig?.().code || "BYN")).toUpperCase(),
      getCurrentDebtPrincipalValue: () => {
        const resolved = core.resolveMoneyInput(el.debtPrincipal?.value || 0);
        return Number(resolved.previewValue || 0);
      },
      getCurrentDebtStartDate: () => core.parseDateInputValue(el.debtStartDate?.value || "") || core.getTodayIso(),
      getCurrentDebtDueDate: () => core.parseDateInputValue(el.debtDueDate?.value || "") || "",
      getCurrentDebtNote: () => String(el.debtNote?.value || "").trim(),
      updateCreatePreview,
    })
    : {};
  getDebtPreviewSnapshot = debtCounterpartyFeature.getDebtPreviewSnapshot || null;
  const debtFeature = createOperationModalDebtFeature
    ? createOperationModalDebtFeature({
      state,
      el,
      core,
      updateCreatePreview,
      setCreateModalActivity,
      openCreateModal,
      selectDebtCounterparty: (...args) => debtCounterpartyFeature.selectDebtCounterparty?.(...args),
      renderDebtCounterpartyPicker: (...args) => debtCounterpartyFeature.renderDebtCounterpartyPicker?.(...args),
      closeDebtCounterpartyPopover: (...args) => debtCounterpartyFeature.closeDebtCounterpartyPopover?.(...args),
      syncSelectableCurrencyFields,
      applyDebtCurrencyUi,
      updateDebtDueHint,
    })
    : {};
  const setDebtDirection = debtFeature.setDebtDirection || (() => {});
  const resetCreateDebtFields = debtFeature.resetCreateDebtFields || (() => {});
  const prepareDebtEntryMode = debtFeature.prepareDebtEntryMode || (() => {});
  const openCreateModalForDebtEdit = debtFeature.openCreateModalForDebtEdit || (async () => {});
  function setCreateOperationMode(mode) {
    const nextMode = mode === "receipt" ? "receipt" : "common";
    if (el.opOperationMode) {
      el.opOperationMode.value = nextMode;
    }
    if (el.createOperationModeSwitch) {
      core.syncSegmentedActive(el.createOperationModeSwitch, "operation-mode", nextMode);
    }
    el.opReceiptBlock?.classList.toggle("hidden", el.opEntryMode?.value === "debt" || el.opEntryMode?.value === "currency" || nextMode !== "receipt");
    el.convertAmountToDiscountReceiptBtn?.classList.toggle("hidden", nextMode !== "common");
    setReceiptEnabled(nextMode === "receipt", "create");
    updateCreateCategoryFieldUi();
    renderCreateCategoryPicker();
    renderDebtCounterpartyPicker();
    syncCreateFxSettlementFieldUi();
    updateCreatePreview();
  }
  function convertCreateAmountToDiscountReceipt() {
    if (el.opEntryMode?.value && el.opEntryMode.value !== "operation") {
      return;
    }
    const amountInput = document.getElementById("opAmount");
    const amountResolved = core.resolveMoneyInput(amountInput?.value || "");
    const amountValue = amountResolved?.valid && Number(amountResolved.previewValue || 0) > 0
      ? core.formatAmount(amountResolved.previewValue)
      : "";
    setCreateOperationMode("receipt");
    const existingRows = Array.isArray(state.createReceiptItems)
      ? state.createReceiptItems.filter((item) => {
        const hasName = String(item?.name || "").trim() !== "";
        const hasShop = String(item?.shop_name || "").trim() !== "";
        const hasPrice = Number(item?.unit_price || 0) > 0;
        return hasName || hasShop || hasPrice;
      })
      : [];
    const seed = {
      quantity: 1,
      unit_price: amountValue,
      is_discounted: true,
      regular_unit_price: "",
      discount_type: "promo",
    };
    state.createReceiptItems = existingRows.length
      ? existingRows
      : [createReceiptDraft ? createReceiptDraft(seed, "create") : seed];
    if (state.createReceiptItems[0]) {
      state.createReceiptItems[0].is_discounted = true;
      state.createReceiptItems[0].discount_type = state.createReceiptItems[0].discount_type || "promo";
      if (amountValue && Number(state.createReceiptItems[0].unit_price || 0) <= 0) {
        state.createReceiptItems[0].unit_price = Number(amountResolved.previewValue || 0);
      }
      if (!state.createReceiptItems[0].quantity || Number(state.createReceiptItems[0].quantity) <= 0) {
        state.createReceiptItems[0].quantity = 1;
      }
    }
    if (amountInput) {
      amountInput.value = "";
    }
    renderReceiptItems("create");
    renderReceiptSummary("create");
    syncCreateFxSettlementFieldUi();
    updateCreatePreview();
    const focusTarget = document.querySelector(
      '#receiptItemsList .receipt-item-row:first-child [data-receipt-field="regular_unit_price"], #receiptItemsList .receipt-item-row:first-child [data-receipt-field="unit_price"]',
    );
    focusTarget?.focus();
  }
  function setEditOperationMode(mode) {
    const nextMode = mode === "receipt" ? "receipt" : "common";
    if (el.editOperationMode) {
      el.editOperationMode.value = nextMode;
    }
    if (el.editOperationModeSwitch) {
      core.syncSegmentedActive(el.editOperationModeSwitch, "operation-mode", nextMode);
    }
    el.editReceiptBlock?.classList.toggle("hidden", nextMode !== "receipt");
    setReceiptEnabled(nextMode === "receipt", "edit");
    updateEditCategoryFieldUi();
    renderEditCategoryPicker();
    syncEditFxSettlementFieldUi();
    updateEditPreview();
  }
  async function setCreateEntryMode(mode) {
    const nextMode = mode === "debt" ? "debt" : mode === "currency" ? "currency" : "operation";
    el.opEntryMode.value = nextMode;
    core.syncSegmentedActive(el.createEntryModeSwitch, "entry-mode", nextMode);
    const isDebt = nextMode === "debt";
    const isCurrency = nextMode === "currency";
    const createTitle = document.getElementById("createTitle");
    if (createTitle) {
      createTitle.textContent = isDebt
        ? "Новый долг"
        : isCurrency
          ? "Новая валютная сделка"
          : "Новая операция";
    }
    el.createKindSwitch.classList.toggle("hidden", isDebt || isCurrency);
    el.createOperationModeSwitch?.classList.toggle("hidden", isDebt || isCurrency);
    el.createCategoryField.classList.toggle("hidden", isDebt || isCurrency);
    el.opReceiptBlock?.classList.toggle("hidden", isDebt || isCurrency || !isCreateReceiptMode());
    const opAmountField = document.getElementById("opAmountCompound");
    const opAmount = document.getElementById("opAmount");
    const opFxRateField = document.getElementById("opFxRateField");
    const opDateField = document.getElementById("opDateField");
    const opDate = document.getElementById("opDate");
    const opNote = document.getElementById("opNote");
    if (opAmountField) {
      opAmountField.classList.toggle("hidden", isDebt || isCurrency);
    }
    el.convertAmountToDiscountReceiptBtn?.classList.toggle("hidden", isDebt || isCurrency || isCreateReceiptMode());
    if (opAmount) {
      opAmount.required = !isDebt && !isCurrency;
      if (!isDebt && !isCurrency && isCreateReceiptMode()) {
        opAmount.required = false;
      }
    }
    if (opFxRateField) {
      opFxRateField.classList.toggle("hidden", isDebt || isCurrency);
    }
    if (opDateField) {
      opDateField.classList.toggle("hidden", isDebt || isCurrency);
    }
    if (opDate) {
      opDate.required = !isDebt && !isCurrency;
    }
    if (opNote) {
      opNote.classList.toggle("hidden", isDebt || isCurrency);
      opNote.placeholder = isDebt ? "Комментарий (долг)" : "Комментарий";
    }
    el.createDebtFields.classList.toggle("hidden", !isDebt);
    el.createCurrencyFields?.classList.toggle("hidden", !isCurrency);
    if (el.createPreviewHeadOperation && el.createPreviewHeadDebt) {
      el.createPreviewHeadOperation.classList.toggle("hidden", isDebt || isCurrency);
      el.createPreviewHeadDebt.classList.toggle("hidden", !isDebt);
    }
    if (el.createPreviewHeadCurrency) {
      el.createPreviewHeadCurrency.classList.toggle("hidden", !isCurrency);
    }
    if (isDebt || isCurrency) {
      closeCreateCategoryPopover();
      closeDebtCounterpartyPopover();
    }
    const submit = document.getElementById("submitCreateOperationBtn");
    if (isDebt) {
      prepareDebtEntryMode({ isDebt, submit });
    } else if (isCurrency) {
      prepareDebtEntryMode({ isDebt: false, submit });
      if (el.currencyTradeDateModal && !el.currencyTradeDateModal.value) {
        core.syncDateFieldValue(el.currencyTradeDateModal, core.getTodayIso());
      }
      syncCurrencyTradeFieldUi();
      await syncSuggestedCurrencyRate().catch(() => {});
      if (submit) {
        submit.textContent = state.editCurrencyTradeId ? "Сохранить валютную сделку" : "Создать валютную сделку";
      }
    } else if (submit) {
      submit.textContent = "Добавить";
    }
    if (!isDebt && !isCurrency) {
      prepareDebtEntryMode({ isDebt: false, submit });
    }
    if (!isDebt && !isCurrency) {
      updateCreateCategoryFieldUi();
      await syncOperationCurrencyFields("create").catch(() => {});
    }
    syncCreateFxSettlementFieldUi();
    updateCreatePreview();
  }
  function setOperationKind(mode, kind) {
    if (mode === "create") {
      el.opKind.value = kind;
      core.syncSegmentedActive(el.createKindSwitch, "kind", kind);
      getCategoryActions().populateCategorySelect?.(el.opCategory, el.opCategory.value, kind);
      if (el.opCategory.value && !state.categories.some((item) => String(item.id) === el.opCategory.value && item.kind === kind)) {
        el.opCategory.value = "";
        el.opCategorySearch.value = "";
      }
      renderCreateCategoryPicker();
      syncReceiptCategoriesToKind("create");
      updateCreatePreview();
      return;
    }
    if (mode === "edit") {
      el.editKind.value = kind;
      core.syncSegmentedActive(el.editKindSwitch, "kind", kind);
      getCategoryActions().populateCategorySelect?.(el.editCategory, el.editCategory.value, kind);
      if (el.editCategory.value && !state.categories.some((item) => String(item.id) === el.editCategory.value && item.kind === kind)) {
        el.editCategory.value = "";
        if (el.editCategorySearch) {
          el.editCategorySearch.value = "";
        }
      }
      renderEditCategoryPicker();
      syncReceiptCategoriesToKind("edit");
      updateEditPreview();
    }
  }
  function ensureCategoryCatalogReady(mode = "create") {
    if (Array.isArray(state.categories) && state.categories.length > 0) {
      return Promise.resolve();
    }
    if (!getCategoryActions().loadCategoryCatalog) {
      return Promise.resolve();
    }
    return getCategoryActions().loadCategoryCatalog().then(() => {
      if (mode === "edit") {
        renderEditCategoryPicker();
        renderReceiptItems("edit");
        renderReceiptSummary("edit");
        updateEditPreview();
      } else {
        renderCreateCategoryPicker();
        renderReceiptItems("create");
        renderReceiptSummary("create");
        updateCreatePreview();
      }
    }).catch(() => {});
  }

  async function openCreateModal(options = {}) {
    const initialEntryMode = options?.entryMode === "debt"
      ? "debt"
      : options?.entryMode === "currency"
        ? "currency"
        : "operation";
    await ensureCategoryCatalogReady("create");
    state.createFlowMode = "operation";
    state.editPlanId = null;
    state.editDebtCreateId = null;
    state.editCurrencyTradeId = null;
    setCreateModalActivity(null, null);
    const createTitle = document.getElementById("createTitle");
    if (createTitle) {
      createTitle.textContent = "Новая операция";
    }
    if (el.createEntryModeSwitch) {
      el.createEntryModeSwitch.classList.remove("hidden");
    }
    const dateInput = document.getElementById("opDate");
    if (!dateInput.value) {
      core.syncDateFieldValue(dateInput, core.getTodayIso());
    }
    setOperationKind("create", el.opKind.value || "expense");
    el.opCategory.value = "";
    el.opCategorySearch.value = "";
    clearReceiptItems("create");
    setCreateOperationMode("common");
    closeCreateCategoryPopover();
    resetCreateDebtFields();
    if (el.currencyAsset) {
      el.currencyAsset.value = buildSelectableCurrencyList(false)[0] || "USD";
    }
    if (el.currencyQuote) {
      el.currencyQuote.value = core.getCurrencyConfig?.().code || "BYN";
    }
    if (el.currencyTradeDateModal) {
      core.syncDateFieldValue(el.currencyTradeDateModal, core.getTodayIso());
    }
    if (el.currencyQuantity) {
      el.currencyQuantity.value = "";
    }
    if (el.currencyQuoteTotal) {
      el.currencyQuoteTotal.value = "";
    }
    if (el.currencyUnitPrice) {
      el.currencyUnitPrice.value = "";
    }
    currencyFeature.resetCurrencyTradeState?.();
    if (el.currencyNote) {
      el.currencyNote.value = "";
    }
    if (el.opUseFxSettlement) {
      el.opUseFxSettlement.checked = false;
    }
    if (el.opFxSettlementQuantity) {
      el.opFxSettlementQuantity.value = "";
    }
    if (el.opFxSettlementUnitPrice) {
      el.opFxSettlementUnitPrice.value = "";
    }
    if (el.opFxSettlementNote) {
      el.opFxSettlementNote.value = "";
    }
    if (el.opCurrency) {
      el.opCurrency.value = core.getCurrencyConfig?.().code || "BYN";
      el.opCurrency.disabled = false;
      el.opCurrency.title = "";
    }
    if (el.opFxRate) {
      el.opFxRate.value = "1";
    }
    setOperationFxRateHint("create", "");
    setOperationFxRateManual("create", false);
    if (el.planRecurrenceBlock) {
      el.planRecurrenceBlock.classList.add("hidden");
    }
    if (el.planScheduleMode) {
      el.planScheduleMode.value = "oneoff";
    }
    if (el.planScheduleModeSwitch) {
      core.syncSegmentedActive(el.planScheduleModeSwitch, "plan-schedule-mode", "oneoff");
    }
    if (el.planRecurrenceFields) {
      el.planRecurrenceFields.classList.add("hidden");
    }
    if (el.planRecurrenceFrequency) {
      el.planRecurrenceFrequency.value = "monthly";
    }
    if (el.planRecurrenceInterval) {
      el.planRecurrenceInterval.value = "1";
    }
    if (el.planRecurrenceWorkdaysOnly) {
      el.planRecurrenceWorkdaysOnly.value = "off";
    }
    if (el.planRecurrenceWorkdaysSwitch) {
      core.syncSegmentedActive(el.planRecurrenceWorkdaysSwitch, "plan-workdays-only", "off");
    }
    if (el.planRecurrenceMonthEnd) {
      el.planRecurrenceMonthEnd.value = "off";
    }
    if (el.planRecurrenceMonthEndSwitch) {
      core.syncSegmentedActive(el.planRecurrenceMonthEndSwitch, "plan-month-end", "off");
    }
    if (el.planRecurrenceEndDate) {
      core.syncDateFieldValue(el.planRecurrenceEndDate, "");
    }
    if (el.planRecurrenceWeekdays) {
      Array.from(el.planRecurrenceWeekdays.querySelectorAll("button[data-plan-weekday]")).forEach((button) => {
        button.classList.remove("active");
      });
    }
    el.planRecurrenceWeeklyBlock?.classList.add("hidden");
    el.planRecurrenceWorkdaysWrap?.classList.add("hidden");
    el.planRecurrenceMonthEndWrap?.classList.add("hidden");
    await setCurrencySide("buy");
    currencyFeature.resetCurrencyTradeState?.();
    currencyFeature.resetCreateFxSettlementDrivers?.();
    syncCurrencyTradeFieldUi();
    syncCreateFxSettlementFieldUi();
    syncOperationCurrencyFields("create").catch(() => {});
    syncOperationCurrencyFields("edit").catch(() => {});
    await setCreateEntryMode(initialEntryMode);
    renderCreateCategoryPicker();
    renderDebtCounterpartyPicker();
    loadReceiptTemplateHints().catch(() => {});
    renderReceiptItems();
    renderReceiptSummary();
    updateCreatePreview();
    el.createModal.classList.remove("hidden");
  }
  function closeCreateModal() {
    window.App.getRuntimeModule?.("finance-calculator")?.closeIfAttachedToModal?.(el.createModal);
    state.createFlowMode = "operation";
    state.editPlanId = null;
    state.editDebtCreateId = null;
    state.editCurrencyTradeId = null;
    setCreateModalActivity(null, null);
    const createTitle = document.getElementById("createTitle");
    if (createTitle) {
      createTitle.textContent = "Новая операция";
    }
    el.createModal.classList.add("hidden");
  }
  async function openCreateModalForCurrency() {
    await openCreateModal({ entryMode: "currency" });
    currencyFeature.resetCurrencyTradeState?.();
    syncCurrencyTradeFieldUi();
    updateCreatePreview();
  }
  async function openCreateModalForCurrencyEdit(payload) {
    if (!payload?.id) {
      return;
    }
    await openCreateModal({ entryMode: "currency" });
    state.editCurrencyTradeId = Number(payload.id);
    setCreateModalActivity("currency_trade", payload.id);
    if (el.createEntryModeSwitch) {
      el.createEntryModeSwitch.classList.add("hidden");
    }
    const createTitle = document.getElementById("createTitle");
    if (createTitle) {
      createTitle.textContent = "Редактировать валютную сделку";
    }
    const submit = document.getElementById("submitCreateOperationBtn");
    if (submit) {
      submit.textContent = "Сохранить валютную сделку";
    }
    if (el.currencyAsset) {
      el.currencyAsset.value = String(payload.asset_currency || buildSelectableCurrencyList(false)[0] || "USD").toUpperCase();
    }
    if (el.currencyQuote) {
      el.currencyQuote.value = String(payload.quote_currency || (core.getCurrencyConfig?.().code || "BYN")).toUpperCase();
    }
    core.syncDateFieldValue(el.currencyTradeDateModal, payload.trade_date || core.getTodayIso());
    await setCurrencySide(payload.side || "buy");
    if (el.currencyNote) {
      el.currencyNote.value = payload.note || "";
    }
    if (el.currencyUnitPrice) {
      el.currencyUnitPrice.value = Number(payload.unit_price || 0).toFixed(4);
    }
    if (el.currencyQuoteTotal) {
      const quoteTotalValue = Number(payload.quantity || 0) * Number(payload.unit_price || 0);
      el.currencyQuoteTotal.value = quoteTotalValue > 0 ? core.formatAmount(quoteTotalValue) : "";
    }
    if (el.currencyQuantity) {
      const quantityValue = Number(payload.quantity || 0);
      el.currencyQuantity.value = quantityValue > 0 ? core.formatAmount(quantityValue) : "";
    }
    currencyFeature.setCurrencyTradeState?.({
      sourceField: "quantity",
      unitPriceManual: true,
      rateDriver: false,
      manualOrder: ["quantity", "rate"],
    });
    syncCurrencyTradeFieldUi();
    updateCreatePreview();
  }
  async function openEditModal(item) {
    await ensureCategoryCatalogReady("edit");
    state.editOperationId = item.id;
    setEditModalActivity("operation", item.id);
    document.getElementById("editAmount").value = item.original_amount || item.amount;
    syncSelectableCurrencyFields({ editCurrency: item.currency || "" });
    if (el.editCurrency) {
      el.editCurrency.value = item.currency || "BYN";
    }
    if (el.editFxRate) {
      el.editFxRate.value = item.fx_rate || "1";
    }
    setOperationFxRateHint("edit", item.currency && item.currency !== (core.getCurrencyConfig?.().code || "BYN") ? "Сохранившийся курс операции" : "");
    setOperationFxRateManual("edit", true);
    core.syncDateFieldValue(document.getElementById("editDate"), item.operation_date);
    document.getElementById("editNote").value = item.note || "";
    clearReceiptItems("edit");
    if (typeof createReceiptDraft === "function") {
      state.editReceiptItems = (Array.isArray(item.receipt_items) ? item.receipt_items : []).map((row) => createReceiptDraft({
        template_id: row.template_id || null,
        category_id: row.category_id || null,
        shop_name: row.shop_name || "",
        name: row.name || "",
        quantity: row.quantity || 0,
        unit_price: row.unit_price || 0,
        is_discounted: Boolean(row.is_discounted),
        regular_unit_price: row.regular_unit_price || 0,
        discount_type: row.discount_type || null,
        note: row.note || "",
      }, "edit"));
    } else {
      state.editReceiptItems = [];
    }
    const hasReceipt = state.editReceiptItems.length > 0;
    el.editCategory.value = item.category_id ? String(item.category_id) : "";
    setOperationKind("edit", item.kind);
    syncOperationCurrencyFields("edit");
    selectEditCategory(item.category_id ? Number(item.category_id) : null);
    setEditOperationMode(hasReceipt ? "receipt" : "common");
    if (el.editUseFxSettlement) {
      el.editUseFxSettlement.checked = Boolean(item.fx_settlement);
    }
    if (el.editFxSettlementAsset) {
      el.editFxSettlementAsset.value = String(item.fx_settlement?.asset_currency || buildSelectableCurrencyList(false)[0] || "USD").toUpperCase();
    }
    if (el.editFxSettlementQuantity) {
      el.editFxSettlementQuantity.value = item.fx_settlement?.quantity ? core.formatAmount(item.fx_settlement.quantity) : "";
    }
    if (el.editFxSettlementUnitPrice) {
      el.editFxSettlementUnitPrice.value = item.fx_settlement?.unit_price ? formatTradeRateValue(item.fx_settlement.unit_price) : "";
    }
    if (el.editFxSettlementNote) {
      el.editFxSettlementNote.value = item.fx_settlement?.note || "";
    }
    currencyFeature.resetEditFxSettlementDrivers?.();
    syncEditFxSettlementFieldUi();
    updateEditPreview();
    el.editModal.classList.remove("hidden");
  }
  function closeEditModal() {
    window.App.getRuntimeModule?.("finance-calculator")?.closeIfAttachedToModal?.(el.editModal);
    state.editOperationId = null;
    setEditModalActivity(null, null);
    clearReceiptItems("edit");
    setEditOperationMode("common");
    if (el.editUseFxSettlement) {
      el.editUseFxSettlement.checked = false;
    }
    if (el.editFxSettlementQuantity) {
      el.editFxSettlementQuantity.value = "";
    }
    if (el.editFxSettlementUnitPrice) {
      el.editFxSettlementUnitPrice.value = "";
    }
    if (el.editFxSettlementNote) {
      el.editFxSettlementNote.value = "";
    }
    setAutoComputedField(el.editFxSettlementQuantityField, false);
    setAutoComputedField(el.editFxSettlementUnitPriceField, false);
    currencyFeature.resetEditFxSettlementDrivers?.();
    closeEditCategoryPopover();
    el.editModal.classList.remove("modal-front");
    el.editModal.classList.add("hidden");
  }
  function applySettingsUi() {
    const savedTz = state.preferences?.data?.ui?.timezone || "auto";
    if (el.timezoneSelect) {
      const hasOption = Array.from(el.timezoneSelect.options).some((opt) => opt.value === savedTz);
      el.timezoneSelect.value = hasOption ? savedTz : "auto";
    }
    syncSelectableCurrencyFields();
    applyDebtCurrencyUi();
  }
  function openPeriodCustomModal() {
    const today = core.getTodayIso();
    core.syncDateFieldValue(el.customDateTo, state.customDateTo || today);
    core.syncDateFieldValue(el.customDateFrom, state.customDateFrom || today);
    if (el.customDayDate) {
      const dayValue = el.customDateFrom?.value === el.customDateTo?.value
        ? el.customDateFrom.value
        : (state.customDateFrom || today);
      core.syncDateFieldValue(el.customDayDate, dayValue || today);
    }
    const mode = el.customDateFrom?.value && el.customDateTo?.value && el.customDateFrom.value !== el.customDateTo.value
      ? "range"
      : "day";
    if (el.customPeriodMode) {
      el.customPeriodMode.value = mode;
    }
    if (el.periodCustomModeTabs) {
      core.syncSegmentedActive(el.periodCustomModeTabs, "period-custom-mode", mode);
    }
    el.customDayField?.classList.toggle("hidden", mode !== "day");
    el.customRangeFields?.classList.toggle("hidden", mode !== "range");
    if (el.submitPeriodCustomBtn) {
      el.submitPeriodCustomBtn.textContent = mode === "day" ? "Показать день" : "Применить период";
    }
    el.periodCustomModal.classList.remove("hidden");
  }
  function closePeriodCustomModal() {
    el.periodCustomModal.classList.add("hidden");
  }
  const createOperationModalCategoryFeature = window.App.getRuntimeModule?.("operation-modal-category-factory");
  const categoryFeature = createOperationModalCategoryFeature
    ? createOperationModalCategoryFeature({
      state,
      el,
      core,
      categoryActions: getCategoryActions(),
      renderReceiptItems,
      renderReceiptSummary,
      updateCreatePreview,
      updateEditPreview,
      isCreateReceiptMode,
      isEditReceiptMode,
      getSelectedCreateCategoryId,
      getCategoryMetaById,
    })
    : {};
  const trackCategoryUsage = categoryFeature.trackCategoryUsage || (() => {});
  const updateCreateCategoryFieldUi = categoryFeature.updateCreateCategoryFieldUi || (() => {});
  const updateEditCategoryFieldUi = categoryFeature.updateEditCategoryFieldUi || (() => {});
  const openCreateCategoryPopover = categoryFeature.openCreateCategoryPopover || (() => {});
  const closeCreateCategoryPopover = categoryFeature.closeCreateCategoryPopover || (() => {});
  const openEditCategoryPopover = categoryFeature.openEditCategoryPopover || (() => {});
  const closeEditCategoryPopover = categoryFeature.closeEditCategoryPopover || (() => {});
  const renderCreateCategoryPicker = categoryFeature.renderCreateCategoryPicker || (() => {});
  const renderEditCategoryPicker = categoryFeature.renderEditCategoryPicker || (() => {});
  const handleCreateCategorySearchFocus = categoryFeature.handleCreateCategorySearchFocus || (() => {});
  const handleCreateCategorySearchInput = categoryFeature.handleCreateCategorySearchInput || (() => {});
  const handleCreateCategorySearchKeydown = categoryFeature.handleCreateCategorySearchKeydown || (() => {});
  const renderDebtCounterpartyPicker = debtCounterpartyFeature.renderDebtCounterpartyPicker || (() => {});
  const openDebtCounterpartyPopover = debtCounterpartyFeature.openDebtCounterpartyPopover || (() => {});
  const closeDebtCounterpartyPopover = debtCounterpartyFeature.closeDebtCounterpartyPopover || (() => {});
  const handleDebtCounterpartySearchFocus = debtCounterpartyFeature.handleDebtCounterpartySearchFocus || (() => {});
  const handleDebtCounterpartySearchInput = debtCounterpartyFeature.handleDebtCounterpartySearchInput || (() => {});
  const handleDebtCounterpartySearchKeydown = debtCounterpartyFeature.handleDebtCounterpartySearchKeydown || (() => {});
  const handleEditCategorySearchFocus = categoryFeature.handleEditCategorySearchFocus || (() => {});
  const handleEditCategorySearchInput = categoryFeature.handleEditCategorySearchInput || (() => {});
  const handleEditCategorySearchKeydown = categoryFeature.handleEditCategorySearchKeydown || (() => {});
  const handleCreateCategoryOutsidePointer = categoryFeature.handleCreateCategoryOutsidePointer || (() => {});
  const handleDebtCounterpartyOutsidePointer = debtCounterpartyFeature.handleDebtCounterpartyOutsidePointer || (() => {});
  const handleEditCategoryOutsidePointer = categoryFeature.handleEditCategoryOutsidePointer || (() => {});
  const handleCreateCategoryPickerClick = categoryFeature.handleCreateCategoryPickerClick || (() => {});
  const handleDebtCounterpartyPickerClick = debtCounterpartyFeature.handleDebtCounterpartyPickerClick || (() => {});
  const handleEditCategoryPickerClick = categoryFeature.handleEditCategoryPickerClick || (() => {});
  const onCategoryCreated = categoryFeature.onCategoryCreated || (() => {});
  const selectCreateCategory = categoryFeature.selectCreateCategory || (() => {});
  const selectDebtCounterparty = debtCounterpartyFeature.selectDebtCounterparty || (() => {});
  const selectEditCategory = categoryFeature.selectEditCategory || (() => {});
  const api = {
    trackCategoryUsage,
    getCategoryMetaById,
    getCreateFormPreviewItem,
    updateCreatePreview,
    updateEditPreview,
    renderCreateCategoryPicker,
    renderDebtCounterpartyPicker,
    renderEditCategoryPicker,
    openCreateCategoryPopover,
    closeCreateCategoryPopover,
    openDebtCounterpartyPopover,
    closeDebtCounterpartyPopover,
    openEditCategoryPopover,
    closeEditCategoryPopover,
    handleCreateCategoryPickerClick,
    handleDebtCounterpartyPickerClick,
    handleEditCategoryPickerClick,
    handleCreateCategorySearchFocus,
    handleCreateCategorySearchInput,
    handleCreateCategorySearchKeydown,
    handleDebtCounterpartySearchFocus,
    handleDebtCounterpartySearchInput,
    handleDebtCounterpartySearchKeydown,
    handleEditCategorySearchFocus,
    handleEditCategorySearchInput,
    handleEditCategorySearchKeydown,
    handleCreateCategoryOutsidePointer,
    handleDebtCounterpartyOutsidePointer,
    handleEditCategoryOutsidePointer,
    handleReceiptItemsListInput,
    handleReceiptItemsListFocusOut,
    handleReceiptItemsListFocusIn,
    handleReceiptItemsListKeydown,
    handleReceiptItemsListClick,
    handleReceiptOutsidePointer,
    handlePullReceiptTotal,
    convertCreateAmountToDiscountReceipt,
    setReceiptEnabled,
    getCreateReceiptPayload,
    getCreateFxSettlementPayload,
    getEditReceiptPayload,
    getEditFxSettlementPayload,
    renderReceiptSummary,
    onCategoryCreated,
    selectCreateCategory,
    selectDebtCounterparty,
    selectEditCategory,
    createReceiptDraft,
    clearReceiptItems,
    renderReceiptItems,
    handleCreatePreviewClick,
    setDebtDirection,
    setCurrencySide,
    setOperationKind,
    setCreateEntryMode,
    setCreateOperationMode,
    setEditOperationMode,
    syncOperationCurrencyFields,
    getOperationCurrencyContext,
    syncSuggestedOperationFxRate,
    markCreateOperationFxRateManual: () => {
      setOperationFxRateManual("create", true);
      setOperationFxRateHint("create", "Курс изменен вручную", "manual");
    },
    markEditOperationFxRateManual: () => {
      setOperationFxRateManual("edit", true);
      setOperationFxRateHint("edit", "Курс изменен вручную", "manual");
    },
    resetCreateOperationFxRateAutofill: () => setOperationFxRateManual("create", false),
    resetEditOperationFxRateAutofill: () => setOperationFxRateManual("edit", false),
    syncCurrencyTradeFieldUi,
    syncCreateFxSettlementFieldUi,
    syncEditFxSettlementFieldUi,
    syncSelectableCurrencyFields,
    getCurrencyTradeContext,
    syncSuggestedCurrencyRate,
    markCurrencyRateManual,
    markCurrencyQuantitySource,
    markCurrencyQuoteSource,
    resetCurrencyRateAutofill,
    toggleCreateFxSettlement: () => currencyFeature.toggleCreateFxSettlement?.(),
    markFxSettlementQuantitySource: () => currencyFeature.markFxSettlementQuantitySource?.(),
    markFxSettlementRateSource: () => currencyFeature.markFxSettlementRateSource?.(),
    toggleEditFxSettlement: () => currencyFeature.toggleEditFxSettlement?.(),
    markEditFxSettlementQuantitySource: () => currencyFeature.markEditFxSettlementQuantitySource?.(),
    markEditFxSettlementRateSource: () => currencyFeature.markEditFxSettlementRateSource?.(),
    applyDebtCurrencyUi,
    updateDebtDueHint,
    openCreateModal,
    setCreateModalActivity,
    openCreateModalForCurrency,
    openCreateModalForCurrencyEdit,
    openCreateModalForDebtEdit,
    closeCreateModal,
    openEditModal,
    closeEditModal,
    applySettingsUi,
    openPeriodCustomModal,
    closePeriodCustomModal,
  };

  window.App.registerRuntimeModule?.("operation-modal", api);
})();
