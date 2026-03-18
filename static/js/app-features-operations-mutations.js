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
    const dashboardData = window.App.dashboardData || {};

    function isSectionVisible(section) {
      return state.activeSection === section;
    }

    async function refreshAfterOperationMutation() {
      const tasks = [loadOperations({ reset: true })];
      if (isSectionVisible("dashboard")) {
        tasks.push(loadDashboard(), loadDashboardOperations());
        if (window.App.actions.loadDashboardAnalyticsPreview) {
          tasks.push(window.App.actions.loadDashboardAnalyticsPreview({ force: true }));
        }
      }
      if (isSectionVisible("analytics") && window.App.actions.loadAnalyticsSection) {
        tasks.push(window.App.actions.loadAnalyticsSection({ force: true }));
      }
      await Promise.all(tasks);
    }

    async function refreshAfterDebtMutation() {
      const tasks = [];
      if (isSectionVisible("debts") || isSectionVisible("dashboard")) {
        tasks.push(loadDebtsCards());
      }
      if (isSectionVisible("dashboard")) {
        tasks.push(loadDashboard());
        if (window.App.actions.loadDashboardAnalyticsPreview) {
          tasks.push(window.App.actions.loadDashboardAnalyticsPreview({ force: true }));
        }
      }
      if (isSectionVisible("analytics") && window.App.actions.loadAnalyticsSection) {
        tasks.push(window.App.actions.loadAnalyticsSection({ force: true }));
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
      } = options;
      const operationDate = core.parseDateInputValue(document.getElementById(dateInputId).value);
      if (!operationDate) {
        throw new Error("Проверь дату операции");
      }
      const receiptItems = receiptPayloadGetter ? receiptPayloadGetter() : [];
      const amount = core.resolveMoneyInput(document.getElementById(amountInputId).value);
      const hasReceiptItems = receiptItems.length > 0;
      const canDeriveAmountFromReceipt = hasReceiptItems && amount.empty;
      if (!canDeriveAmountFromReceipt && (!amount.valid || amount.value <= 0)) {
        throw new Error("Проверь сумму операции");
      }
      return {
        kind,
        category_id: categoryId,
        amount: canDeriveAmountFromReceipt ? null : amount.formatted,
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
        core.invalidateUiRequestCache("debts");
        dashboardData.invalidateReadCaches?.();
        state.editDebtCreateId = null;
        closeCreateModal();
        await refreshAfterDebtMutation();
        return;
      }
      const payload = getValidatedCreateOperationPayload();
      await core.requestJson("/api/v1/operations", {
        method: "POST",
        headers: core.authHeaders(),
        body: JSON.stringify(payload),
      });
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
              operation_date: item.operation_date,
              note: item.note,
            }),
          });
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
      core.syncSegmentedActive(el.operationsSortTabs, "op-sort", state.operationSortPreset);
      await loadOperations({ reset: true });
      await savePreferences();
    }

    async function refreshAll() {
      const tasks = [
        { label: "Дашборд", run: () => loadDashboard() },
        { label: "Аналитика (дашборд)", run: () => (window.App.actions.loadDashboardAnalyticsPreview ? window.App.actions.loadDashboardAnalyticsPreview({ force: true }) : Promise.resolve()) },
        { label: "Операции", run: () => loadOperations({ reset: true }) },
        { label: "Операции (дашборд)", run: () => loadDashboardOperations() },
        { label: "Аналитика", run: () => (window.App.actions.loadAnalyticsSection ? window.App.actions.loadAnalyticsSection({ force: true }) : Promise.resolve()) },
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

  window.App = window.App || {};
  window.App.createOperationsMutationFeature = createOperationsMutationFeature;
})();
