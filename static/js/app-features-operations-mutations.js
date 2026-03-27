(() => {
  function createOperationsMutationFeature(deps) {
    const {
      state,
      el,
      core,
      categoryActions,
      trackCategoryUsage,
      renderCreateCategoryPicker,
      updateCreatePreview,
      getCreateReceiptPayload,
      getEditReceiptPayload,
      closeCreateModal,
      closeEditModal,
      loadOperations,
      loadDashboard,
      loadDashboardOperations,
      loadDebtsCards,
      loadItemCatalog,
      invalidateAllTimeAnchor,
    } = deps;
    function getDashboardData() {
      return window.App.getRuntimeModule?.("dashboard-data") || {};
    }

    function getActions() {
      return window.App.actions || {};
    }

    function getAnalyticsFeature() {
      return window.App.getRuntimeModule?.("analytics") || {};
    }

    function isSectionVisible(section) {
      return state.activeSection === section;
    }

    async function refreshAfterOperationMutation() {
      const tasks = [loadOperations({ reset: true })];
      const analyticsFeature = getAnalyticsFeature();
      const currencyFeature = window.App.getRuntimeModule?.("currency") || {};
      if (isSectionVisible("dashboard")) {
        tasks.push(loadDashboard(), loadDashboardOperations());
        if (analyticsFeature.loadDashboardAnalyticsPreview) {
          tasks.push(analyticsFeature.loadDashboardAnalyticsPreview({ force: true }));
        }
      }
      if (isSectionVisible("currency") && currencyFeature.loadCurrencySection) {
        tasks.push(currencyFeature.loadCurrencySection({ force: true }));
      }
      if (isSectionVisible("analytics") && analyticsFeature.loadAnalyticsSection) {
        tasks.push(analyticsFeature.loadAnalyticsSection({ force: true }));
      }
      await Promise.all(tasks);
    }

    async function refreshAfterDebtMutation() {
      const tasks = [];
      const analyticsFeature = getAnalyticsFeature();
      if (isSectionVisible("debts") || isSectionVisible("dashboard")) {
        tasks.push(loadDebtsCards());
      }
      if (isSectionVisible("dashboard")) {
        tasks.push(loadDashboard());
        if (analyticsFeature.loadDashboardAnalyticsPreview) {
          tasks.push(analyticsFeature.loadDashboardAnalyticsPreview({ force: true }));
        }
      }
      if (isSectionVisible("analytics") && analyticsFeature.loadAnalyticsSection) {
        tasks.push(analyticsFeature.loadAnalyticsSection({ force: true }));
      }
      if (!tasks.length) {
        return;
      }
      await Promise.all(tasks);
    }

    function validateOperationPayload(options = {}) {
      const {
        mode = "create",
        kind,
        categoryId,
        amountInputId,
        dateInputId,
        noteInputId,
        receiptPayloadGetter,
        currencySelectId,
        fxRateInputId,
      } = options;
      const operationDate = core.parseDateInputValue(document.getElementById(dateInputId).value);
      if (!operationDate) {
        throw new Error("Проверь дату операции");
      }
      const receiptItems = receiptPayloadGetter ? receiptPayloadGetter() : [];
      const amount = core.resolveMoneyInput(document.getElementById(amountInputId).value);
      const currency = String(document.getElementById(currencySelectId)?.value || (core.getCurrencyConfig?.().code || "BYN")).toUpperCase();
      const fxRate = core.resolveMoneyInput(document.getElementById(fxRateInputId)?.value || 1);
      const baseCurrency = core.getCurrencyConfig?.().code || "BYN";
      const hasReceiptItems = receiptItems.length > 0;
      const canDeriveAmountFromReceipt = hasReceiptItems && amount.empty;
      if (!canDeriveAmountFromReceipt && (!amount.valid || amount.value <= 0)) {
        throw new Error("Проверь сумму операции");
      }
      if (currency !== baseCurrency && (!fxRate.valid || fxRate.value <= 0)) {
        throw new Error("Проверь курс конверсии");
      }
      return {
        kind,
        category_id: categoryId,
        amount: canDeriveAmountFromReceipt ? null : amount.formatted,
        currency,
        fx_rate: currency === baseCurrency ? null : fxRate.formatted,
        operation_date: operationDate,
        note: document.getElementById(noteInputId).value,
        receipt_items: receiptItems,
        _mode: mode,
      };
    }

    function getValidatedCreateOperationPayload() {
      const payload = validateOperationPayload({
        mode: "create",
        kind: el.opKind.value,
        categoryId: el.opCategory.value ? Number(el.opCategory.value) : null,
        amountInputId: "opAmount",
        dateInputId: "opDate",
        noteInputId: "opNote",
        receiptPayloadGetter: getCreateReceiptPayload,
        currencySelectId: "opCurrency",
        fxRateInputId: "opFxRate",
      });
      delete payload._mode;
      return payload;
    }

    function getValidatedUpdateOperationPayload() {
      const payload = validateOperationPayload({
        mode: "edit",
        kind: el.editKind.value,
        categoryId: el.editCategory.value ? Number(el.editCategory.value) : null,
        amountInputId: "editAmount",
        dateInputId: "editDate",
        noteInputId: "editNote",
        receiptPayloadGetter: getEditReceiptPayload,
        currencySelectId: "editCurrency",
        fxRateInputId: "editFxRate",
      });
      delete payload._mode;
      return payload;
    }

    async function createOperation(event) {
      event.preventDefault();
      if (el.opEntryMode.value === "debt") {
        const startDate = core.parseDateInputValue(el.debtStartDate.value);
        const dueDate = core.parseDateInputValue(el.debtDueDate.value);
        if (!startDate) {
          throw new Error("Проверь дату долга");
        }
        if (el.debtDueDate.value && !dueDate) {
          throw new Error("Проверь срок долга");
        }
        const principal = core.resolveMoneyInput(el.debtPrincipal.value);
        if (!principal.valid || principal.value <= 0) {
          throw new Error("Проверь сумму долга");
        }
        const payload = {
          counterparty: el.debtCounterparty.value.trim(),
          direction: el.debtDirection.value,
          principal: principal.formatted,
          start_date: startDate,
          due_date: dueDate || null,
          note: el.debtNote.value.trim() || null,
        };
        const isEditDebt = Number(state.editDebtCreateId || 0) > 0;
        const url = isEditDebt ? `/api/v1/debts/${state.editDebtCreateId}` : "/api/v1/debts";
        await core.requestJson(url, {
          method: isEditDebt ? "PATCH" : "POST",
          headers: core.authHeaders(),
          body: JSON.stringify(payload),
        });
        const dashboardData = getDashboardData();
        core.invalidateUiRequestCache("debts");
        dashboardData.invalidateReadCaches?.();
        state.editDebtCreateId = null;
        closeCreateModal();
        await refreshAfterDebtMutation();
        return;
      }
      if (el.opEntryMode.value === "currency") {
        const tradeDate = core.parseDateInputValue(el.currencyTradeDateModal?.value || "");
        if (!tradeDate) {
          throw new Error("Проверь дату валютной сделки");
        }
        const operationModal = window.App.getRuntimeModule?.("operation-modal") || {};
        const tradeContext = typeof operationModal.getCurrencyTradeContext === "function"
          ? operationModal.getCurrencyTradeContext()
          : null;
        const quantityInput = tradeContext?.quantityResolved || core.resolveMoneyInput(el.currencyQuantity?.value || 0);
        const unitPrice = tradeContext?.rateResolved || core.resolveMoneyInput(el.currencyUnitPrice?.value || 0);
        const fee = tradeContext?.feeResolved || core.resolveMoneyInput(el.currencyFee?.value || 0);
        if (!quantityInput.valid || quantityInput.value <= 0) {
          throw new Error((tradeContext?.side || "buy") === "buy" ? "Проверь сумму покупки" : "Проверь количество продаваемой валюты");
        }
        if (!unitPrice.valid || unitPrice.value <= 0) {
          throw new Error("Проверь курс валюты");
        }
        if (!fee.valid || fee.value < 0) {
          throw new Error("Проверь комиссию");
        }
        const effectiveQuantity = Number(tradeContext?.effectiveQuantity || 0);
        if (!(effectiveQuantity > 0)) {
          throw new Error((tradeContext?.side || "buy") === "buy" ? "Проверь сумму покупки и курс" : "Проверь количество валюты");
        }
        await core.requestJson("/api/v1/currency/trades", {
          method: "POST",
          headers: core.authHeaders(),
          body: JSON.stringify({
            side: el.currencySide?.value || "buy",
            asset_currency: String(el.currencyAsset?.value || "USD").toUpperCase(),
            quote_currency: String(el.currencyQuote?.value || "BYN").toUpperCase(),
            quantity: core.formatAmount(effectiveQuantity),
            unit_price: unitPrice.formatted,
            fee: fee.formatted,
            trade_date: tradeDate,
            note: el.currencyNote?.value?.trim() || null,
          }),
        });
        const dashboardData = getDashboardData();
        dashboardData.invalidateSummaryCache?.();
        core.invalidateUiRequestCache("dashboard:summary");
        core.invalidateUiRequestCache("currency");
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
        closeCreateModal();
        if (isSectionVisible("currency")) {
          window.App.getRuntimeModule?.("currency")?.loadCurrencySection?.({ force: true }).catch(() => {});
        }
        await refreshAfterOperationMutation();
        return;
      }
      const payload = getValidatedCreateOperationPayload();
      await core.requestJson("/api/v1/operations", {
        method: "POST",
        headers: core.authHeaders(),
        body: JSON.stringify(payload),
      });
      const dashboardData = getDashboardData();
      core.invalidateUiRequestCache("operations");
      dashboardData.invalidateSummaryCache?.();
      invalidateAllTimeAnchor();
      trackCategoryUsage(payload.category_id);
      document.getElementById("opAmount").value = "";
      document.getElementById("opNote").value = "";
      el.opCategory.value = "";
      el.opCategorySearch.value = "";
      renderCreateCategoryPicker();
      updateCreatePreview();
      closeCreateModal();
      await refreshAfterOperationMutation();
    }

    async function updateOperation(event) {
      event.preventDefault();
      if (!state.editOperationId) {
        return;
      }
      const payload = getValidatedUpdateOperationPayload();
      await core.requestJson(`/api/v1/operations/${state.editOperationId}`, {
        method: "PATCH",
        headers: core.authHeaders(),
        body: JSON.stringify(payload),
      });
      const dashboardData = getDashboardData();
      core.invalidateUiRequestCache("operations");
      dashboardData.invalidateSummaryCache?.();
      invalidateAllTimeAnchor();
      trackCategoryUsage(payload.category_id);
      closeEditModal();
      await refreshAfterOperationMutation();
    }

    async function deleteOperationFlow(item) {
      core.runDestructiveAction({
        confirmMessage: "Удалить операцию?",
        doDelete: async () => {
          await core.requestJson(`/api/v1/operations/${item.id}`, {
            method: "DELETE",
            headers: core.authHeaders(),
          });
          const dashboardData = getDashboardData();
          core.invalidateUiRequestCache("operations");
          dashboardData.invalidateSummaryCache?.();
          invalidateAllTimeAnchor();
        },
        onAfterDelete: async () => {
          await refreshAfterOperationMutation();
        },
        toastMessage: "Операция удалена",
        undoAction: async () => {
          await core.requestJson("/api/v1/operations", {
            method: "POST",
            headers: core.authHeaders(),
            body: JSON.stringify({
              kind: item.kind,
              category_id: item.category_id,
              amount: item.amount,
              currency: item.currency || "BYN",
              fx_rate: item.currency && item.base_currency && item.currency !== item.base_currency ? item.fx_rate : null,
              operation_date: item.operation_date,
              note: item.note,
            }),
          });
          const dashboardData = getDashboardData();
          core.invalidateUiRequestCache("operations");
          dashboardData.invalidateSummaryCache?.();
          invalidateAllTimeAnchor();
          await refreshAfterOperationMutation();
          return "Операция восстановлена";
        },
        onDeleteError: "Не удалось удалить операцию",
      });
    }

    async function applyFilters(savePreferences) {
      await savePreferences();
      await loadOperations({ reset: true });
    }

    async function applyRealtimeSearch(savePreferencesDebounced) {
      await loadOperations({ reset: true });
      savePreferencesDebounced(450);
    }

    async function setOperationsSortPreset(value, savePreferences) {
      state.operationSortPreset = value || "date";
      localStorage.setItem("operations_sort_preset", state.operationSortPreset);
      core.syncSegmentedActive(el.operationsSortTabs, "op-sort", state.operationSortPreset);
      await loadOperations({ reset: true });
      await savePreferences();
    }

    async function refreshAll() {
      const analyticsFeature = getAnalyticsFeature();
      const tasks = [
        { label: "Дашборд", run: () => loadDashboard() },
        { label: "Аналитика (дашборд)", run: () => (analyticsFeature.loadDashboardAnalyticsPreview ? analyticsFeature.loadDashboardAnalyticsPreview({ force: true }) : Promise.resolve()) },
        { label: "Операции", run: () => loadOperations({ reset: true }) },
        { label: "Операции (дашборд)", run: () => loadDashboardOperations() },
        { label: "Аналитика", run: () => (analyticsFeature.loadAnalyticsSection ? analyticsFeature.loadAnalyticsSection({ force: true }) : Promise.resolve()) },
        { label: "Категории", run: () => categoryActions.loadCategories() },
        { label: "Долги", run: () => loadDebtsCards() },
        { label: "Каталог позиций", run: () => loadItemCatalog({ force: true }) },
      ];
      const results = await Promise.allSettled(tasks.map((task) => task.run()));
      const failed = [];
      for (let idx = 0; idx < results.length; idx += 1) {
        const result = results[idx];
        if (result.status !== "rejected") {
          continue;
        }
        failed.push(`${tasks[idx].label}: ${core.errorMessage(result.reason)}`);
      }
      if (failed.length > 0) {
        core.setStatus(`Часть данных не загружена (${failed.length}/${tasks.length}): ${failed.join("; ")}`);
      }
    }

    return {
      getValidatedCreateOperationPayload,
      getValidatedUpdateOperationPayload,
      createOperation,
      updateOperation,
      deleteOperationFlow,
      applyFilters,
      applyRealtimeSearch,
      setOperationsSortPreset,
      refreshAll,
      refreshAfterOperationMutation,
      refreshAfterDebtMutation,
    };
  }

  window.App.registerRuntimeModule?.("operations-mutation-factory", createOperationsMutationFeature);
})();
