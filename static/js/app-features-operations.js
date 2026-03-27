(() => {
  const { state, el, core } = window.App;
  const dashboardFeatures = window.App.getRuntimeModule?.("dashboard") || {};
  const debtFeatures = window.App.getRuntimeModule?.("debts") || {};
  const sessionFeatures = window.App.getRuntimeModule?.("session") || {};
  const itemCatalogFeatures = window.App.getRuntimeModule?.("item-catalog") || {};
  const operationModal = window.App.getRuntimeModule?.("operation-modal") || {};
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
  const OPERATIONS_SUMMARY_CACHE_TTL_MS = 15000;
  const createOperationsMutationFeature = window.App.getRuntimeModule?.("operations-mutation-factory");
  const createOperationsDisplayFeature = window.App.getRuntimeModule?.("operations-display-factory");

  function getActions() {
    return window.App.actions || {};
  }

  function getCategoryActions() {
    return window.App.actions || {};
  }

  function getBulkUi() {
    return window.App.getRuntimeModule?.("bulk-ui") || {};
  }

  function invalidateAllTimeAnchor() {
    state.firstOperationDate = "";
    state.allTimeAnchorResolved = false;
  }

  async function ensureAllTimeBounds(force = false, periodOverride = null) {
    const targetPeriod = periodOverride || state.period;
    if (targetPeriod !== "all_time") {
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
    if ((state.operationsQuickView || "all") !== "all") {
      params.set("quick_view", state.operationsQuickView);
    }
    if (state.operationsCategoryFilterId !== null && state.operationsCategoryFilterId !== undefined && state.operationsCategoryFilterId !== "") {
      params.set("category_id", String(state.operationsCategoryFilterId));
    }
    const query = el.filterQ.value.trim();
    if (query) {
      params.set("q", query);
    }
    return params;
  }

  function renderOperationsActiveFilters() {
    if (!el.operationsActiveFilters || !el.operationsCategoryFilterChip || !el.clearOperationsCategoryFilterBtn) {
      return;
    }
    const hasCategory = state.operationsCategoryFilterId !== null && state.operationsCategoryFilterId !== undefined && state.operationsCategoryFilterId !== "";
    const quickViewLabel = state.operationsQuickView === "receipt"
      ? "Срез: Только с чеком"
      : state.operationsQuickView === "large"
        ? `Срез: Крупные от ${core.formatMoney(100)}`
        : state.operationsQuickView === "uncategorized"
          ? "Срез: Без категории"
          : "";
    const kindLabel = state.filterKind === "expense"
      ? "Тип: Только расходы"
      : state.filterKind === "income"
        ? "Тип: Только доходы"
        : "";
    const hasQuickView = Boolean(quickViewLabel);
    const hasKind = Boolean(kindLabel);
    el.operationsActiveFilters.classList.toggle("hidden", !hasCategory && !hasQuickView && !hasKind);
    if (el.operationsKindFilterChip) {
      el.operationsKindFilterChip.classList.toggle("hidden", !hasKind);
      el.operationsKindFilterChip.textContent = kindLabel;
    }
    if (el.operationsQuickViewChip) {
      el.operationsQuickViewChip.classList.toggle("hidden", !hasQuickView);
      el.operationsQuickViewChip.textContent = quickViewLabel;
    }
    el.operationsCategoryFilterChip.classList.toggle("hidden", !hasCategory);
    el.clearOperationsCategoryFilterBtn.classList.toggle("hidden", !hasCategory);
    el.operationsCategoryFilterChip.textContent = hasCategory
      ? `Категория: ${state.operationsCategoryFilterName || `#${state.operationsCategoryFilterId}`}`
      : "";
    if (el.resetOperationsFiltersBtn) {
      const hasQuery = Boolean(el.filterQ?.value.trim());
      el.resetOperationsFiltersBtn.disabled = !hasCategory && !hasQuery && !hasKind && !hasQuickView;
    }
  }

  function renderOperationsSummary(data) {
    if (el.operationsIncomeTotal) {
      el.operationsIncomeTotal.textContent = core.formatMoney(data?.income_total || 0);
    }
    if (el.operationsExpenseTotal) {
      el.operationsExpenseTotal.textContent = core.formatMoney(data?.expense_total || 0);
    }
    if (el.operationsBalanceTotal) {
      el.operationsBalanceTotal.textContent = core.formatMoney(data?.balance || 0);
    }
    if (el.operationsTotalCount) {
      el.operationsTotalCount.textContent = String(data?.total || 0);
    }
  }

  async function loadOperationsSummary(options = {}) {
    const force = options.force === true;
    const { dateFrom, dateTo } = core.getPeriodBounds(state.period);
    const params = new URLSearchParams({
      date_from: dateFrom,
      date_to: dateTo,
    });
    if (state.filterKind) {
      params.set("kind", state.filterKind);
    }
    if ((state.operationsQuickView || "all") !== "all") {
      params.set("quick_view", state.operationsQuickView);
    }
    if (state.operationsCategoryFilterId !== null && state.operationsCategoryFilterId !== undefined && state.operationsCategoryFilterId !== "") {
      params.set("category_id", String(state.operationsCategoryFilterId));
    }
    const query = el.filterQ.value.trim();
    if (query) {
      params.set("q", query);
    }
    const cacheKey = `operations:summary:${params.toString()}`;
    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, OPERATIONS_SUMMARY_CACHE_TTL_MS);
      if (cached) {
        renderOperationsSummary(cached);
        return cached;
      }
    }
    const data = await core.requestJson(`/api/v1/operations/summary?${params.toString()}`, {
      headers: core.authHeaders(),
    });
    core.setUiRequestCache(cacheKey, data);
    renderOperationsSummary(data);
    return data;
  }

  function renderPagination() {
    const loaded = operationsRawItems.length;
    el.pageInfo.textContent = `Показано ${loaded} из ${state.total}`;
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
    renderOperationsActiveFilters();
    if (el.deleteAllOperationsBtn) {
      el.deleteAllOperationsBtn.disabled = sortedItems.length === 0;
    }
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
          category: getOperationDisplayCategory(item),
          categories: getOperationDisplayCategories(item),
          selectable: true,
          selected: state.selectedOperationIds.has(item.id),
        }),
      );
    }
    getBulkUi().updateOperationsBulkUi?.();
  }

  async function loadOperations(options = {}) {
    await ensureAllTimeBounds();
    renderOperationsActiveFilters();
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
        await loadOperationsSummary({ force: false });
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
      await loadOperationsSummary({ force });
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

  async function clearOperationsCategoryFilter() {
    state.operationsCategoryFilterId = null;
    state.operationsCategoryFilterName = "";
    renderOperationsActiveFilters();
    await loadOperations({ reset: true, force: true });
    await savePreferences();
  }

  async function resetOperationsFilters() {
    state.filterKind = "";
    state.operationsQuickView = "all";
    state.operationsCategoryFilterId = null;
    state.operationsCategoryFilterName = "";
    if (el.filterQ) {
      el.filterQ.value = "";
    }
    core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
    core.syncSegmentedActive(el.operationsQuickViewTabs, "operations-quick-view", state.operationsQuickView);
    renderOperationsActiveFilters();
    await loadOperations({ reset: true, force: true });
    await savePreferences();
  }

  async function setOperationsQuickView(value) {
    state.operationsQuickView = value || "all";
    core.syncSegmentedActive(el.operationsQuickViewTabs, "operations-quick-view", state.operationsQuickView);
    renderOperationsActiveFilters();
    await loadOperations({ reset: true, force: true });
    await savePreferences();
  }

  function selectVisibleOperations() {
    const checkboxes = Array.from(el.operationsBody?.querySelectorAll("input[data-select-operation-id]") || []);
    for (const checkbox of checkboxes) {
      const id = Number(checkbox.dataset.selectOperationId);
      state.selectedOperationIds.add(id);
      checkbox.checked = true;
      const row = checkbox.closest("tr[data-item]");
      if (row) {
        row.classList.add("row-selected");
      }
    }
    getBulkUi().updateOperationsBulkUi?.();
  }

  function clearVisibleOperationsSelection() {
    const checkboxes = Array.from(el.operationsBody?.querySelectorAll("input[data-select-operation-id]") || []);
    for (const checkbox of checkboxes) {
      const id = Number(checkbox.dataset.selectOperationId);
      state.selectedOperationIds.delete(id);
      checkbox.checked = false;
      const row = checkbox.closest("tr[data-item]");
      if (row) {
        row.classList.remove("row-selected");
      }
    }
    getBulkUi().updateOperationsBulkUi?.();
  }

  async function setOperationsKindFilter(value) {
    state.filterKind = value || "";
    core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
    renderOperationsActiveFilters();
    await loadOperations({ reset: true, force: true });
    await savePreferences();
  }
  function refreshOperationsView() {
    renderOperations(operationsRawItems);
  }

  function getCurrentOperationItems() {
    return operationsRawItems.slice();
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
  const mutationFeature = createOperationsMutationFeature
    ? createOperationsMutationFeature({
      state,
      el,
      core,
      categoryActions: getCategoryActions(),
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
    })
    : {};
  const createOperation = mutationFeature.createOperation || (async () => {});
  const updateOperation = mutationFeature.updateOperation || (async () => {});
  const deleteOperationFlow = mutationFeature.deleteOperationFlow || (async () => {});
  const applyFilters = mutationFeature.applyFilters
    ? () => mutationFeature.applyFilters(savePreferences)
    : (async () => {});
  const applyRealtimeSearch = mutationFeature.applyRealtimeSearch
    ? () => mutationFeature.applyRealtimeSearch(savePreferencesDebounced)
    : (async () => {});
  const setOperationsSortPreset = mutationFeature.setOperationsSortPreset
    ? (value) => mutationFeature.setOperationsSortPreset(value, savePreferences)
    : (async () => {});
  const refreshAll = mutationFeature.refreshAll || (async () => {});
  const displayFeature = createOperationsDisplayFeature
    ? createOperationsDisplayFeature({
      el,
      core,
      getCategoryMetaById,
    })
    : {};
  const getOperationDisplayCategory = displayFeature.getOperationDisplayCategory || (() => null);
  const getOperationDisplayCategories = displayFeature.getOperationDisplayCategories || (() => []);
  const openOperationReceiptModal = displayFeature.openOperationReceiptModal || (() => {});
  const closeOperationReceiptModal = displayFeature.closeOperationReceiptModal || (() => {});
  const api = {
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
    clearOperationsCategoryFilter,
    resetOperationsFilters,
    setOperationsQuickView,
    selectVisibleOperations,
    clearVisibleOperationsSelection,
    setOperationsKindFilter,
    loadOperationsSummary,
    openOperationReceiptModal,
    closeOperationReceiptModal,
    cleanupOperationsRuntime,
  };

  window.App.registerRuntimeModule?.("operations", api);
})();
