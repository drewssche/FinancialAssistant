(() => {
  function createOperationModalFxSettlementFeature(deps) {
    const {
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
    } = deps;

    let fxSettlementQuantityDriver = false;
    let fxSettlementRateDriver = false;
    let editFxSettlementQuantityDriver = false;
    let editFxSettlementRateDriver = false;
    const fxSettlementBalanceState = {
      create: { key: "", data: null, pending: null },
      edit: { key: "", data: null, pending: null },
    };

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

  function getCreateOperationBaseContext() {
    const amountInput = document.getElementById("opAmount");
    const amountResolved = core.resolveMoneyInput(amountInput?.value || 0);
    if (!amountResolved.empty && Number(amountResolved.previewValue || 0) > 0) {
      return enrichOperationAmountContext("create", Number(amountResolved.previewValue || 0), "operation");
    }
    const receiptItems = getCreateReceiptPayload();
    if (!Array.isArray(receiptItems) || !receiptItems.length) {
      return enrichOperationAmountContext("create", 0, isCreateReceiptMode() ? "receipt" : "operation");
    }
    return enrichOperationAmountContext("create", receiptItems.reduce((sum, row) => {
        const qty = Number(row?.quantity || 0);
        const unitPrice = Number(row?.unit_price || 0);
        return sum + (qty > 0 && unitPrice > 0 ? qty * unitPrice : 0);
      }, 0), "receipt");
  }

  function getCreateOperationBaseAmountValue() {
    return getCreateOperationBaseContext().amount;
  }

  function getEditOperationBaseContext() {
    const amountInput = document.getElementById("editAmount");
    const amountResolved = core.resolveMoneyInput(amountInput?.value || 0);
    if (!amountResolved.empty && Number(amountResolved.previewValue || 0) > 0) {
      return enrichOperationAmountContext("edit", Number(amountResolved.previewValue || 0), "operation");
    }
    const receiptItems = getEditReceiptPayload();
    if (!Array.isArray(receiptItems) || !receiptItems.length) {
      return enrichOperationAmountContext("edit", 0, isEditReceiptMode() ? "receipt" : "operation");
    }
    return enrichOperationAmountContext("edit", receiptItems.reduce((sum, row) => {
        const qty = Number(row?.quantity || 0);
        const unitPrice = Number(row?.unit_price || 0);
        return sum + (qty > 0 && unitPrice > 0 ? qty * unitPrice : 0);
      }, 0), "receipt");
  }

  function enrichOperationAmountContext(mode, originalAmount, source) {
    const isEdit = mode === "edit";
    const baseCurrency = String(core.getCurrencyConfig?.().code || "BYN").toUpperCase();
    const operationCurrency = String((isEdit ? el.editCurrency : el.opCurrency)?.value || baseCurrency).toUpperCase();
    const rateState = core.resolveRateInput((isEdit ? el.editFxRate : el.opFxRate)?.value || 1, 1, 6);
    const operationRate = operationCurrency === baseCurrency ? 1 : Number(rateState.previewValue || 0);
    return {
      amount: operationRate > 0 ? originalAmount * operationRate : 0,
      originalAmount,
      operationCurrency,
      operationRate,
      source,
    };
  }

  function getEditOperationBaseAmountValue() {
    return getEditOperationBaseContext().amount;
  }

  function getFxSettlementSourceLabel(context) {
    return context?.baseSource === "receipt" ? "чека" : "операции";
  }

  function getFxSettlementSourceTitle(context) {
    return context?.baseSource === "receipt" ? "Сумма чека" : "Сумма операции";
  }

  function getFxSettlementEmptyHint(context) {
    return context?.baseSource === "receipt"
      ? "Сначала собери чек или подтяни итог"
      : "Сначала укажи сумму операции или заполни чек";
  }

  function renderFxSettlementBalance(mode, context, data = null, loading = false) {
    const node = mode === "edit" ? el.editFxSettlementBalance : el.opFxSettlementBalance;
    if (!node) {
      return;
    }
    node.removeAttribute("data-tone");
    if (loading) {
      node.textContent = "Проверяем доступный валютный остаток...";
      return;
    }
    if (!data) {
      node.textContent = "Не удалось проверить валютный остаток";
      return;
    }
    const available = Number(data.available_quantity || 0);
    const debit = Number(context.effectiveQuantity || 0);
    const projected = available - debit;
    const dateLabel = core.formatDateRu(data.as_of || "");
    node.textContent = `Доступно для списания${dateLabel ? ` на ${dateLabel}` : ""}: ${core.formatAmount(available)} ${context.assetCurrency} · После операции: ${core.formatAmount(projected)} ${context.assetCurrency}`;
    node.dataset.tone = projected < 0 ? "danger" : "positive";
  }

  async function refreshFxSettlementBalance(mode, context) {
    const isEdit = mode === "edit";
    const dateInput = document.getElementById(isEdit ? "editDate" : "opDate");
    const operationDate = core.parseDateInputValue(dateInput?.value || "");
    if (!operationDate || !context?.assetCurrency) {
      renderFxSettlementBalance(mode, context, null, false);
      return;
    }
    const excludedOperationId = isEdit ? Number(state.editOperationId || 0) : 0;
    const key = `${context.assetCurrency}|${operationDate}|${excludedOperationId}`;
    const balanceState = fxSettlementBalanceState[mode];
    if (balanceState.key === key && balanceState.data) {
      renderFxSettlementBalance(mode, context, balanceState.data, false);
      return;
    }
    if (balanceState.key === key && balanceState.pending) {
      renderFxSettlementBalance(mode, context, null, true);
      await balanceState.pending;
      renderFxSettlementBalance(mode, context, balanceState.data, false);
      return;
    }
    balanceState.key = key;
    balanceState.data = null;
    renderFxSettlementBalance(mode, context, null, true);
    const params = new URLSearchParams({
      currency: context.assetCurrency,
      as_of: operationDate,
    });
    if (excludedOperationId > 0) {
      params.set("exclude_linked_operation_id", String(excludedOperationId));
    }
    balanceState.pending = core.requestJson(`/api/v1/currency/available-balance?${params.toString()}`, {
      headers: core.authHeaders(),
    }).then((data) => {
      if (balanceState.key === key) {
        balanceState.data = data;
      }
    }).catch(() => {
      if (balanceState.key === key) {
        balanceState.data = null;
      }
    }).finally(() => {
      if (balanceState.key === key) {
        balanceState.pending = null;
      }
    });
    await balanceState.pending;
    if (balanceState.key === key) {
      renderFxSettlementBalance(mode, context, balanceState.data, false);
    }
  }

  function validateFxSettlementBalance(mode, context) {
    const data = fxSettlementBalanceState[mode]?.data;
    if (!data) {
      return;
    }
    const available = Number(data.available_quantity || 0);
    if (Number(context.effectiveQuantity || 0) > available + 0.000001) {
      throw new Error(`Недостаточно ${context.assetCurrency} для списания. Доступно: ${core.formatAmount(available)} ${context.assetCurrency}`);
    }
  }

  function getReceiptPayloadTotal(mode = "create") {
    const rows = mode === "edit" ? getEditReceiptPayload() : getCreateReceiptPayload();
    if (!Array.isArray(rows) || !rows.length) {
      return 0;
    }
    return rows.reduce((sum, row) => {
      const qty = Number(row?.quantity || 0);
      const unitPrice = Number(row?.unit_price || 0);
      return sum + (qty > 0 && unitPrice > 0 ? qty * unitPrice : 0);
    }, 0);
  }

  function forceAutofillCreateFxSettlementRate() {
    const context = getCreateFxSettlementContext();
    if (!(context.baseAmount > 0) || !(context.hasQuantity) || !(context.effectiveRate > 0) || !el.opFxSettlementUnitPrice) {
      return;
    }
    fxSettlementRateDriver = false;
    el.opFxSettlementUnitPrice.value = formatTradeRateValue(context.effectiveRate);
  }

  function forceAutofillEditFxSettlementRate() {
    const context = getEditFxSettlementContext();
    if (!(context.baseAmount > 0) || !(context.hasQuantity) || !(context.effectiveRate > 0) || !el.editFxSettlementUnitPrice) {
      return;
    }
    editFxSettlementRateDriver = false;
    el.editFxSettlementUnitPrice.value = formatTradeRateValue(context.effectiveRate);
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
      if (el.opFxSettlementBalance) {
        el.opFxSettlementBalance.textContent = "";
      }
      if (el.opFxSettlementBaseTotal) {
        el.opFxSettlementBaseTotal.textContent = "Операция не изменит валютный остаток";
      }
    }
    if (el.opCurrency) {
      el.opCurrency.disabled = false;
      el.opCurrency.title = "";
    }
  }

  function getCreateFxSettlementContext() {
    const baseCurrency = String(core.getCurrencyConfig?.().code || "BYN").toUpperCase();
    const assetCurrency = String(el.opFxSettlementAsset?.value || "USD").toUpperCase();
    const quantityResolved = core.resolveMoneyInput(el.opFxSettlementQuantity?.value || 0);
    const rateResolved = core.resolveRateInput(el.opFxSettlementUnitPrice?.value || 0, 0, 6);
    const baseContext = getCreateOperationBaseContext();
    const baseAmount = baseContext.amount;
    const enteredQuantity = Number(quantityResolved.previewValue || 0);
    const enteredRate = Number(rateResolved.previewValue || 0);
    const hasQuantity = quantityResolved.valid && enteredQuantity > 0;
    const hasRate = rateResolved.valid && enteredRate > 0;
    let effectiveQuantity = enteredQuantity;
    let effectiveRate = enteredRate;
    const directForeignSettlement = baseContext.operationCurrency !== baseCurrency
      && assetCurrency === baseContext.operationCurrency;
    if (directForeignSettlement) {
      effectiveQuantity = baseContext.originalAmount;
      effectiveRate = baseContext.operationRate;
    } else if (baseAmount > 0 && hasQuantity && fxSettlementQuantityDriver) {
      effectiveRate = baseAmount / enteredQuantity;
    } else if (baseAmount > 0 && hasRate && fxSettlementRateDriver) {
      effectiveQuantity = baseAmount / enteredRate;
    } else if (baseAmount > 0 && hasQuantity && !hasRate) {
      effectiveRate = baseAmount / enteredQuantity;
    } else if (baseAmount > 0 && !hasQuantity && hasRate) {
      effectiveQuantity = baseAmount / enteredRate;
    }
    const computedBase = effectiveQuantity > 0 && effectiveRate > 0 ? effectiveQuantity * effectiveRate : 0;
    return {
      baseCurrency,
      assetCurrency,
      baseAmount,
      originalAmount: baseContext.originalAmount,
      operationCurrency: baseContext.operationCurrency,
      operationRate: baseContext.operationRate,
      directForeignSettlement,
      receiptTotal: getReceiptPayloadTotal("create"),
      quantityResolved,
      rateResolved,
      effectiveQuantity,
      effectiveRate,
      computedBase,
      hasQuantity,
      hasRate,
      baseSource: baseContext.source,
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
        ? `${getFxSettlementSourceTitle(context)}: ${core.formatMoney(context.baseAmount, { currency: context.baseCurrency })}`
        : getFxSettlementEmptyHint(context);
    }
    if (el.opFxSettlementQuantity) {
      el.opFxSettlementQuantity.readOnly = context.directForeignSettlement;
      el.opFxSettlementQuantity.placeholder = `Списано ${context.assetCurrency}`;
      if (context.directForeignSettlement && context.effectiveQuantity > 0) {
        el.opFxSettlementQuantity.value = core.formatAmount(context.effectiveQuantity);
      } else if (!fxSettlementQuantityDriver && context.baseAmount > 0 && context.effectiveQuantity > 0 && context.hasRate) {
        el.opFxSettlementQuantity.value = core.formatAmount(context.effectiveQuantity);
      }
    }
    if (el.opFxSettlementUnitPrice) {
      el.opFxSettlementUnitPrice.readOnly = context.directForeignSettlement;
      el.opFxSettlementUnitPrice.placeholder = `Курс ${context.baseCurrency} за 1 ${context.assetCurrency}`;
      const shouldAutoFillRate = context.baseAmount > 0
        && context.effectiveRate > 0
        && context.hasQuantity
        && (
          fxSettlementQuantityDriver
          || !fxSettlementRateDriver
          || !(Number(core.resolveRateInput(el.opFxSettlementUnitPrice?.value || 0, 0, 6).previewValue || 0) > 0)
        );
      if (context.directForeignSettlement && context.effectiveRate > 0) {
        el.opFxSettlementUnitPrice.value = formatTradeRateValue(context.effectiveRate);
      } else if (shouldAutoFillRate) {
        el.opFxSettlementUnitPrice.value = formatTradeRateValue(context.effectiveRate);
      }
    }
    if (el.opFxSettlementHint) {
      if (!(context.baseAmount > 0)) {
        el.opFxSettlementHint.textContent = "Сумма списания берется из операции или из суммы чека, поэтому в валютном блоке достаточно указать количество и/или курс.";
      } else if (context.effectiveQuantity > 0 && context.effectiveRate > 0) {
        const mismatch = Math.abs(context.computedBase - context.baseAmount) >= 0.01;
        const baseHint = mismatch
          ? `Проверь связку: ${core.formatAmount(context.effectiveQuantity)} ${context.assetCurrency} по курсу ${formatTradeRateValue(context.effectiveRate)} дают ${core.formatMoney(context.computedBase, { currency: context.baseCurrency })}, а сумма ${getFxSettlementSourceLabel(context)} = ${core.formatMoney(context.baseAmount, { currency: context.baseCurrency })}.`
          : `Будет списано ${core.formatAmount(context.effectiveQuantity)} ${context.assetCurrency} по курсу ${formatTradeRateValue(context.effectiveRate)} на ${core.formatMoney(context.baseAmount, { currency: context.baseCurrency })}.`;
        const receiptMismatch = context.baseSource === "operation"
          && context.receiptTotal > 0
          && Math.abs(context.receiptTotal - context.baseAmount) >= 0.01;
        el.opFxSettlementHint.textContent = receiptMismatch
          ? `${baseHint} Сейчас расчет идет от общей суммы сверху: ${core.formatMoney(context.baseAmount, { currency: context.baseCurrency })}, а итог чека = ${core.formatMoney(context.receiptTotal, { currency: context.baseCurrency })}.`
          : baseHint;
      } else {
        const baseHint = `Укажи количество ${context.assetCurrency} или курс. Второе поле пересчитается от суммы ${getFxSettlementSourceLabel(context)} в ${context.baseCurrency}.`;
        const receiptMismatch = context.baseSource === "operation"
          && context.receiptTotal > 0
          && Math.abs(context.receiptTotal - context.baseAmount) >= 0.01;
        el.opFxSettlementHint.textContent = receiptMismatch
          ? `${baseHint} Сейчас приоритет у общей суммы сверху, а не у итога чека.`
          : baseHint;
      }
    }
    applyTradeFieldCurrency(el.opFxSettlementQuantityField, context.assetCurrency);
    applyTradeFieldCurrency(el.opFxSettlementUnitPriceField, context.baseCurrency);
    setAutoComputedField(el.opFxSettlementQuantityField, context.directForeignSettlement || (context.baseAmount > 0 && !context.hasQuantity && context.hasRate));
    setAutoComputedField(el.opFxSettlementUnitPriceField, context.directForeignSettlement || (context.baseAmount > 0 && context.hasQuantity && !context.hasRate));
    refreshFxSettlementBalance("create", context).catch(() => {});
  }

  function getCreateFxSettlementPayload() {
    if (!isCreateFxSettlementEnabled()) {
      return null;
    }
    const context = getCreateFxSettlementContext();
    if (!(context.baseAmount > 0)) {
      throw new Error(context.baseSource === "receipt"
        ? "Сначала собери чек или подтяни его итог для списания валюты"
        : "Сначала укажи сумму операции для списания валюты");
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
      throw new Error(`Сумма валютного списания должна совпадать с суммой ${getFxSettlementSourceLabel(context)}`);
    }
    validateFxSettlementBalance("create", context);
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
      if (el.editFxSettlementBalance) {
        el.editFxSettlementBalance.textContent = "";
      }
      if (el.editFxSettlementBaseTotal) {
        el.editFxSettlementBaseTotal.textContent = "Операция не изменит валютный остаток";
      }
    }
    if (el.editCurrency) {
      el.editCurrency.disabled = false;
      el.editCurrency.title = "";
    }
  }

  function getEditFxSettlementContext() {
    const baseCurrency = String(core.getCurrencyConfig?.().code || "BYN").toUpperCase();
    const assetCurrency = String(el.editFxSettlementAsset?.value || "USD").toUpperCase();
    const quantityResolved = core.resolveMoneyInput(el.editFxSettlementQuantity?.value || 0);
    const rateResolved = core.resolveRateInput(el.editFxSettlementUnitPrice?.value || 0, 0, 6);
    const baseContext = getEditOperationBaseContext();
    const baseAmount = baseContext.amount;
    const enteredQuantity = Number(quantityResolved.previewValue || 0);
    const enteredRate = Number(rateResolved.previewValue || 0);
    const hasQuantity = quantityResolved.valid && enteredQuantity > 0;
    const hasRate = rateResolved.valid && enteredRate > 0;
    let effectiveQuantity = enteredQuantity;
    let effectiveRate = enteredRate;
    const directForeignSettlement = baseContext.operationCurrency !== baseCurrency
      && assetCurrency === baseContext.operationCurrency;
    if (directForeignSettlement) {
      effectiveQuantity = baseContext.originalAmount;
      effectiveRate = baseContext.operationRate;
    } else if (baseAmount > 0 && hasQuantity && editFxSettlementQuantityDriver) {
      effectiveRate = baseAmount / enteredQuantity;
    } else if (baseAmount > 0 && hasRate && editFxSettlementRateDriver) {
      effectiveQuantity = baseAmount / enteredRate;
    } else if (baseAmount > 0 && hasQuantity && !hasRate) {
      effectiveRate = baseAmount / enteredQuantity;
    } else if (baseAmount > 0 && !hasQuantity && hasRate) {
      effectiveQuantity = baseAmount / enteredRate;
    }
    const computedBase = effectiveQuantity > 0 && effectiveRate > 0 ? effectiveQuantity * effectiveRate : 0;
    return {
      baseCurrency,
      assetCurrency,
      baseAmount,
      originalAmount: baseContext.originalAmount,
      operationCurrency: baseContext.operationCurrency,
      operationRate: baseContext.operationRate,
      directForeignSettlement,
      receiptTotal: getReceiptPayloadTotal("edit"),
      effectiveQuantity,
      effectiveRate,
      computedBase,
      hasQuantity,
      hasRate,
      baseSource: baseContext.source,
    };
  }

  function syncEditFxSettlementFieldUi() {
    syncEditFxSettlementVisibility();
    if (!isEditFxSettlementEnabled()) {
      return;
    }
    const context = getEditFxSettlementContext();
    if (el.editFxSettlementBaseTotal) {
      el.editFxSettlementBaseTotal.textContent = context.baseAmount > 0
        ? `${getFxSettlementSourceTitle(context)}: ${core.formatMoney(context.baseAmount, { currency: context.baseCurrency })}`
        : getFxSettlementEmptyHint(context);
    }
    if (el.editFxSettlementQuantity) {
      el.editFxSettlementQuantity.readOnly = context.directForeignSettlement;
      el.editFxSettlementQuantity.placeholder = `Списано ${context.assetCurrency}`;
      if (context.directForeignSettlement && context.effectiveQuantity > 0) {
        el.editFxSettlementQuantity.value = core.formatAmount(context.effectiveQuantity);
      } else if (!editFxSettlementQuantityDriver && context.baseAmount > 0 && context.effectiveQuantity > 0 && context.hasRate) {
        el.editFxSettlementQuantity.value = core.formatAmount(context.effectiveQuantity);
      }
    }
    if (el.editFxSettlementUnitPrice) {
      el.editFxSettlementUnitPrice.readOnly = context.directForeignSettlement;
      el.editFxSettlementUnitPrice.placeholder = `Курс ${context.baseCurrency} за 1 ${context.assetCurrency}`;
      const shouldAutoFillRate = context.baseAmount > 0
        && context.effectiveRate > 0
        && context.hasQuantity
        && (
          editFxSettlementQuantityDriver
          || !editFxSettlementRateDriver
          || !(Number(core.resolveRateInput(el.editFxSettlementUnitPrice?.value || 0, 0, 6).previewValue || 0) > 0)
        );
      if (context.directForeignSettlement && context.effectiveRate > 0) {
        el.editFxSettlementUnitPrice.value = formatTradeRateValue(context.effectiveRate);
      } else if (shouldAutoFillRate) {
        el.editFxSettlementUnitPrice.value = formatTradeRateValue(context.effectiveRate);
      }
    }
    if (el.editFxSettlementHint) {
      if (!(context.baseAmount > 0)) {
        el.editFxSettlementHint.textContent = "Сумма списания берется из операции или из суммы чека.";
      } else if (context.effectiveQuantity > 0 && context.effectiveRate > 0) {
        const mismatch = Math.abs(context.computedBase - context.baseAmount) >= 0.01;
        const baseHint = mismatch
          ? `Проверь связку: ${core.formatAmount(context.effectiveQuantity)} ${context.assetCurrency} по курсу ${formatTradeRateValue(context.effectiveRate)} дают ${core.formatMoney(context.computedBase, { currency: context.baseCurrency })}, а сумма ${getFxSettlementSourceLabel(context)} = ${core.formatMoney(context.baseAmount, { currency: context.baseCurrency })}.`
          : `Будет списано ${core.formatAmount(context.effectiveQuantity)} ${context.assetCurrency} на ${core.formatMoney(context.baseAmount, { currency: context.baseCurrency })}.`;
        const receiptMismatch = context.baseSource === "operation"
          && context.receiptTotal > 0
          && Math.abs(context.receiptTotal - context.baseAmount) >= 0.01;
        el.editFxSettlementHint.textContent = receiptMismatch
          ? `${baseHint} Сейчас расчет идет от общей суммы сверху: ${core.formatMoney(context.baseAmount, { currency: context.baseCurrency })}, а итог чека = ${core.formatMoney(context.receiptTotal, { currency: context.baseCurrency })}.`
          : baseHint;
      } else {
        const baseHint = `Укажи количество ${context.assetCurrency} или курс. Второе поле пересчитается от суммы ${getFxSettlementSourceLabel(context)} в ${context.baseCurrency}.`;
        const receiptMismatch = context.baseSource === "operation"
          && context.receiptTotal > 0
          && Math.abs(context.receiptTotal - context.baseAmount) >= 0.01;
        el.editFxSettlementHint.textContent = receiptMismatch
          ? `${baseHint} Сейчас приоритет у общей суммы сверху, а не у итога чека.`
          : baseHint;
      }
    }
    applyTradeFieldCurrency(el.editFxSettlementQuantityField, context.assetCurrency);
    applyTradeFieldCurrency(el.editFxSettlementUnitPriceField, context.baseCurrency);
    setAutoComputedField(el.editFxSettlementQuantityField, context.directForeignSettlement || (context.baseAmount > 0 && !context.hasQuantity && context.hasRate));
    setAutoComputedField(el.editFxSettlementUnitPriceField, context.directForeignSettlement || (context.baseAmount > 0 && context.hasQuantity && !context.hasRate));
    refreshFxSettlementBalance("edit", context).catch(() => {});
  }

  function getEditFxSettlementPayload() {
    if (!isEditFxSettlementEnabled()) {
      return null;
    }
    const context = getEditFxSettlementContext();
    if (!(context.baseAmount > 0)) {
      throw new Error(context.baseSource === "receipt"
        ? "Сначала собери чек или подтяни его итог для списания валюты"
        : "Сначала укажи сумму операции для списания валюты");
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
      throw new Error(`Сумма валютного списания должна совпадать с суммой ${getFxSettlementSourceLabel(context)}`);
    }
    validateFxSettlementBalance("edit", context);
    return {
      asset_currency: context.assetCurrency,
      quantity: core.formatAmount(context.effectiveQuantity),
      quote_total: core.formatAmount(context.baseAmount),
      unit_price: core.resolveRateInput(context.effectiveRate, 0, 6).formatted,
      note: el.editFxSettlementNote?.value?.trim() || null,
    };
  }


    function resetCreateFxSettlementDrivers() {
      fxSettlementQuantityDriver = false;
      fxSettlementRateDriver = false;
      fxSettlementBalanceState.create = { key: "", data: null, pending: null };
    }

    function resetEditFxSettlementDrivers() {
      editFxSettlementQuantityDriver = false;
      editFxSettlementRateDriver = false;
      fxSettlementBalanceState.edit = { key: "", data: null, pending: null };
    }

    function toggleCreateFxSettlement() {
      resetCreateFxSettlementDrivers();
      if (isCreateFxSettlementEnabled()) {
        const baseCurrency = String(core.getCurrencyConfig?.().code || "BYN").toUpperCase();
        const operationCurrency = String(el.opCurrency?.value || baseCurrency).toUpperCase();
        if (operationCurrency !== baseCurrency && !String(el.opFxSettlementQuantity?.value || "").trim()) {
          el.opFxSettlementAsset.value = operationCurrency;
        }
      }
      syncCreateFxSettlementFieldUi();
      updateCreatePreview();
    }

    function markFxSettlementQuantitySource() {
      fxSettlementQuantityDriver = true;
      fxSettlementRateDriver = false;
      forceAutofillCreateFxSettlementRate();
      syncCreateFxSettlementFieldUi();
      updateCreatePreview();
    }

    function markFxSettlementRateSource() {
      fxSettlementRateDriver = true;
      fxSettlementQuantityDriver = false;
      syncCreateFxSettlementFieldUi();
      updateCreatePreview();
    }

    function toggleEditFxSettlement() {
      resetEditFxSettlementDrivers();
      if (isEditFxSettlementEnabled()) {
        const baseCurrency = String(core.getCurrencyConfig?.().code || "BYN").toUpperCase();
        const operationCurrency = String(el.editCurrency?.value || baseCurrency).toUpperCase();
        if (operationCurrency !== baseCurrency && !String(el.editFxSettlementQuantity?.value || "").trim()) {
          el.editFxSettlementAsset.value = operationCurrency;
        }
      }
      syncEditFxSettlementFieldUi();
      updateEditPreview();
    }

    function markEditFxSettlementQuantitySource() {
      editFxSettlementQuantityDriver = true;
      editFxSettlementRateDriver = false;
      forceAutofillEditFxSettlementRate();
      syncEditFxSettlementFieldUi();
      updateEditPreview();
    }

    function markEditFxSettlementRateSource() {
      editFxSettlementRateDriver = true;
      editFxSettlementQuantityDriver = false;
      syncEditFxSettlementFieldUi();
      updateEditPreview();
    }

    return {
      getCreateFxSettlementPayload,
      getEditFxSettlementPayload,
      syncCreateFxSettlementFieldUi,
      syncEditFxSettlementFieldUi,
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

  window.App.registerRuntimeModule?.("operation-modal-fx-settlement-factory", createOperationModalFxSettlementFeature);
})();
