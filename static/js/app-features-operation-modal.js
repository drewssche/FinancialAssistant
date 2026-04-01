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
  let currencyTradeSourceField = "quantity";
  let currencyTradeRateDriver = false;
  let fxSettlementQuantityDriver = false;
  let fxSettlementRateDriver = false;
  let editFxSettlementQuantityDriver = false;
  let editFxSettlementRateDriver = false;
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
    currencyTradeSourceField = "quantity";
    currencyTradeRateDriver = false;
    syncCurrencyTradeFieldUi();
    await syncSuggestedCurrencyRate({ force: true }).catch(() => {});
    updateCreatePreview();
  }

  function markCurrencyQuantitySource() {
    const rateResolved = core.resolveRateInput(el.currencyUnitPrice?.value || 0, 0, 6);
    const preserveRateDriver = rateResolved.valid && Number(rateResolved.previewValue || 0) > 0;
    currencyTradeSourceField = "quantity";
    currencyUnitPriceManual = preserveRateDriver;
    currencyTradeRateDriver = preserveRateDriver;
    syncCurrencyTradeFieldUi();
    updateCreatePreview();
  }

  function markCurrencyQuoteSource() {
    const rateResolved = core.resolveRateInput(el.currencyUnitPrice?.value || 0, 0, 6);
    const preserveRateDriver = rateResolved.valid && Number(rateResolved.previewValue || 0) > 0;
    currencyTradeSourceField = "quote";
    currencyUnitPriceManual = preserveRateDriver;
    currencyTradeRateDriver = preserveRateDriver;
    syncCurrencyTradeFieldUi();
    updateCreatePreview();
  }

  function formatTradeRateValue(value) {
    const numeric = Number(value || 0);
    if (!(numeric > 0)) {
      return "";
    }
    const fixed = numeric.toFixed(6);
    const [whole, fraction = ""] = fixed.split(".");
    const trimmedFraction = fraction.replace(/0+$/, "");
    const nextFraction = trimmedFraction.length >= 4 ? trimmedFraction : fraction.slice(0, 4);
    return `${whole}.${nextFraction}`;
  }

  function getCurrencyTradeContext() {
    const side = el.currencySide?.value === "sell" ? "sell" : "buy";
    const assetCurrency = String(el.currencyAsset?.value || "USD").toUpperCase();
    const quoteCurrency = String(el.currencyQuote?.value || (core.getCurrencyConfig?.().code || "BYN")).toUpperCase();
    const assetLabel = core.formatCurrencyLabel?.(assetCurrency) || assetCurrency;
    const quoteLabel = core.formatCurrencyLabel?.(quoteCurrency) || quoteCurrency;
    const quantityResolved = core.resolveMoneyInput(el.currencyQuantity?.value || 0);
    const quoteResolved = core.resolveMoneyInput(el.currencyQuoteTotal?.value || 0);
    const rateResolved = core.resolveRateInput(el.currencyUnitPrice?.value || 0, 0, 6);
    const enteredQuantity = Number(quantityResolved.previewValue || 0);
    const enteredQuoteTotal = Number(quoteResolved.previewValue || 0);
    const enteredUnitPrice = Number(rateResolved.previewValue || 0);
    const hasQuantity = quantityResolved.valid && enteredQuantity > 0;
    const hasQuoteTotal = quoteResolved.valid && enteredQuoteTotal > 0;
    const hasPairInputs = hasQuantity && hasQuoteTotal;
    const pairDerivedRate = hasPairInputs ? enteredQuoteTotal / enteredQuantity : 0;
    const preferredSource = currencyTradeSourceField === "quote" ? "quote" : "quantity";
    const derivedRateFromAmounts = hasPairInputs && (!rateResolved.valid || enteredUnitPrice <= 0);
    const effectiveRateResolved = derivedRateFromAmounts
      ? core.resolveRateInput(pairDerivedRate, 0, 6)
      : rateResolved;
    const resolvedSource = derivedRateFromAmounts
      ? "pair"
      : hasQuoteTotal && !hasQuantity
        ? "quote"
        : hasQuantity && !hasQuoteTotal
          ? "quantity"
          : preferredSource;
    const unitPrice = Number(effectiveRateResolved.previewValue || enteredUnitPrice || 0);
    const effectiveQuantity = resolvedSource === "quote" && unitPrice > 0
      ? enteredQuoteTotal / unitPrice
      : enteredQuantity;
    const estimatedQuoteTotal = resolvedSource === "quote"
      ? enteredQuoteTotal
      : resolvedSource === "pair"
        ? enteredQuoteTotal
        : effectiveQuantity * unitPrice;
    return {
      side,
      assetCurrency,
      quoteCurrency,
      assetLabel,
      quoteLabel,
      quantityResolved,
      quoteResolved,
      rateResolved: effectiveRateResolved,
      enteredQuantity,
      enteredQuoteTotal,
      unitPrice,
      effectiveQuantity,
      estimatedQuoteTotal,
      derivedRateFromAmounts,
      sourceField: resolvedSource,
      amountLabel: side === "buy" ? `Покупаю ${assetLabel}` : `Продаю ${assetLabel}`,
      quoteAmountLabel: side === "buy" ? `Плачу ${quoteLabel}` : `Получаю ${quoteLabel}`,
      amountSuffixCurrency: assetCurrency,
      amountColumnLabel: "Количество",
      amountPreviewText: core.formatAmount(effectiveQuantity || 0),
      directionLabel: side === "sell"
        ? `${assetLabel} → ${quoteCurrency}`
        : `${quoteCurrency} → ${assetLabel}`,
      unitPriceLabel: `Курс ${quoteCurrency} за 1 ${assetCurrency}`,
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
    if (requestSeq !== currencyRateRequestSeq || currencyUnitPriceManual || currencyTradeRateDriver) {
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
    const rateResolved = core.resolveRateInput(el.currencyUnitPrice?.value || 0, 0, 6);
    const hasValidRate = rateResolved.valid && Number(rateResolved.previewValue || 0) > 0;
    currencyUnitPriceManual = hasValidRate;
    currencyTradeRateDriver = hasValidRate;
    syncCurrencyTradeFieldUi();
    updateCreatePreview();
  }

  function resetCurrencyRateAutofill() {
    currencyUnitPriceManual = false;
    currencyTradeRateDriver = false;
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

  function setAutoComputedField(node, enabled) {
    if (!node) {
      return;
    }
    node.classList.toggle("money-input-auto", Boolean(enabled));
    if (enabled) {
      node.setAttribute("data-auto-badge", "AUTO");
      node.setAttribute("title", "Поле рассчитывается автоматически");
    } else {
      node.removeAttribute("data-auto-badge");
      node.removeAttribute("title");
    }
  }

  function syncCurrencyTradeFieldUi() {
    const context = getCurrencyTradeContext();
    if (el.createPreviewCurrencyAmountHead) {
      el.createPreviewCurrencyAmountHead.textContent = context.amountColumnLabel;
    }
    if (el.currencyQuantity) {
      if (context.sourceField === "quote" && context.unitPrice > 0) {
        el.currencyQuantity.value = context.effectiveQuantity > 0 ? core.formatAmount(context.effectiveQuantity) : "";
      } else if (context.sourceField === "quote" && context.unitPrice <= 0) {
        el.currencyQuantity.value = "";
      }
      el.currencyQuantity.placeholder = context.amountLabel;
      el.currencyQuantity.setAttribute("aria-label", context.amountLabel);
      el.currencyQuantity.title = context.amountLabel;
    }
    if (el.currencyQuoteTotal) {
      if (context.sourceField === "quantity" && context.unitPrice > 0) {
        el.currencyQuoteTotal.value = context.estimatedQuoteTotal > 0 ? core.formatAmount(context.estimatedQuoteTotal) : "";
      } else if (context.sourceField === "quantity" && context.unitPrice <= 0) {
        el.currencyQuoteTotal.value = "";
      }
      el.currencyQuoteTotal.placeholder = context.quoteAmountLabel;
      el.currencyQuoteTotal.setAttribute("aria-label", context.quoteAmountLabel);
      el.currencyQuoteTotal.title = context.quoteAmountLabel;
    }
    if (el.currencyUnitPrice) {
      if (context.sourceField === "pair" && context.unitPrice > 0) {
        el.currencyUnitPrice.value = formatTradeRateValue(context.unitPrice);
      } else if (context.sourceField === "pair" && context.unitPrice <= 0) {
        el.currencyUnitPrice.value = "";
      }
      el.currencyUnitPrice.placeholder = `Курс ${context.quoteCurrency} за 1 ${context.assetCurrency}`;
      el.currencyUnitPrice.setAttribute("aria-label", context.unitPriceLabel);
      el.currencyUnitPrice.title = context.unitPriceLabel;
    }
    if (el.currencyTradeHint) {
      const hasRate = context.unitPrice > 0;
      const hasQuantity = context.effectiveQuantity > 0;
      if (context.side === "buy") {
        const computed = hasRate && hasQuantity
          ? `Будет списано примерно ${core.formatMoney(context.estimatedQuoteTotal, { currency: context.quoteCurrency })} за ${core.formatAmount(context.effectiveQuantity)} ${context.assetCurrency}.`
          : `Можно заполнить любые две величины: количество в ${context.assetCurrency}, сумму в ${context.quoteCurrency} или курс. Третье поле пересчитается автоматически.`;
        el.currencyTradeHint.textContent = computed;
      } else {
        const computed = hasRate && hasQuantity
          ? `Будет получено примерно ${core.formatMoney(context.estimatedQuoteTotal, { currency: context.quoteCurrency })} за ${core.formatAmount(context.effectiveQuantity)} ${context.assetCurrency}.`
          : `Можно заполнить любые две величины: количество в ${context.assetCurrency}, сумму в ${context.quoteCurrency} или курс. Третье поле пересчитается автоматически.`;
        el.currencyTradeHint.textContent = computed;
      }
    }
    if (el.currencyAsset) {
      el.currencyAsset.setAttribute("aria-label", `Валюта сделки: ${context.assetLabel}`);
      el.currencyAsset.title = `Валюта сделки: ${context.assetLabel}`;
    }
    if (el.currencyTradeDateModal) {
      el.currencyTradeDateModal.title = "Дата валютной сделки";
    }
    if (el.currencyNote) {
      el.currencyNote.title = "Комментарий валютной сделки";
    }
    applyTradeFieldCurrency(el.currencyQuantityField, context.amountSuffixCurrency);
    applyTradeFieldCurrency(el.currencyQuoteTotalField, context.quoteCurrency);
    applyTradeFieldCurrency(el.currencyUnitPriceField, context.quoteCurrency);
    setAutoComputedField(el.currencyQuantityField, context.sourceField === "quote" && context.unitPrice > 0);
    setAutoComputedField(el.currencyQuoteTotalField, context.sourceField === "quantity" && context.unitPrice > 0);
    setAutoComputedField(el.currencyUnitPriceField, context.sourceField === "pair" && context.unitPrice > 0);
  }

  function isCreateFxSettlementEnabled() {
    return el.opUseFxSettlement?.checked === true;
  }

  function syncFxSettlementToggleUi(mode) {
    const isEdit = mode === "edit";
    const input = isEdit ? el.editUseFxSettlement : el.opUseFxSettlement;
    const toggle = isEdit ? el.editFxSettlementToggle : el.opFxSettlementToggle;
    const stateNode = isEdit ? el.editFxSettlementState : el.opFxSettlementState;
    const enabled = input?.checked === true;
    if (toggle) {
      toggle.classList.toggle("is-on", enabled);
      toggle.classList.toggle("is-off", !enabled);
      toggle.setAttribute("aria-checked", enabled ? "true" : "false");
    }
    if (stateNode) {
      stateNode.textContent = enabled ? "Вкл" : "Выкл";
    }
  }

  function getCreateOperationBaseAmountValue() {
    const amountResolved = core.resolveMoneyInput(el.opAmount?.value || 0);
    if (amountResolved.valid && Number(amountResolved.previewValue || 0) > 0) {
      return Number(amountResolved.previewValue || 0);
    }
    const receiptItems = getCreateReceiptPayload();
    if (!Array.isArray(receiptItems) || !receiptItems.length) {
      return 0;
    }
    return receiptItems.reduce((sum, row) => {
      const qty = Number(row?.quantity || 0);
      const unitPrice = Number(row?.unit_price || 0);
      return sum + (qty > 0 && unitPrice > 0 ? qty * unitPrice : 0);
    }, 0);
  }

  function syncCreateFxSettlementVisibility() {
    const isOperationEntry = el.opEntryMode?.value === "operation";
    const isExpense = el.opKind?.value === "expense";
    const shouldShowBlock = isOperationEntry && isExpense;
    el.opFxSettlementBlock?.classList.toggle("hidden", !shouldShowBlock);
    if (!shouldShowBlock && el.opUseFxSettlement) {
      el.opUseFxSettlement.checked = false;
    }
    const enabled = shouldShowBlock && isCreateFxSettlementEnabled();
    el.opFxSettlementFields?.classList.toggle("hidden", !enabled);
    syncFxSettlementToggleUi("create");
    if (!enabled) {
      setAutoComputedField(el.opFxSettlementQuantityField, false);
      setAutoComputedField(el.opFxSettlementUnitPriceField, false);
    }
    if (el.opCurrency) {
      if (enabled) {
        el.opCurrency.value = String(core.getCurrencyConfig?.().code || "BYN").toUpperCase();
        el.opCurrency.disabled = true;
        el.opCurrency.title = "При оплате с валютной карты операция фиксируется в базовой валюте";
      } else {
        el.opCurrency.disabled = false;
        el.opCurrency.title = "";
      }
    }
  }

  function getCreateFxSettlementContext() {
    const baseCurrency = String(core.getCurrencyConfig?.().code || "BYN").toUpperCase();
    const assetCurrency = String(el.opFxSettlementAsset?.value || "USD").toUpperCase();
    const quantityResolved = core.resolveMoneyInput(el.opFxSettlementQuantity?.value || 0);
    const rateResolved = core.resolveRateInput(el.opFxSettlementUnitPrice?.value || 0, 0, 6);
    const baseAmount = getCreateOperationBaseAmountValue();
    const enteredQuantity = Number(quantityResolved.previewValue || 0);
    const enteredRate = Number(rateResolved.previewValue || 0);
    const hasQuantity = quantityResolved.valid && enteredQuantity > 0;
    const hasRate = rateResolved.valid && enteredRate > 0;
    let effectiveQuantity = enteredQuantity;
    let effectiveRate = enteredRate;
    if (baseAmount > 0 && hasQuantity && !hasRate) {
      effectiveRate = baseAmount / enteredQuantity;
    } else if (baseAmount > 0 && !hasQuantity && hasRate) {
      effectiveQuantity = baseAmount / enteredRate;
    }
    const computedBase = effectiveQuantity > 0 && effectiveRate > 0 ? effectiveQuantity * effectiveRate : 0;
    return {
      baseCurrency,
      assetCurrency,
      baseAmount,
      quantityResolved,
      rateResolved,
      effectiveQuantity,
      effectiveRate,
      computedBase,
      hasQuantity,
      hasRate,
    };
  }

  function syncCreateFxSettlementFieldUi() {
    syncCreateFxSettlementVisibility();
    if (!isCreateFxSettlementEnabled()) {
      return;
    }
    const context = getCreateFxSettlementContext();
    if (el.opFxSettlementBaseTotal) {
      el.opFxSettlementBaseTotal.textContent = context.baseAmount > 0
        ? `Сумма операции: ${core.formatMoney(context.baseAmount, { currency: context.baseCurrency })}`
        : "Сначала укажи сумму операции или заполни чек";
    }
    if (el.opFxSettlementQuantity) {
      el.opFxSettlementQuantity.placeholder = `Списано ${context.assetCurrency}`;
      if (!fxSettlementQuantityDriver && context.baseAmount > 0 && context.effectiveQuantity > 0 && context.hasRate) {
        el.opFxSettlementQuantity.value = core.formatAmount(context.effectiveQuantity);
      }
    }
    if (el.opFxSettlementUnitPrice) {
      el.opFxSettlementUnitPrice.placeholder = `Курс ${context.baseCurrency} за 1 ${context.assetCurrency}`;
      if (!fxSettlementRateDriver && context.baseAmount > 0 && context.effectiveRate > 0 && context.hasQuantity) {
        el.opFxSettlementUnitPrice.value = formatTradeRateValue(context.effectiveRate);
      }
    }
    if (el.opFxSettlementHint) {
      if (!(context.baseAmount > 0)) {
        el.opFxSettlementHint.textContent = "Сумма списания берется из операции или из суммы чека, поэтому в валютном блоке достаточно указать количество и/или курс.";
      } else if (context.effectiveQuantity > 0 && context.effectiveRate > 0) {
        const mismatch = Math.abs(context.computedBase - context.baseAmount) >= 0.01;
        el.opFxSettlementHint.textContent = mismatch
          ? `Проверь связку: ${core.formatAmount(context.effectiveQuantity)} ${context.assetCurrency} по курсу ${formatTradeRateValue(context.effectiveRate)} дают ${core.formatMoney(context.computedBase, { currency: context.baseCurrency })}, а операция = ${core.formatMoney(context.baseAmount, { currency: context.baseCurrency })}.`
          : `Будет списано ${core.formatAmount(context.effectiveQuantity)} ${context.assetCurrency} по курсу ${formatTradeRateValue(context.effectiveRate)} на ${core.formatMoney(context.baseAmount, { currency: context.baseCurrency })}.`;
      } else {
        el.opFxSettlementHint.textContent = `Укажи количество ${context.assetCurrency} или курс. Второе поле пересчитается от суммы операции в ${context.baseCurrency}.`;
      }
    }
    applyTradeFieldCurrency(el.opFxSettlementQuantityField, context.assetCurrency);
    applyTradeFieldCurrency(el.opFxSettlementUnitPriceField, context.baseCurrency);
    setAutoComputedField(el.opFxSettlementQuantityField, context.baseAmount > 0 && !context.hasQuantity && context.hasRate);
    setAutoComputedField(el.opFxSettlementUnitPriceField, context.baseAmount > 0 && context.hasQuantity && !context.hasRate);
  }

  function getCreateFxSettlementPayload() {
    if (!isCreateFxSettlementEnabled()) {
      return null;
    }
    const context = getCreateFxSettlementContext();
    if (!(context.baseAmount > 0)) {
      throw new Error("Сначала укажи сумму операции для оплаты с валютной карты");
    }
    if (!(context.effectiveQuantity > 0)) {
      throw new Error(`Проверь количество списания в ${context.assetCurrency}`);
    }
    if (!(context.effectiveRate > 0)) {
      throw new Error("Проверь курс валютного списания");
    }
    const computedBase = Number((context.effectiveQuantity * context.effectiveRate).toFixed(2));
    const baseAmount = Number(context.baseAmount.toFixed(2));
    if (Math.abs(computedBase - baseAmount) >= 0.01) {
      throw new Error("Сумма валютного списания должна совпадать с суммой операции");
    }
    return {
      asset_currency: context.assetCurrency,
      quantity: core.formatAmount(context.effectiveQuantity),
      quote_total: core.formatAmount(context.baseAmount),
      unit_price: core.resolveRateInput(context.effectiveRate, 0, 6).formatted,
      note: el.opFxSettlementNote?.value?.trim() || null,
    };
  }

  function isEditFxSettlementEnabled() {
    return el.editUseFxSettlement?.checked === true;
  }

  function getEditOperationBaseAmountValue() {
    const amountResolved = core.resolveMoneyInput(el.editAmount?.value || 0);
    if (amountResolved.valid && Number(amountResolved.previewValue || 0) > 0) {
      return Number(amountResolved.previewValue || 0);
    }
    const receiptItems = getEditReceiptPayload();
    if (!Array.isArray(receiptItems) || !receiptItems.length) {
      return 0;
    }
    return receiptItems.reduce((sum, row) => {
      const qty = Number(row?.quantity || 0);
      const unitPrice = Number(row?.unit_price || 0);
      return sum + (qty > 0 && unitPrice > 0 ? qty * unitPrice : 0);
    }, 0);
  }

  function syncEditFxSettlementVisibility() {
    const isExpense = el.editKind?.value === "expense";
    const shouldShowBlock = isExpense;
    el.editFxSettlementBlock?.classList.toggle("hidden", !shouldShowBlock);
    if (!shouldShowBlock && el.editUseFxSettlement) {
      el.editUseFxSettlement.checked = false;
    }
    const enabled = shouldShowBlock && isEditFxSettlementEnabled();
    el.editFxSettlementFields?.classList.toggle("hidden", !enabled);
    syncFxSettlementToggleUi("edit");
    if (!enabled) {
      setAutoComputedField(el.editFxSettlementQuantityField, false);
      setAutoComputedField(el.editFxSettlementUnitPriceField, false);
    }
    if (el.editCurrency) {
      if (enabled) {
        el.editCurrency.value = String(core.getCurrencyConfig?.().code || "BYN").toUpperCase();
        el.editCurrency.disabled = true;
        el.editCurrency.title = "При оплате с валютной карты операция фиксируется в базовой валюте";
      } else {
        el.editCurrency.disabled = false;
        el.editCurrency.title = "";
      }
    }
  }

  function getEditFxSettlementContext() {
    const baseCurrency = String(core.getCurrencyConfig?.().code || "BYN").toUpperCase();
    const assetCurrency = String(el.editFxSettlementAsset?.value || "USD").toUpperCase();
    const quantityResolved = core.resolveMoneyInput(el.editFxSettlementQuantity?.value || 0);
    const rateResolved = core.resolveRateInput(el.editFxSettlementUnitPrice?.value || 0, 0, 6);
    const baseAmount = getEditOperationBaseAmountValue();
    const enteredQuantity = Number(quantityResolved.previewValue || 0);
    const enteredRate = Number(rateResolved.previewValue || 0);
    const hasQuantity = quantityResolved.valid && enteredQuantity > 0;
    const hasRate = rateResolved.valid && enteredRate > 0;
    let effectiveQuantity = enteredQuantity;
    let effectiveRate = enteredRate;
    if (baseAmount > 0 && hasQuantity && !hasRate) {
      effectiveRate = baseAmount / enteredQuantity;
    } else if (baseAmount > 0 && !hasQuantity && hasRate) {
      effectiveQuantity = baseAmount / enteredRate;
    }
    const computedBase = effectiveQuantity > 0 && effectiveRate > 0 ? effectiveQuantity * effectiveRate : 0;
    return { baseCurrency, assetCurrency, baseAmount, effectiveQuantity, effectiveRate, computedBase, hasQuantity, hasRate };
  }

  function syncEditFxSettlementFieldUi() {
    syncEditFxSettlementVisibility();
    if (!isEditFxSettlementEnabled()) {
      return;
    }
    const context = getEditFxSettlementContext();
    if (el.editFxSettlementBaseTotal) {
      el.editFxSettlementBaseTotal.textContent = context.baseAmount > 0
        ? `Сумма операции: ${core.formatMoney(context.baseAmount, { currency: context.baseCurrency })}`
        : "Сначала укажи сумму операции или заполни чек";
    }
    if (el.editFxSettlementQuantity) {
      el.editFxSettlementQuantity.placeholder = `Списано ${context.assetCurrency}`;
      if (!editFxSettlementQuantityDriver && context.baseAmount > 0 && context.effectiveQuantity > 0 && context.hasRate) {
        el.editFxSettlementQuantity.value = core.formatAmount(context.effectiveQuantity);
      }
    }
    if (el.editFxSettlementUnitPrice) {
      el.editFxSettlementUnitPrice.placeholder = `Курс ${context.baseCurrency} за 1 ${context.assetCurrency}`;
      if (!editFxSettlementRateDriver && context.baseAmount > 0 && context.effectiveRate > 0 && context.hasQuantity) {
        el.editFxSettlementUnitPrice.value = formatTradeRateValue(context.effectiveRate);
      }
    }
    if (el.editFxSettlementHint) {
      if (!(context.baseAmount > 0)) {
        el.editFxSettlementHint.textContent = "Сумма списания берется из операции или из суммы чека.";
      } else if (context.effectiveQuantity > 0 && context.effectiveRate > 0) {
        const mismatch = Math.abs(context.computedBase - context.baseAmount) >= 0.01;
        el.editFxSettlementHint.textContent = mismatch
          ? `Проверь связку: ${core.formatAmount(context.effectiveQuantity)} ${context.assetCurrency} по курсу ${formatTradeRateValue(context.effectiveRate)} дают ${core.formatMoney(context.computedBase, { currency: context.baseCurrency })}, а операция = ${core.formatMoney(context.baseAmount, { currency: context.baseCurrency })}.`
          : `Будет списано ${core.formatAmount(context.effectiveQuantity)} ${context.assetCurrency} на ${core.formatMoney(context.baseAmount, { currency: context.baseCurrency })}.`;
      } else {
        el.editFxSettlementHint.textContent = `Укажи количество ${context.assetCurrency} или курс. Второе поле пересчитается от суммы операции.`;
      }
    }
    applyTradeFieldCurrency(el.editFxSettlementQuantityField, context.assetCurrency);
    applyTradeFieldCurrency(el.editFxSettlementUnitPriceField, context.baseCurrency);
    setAutoComputedField(el.editFxSettlementQuantityField, context.baseAmount > 0 && !context.hasQuantity && context.hasRate);
    setAutoComputedField(el.editFxSettlementUnitPriceField, context.baseAmount > 0 && context.hasQuantity && !context.hasRate);
  }

  function getEditFxSettlementPayload() {
    if (!isEditFxSettlementEnabled()) {
      return null;
    }
    const context = getEditFxSettlementContext();
    if (!(context.baseAmount > 0)) {
      throw new Error("Сначала укажи сумму операции для оплаты с валютной карты");
    }
    if (!(context.effectiveQuantity > 0)) {
      throw new Error(`Проверь количество списания в ${context.assetCurrency}`);
    }
    if (!(context.effectiveRate > 0)) {
      throw new Error("Проверь курс валютного списания");
    }
    const computedBase = Number((context.effectiveQuantity * context.effectiveRate).toFixed(2));
    const baseAmount = Number(context.baseAmount.toFixed(2));
    if (Math.abs(computedBase - baseAmount) >= 0.01) {
      throw new Error("Сумма валютного списания должна совпадать с суммой операции");
    }
    return {
      asset_currency: context.assetCurrency,
      quantity: core.formatAmount(context.effectiveQuantity),
      quote_total: core.formatAmount(context.baseAmount),
      unit_price: core.resolveRateInput(context.effectiveRate, 0, 6).formatted,
      note: el.editFxSettlementNote?.value?.trim() || null,
    };
  }

  function buildSelectableCurrencyList(includeBase = true, preserveValue = "") {
    const baseCurrency = String(core.getCurrencyConfig?.().code || "BYN").toUpperCase();
    const source = core.getSelectableCurrencies?.({ includeBase }) || (includeBase ? [baseCurrency, "USD", "EUR"] : ["USD", "EUR"]);
    const normalized = source
      .map((item) => String(item || "").trim().toUpperCase())
      .filter(Boolean);
    const preserved = String(preserveValue || "").trim().toUpperCase();
    if (preserved && !normalized.includes(preserved)) {
      normalized.push(preserved);
    }
    return Array.from(new Set(normalized));
  }

  function populateCurrencySelect(selectNode, options = {}) {
    if (!selectNode) {
      return;
    }
    const includeBase = options.includeBase !== false;
    const preserveValue = String(options.preserveValue || selectNode.value || "").trim().toUpperCase();
    const fallbackValue = String(options.fallbackValue || "").trim().toUpperCase();
    const nextOptions = buildSelectableCurrencyList(includeBase, preserveValue);
    const nextValue = preserveValue || fallbackValue || nextOptions[0] || "";
    selectNode.innerHTML = nextOptions.map((currency) => {
      const selected = currency === nextValue ? " selected" : "";
      return `<option value="${currency}"${selected}>${core.formatCurrencyLabel(currency)}</option>`;
    }).join("");
    if (nextValue) {
      selectNode.value = nextValue;
    }
  }

  function syncSelectableCurrencyFields(preserve = {}) {
    const baseCurrency = String(core.getCurrencyConfig?.().code || "BYN").toUpperCase();
    const firstTracked = buildSelectableCurrencyList(false)[0] || "USD";
    populateCurrencySelect(el.opCurrency, {
      includeBase: true,
      preserveValue: preserve.opCurrency || el.opCurrency?.value || baseCurrency,
      fallbackValue: baseCurrency,
    });
    populateCurrencySelect(el.editCurrency, {
      includeBase: true,
      preserveValue: preserve.editCurrency || el.editCurrency?.value || baseCurrency,
      fallbackValue: baseCurrency,
    });
    populateCurrencySelect(el.debtCurrency, {
      includeBase: true,
      preserveValue: preserve.debtCurrency || el.debtCurrency?.value || baseCurrency,
      fallbackValue: baseCurrency,
    });
    populateCurrencySelect(el.currencyAsset, {
      includeBase: false,
      preserveValue: preserve.currencyAsset || el.currencyAsset?.value || firstTracked,
      fallbackValue: firstTracked,
    });
    populateCurrencySelect(el.opFxSettlementAsset, {
      includeBase: false,
      preserveValue: preserve.opFxSettlementAsset || el.opFxSettlementAsset?.value || firstTracked,
      fallbackValue: firstTracked,
    });
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
    const fxRateState = core.resolveRateInput(fxRateInput?.value || 1, 1, 6);
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
    syncCreateFxSettlementFieldUi();
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
    syncEditFxSettlementFieldUi();
    updateEditPreview();
  }
  async function setCreateEntryMode(mode) {
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
      await syncSuggestedCurrencyRate().catch(() => {});
      if (submit) {
        submit.textContent = state.editCurrencyTradeId ? "Сохранить валютную сделку" : "Создать валютную сделку";
      }
    } else if (submit) {
      submit.textContent = "Добавить";
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
    syncSelectableCurrencyFields();
    if (el.debtCurrency) {
      el.debtCurrency.value = core.getCurrencyConfig?.().code || "BYN";
    }
    el.debtStartDate.value = "";
    el.debtDueDate.value = "";
    el.debtNote.value = "";
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
    await setCurrencySide("buy");
    currencyUnitPriceManual = false;
    currencyTradeSourceField = "quantity";
    currencyTradeRateDriver = false;
    fxSettlementQuantityDriver = false;
    fxSettlementRateDriver = false;
    syncCurrencyTradeFieldUi();
    syncCreateFxSettlementFieldUi();
    syncOperationCurrencyFields("create").catch(() => {});
    syncOperationCurrencyFields("edit").catch(() => {});
    applyDebtCurrencyUi();
    updateDebtDueHint();
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
    state.createFlowMode = "operation";
    state.editPlanId = null;
    state.editDebtCreateId = null;
    state.editCurrencyTradeId = null;
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
    await openCreateModal({ entryMode: "debt" });
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
    syncSelectableCurrencyFields({ debtCurrency: payload.currency || "" });
    if (el.debtCurrency) {
      el.debtCurrency.value = payload.currency || (core.getCurrencyConfig?.().code || "BYN");
    }
    core.syncDateFieldValue(el.debtStartDate, payload.start_date || core.getTodayIso());
    core.syncDateFieldValue(el.debtDueDate, payload.due_date || "");
    el.debtNote.value = payload.note || "";
    setDebtDirection(payload.direction || "lend");
    applyDebtCurrencyUi();
    updateDebtDueHint();
    renderDebtCounterpartyPicker();
    updateCreatePreview();
  }
  async function openCreateModalForCurrency() {
    await openCreateModal({ entryMode: "currency" });
    currencyUnitPriceManual = false;
    currencyTradeRateDriver = false;
    syncCurrencyTradeFieldUi();
    updateCreatePreview();
  }
  async function openCreateModalForCurrencyEdit(payload) {
    if (!payload?.id) {
      return;
    }
    await openCreateModal({ entryMode: "currency" });
    state.editCurrencyTradeId = Number(payload.id);
    if (el.createEntryModeSwitch) {
      el.createEntryModeSwitch.classList.add("hidden");
    }
    const createTitle = document.getElementById("createTitle");
    if (createTitle) {
      createTitle.textContent = "Редактировать валютную сделку";
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
    currencyTradeSourceField = "quantity";
    currencyUnitPriceManual = true;
    currencyTradeRateDriver = false;
    syncCurrencyTradeFieldUi();
    updateCreatePreview();
  }
  async function openEditModal(item) {
    await ensureCategoryCatalogReady("edit");
    state.editOperationId = item.id;
    document.getElementById("editAmount").value = item.original_amount || item.amount;
    syncSelectableCurrencyFields({ editCurrency: item.currency || "" });
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
    editFxSettlementQuantityDriver = false;
    editFxSettlementRateDriver = false;
    syncEditFxSettlementFieldUi();
    updateEditPreview();
    el.editModal.classList.remove("hidden");
  }
  function closeEditModal() {
    state.editOperationId = null;
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
    editFxSettlementQuantityDriver = false;
    editFxSettlementRateDriver = false;
    closeEditCategoryPopover();
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
    toggleCreateFxSettlement: () => {
      fxSettlementQuantityDriver = false;
      fxSettlementRateDriver = false;
      syncCreateFxSettlementFieldUi();
      updateCreatePreview();
    },
    markFxSettlementQuantitySource: () => {
      fxSettlementQuantityDriver = true;
      fxSettlementRateDriver = false;
      syncCreateFxSettlementFieldUi();
      updateCreatePreview();
    },
    markFxSettlementRateSource: () => {
      fxSettlementRateDriver = true;
      fxSettlementQuantityDriver = false;
      syncCreateFxSettlementFieldUi();
      updateCreatePreview();
    },
    toggleEditFxSettlement: () => {
      editFxSettlementQuantityDriver = false;
      editFxSettlementRateDriver = false;
      syncEditFxSettlementFieldUi();
      updateEditPreview();
    },
    markEditFxSettlementQuantitySource: () => {
      editFxSettlementQuantityDriver = true;
      editFxSettlementRateDriver = false;
      syncEditFxSettlementFieldUi();
      updateEditPreview();
    },
    markEditFxSettlementRateSource: () => {
      editFxSettlementRateDriver = true;
      editFxSettlementQuantityDriver = false;
      syncEditFxSettlementFieldUi();
      updateEditPreview();
    },
    applyDebtCurrencyUi,
    updateDebtDueHint,
    openCreateModal,
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

  window.App.operationModal = api;
  window.App.registerRuntimeModule?.("operation-modal", api);
})();
