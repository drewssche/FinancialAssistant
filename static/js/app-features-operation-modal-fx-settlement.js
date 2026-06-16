(() => {
  function createOperationModalFxSettlementFeature(deps) {
    const {
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
      return { amount: Number(amountResolved.previewValue || 0), source: "operation" };
    }
    const receiptItems = getCreateReceiptPayload();
    if (!Array.isArray(receiptItems) || !receiptItems.length) {
      return { amount: 0, source: isCreateReceiptMode() ? "receipt" : "operation" };
    }
    return {
      amount: receiptItems.reduce((sum, row) => {
        const qty = Number(row?.quantity || 0);
        const unitPrice = Number(row?.unit_price || 0);
        return sum + (qty > 0 && unitPrice > 0 ? qty * unitPrice : 0);
      }, 0),
      source: "receipt",
    };
  }

  function getCreateOperationBaseAmountValue() {
    return getCreateOperationBaseContext().amount;
  }

  function getEditOperationBaseContext() {
    const amountInput = document.getElementById("editAmount");
    const amountResolved = core.resolveMoneyInput(amountInput?.value || 0);
    if (!amountResolved.empty && Number(amountResolved.previewValue || 0) > 0) {
      return { amount: Number(amountResolved.previewValue || 0), source: "operation" };
    }
    const receiptItems = getEditReceiptPayload();
    if (!Array.isArray(receiptItems) || !receiptItems.length) {
      return { amount: 0, source: isEditReceiptMode() ? "receipt" : "operation" };
    }
    return {
      amount: receiptItems.reduce((sum, row) => {
        const qty = Number(row?.quantity || 0);
        const unitPrice = Number(row?.unit_price || 0);
        return sum + (qty > 0 && unitPrice > 0 ? qty * unitPrice : 0);
      }, 0),
      source: "receipt",
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
    const baseContext = getCreateOperationBaseContext();
    const baseAmount = baseContext.amount;
    const enteredQuantity = Number(quantityResolved.previewValue || 0);
    const enteredRate = Number(rateResolved.previewValue || 0);
    const hasQuantity = quantityResolved.valid && enteredQuantity > 0;
    const hasRate = rateResolved.valid && enteredRate > 0;
    let effectiveQuantity = enteredQuantity;
    let effectiveRate = enteredRate;
    if (baseAmount > 0 && hasQuantity && fxSettlementQuantityDriver) {
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
      el.opFxSettlementQuantity.placeholder = `Списано ${context.assetCurrency}`;
      if (!fxSettlementQuantityDriver && context.baseAmount > 0 && context.effectiveQuantity > 0 && context.hasRate) {
        el.opFxSettlementQuantity.value = core.formatAmount(context.effectiveQuantity);
      }
    }
    if (el.opFxSettlementUnitPrice) {
      el.opFxSettlementUnitPrice.placeholder = `Курс ${context.baseCurrency} за 1 ${context.assetCurrency}`;
      const shouldAutoFillRate = context.baseAmount > 0
        && context.effectiveRate > 0
        && context.hasQuantity
        && (
          fxSettlementQuantityDriver
          || !fxSettlementRateDriver
          || !(Number(core.resolveRateInput(el.opFxSettlementUnitPrice?.value || 0, 0, 6).previewValue || 0) > 0)
        );
      if (shouldAutoFillRate) {
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
    setAutoComputedField(el.opFxSettlementQuantityField, context.baseAmount > 0 && !context.hasQuantity && context.hasRate);
    setAutoComputedField(el.opFxSettlementUnitPriceField, context.baseAmount > 0 && context.hasQuantity && !context.hasRate);
  }

  function getCreateFxSettlementPayload() {
    if (!isCreateFxSettlementEnabled()) {
      return null;
    }
    const context = getCreateFxSettlementContext();
    if (!(context.baseAmount > 0)) {
      throw new Error(context.baseSource === "receipt"
        ? "Сначала собери чек или подтяни его итог для оплаты с валютной карты"
        : "Сначала укажи сумму операции для оплаты с валютной карты");
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
    const baseContext = getEditOperationBaseContext();
    const baseAmount = baseContext.amount;
    const enteredQuantity = Number(quantityResolved.previewValue || 0);
    const enteredRate = Number(rateResolved.previewValue || 0);
    const hasQuantity = quantityResolved.valid && enteredQuantity > 0;
    const hasRate = rateResolved.valid && enteredRate > 0;
    let effectiveQuantity = enteredQuantity;
    let effectiveRate = enteredRate;
    if (baseAmount > 0 && hasQuantity && editFxSettlementQuantityDriver) {
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
      el.editFxSettlementQuantity.placeholder = `Списано ${context.assetCurrency}`;
      if (!editFxSettlementQuantityDriver && context.baseAmount > 0 && context.effectiveQuantity > 0 && context.hasRate) {
        el.editFxSettlementQuantity.value = core.formatAmount(context.effectiveQuantity);
      }
    }
    if (el.editFxSettlementUnitPrice) {
      el.editFxSettlementUnitPrice.placeholder = `Курс ${context.baseCurrency} за 1 ${context.assetCurrency}`;
      const shouldAutoFillRate = context.baseAmount > 0
        && context.effectiveRate > 0
        && context.hasQuantity
        && (
          editFxSettlementQuantityDriver
          || !editFxSettlementRateDriver
          || !(Number(core.resolveRateInput(el.editFxSettlementUnitPrice?.value || 0, 0, 6).previewValue || 0) > 0)
        );
      if (shouldAutoFillRate) {
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
    setAutoComputedField(el.editFxSettlementQuantityField, context.baseAmount > 0 && !context.hasQuantity && context.hasRate);
    setAutoComputedField(el.editFxSettlementUnitPriceField, context.baseAmount > 0 && context.hasQuantity && !context.hasRate);
  }

  function getEditFxSettlementPayload() {
    if (!isEditFxSettlementEnabled()) {
      return null;
    }
    const context = getEditFxSettlementContext();
    if (!(context.baseAmount > 0)) {
      throw new Error(context.baseSource === "receipt"
        ? "Сначала собери чек или подтяни его итог для оплаты с валютной карты"
        : "Сначала укажи сумму операции для оплаты с валютной карты");
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
    }

    function resetEditFxSettlementDrivers() {
      editFxSettlementQuantityDriver = false;
      editFxSettlementRateDriver = false;
    }

    function toggleCreateFxSettlement() {
      resetCreateFxSettlementDrivers();
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
