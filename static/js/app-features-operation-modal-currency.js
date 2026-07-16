(() => {
  function createOperationModalCurrencyFeature(deps) {
    const {
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
    } = deps;

    let currencyUnitPriceManual = false;
    let currencyTradeSourceField = "quantity";
    let currencyTradeRateDriver = false;
    let currencyTradeManualOrder = [];
    let currencyRateRequestSeq = 0;
    let createOperationFxRateManual = false;
    let editOperationFxRateManual = true;
    const operationFxRateRequestSeq = {
      create: 0,
      edit: 0,
    };

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
    currencyTradeManualOrder = [];
    syncCurrencyTradeFieldUi();
    await syncSuggestedCurrencyRate({ force: true }).catch(() => {});
    updateCreatePreview();
  }

  function rememberCurrencyTradeManualField(field) {
    currencyTradeManualOrder = currencyTradeManualOrder.filter((item) => item !== field);
    currencyTradeManualOrder.push(field);
    if (currencyTradeManualOrder.length > 2) {
      currencyTradeManualOrder = currencyTradeManualOrder.slice(-2);
    }
  }

  function markCurrencyQuantitySource() {
    const wasAutoComputed = el.currencyQuantityField?.classList.contains("money-input-auto");
    const rateResolved = core.resolveRateInput(el.currencyUnitPrice?.value || 0, 0, 6);
    const preserveRateDriver = currencyTradeRateDriver && rateResolved.valid && Number(rateResolved.previewValue || 0) > 0;
    if (wasAutoComputed && preserveRateDriver) {
      currencyTradeManualOrder = currencyTradeManualOrder.filter((item) => item !== "quote");
    }
    rememberCurrencyTradeManualField("quantity");
    if (wasAutoComputed && preserveRateDriver && !currencyTradeManualOrder.includes("rate")) {
      currencyTradeManualOrder = ["rate", "quantity"];
    }
    currencyTradeSourceField = "quantity";
    currencyUnitPriceManual = preserveRateDriver;
    currencyTradeRateDriver = preserveRateDriver;
    syncCurrencyTradeFieldUi();
    updateCreatePreview();
  }

  function markCurrencyQuoteSource() {
    const wasAutoComputed = el.currencyQuoteTotalField?.classList.contains("money-input-auto");
    const rateResolved = core.resolveRateInput(el.currencyUnitPrice?.value || 0, 0, 6);
    const preserveRateDriver = currencyTradeRateDriver && rateResolved.valid && Number(rateResolved.previewValue || 0) > 0;
    if (wasAutoComputed && preserveRateDriver) {
      currencyTradeManualOrder = currencyTradeManualOrder.filter((item) => item !== "quantity");
    }
    rememberCurrencyTradeManualField("quote");
    if (wasAutoComputed && preserveRateDriver && !currencyTradeManualOrder.includes("rate")) {
      currencyTradeManualOrder = ["rate", "quote"];
    }
    currencyTradeSourceField = "quote";
    currencyUnitPriceManual = preserveRateDriver;
    currencyTradeRateDriver = preserveRateDriver;
    syncCurrencyTradeFieldUi();
    updateCreatePreview();
  }

  function formatTradeRateValue(value) {
    if (core.formatRateDisplay) {
      return core.formatRateDisplay(value, 4, 6);
    }
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
    const hasUnitPrice = rateResolved.valid && enteredUnitPrice > 0;
    const hasPairInputs = hasQuantity && hasQuoteTotal;
    const pairDerivedRate = hasPairInputs ? enteredQuoteTotal / enteredQuantity : 0;
    const preferredSource = currencyTradeSourceField === "quote" ? "quote" : "quantity";
    const validManualFields = currencyTradeManualOrder.filter((field) => (
      (field === "quantity" && hasQuantity)
      || (field === "quote" && hasQuoteTotal)
      || (field === "rate" && hasUnitPrice)
    ));
    const manualPairKey = validManualFields.length >= 2 ? validManualFields.slice(-2).sort().join(":") : "";
    const derivedRateFromAmounts = hasPairInputs && (manualPairKey === "quantity:quote" || !hasUnitPrice);
    const derivedQuantityFromQuoteAndRate = hasQuoteTotal && hasUnitPrice && manualPairKey === "quote:rate";
    const derivedQuoteFromQuantityAndRate = hasQuantity && hasUnitPrice && manualPairKey === "quantity:rate";
    const effectiveRateResolved = derivedRateFromAmounts
      ? core.resolveRateInput(pairDerivedRate, 0, 6)
      : rateResolved;
    const resolvedSource = derivedRateFromAmounts
      ? "pair"
      : derivedQuantityFromQuoteAndRate
        ? "quote"
        : derivedQuoteFromQuantityAndRate
          ? "quantity"
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
    el.currencyUnitPrice.value = formatTradeRateValue(currentRate.rate || 0);
    syncCurrencyTradeFieldUi();
    updateCreatePreview();
  }

  function markCurrencyRateManual() {
    const wasAutoComputed = el.currencyUnitPriceField?.classList.contains("money-input-auto");
    if (wasAutoComputed) {
      currencyTradeManualOrder = currencyTradeManualOrder.filter((item) => item !== "quote");
    }
    rememberCurrencyTradeManualField("rate");
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
    const cfg = core.resolveCurrencyConfig?.(currencyCode || "BYN", "suffix") || { symbol: "BYN", position: "suffix" };
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

  const createOperationModalFxSettlementFeature = window.App.getRuntimeModule?.("operation-modal-fx-settlement-factory");
  const fxSettlement = createOperationModalFxSettlementFeature
      ? createOperationModalFxSettlementFeature({
      state,
      el,
      core,
      updateCreatePreview,
      updateEditPreview,
      getCreateReceiptPayload,
      getEditReceiptPayload,
      isCreateReceiptMode,
      isEditReceiptMode,
      formatTradeRateValue,
      applyTradeFieldCurrency,
      setAutoComputedField,
    })
    : {};
  const getCreateFxSettlementPayload = fxSettlement.getCreateFxSettlementPayload || (() => null);
  const getEditFxSettlementPayload = fxSettlement.getEditFxSettlementPayload || (() => null);
  const syncCreateFxSettlementFieldUi = fxSettlement.syncCreateFxSettlementFieldUi || (() => {});
  const syncEditFxSettlementFieldUi = fxSettlement.syncEditFxSettlementFieldUi || (() => {});
  const resetCreateFxSettlementDrivers = fxSettlement.resetCreateFxSettlementDrivers || (() => {});
  const resetEditFxSettlementDrivers = fxSettlement.resetEditFxSettlementDrivers || (() => {});
  const toggleCreateFxSettlement = fxSettlement.toggleCreateFxSettlement || (() => {});
  const markFxSettlementQuantitySource = fxSettlement.markFxSettlementQuantitySource || (() => {});
  const markFxSettlementRateSource = fxSettlement.markFxSettlementRateSource || (() => {});
  const toggleEditFxSettlement = fxSettlement.toggleEditFxSettlement || (() => {});
  const markEditFxSettlementQuantitySource = fxSettlement.markEditFxSettlementQuantitySource || (() => {});
  const markEditFxSettlementRateSource = fxSettlement.markEditFxSettlementRateSource || (() => {});

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
      fxRateInput.value = formatTradeRateValue(currentRate.rate || 0);
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
        fxRateInput.value = formatTradeRateValue(latestCurrentRate.rate || 0);
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
    fxRateInput.value = formatTradeRateValue(rateRow.rate || 0);
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
      } else if (isEdit && isOperationFxRateManual(mode)) {
        // Opening an existing operation must preserve its historical rate.
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
      const cfg = core.resolveCurrencyConfig?.(currency, "suffix") || { symbol: "BYN" };
      node.dataset.currencySymbol = cfg.symbol || currency;
      node.classList.remove("money-input-no-suffix", "currency-prefix");
      node.classList.add("currency-suffix");
    }
    core.applyMoneyInputs();
  }

    function setCurrencyTradeState(nextState = {}) {
      if (Object.prototype.hasOwnProperty.call(nextState, "unitPriceManual")) {
        currencyUnitPriceManual = Boolean(nextState.unitPriceManual);
      }
      if (Object.prototype.hasOwnProperty.call(nextState, "sourceField")) {
        currencyTradeSourceField = nextState.sourceField === "quote" ? "quote" : "quantity";
      }
      if (Object.prototype.hasOwnProperty.call(nextState, "rateDriver")) {
        currencyTradeRateDriver = Boolean(nextState.rateDriver);
      }
      if (Array.isArray(nextState.manualOrder)) {
        currencyTradeManualOrder = nextState.manualOrder.slice(-2);
      }
    }

    function resetCurrencyTradeState() {
      currencyUnitPriceManual = false;
      currencyTradeSourceField = "quantity";
      currencyTradeRateDriver = false;
      currencyTradeManualOrder = [];
    }


    return {
      setCurrencySide,
      markCurrencyQuantitySource,
      markCurrencyQuoteSource,
      formatTradeRateValue,
      setAutoComputedField,
      getCurrencyTradeContext,
      syncSuggestedCurrencyRate,
      markCurrencyRateManual,
      resetCurrencyRateAutofill,
      syncCurrencyTradeFieldUi,
      getCreateFxSettlementPayload,
      getEditFxSettlementPayload,
      syncCreateFxSettlementFieldUi,
      syncEditFxSettlementFieldUi,
      buildSelectableCurrencyList,
      populateCurrencySelect,
      syncSelectableCurrencyFields,
      setOperationFxRateManual,
      setOperationFxRateHint,
      getOperationCurrencyContext,
      syncSuggestedOperationFxRate,
      syncOperationCurrencyFields,
      applyDebtCurrencyUi,
      setCurrencyTradeState,
      resetCurrencyTradeState,
      resetCreateFxSettlementDrivers,
      resetEditFxSettlementDrivers,
      toggleCreateFxSettlement,
      markFxSettlementQuantitySource,
      markFxSettlementRateSource,
      toggleEditFxSettlement,
      markEditFxSettlementQuantitySource,
      markEditFxSettlementRateSource,
    };
  }

  window.App.registerRuntimeModule?.("operation-modal-currency-factory", createOperationModalCurrencyFeature);
})();
