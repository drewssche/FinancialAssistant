(() => {
  const { state, el, core } = window.App;
  const categoryActions = window.App.actions;
  const dashboardFeatures = window.App.featureDashboard;
  const debtFeatures = window.App.featureDebts;
  const sessionFeatures = window.App.featureSession;
  const itemCatalogFeatures = window.App.featureItemCatalog;
  const operationModal = window.App.operationModal;
  let operationsRawItems = [];
  let operationsRequestController = null;
  let operationsRequestSeq = 0;
  const OPERATIONS_CACHE_TTL_MS = 15000;
  const getCategoryMetaById = operationModal.getCategoryMetaById;
  const trackCategoryUsage = operationModal.trackCategoryUsage;
  const renderCreateCategoryPicker = operationModal.renderCreateCategoryPicker;
  const updateCreatePreview = operationModal.updateCreatePreview;
  const getCreateReceiptPayload = operationModal.getCreateReceiptPayload;
  const getEditReceiptPayload = operationModal.getEditReceiptPayload;
  const closeCreateModal = operationModal.closeCreateModal;
  const closeEditModal = operationModal.closeEditModal;
  const savePreferences = sessionFeatures.savePreferences;
  const savePreferencesDebounced = sessionFeatures.savePreferencesDebounced;
  const loadDashboard = dashboardFeatures.loadDashboard;
  const loadDashboardOperations = dashboardFeatures.loadDashboardOperations;
  const loadDebtsCards = debtFeatures.loadDebtsCards;
  const loadItemCatalog = itemCatalogFeatures.loadItemCatalog;

  function invalidateAllTimeAnchor() {
    state.firstOperationDate = "";
    state.allTimeAnchorResolved = false;
  }

  async function ensureAllTimeBounds(force = false) {
    if (state.period !== "all_time") {
      return;
    }
    if (state.allTimeAnchorResolved && !force) {
      return;
    }
    const params = new URLSearchParams({
      page: "1",
      page_size: "1",
      sort_by: "operation_date",
      sort_dir: "asc",
    });
    const data = await core.requestJson(`/api/v1/operations?${params.toString()}`, {
      headers: core.authHeaders(),
    });
    state.firstOperationDate = data.items?.[0]?.operation_date || "";
    state.allTimeAnchorResolved = true;
  }

  function buildOperationsQuery(page) {
    const { dateFrom, dateTo } = core.getPeriodBounds(state.period);
    el.operationsPeriodLabel.textContent = core.formatPeriodLabel(dateFrom, dateTo);
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(state.pageSize),
      sort_by: state.operationSortPreset === "amount" ? "amount" : "operation_date",
      sort_dir: "desc",
      date_from: dateFrom,
      date_to: dateTo,
    });

    if (state.filterKind) {
      params.set("kind", state.filterKind);
    }
    const query = el.filterQ.value.trim();
    if (query) {
      params.set("q", query);
    }
    return params;
  }

  function renderPagination() {
    const loaded = operationsRawItems.length;
    el.pageInfo.textContent = `Загружено ${loaded} из ${state.total}`;
    el.prevPageBtn.disabled = true;
    el.nextPageBtn.disabled = !state.operationsHasMore;
  }

  function compareIsoDateDesc(a, b) {
    const aDate = String(a || "");
    const bDate = String(b || "");
    return bDate.localeCompare(aDate);
  }

  function applyOperationsSort(items) {
    const preset = state.operationSortPreset || "date";
    const sorted = items.slice();
    if (preset === "amount") {
      sorted.sort((a, b) => {
        const diff = Number(b.amount || 0) - Number(a.amount || 0);
        if (diff !== 0) {
          return diff;
        }
        return compareIsoDateDesc(a.operation_date, b.operation_date);
      });
      return sorted;
    }
    if (preset === "risk") {
      sorted.sort((a, b) => {
        const aExpense = a.kind === "expense" ? 0 : 1;
        const bExpense = b.kind === "expense" ? 0 : 1;
        if (aExpense !== bExpense) {
          return aExpense - bExpense;
        }
        const amountDiff = Number(b.amount || 0) - Number(a.amount || 0);
        if (amountDiff !== 0) {
          return amountDiff;
        }
        return compareIsoDateDesc(a.operation_date, b.operation_date);
      });
      return sorted;
    }
    return sorted;
  }

  function appendUniqueOperations(items) {
    const existing = new Set(operationsRawItems.map((item) => item.id));
    for (const item of items) {
      if (!existing.has(item.id)) {
        operationsRawItems.push(item);
      }
    }
  }

  function applyOperationsPageData(data, reset, requestPage) {
    state.total = data.total;
    if (reset) {
      operationsRawItems = data.items.slice();
    } else {
      appendUniqueOperations(data.items);
    }
    if (data.items.length > 0) {
      state.page = requestPage + 1;
    }
    state.operationsHasMore = operationsRawItems.length < state.total && data.items.length > 0;
    renderOperations(operationsRawItems);
    renderPagination();
  }

  function renderOperations(items) {
    const sortedItems = applyOperationsSort(items);
    const query = el.filterQ.value.trim();
    const visibleIds = new Set(sortedItems.map((item) => item.id));
    for (const id of Array.from(state.selectedOperationIds)) {
      if (!visibleIds.has(id)) {
        state.selectedOperationIds.delete(id);
      }
    }
    el.operationsBody.innerHTML = "";
    if (!sortedItems.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="7">Нет операций</td>';
      el.operationsBody.appendChild(row);
      return;
    }
    for (const item of sortedItems) {
      el.operationsBody.appendChild(
        core.createOperationRow(item, {
          searchQuery: query,
          category: getCategoryMetaById(item.category_id),
          selectable: true,
          selected: state.selectedOperationIds.has(item.id),
        }),
      );
    }
    if (window.App.actions.updateOperationsBulkUi) {
      window.App.actions.updateOperationsBulkUi();
    }
  }

  async function loadOperations(options = {}) {
    await ensureAllTimeBounds();
    const reset = options.reset !== false;
    const force = options.force === true;
    if (state.operationsLoading && reset && operationsRequestController) {
      operationsRequestController.abort();
    } else if (state.operationsLoading && !force) {
      return;
    }
    if (!reset && !state.operationsHasMore) {
      return;
    }

    if (reset) {
      state.page = 1;
      state.operationsHasMore = true;
      operationsRawItems = [];
      state.selectedOperationIds.clear();
    }

    const requestPage = state.page;
    const params = buildOperationsQuery(requestPage);
    const cacheKey = `operations:list:${params.toString()}`;
    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, OPERATIONS_CACHE_TTL_MS);
      if (cached) {
        applyOperationsPageData(cached, reset, requestPage);
        return;
      }
    }

    state.operationsLoading = true;
    const requestController = new AbortController();
    operationsRequestController = requestController;
    const requestSeq = ++operationsRequestSeq;
    try {
      const data = await core.requestJson(`/api/v1/operations?${params.toString()}`, {
        headers: core.authHeaders(),
        signal: requestController.signal,
      });
      if (requestSeq !== operationsRequestSeq) {
        return;
      }
      core.setUiRequestCache(cacheKey, data);
      applyOperationsPageData(data, reset, requestPage);
    } catch (err) {
      if (core.isAbortError && core.isAbortError(err)) {
        return;
      }
      throw err;
    } finally {
      if (operationsRequestController === requestController) {
        operationsRequestController = null;
        state.operationsLoading = false;
      }
    }
  }

  async function loadMoreOperations() {
    await loadOperations({ reset: false });
  }
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

  async function createOperation(event) {
    event.preventDefault();
    if (el.opEntryMode.value === "debt") {
      const startDate = core.parseDateInputValue(el.debtStartDate.value);
      const dueDate = core.parseDateInputValue(el.debtDueDate.value);
      if (!startDate) {
        core.setStatus("Проверь дату долга");
        return;
      }
      if (el.debtDueDate.value && !dueDate) {
        core.setStatus("Проверь срок долга");
        return;
      }
      const payload = {
        counterparty: el.debtCounterparty.value.trim(),
        direction: el.debtDirection.value,
        principal: el.debtPrincipal.value,
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
      state.editDebtCreateId = null;
      closeCreateModal();
      await refreshAfterDebtMutation();
      return;
    }
    const operationDate = core.parseDateInputValue(document.getElementById("opDate").value);
    if (!operationDate) {
      core.setStatus("Проверь дату операции");
      return;
    }
    const payload = {
      kind: el.opKind.value,
      category_id: el.opCategory.value ? Number(el.opCategory.value) : null,
      amount: String(document.getElementById("opAmount").value || "").trim() || null,
      operation_date: operationDate,
      note: document.getElementById("opNote").value,
      receipt_items: getCreateReceiptPayload ? getCreateReceiptPayload() : [],
    };

    await core.requestJson("/api/v1/operations", {
      method: "POST",
      headers: core.authHeaders(),
      body: JSON.stringify(payload),
    });
    core.invalidateUiRequestCache("operations");
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
    const operationDate = core.parseDateInputValue(document.getElementById("editDate").value);
    if (!operationDate) {
      core.setStatus("Проверь дату операции");
      return;
    }
    const payload = {
      kind: el.editKind.value,
      category_id: el.editCategory.value ? Number(el.editCategory.value) : null,
      amount: document.getElementById("editAmount").value,
      operation_date: operationDate,
      note: document.getElementById("editNote").value,
      receipt_items: getEditReceiptPayload ? getEditReceiptPayload() : [],
    };

    await core.requestJson(`/api/v1/operations/${state.editOperationId}`, {
      method: "PATCH",
      headers: core.authHeaders(),
      body: JSON.stringify(payload),
    });
    core.invalidateUiRequestCache("operations");
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
        invalidateAllTimeAnchor();
        await refreshAfterOperationMutation();
        return "Операция восстановлена";
      },
      onDeleteError: "Не удалось удалить операцию",
    });
  }

  async function applyFilters() {
    await savePreferences();
    await loadOperations({ reset: true });
  }

  async function applyRealtimeSearch() {
    await loadOperations({ reset: true });
    savePreferencesDebounced(450);
  }

  async function setOperationsSortPreset(value) {
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

  function refreshOperationsView() {
    renderOperations(operationsRawItems);
  }

  function getCurrentOperationItems() {
    return operationsRawItems.slice();
  }
  function openOperationReceiptModal(item) {
    if (!item || !Array.isArray(item.receipt_items) || item.receipt_items.length === 0) {
      return;
    }
    if (!el.operationReceiptModal || !el.operationReceiptItems) {
      return;
    }
    const esc = (value) => String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
    if (el.operationReceiptMeta) {
      const note = item.note ? ` · ${item.note}` : "";
      el.operationReceiptMeta.textContent = `${core.formatDateRu(item.operation_date)} · ${core.formatMoney(item.amount)}${note}`;
    }
    el.operationReceiptItems.innerHTML = item.receipt_items.map((row) => {
      const qty = Number(row.quantity || 0);
      const price = Number(row.unit_price || 0);
      const total = Number(row.line_total || qty * price || 0);
      const shopChip = row.shop_name
        ? `<div class="operation-receipt-shop">${core.renderCategoryChip({ name: row.shop_name, icon: null, accent_color: null }, "")}</div>`
        : "";
      return `
        <article class="operation-receipt-item">
          <div class="operation-receipt-head">
            <strong>${esc(row.name || "Без названия")}</strong>
            <span class="muted-small">${core.formatMoney(total)}</span>
          </div>
          ${shopChip}
          <div class="operation-receipt-meta muted-small">
            ${esc(core.formatAmount(qty))} × ${core.formatMoney(price)}
          </div>
          ${row.note ? `<div class="muted-small">${esc(row.note)}</div>` : ""}
        </article>
      `;
    }).join("");
    el.operationReceiptModal.classList.remove("hidden");
  }

  function closeOperationReceiptModal() {
    el.operationReceiptModal?.classList.add("hidden");
  }
  function cleanupOperationsRuntime() {
    if (operationsRequestController) {
      operationsRequestController.abort();
      operationsRequestController = null;
    }
    operationsRequestSeq = 0;
    operationsRawItems = [];
    state.operationsLoading = false;
  }
  window.App.featureOperations = {
    ensureAllTimeBounds,
    invalidateAllTimeAnchor,
    loadOperations,
    loadMoreOperations,
    createOperation,
    updateOperation,
    deleteOperationFlow,
    applyFilters,
    applyRealtimeSearch,
    setOperationsSortPreset,
    refreshAll,
    refreshOperationsView,
    getCurrentOperationItems,
    openOperationReceiptModal,
    closeOperationReceiptModal,
    cleanupOperationsRuntime,
  };
})();
