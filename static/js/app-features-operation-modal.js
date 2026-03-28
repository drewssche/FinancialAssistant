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
  let currencyUnitPriceManual = false;
  let currencyRateRequestSeq = 0;
  let createOperationFxRateManual = false;
  let editOperationFxRateManual = true;
  const operationFxRateRequestSeq = {
    create: 0,
    edit: 0,
  };
  const createOperationModalReceiptFeature = window.App.getRuntimeModule?.("operation-modal-receipt-factory");
  const receipt = createOperationModalReceiptFeature
    ? createOperationModalReceiptFeature({
      state,
      el,
      core,
      updateCreatePreview,
      updateEditPreview,
    })
    : {};
  const createReceiptDraft = receipt.createReceiptDraft;
  const clearReceiptItems = receipt.clearReceiptItems || (() => {});
  const setReceiptEnabled = receipt.setReceiptEnabled || (() => {});
  const renderReceiptItems = receipt.renderReceiptItems || (() => {});
  const renderReceiptSummary = receipt.renderReceiptSummary || (() => {});
  const loadReceiptTemplateHints = receipt.loadReceiptTemplateHints || (async () => {});
  const handleReceiptItemsListInput = receipt.handleReceiptItemsListInput || (() => {});
  const handleReceiptItemsListFocusIn = receipt.handleReceiptItemsListFocusIn || (() => {});
  const handleReceiptItemsListKeydown = receipt.handleReceiptItemsListKeydown || (() => {});
  const handleReceiptItemsListClick = receipt.handleReceiptItemsListClick || (() => {});
  const handleReceiptOutsidePointer = receipt.handleReceiptOutsidePointer || (() => {});
  const handlePullReceiptTotal = receipt.handlePullReceiptTotal || (() => {});
  const getCreateReceiptPayload = receipt.getCreateReceiptPayload || (() => []);
  const getEditReceiptPayload = receipt.getEditReceiptPayload || (() => []);
  const syncReceiptCategoriesToKind = receipt.syncReceiptCategoriesToKind || (() => {});
  const createOperationModalDebtCounterpartyFeature = window.App.getRuntimeModule?.("operation-modal-debt-counterparty-factory");

  function isCreateReceiptMode() {
    return el.opOperationMode?.value === "receipt";
  }

  function isEditReceiptMode() {
    return el.editOperationMode?.value === "receipt";
  }
  function setDebtDirection(direction) {
    const nextDirection = direction === "borrow" ? "borrow" : "lend";
    el.debtDirection.value = nextDirection;
    core.syncSegmentedActive(el.createDebtDirectionSwitch, "debt-direction", nextDirection);
    updateCreatePreview();
  }
  async function setCurrencySide(side) {
    const nextSide = side === "sell" ? "sell" : "buy";
    if (el.currencySide) {
      el.currencySide.value = nextSide;
    }
    if (el.createCurrencySideSwitch) {
      core.syncSegmentedActive(el.createCurrencySideSwitch, "currency-side", nextSide);
    }
    currencyUnitPriceManual = false;
    syncCurrencyTradeFieldUi();
    await syncSuggestedCurrencyRate({ force: true }).catch(() => {});
    updateCreatePreview();
  }

  function getCurrencyTradeContext() {
    const side = el.currencySide?.value === "sell" ? "sell" : "buy";
    const assetCurrency = String(el.currencyAsset?.value || "USD").toUpperCase();
    const quoteCurrency = String(el.currencyQuote?.value || (core.getCurrencyConfig?.().code || "BYN")).toUpperCase();
    const assetLabel = core.formatCurrencyLabel?.(assetCurrency) || assetCurrency;
    const quoteLabel = core.formatCurrencyLabel?.(quoteCurrency) || quoteCurrency;
    const quantityResolved = core.resolveMoneyInput(el.currencyQuantity?.value || 0);
    const rateResolved = core.resolveMoneyInput(el.currencyUnitPrice?.value || 0);
    const feeResolved = core.resolveMoneyInput(el.currencyFee?.value || 0);
    const enteredAmount = Number(quantityResolved.previewValue || 0);
    const unitPrice = Number(rateResolved.previewValue || 0);
    const effectiveQuantity = side === "buy"
      ? (unitPrice > 0 ? enteredAmount / unitPrice : 0)
      : enteredAmount;
    return {
      side,
      assetCurrency,
      quoteCurrency,
      assetLabel,
      quoteLabel,
      quantityResolved,
      rateResolved,
      feeResolved,
      enteredAmount,
      unitPrice,
      effectiveQuantity,
      amountLabel: side === "buy" ? `Сумма в ${quoteLabel}` : `Количество ${assetLabel}`,
      amountSuffixCurrency: side === "buy" ? quoteCurrency : assetCurrency,
      amountColumnLabel: side === "buy" ? "Сумма" : "Количество",
      amountPreviewText: side === "buy"
        ? core.formatMoney(enteredAmount || 0, { currency: quoteCurrency })
        : core.formatAmount(enteredAmount || 0),
      directionLabel: side === "sell"
        ? `${assetLabel} → ${quoteCurrency}`
        : `${quoteCurrency} → ${assetLabel}`,
      unitPriceLabel: `Курс ${quoteCurrency} за 1 ${assetCurrency}`,
      feeLabel: `Комиссия в ${quoteLabel}`,
    };
  }

  async function syncSuggestedCurrencyRate(options = {}) {
    if (!el.currencyUnitPrice || !el.currencyAsset || !el.currencyTradeDateModal) {
      return;
    }
    if (currencyUnitPriceManual && options.force !== true) {
      return;
    }
    const requestSeq = ++currencyRateRequestSeq;
    const currency = String(el.currencyAsset.value || "").trim().toUpperCase();
    const dateTo = core.parseDateInputValue(el.currencyTradeDateModal.value) || core.getTodayIso();
    if (!currency || !dateTo) {
      return;
    }
    const overview = await core.requestJson(
      `/api/v1/currency/overview?currency=${encodeURIComponent(currency)}&trades_limit=1`,
      { headers: core.authHeaders() },
    ).catch(() => null);
    if (requestSeq !== currencyRateRequestSeq) {
      return;
    }
    const currentRate = Array.isArray(overview?.current_rates) ? overview.current_rates[0] : null;
    if (!currentRate?.rate) {
      return;
    }
    el.currencyUnitPrice.value = Number(currentRate.rate || 0).toFixed(4);
    syncCurrencyTradeFieldUi();
    updateCreatePreview();
  }

  function markCurrencyRateManual() {
    currencyUnitPriceManual = true;
  }

  function resetCurrencyRateAutofill() {
    currencyUnitPriceManual = false;
  }

  function applyTradeFieldCurrency(node, currencyCode) {
    if (!node) {
      return;
    }
    const cfg = core.resolveCurrencyConfig?.(currencyCode || "BYN", "suffix") || { symbol: "руб.", position: "suffix" };
    node.dataset.currencySymbol = cfg.symbol || String(currencyCode || "BYN").toUpperCase();
    node.classList.remove("currency-prefix");
    node.classList.add("currency-suffix");
  }

  function syncCurrencyTradeFieldUi() {
    const context = getCurrencyTradeContext();
    if (el.currencyQuantityLabel) {
      el.currencyQuantityLabel.textContent = context.amountLabel;
    }
    if (el.currencyUnitPriceLabel) {
      el.currencyUnitPriceLabel.textContent = context.unitPriceLabel;
    }
    if (el.currencyFeeLabel) {
      el.currencyFeeLabel.textContent = context.feeLabel;
    }
    if (el.createPreviewCurrencyAmountHead) {
      el.createPreviewCurrencyAmountHead.textContent = context.amountColumnLabel;
    }
    if (el.currencyQuantity) {
      el.currencyQuantity.placeholder = context.side === "buy" ? "320.00" : "100.00";
    }
    if (el.currencyUnitPrice) {
      el.currencyUnitPrice.placeholder = "3.2700";
    }
    if (el.currencyFee) {
      el.currencyFee.placeholder = "0.00";
    }
    applyTradeFieldCurrency(el.currencyQuantityField, context.amountSuffixCurrency);
    applyTradeFieldCurrency(el.currencyUnitPriceField, context.quoteCurrency);
    applyTradeFieldCurrency(el.currencyFeeField, context.quoteCurrency);
  }

  function isOperationFxRateManual(mode = "create") {
    return mode === "edit" ? editOperationFxRateManual : createOperationFxRateManual;
  }

  function setOperationFxRateManual(mode = "create", value = true) {
    if (mode === "edit") {
      editOperationFxRateManual = value;
      return;
    }
    createOperationFxRateManual = value;
  }

  function setOperationFxRateHint(mode = "create", message = "", tone = "neutral") {
    const hintNode = mode === "edit" ? el.editFxRateHint : el.opFxRateHint;
    if (!hintNode) {
      return;
    }
    hintNode.textContent = message;
    hintNode.classList.toggle("hidden", !message);
    hintNode.dataset.tone = tone;
  }

  function getOperationCurrencyContext(mode = "create") {
    const isEdit = mode === "edit";
    const currencySelect = isEdit ? el.editCurrency : el.opCurrency;
    const fxRateInput = isEdit ? el.editFxRate : el.opFxRate;
    const dateInput = document.getElementById(isEdit ? "editDate" : "opDate");
    const baseCurrency = String(core.getCurrencyConfig?.().code || "BYN").toUpperCase();
    const currency = String(currencySelect?.value || baseCurrency).toUpperCase();
    const fxRateState = core.resolveMoneyInput(fxRateInput?.value || 1);
    return {
      mode,
      isEdit,
      isPlanFlow: !isEdit && state.createFlowMode === "plan",
      currency,
      baseCurrency,
      operationDate: core.parseDateInputValue(dateInput?.value || "") || "",
      fxRate: Number(fxRateState.previewValue || 1),
      hasForeignCurrency: currency !== baseCurrency,
    };
  }

  async function getLatestCurrentCurrencyRate(currency) {
    const normalizedCurrency = String(currency || "").trim().toUpperCase();
    if (!normalizedCurrency) {
      return null;
    }
    const overview = await core.requestJson(
      `/api/v1/currency/overview?currency=${encodeURIComponent(normalizedCurrency)}&trades_limit=1`,
      { headers: core.authHeaders() },
    ).catch(() => null);
    const currentRate = Array.isArray(overview?.current_rates) ? overview.current_rates[0] : null;
    if (!currentRate?.rate) {
      return null;
    }
    return currentRate;
  }

  async function syncSuggestedOperationFxRate(mode = "create", options = {}) {
    const context = getOperationCurrencyContext(mode);
    const fxRateInput = context.isEdit ? el.editFxRate : el.opFxRate;
    if (!fxRateInput || !context.currency) {
      return;
    }
    if (context.currency === context.baseCurrency) {
      fxRateInput.value = "1";
      setOperationFxRateHint(mode, "");
      renderReceiptSummary(mode);
      if (context.isEdit) {
        updateEditPreview();
      } else {
        updateCreatePreview();
      }
      return;
    }
    if (isOperationFxRateManual(mode) && options.force !== true) {
      return;
    }
    const requestSeq = Number(operationFxRateRequestSeq[mode] || 0) + 1;
    operationFxRateRequestSeq[mode] = requestSeq;
    if (context.isPlanFlow) {
      const currentRate = await getLatestCurrentCurrencyRate(context.currency);
      if (requestSeq !== operationFxRateRequestSeq[mode]) {
        return;
      }
      if (!currentRate?.rate) {
        setOperationFxRateHint(mode, `Текущий курс ${core.formatCurrencyLabel(context.currency)} не найден`, "warning");
        return;
      }
      fxRateInput.value = Number(currentRate.rate || 0).toFixed(4);
      const rateDate = currentRate.rate_date ? core.formatDateRu(currentRate.rate_date) : "";
      setOperationFxRateHint(mode, `Текущий курс подставлен автоматически${rateDate ? ` · ${rateDate}` : ""}`, "auto");
      renderReceiptSummary(mode);
      updateCreatePreview();
      return;
    }
    const operationDate = context.operationDate;
    if (!operationDate) {
      return;
    }
    const params = new URLSearchParams({
      currency: context.currency,
      date_from: operationDate,
      date_to: operationDate,
      limit: "5",
    });
    let history = await core.requestJson(`/api/v1/currency/rates/history?${params.toString()}`, {
      headers: core.authHeaders(),
    }).catch(() => []);
    if (requestSeq !== operationFxRateRequestSeq[mode]) {
      return;
    }
    if (!Array.isArray(history) || !history.length) {
      history = await core.requestJson(`/api/v1/currency/rates/history/fill?currency=${encodeURIComponent(context.currency)}&date_from=${encodeURIComponent(operationDate)}&date_to=${encodeURIComponent(operationDate)}`, {
        method: "POST",
        headers: core.authHeaders(),
      }).catch(() => []);
      if (requestSeq !== operationFxRateRequestSeq[mode]) {
        return;
      }
    }
    const rateRow = Array.isArray(history) && history.length ? history[history.length - 1] : null;
    if (!rateRow?.rate) {
      const latestCurrentRate = await getLatestCurrentCurrencyRate(context.currency);
      if (requestSeq !== operationFxRateRequestSeq[mode]) {
        return;
      }
      if (latestCurrentRate?.rate) {
        fxRateInput.value = Number(latestCurrentRate.rate || 0).toFixed(4);
        const rateDate = latestCurrentRate.rate_date ? core.formatDateRu(latestCurrentRate.rate_date) : "";
        setOperationFxRateHint(
          mode,
          `Последний доступный курс подставлен автоматически${rateDate ? ` · ${rateDate}` : ""}`,
          "auto",
        );
        renderReceiptSummary(mode);
        if (context.isEdit) {
          updateEditPreview();
        } else {
          updateCreatePreview();
        }
        return;
      }
      setOperationFxRateHint(mode, `Курс на ${core.formatDateRu(operationDate)} не найден, укажи вручную`, "warning");
      return;
    }
    fxRateInput.value = Number(rateRow.rate || 0).toFixed(4);
    setOperationFxRateHint(mode, `Курс подставлен автоматически на ${core.formatDateRu(operationDate)}`, "auto");
    renderReceiptSummary(mode);
    if (context.isEdit) {
      updateEditPreview();
    } else {
      updateCreatePreview();
    }
  }

  async function syncOperationCurrencyFields(mode = "create") {
    const isEdit = mode === "edit";
    const currencySelect = isEdit ? el.editCurrency : el.opCurrency;
    const fxRateField = isEdit ? el.editFxRateField : el.opFxRateField;
    const fxRateInput = isEdit ? el.editFxRate : el.opFxRate;
    const baseCurrency = core.getCurrencyConfig?.().code || "BYN";
    const selectedCurrency = String(currencySelect?.value || baseCurrency).toUpperCase();
    const createPlanFlow = !isEdit && state.createFlowMode === "plan";
    const needsFxRate = selectedCurrency !== baseCurrency;
    fxRateField?.classList.add("hidden");
    if (createPlanFlow) {
      setOperationFxRateHint(mode, "");
    }
    if (!needsFxRate) {
      setOperationFxRateHint(mode, "");
    }
    if (fxRateInput) {
      fxRateInput.required = false;
      if (!needsFxRate) {
        fxRateInput.value = "1";
        setOperationFxRateManual(mode, false);
      } else {
        setOperationFxRateManual(mode, false);
        await syncSuggestedOperationFxRate(mode, { force: true }).catch(() => {});
      }
    }
  }
  function applyDebtCurrencyUi() {
    const node = el.debtPrincipalField;
    if (node) {
      const currency = String(el.debtCurrency?.value || (core.getCurrencyConfig?.().code || "BYN")).toUpperCase();
      const cfg = core.resolveCurrencyConfig?.(currency, "suffix") || { symbol: "руб." };
      node.dataset.currencySymbol = cfg.symbol || currency;
      node.classList.remove("money-input-no-suffix", "currency-prefix");
      node.classList.add("currency-suffix");
    }
    core.applyMoneyInputs();
  }
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
  function setCreateOperationMode(mode) {
    const nextMode = mode === "receipt" ? "receipt" : "common";
    if (el.opOperationMode) {
      el.opOperationMode.value = nextMode;
    }
    if (el.createOperationModeSwitch) {
      core.syncSegmentedActive(el.createOperationModeSwitch, "operation-mode", nextMode);
    }
    el.opReceiptBlock?.classList.toggle("hidden", el.opEntryMode?.value === "debt" || el.opEntryMode?.value === "currency" || nextMode !== "receipt");
    setReceiptEnabled(nextMode === "receipt", "create");
    updateCreateCategoryFieldUi();
    renderCreateCategoryPicker();
    renderDebtCounterpartyPicker();
    updateCreatePreview();
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
    updateEditPreview();
  }
  function setCreateEntryMode(mode) {
    const nextMode = mode === "debt" ? "debt" : mode === "currency" ? "currency" : "operation";
    el.opEntryMode.value = nextMode;
    core.syncSegmentedActive(el.createEntryModeSwitch, "entry-mode", nextMode);
    const isDebt = nextMode === "debt";
    const isCurrency = nextMode === "currency";
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
    el.debtCounterparty.required = isDebt;
    el.debtPrincipal.required = isDebt;
    el.debtStartDate.required = isDebt;
    const submit = document.getElementById("submitCreateOperationBtn");
    if (isDebt) {
      if (!el.debtStartDate.value) {
        core.syncDateFieldValue(el.debtStartDate, core.getTodayIso());
      }
      renderDebtCounterpartyPicker();
      if (submit) {
        submit.textContent = state.editDebtCreateId ? "Сохранить долг" : "Создать долг";
      }
    } else if (isCurrency) {
      if (el.currencyTradeDateModal && !el.currencyTradeDateModal.value) {
        core.syncDateFieldValue(el.currencyTradeDateModal, core.getTodayIso());
      }
      syncCurrencyTradeFieldUi();
      syncSuggestedCurrencyRate().catch(() => {});
      if (submit) {
        submit.textContent = "Сохранить валютную сделку";
      }
    } else if (submit) {
      submit.textContent = "Добавить";
    }
    if (!isDebt && !isCurrency) {
      updateCreateCategoryFieldUi();
      syncOperationCurrencyFields("create").catch(() => {});
    }
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

  async function openCreateModal() {
    await ensureCategoryCatalogReady("create");
    state.createFlowMode = "operation";
    state.editPlanId = null;
    state.editDebtCreateId = null;
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
    closeDebtCounterpartyPopover();
    el.debtCounterparty.value = "";
    el.debtPrincipal.value = "";
    if (el.debtCurrency) {
      el.debtCurrency.value = core.getCurrencyConfig?.().code || "BYN";
    }
    el.debtStartDate.value = "";
    el.debtDueDate.value = "";
    el.debtNote.value = "";
    if (el.currencyAsset) {
      el.currencyAsset.value = "USD";
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
    if (el.currencyUnitPrice) {
      el.currencyUnitPrice.value = "";
    }
    if (el.currencyFee) {
      el.currencyFee.value = "";
    }
    if (el.currencyNote) {
      el.currencyNote.value = "";
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
    createOperationFxRateManual = false;
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
    setDebtDirection("lend");
    setCurrencySide("buy");
    currencyUnitPriceManual = false;
    syncCurrencyTradeFieldUi();
    syncOperationCurrencyFields("create").catch(() => {});
    syncOperationCurrencyFields("edit").catch(() => {});
    applyDebtCurrencyUi();
    updateDebtDueHint();
    setCreateEntryMode("operation");
    renderCreateCategoryPicker();
    renderDebtCounterpartyPicker();
    loadReceiptTemplateHints().catch(() => {});
    renderReceiptItems();
    renderReceiptSummary();
    updateCreatePreview();
    el.createModal.classList.remove("hidden");
  }
  function closeCreateModal() {
    state.createFlowMode = "operation";
    state.editPlanId = null;
    state.editDebtCreateId = null;
    const createTitle = document.getElementById("createTitle");
    if (createTitle) {
      createTitle.textContent = "Новая операция";
    }
    el.createModal.classList.add("hidden");
  }
  async function openCreateModalForDebtEdit(payload) {
    if (!payload?.id) {
      return;
    }
    await openCreateModal();
    state.editDebtCreateId = Number(payload.id);
    if (el.createEntryModeSwitch) {
      el.createEntryModeSwitch.classList.add("hidden");
    }
    const createTitle = document.getElementById("createTitle");
    if (createTitle) {
      createTitle.textContent = "Редактировать долг";
    }
    selectDebtCounterparty(payload.counterparty || "", { keepOpen: false });
    el.debtPrincipal.value = payload.principal || "";
    if (el.debtCurrency) {
      el.debtCurrency.value = payload.currency || (core.getCurrencyConfig?.().code || "BYN");
    }
    core.syncDateFieldValue(el.debtStartDate, payload.start_date || core.getTodayIso());
    core.syncDateFieldValue(el.debtDueDate, payload.due_date || "");
    el.debtNote.value = payload.note || "";
    setDebtDirection(payload.direction || "lend");
    setCreateEntryMode("debt");
    applyDebtCurrencyUi();
    updateDebtDueHint();
    renderDebtCounterpartyPicker();
    updateCreatePreview();
  }
  async function openCreateModalForCurrency() {
    await openCreateModal();
    setCreateEntryMode("currency");
    currencyUnitPriceManual = false;
    syncSuggestedCurrencyRate({ force: true }).catch(() => {});
  }
  async function openEditModal(item) {
    await ensureCategoryCatalogReady("edit");
    state.editOperationId = item.id;
    document.getElementById("editAmount").value = item.original_amount || item.amount;
    if (el.editCurrency) {
      el.editCurrency.value = item.currency || "BYN";
    }
    if (el.editFxRate) {
      el.editFxRate.value = item.fx_rate || "1";
    }
    setOperationFxRateHint("edit", item.currency && item.currency !== (core.getCurrencyConfig?.().code || "BYN") ? "Сохранившийся курс операции" : "");
    editOperationFxRateManual = true;
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
    updateEditPreview();
    el.editModal.classList.remove("hidden");
  }
  function closeEditModal() {
    state.editOperationId = null;
    clearReceiptItems("edit");
    setEditOperationMode("common");
    closeEditCategoryPopover();
    el.editModal.classList.add("hidden");
  }
  function applySettingsUi() {
    const savedTz = state.preferences?.data?.ui?.timezone || "auto";
    if (el.timezoneSelect) {
      const hasOption = Array.from(el.timezoneSelect.options).some((opt) => opt.value === savedTz);
      el.timezoneSelect.value = hasOption ? savedTz : "auto";
    }
    applyDebtCurrencyUi();
  }
  function openPeriodCustomModal() {
    const today = core.getTodayIso();
    core.syncDateFieldValue(el.customDateTo, state.customDateTo || today);
    core.syncDateFieldValue(el.customDateFrom, state.customDateFrom || today);
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
    handleReceiptItemsListFocusIn,
    handleReceiptItemsListKeydown,
    handleReceiptItemsListClick,
    handleReceiptOutsidePointer,
    handlePullReceiptTotal,
    setReceiptEnabled,
    getCreateReceiptPayload,
    getEditReceiptPayload,
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
    getCurrencyTradeContext,
    syncSuggestedCurrencyRate,
    markCurrencyRateManual,
    resetCurrencyRateAutofill,
    applyDebtCurrencyUi,
    updateDebtDueHint,
    openCreateModal,
    openCreateModalForCurrency,
    openCreateModalForDebtEdit,
    closeCreateModal,
    openEditModal,
    closeEditModal,
    applySettingsUi,
    openPeriodCustomModal,
    closePeriodCustomModal,
  };

  window.App.operationModal = api;
  window.App.registerRuntimeModule?.("operation-modal", api);
})();
