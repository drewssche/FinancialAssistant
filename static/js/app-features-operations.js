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
  const getCreateFxSettlementPayload = operationModal.getCreateFxSettlementPayload;
  const getEditReceiptPayload = operationModal.getEditReceiptPayload;
  const getEditFxSettlementPayload = operationModal.getEditFxSettlementPayload;
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
  const analyticsShared = window.App.analyticsShared || {};
  const describeResult = analyticsShared.describeResult || ((balanceRaw) => {
    const balance = Number(balanceRaw || 0);
    if (balance > 0) {
      return { label: "Профицит", tone: "positive", cardClass: "positive", amount: balance };
    }
    if (balance < 0) {
      return { label: "Дефицит", tone: "negative", cardClass: "negative", amount: Math.abs(balance) };
    }
    return { label: "Ноль", tone: "neutral", cardClass: "neutral", amount: 0 };
  });

  function getActions() {
    return window.App.actions || {};
  }

  function getCategoryActions() {
    return window.App.actions || {};
  }

  function getBulkUi() {
    return window.App.getRuntimeModule?.("bulk-ui") || {};
  }

  function getLoadingSkeletons() {
    return window.App.getRuntimeModule?.("loading-skeletons") || {};
  }

  function getInlineRefreshState() {
    return window.App.getRuntimeModule?.("inline-refresh-state") || {};
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
    const isMoneyFlowMode = state.operationsMode === "money_flow";
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(state.pageSize),
      sort_by: state.operationSortPreset === "amount" ? "amount" : "operation_date",
      sort_dir: "desc",
      date_from: dateFrom,
      date_to: dateTo,
    });

    if (state.filterKind) {
      if (isMoneyFlowMode) {
        params.set("direction", state.filterKind === "income" ? "inflow" : "outflow");
      } else {
        params.set("kind", state.filterKind);
      }
    }
    if (isMoneyFlowMode && (state.operationsSourceFilter || "all") !== "all") {
      params.set("source", state.operationsSourceFilter);
    }
    if (!isMoneyFlowMode && (state.operationsQuickView || "all") !== "all") {
      params.set("quick_view", state.operationsQuickView);
    }
    if ((state.operationsCurrencyScope || "all") !== "all") {
      params.set("currency_scope", state.operationsCurrencyScope);
    }
    if (!isMoneyFlowMode && state.operationsCategoryFilterId !== null && state.operationsCategoryFilterId !== undefined && state.operationsCategoryFilterId !== "") {
      params.set("category_id", String(state.operationsCategoryFilterId));
    }
    const query = el.filterQ.value.trim();
    if (query) {
      params.set("q", query);
    }
    return params;
  }

  function syncOperationsCurrencyScopeUi() {
    const baseCurrency = String(core.getCurrencyConfig?.().code || "BYN").toUpperCase();
    if (el.operationsBaseCurrencyLabels?.length) {
      el.operationsBaseCurrencyLabels.forEach((node) => {
        node.textContent = baseCurrency;
      });
    }
    if (el.operationsCurrencyScopeTabs) {
      core.syncSegmentedActive(el.operationsCurrencyScopeTabs, "operations-currency-scope", state.operationsCurrencyScope || "all");
    }
    return baseCurrency;
  }

  function renderOperationsActiveFilters() {
    if (!el.operationsActiveFilters || !el.operationsCategoryFilterChip || !el.clearOperationsCategoryFilterBtn) {
      return;
    }
    const isMoneyFlowMode = state.operationsMode === "money_flow";
    const baseCurrency = syncOperationsCurrencyScopeUi();
    const hasCategory = !isMoneyFlowMode && state.operationsCategoryFilterId !== null && state.operationsCategoryFilterId !== undefined && state.operationsCategoryFilterId !== "";
    const sourceLabel = isMoneyFlowMode && state.operationsSourceFilter === "operation"
      ? "Источник: Операции"
      : isMoneyFlowMode && state.operationsSourceFilter === "debt"
        ? "Источник: Долги"
        : isMoneyFlowMode && state.operationsSourceFilter === "fx"
          ? "Источник: Валюта"
          : "";
    const quickViewLabel = state.operationsQuickView === "receipt"
      ? "Срез: Только с чеком"
      : state.operationsQuickView === "large"
        ? `Срез: Крупные от ${core.formatMoney(100)}`
        : state.operationsQuickView === "uncategorized"
          ? "Срез: Без категории"
          : "";
    const kindLabel = state.filterKind === "expense"
      ? `Тип: Только ${isMoneyFlowMode ? "оттоки" : "расходы"}`
      : state.filterKind === "income"
        ? `Тип: Только ${isMoneyFlowMode ? "притоки" : "доходы"}`
        : "";
    const currencyScopeLabel = state.operationsCurrencyScope === "base"
      ? `Валюта: ${baseCurrency}`
      : state.operationsCurrencyScope === "foreign"
        ? "Валюта: Другая"
        : "";
    const hasQuickView = Boolean(quickViewLabel);
    const hasKind = Boolean(kindLabel);
    const hasCurrencyScope = Boolean(currencyScopeLabel);
    el.operationsActiveFilters.classList.toggle("hidden", !hasCategory && !hasQuickView && !hasKind && !hasCurrencyScope && !sourceLabel);
    if (el.operationsKindFilterChip) {
      el.operationsKindFilterChip.classList.toggle("hidden", !hasKind);
      el.operationsKindFilterChip.textContent = kindLabel;
    }
    if (el.operationsQuickViewChip) {
      el.operationsQuickViewChip.classList.toggle("hidden", !hasQuickView);
      el.operationsQuickViewChip.textContent = quickViewLabel;
    }
    if (el.operationsCurrencyScopeChip) {
      el.operationsCurrencyScopeChip.classList.toggle("hidden", !hasCurrencyScope);
      el.operationsCurrencyScopeChip.textContent = currencyScopeLabel;
    }
    if (el.operationsSourceFilterChip) {
      el.operationsSourceFilterChip.classList.toggle("hidden", !sourceLabel);
      el.operationsSourceFilterChip.textContent = sourceLabel;
    }
    el.operationsCategoryFilterChip.classList.toggle("hidden", !hasCategory);
    el.clearOperationsCategoryFilterBtn.classList.toggle("hidden", !hasCategory);
    el.operationsCategoryFilterChip.textContent = hasCategory
      ? `Категория: ${state.operationsCategoryFilterName || `#${state.operationsCategoryFilterId}`}`
      : "";
    if (el.resetOperationsFiltersBtn) {
      const hasQuery = Boolean(el.filterQ?.value.trim());
      el.resetOperationsFiltersBtn.disabled = !hasCategory && !hasQuery && !hasKind && !hasQuickView && !hasCurrencyScope && !sourceLabel;
    }
  }

  function renderOperationsSummary(data) {
    const isMoneyFlowMode = state.operationsMode === "money_flow";
    const resultValue = Number(data?.balance || 0);
    const resultTone = resultValue > 0 ? "income" : resultValue < 0 ? "expense" : "neutral";
    if (el.operationsResultCard) {
      el.operationsResultCard.classList.remove(
        "analytics-kpi-income",
        "analytics-kpi-expense",
        "analytics-kpi-balance",
        "analytics-kpi-positive",
        "analytics-kpi-negative",
        "analytics-kpi-neutral",
      );
      el.operationsResultCard.classList.add(`analytics-kpi-${resultTone}`);
    }
    if (el.operationsResultLabel) {
      el.operationsResultLabel.textContent = isMoneyFlowMode ? "Денежный поток по выборке" : "Операционный результат по выборке";
    }
    if (el.operationsIncomeTotal) {
      el.operationsIncomeTotal.textContent = core.formatMoney(data?.income_total || 0);
    }
    if (el.operationsExpenseTotal) {
      el.operationsExpenseTotal.textContent = core.formatMoney(data?.expense_total || 0);
    }
    if (el.operationsBalanceTotal) {
      el.operationsBalanceTotal.textContent = core.formatMoney(resultValue || 0);
    }
    if (el.operationsTotalCount) {
      el.operationsTotalCount.textContent = String(data?.total || 0);
    }
    if (el.operationsIncomeLabel) {
      el.operationsIncomeLabel.textContent = `${isMoneyFlowMode ? "Приток" : "Доход"} по выборке`;
    }
    if (el.operationsExpenseLabel) {
      el.operationsExpenseLabel.textContent = `${isMoneyFlowMode ? "Отток" : "Расход"} по выборке`;
    }
    if (el.operationsTotalCountLabel) {
      el.operationsTotalCountLabel.textContent = `${isMoneyFlowMode ? "Событий" : "Операций"} найдено`;
    }
  }

  async function loadOperationsSummarySafely(options = {}) {
    try {
      return await loadOperationsSummary(options);
    } catch (err) {
      const message = core.errorMessage ? core.errorMessage(err) : String(err);
      if (!String(message).includes("[404]")) {
        core.setStatus(`Не удалось обновить сводку операций: ${message}`);
      }
      return null;
    }
  }

  async function loadOperationsSummary(options = {}) {
    const force = options.force === true;
    const { dateFrom, dateTo } = core.getPeriodBounds(state.period);
    const isMoneyFlowMode = state.operationsMode === "money_flow";
    const params = new URLSearchParams({
      date_from: dateFrom,
      date_to: dateTo,
    });
    if (state.filterKind) {
      if (isMoneyFlowMode) {
        params.set("direction", state.filterKind === "income" ? "inflow" : "outflow");
      } else {
        params.set("kind", state.filterKind);
      }
    }
    if (isMoneyFlowMode && (state.operationsSourceFilter || "all") !== "all") {
      params.set("source", state.operationsSourceFilter);
    }
    if (!isMoneyFlowMode && (state.operationsQuickView || "all") !== "all") {
      params.set("quick_view", state.operationsQuickView);
    }
    if ((state.operationsCurrencyScope || "all") !== "all") {
      params.set("currency_scope", state.operationsCurrencyScope);
    }
    if (!isMoneyFlowMode && state.operationsCategoryFilterId !== null && state.operationsCategoryFilterId !== undefined && state.operationsCategoryFilterId !== "") {
      params.set("category_id", String(state.operationsCategoryFilterId));
    }
    const query = el.filterQ.value.trim();
    if (query) {
      params.set("q", query);
    }
    const cacheKey = `operations:${isMoneyFlowMode ? "money-flow" : "list"}:summary:${params.toString()}`;
    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, OPERATIONS_SUMMARY_CACHE_TTL_MS);
      if (cached) {
        renderOperationsSummary(cached);
        return cached;
      }
    }
    const endpoint = isMoneyFlowMode ? "/api/v1/operations/money-flow/summary" : "/api/v1/operations/summary";
    const data = await core.requestJson(`${endpoint}?${params.toString()}`, {
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

  function applyOperationsModeUi() {
    const isMoneyFlowMode = state.operationsMode === "money_flow";
    core.syncSegmentedActive(el.operationsModeTabs, "operations-mode", state.operationsMode || "operations");
    if (el.operationsQuickViewCard) {
      el.operationsQuickViewCard.classList.toggle("hidden", isMoneyFlowMode);
    }
    if (el.operationsSourceCard) {
      el.operationsSourceCard.classList.toggle("hidden", !isMoneyFlowMode);
    }
    if (el.operationsModeHint) {
      el.operationsModeHint.textContent = isMoneyFlowMode
        ? "Единый поток денег: операции, долги и FX в одной ленте."
        : "Текущий CRUD-режим по доходам и расходам.";
    }
    if (el.operationsKindAllLabel) {
      el.operationsKindAllLabel.textContent = "Все";
    }
    if (el.operationsKindExpenseLabel) {
      el.operationsKindExpenseLabel.textContent = isMoneyFlowMode ? "Отток" : "Расход";
    }
    if (el.operationsKindIncomeLabel) {
      el.operationsKindIncomeLabel.textContent = isMoneyFlowMode ? "Приток" : "Доход";
    }
    if (el.quickFilterExpenseBtn) {
      el.quickFilterExpenseBtn.textContent = isMoneyFlowMode ? "Только отток" : "Только расходы";
    }
    if (el.quickFilterIncomeBtn) {
      el.quickFilterIncomeBtn.textContent = isMoneyFlowMode ? "Только приток" : "Только доходы";
    }
    if (el.operationsCategoryHeader) {
      el.operationsCategoryHeader.textContent = isMoneyFlowMode ? "Контекст" : "Категория";
    }
    if (el.operationsReceiptHeader) {
      el.operationsReceiptHeader.textContent = isMoneyFlowMode ? "Источник" : "Чек";
    }
    if (el.operationsBulkBar) {
      el.operationsBulkBar.classList.toggle("hidden", isMoneyFlowMode);
    }
    core.syncSegmentedActive(el.operationsSourceTabs, "operations-source", state.operationsSourceFilter || "all");
    if (el.operationsSelectAll) {
      el.operationsSelectAll.disabled = isMoneyFlowMode;
      el.operationsSelectAll.checked = false;
      el.operationsSelectAll.indeterminate = false;
    }
    if (el.deleteAllOperationsBtn) {
      el.deleteAllOperationsBtn.classList.toggle("hidden", isMoneyFlowMode);
    }
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
    const isMoneyFlowMode = state.operationsMode === "money_flow";
    const sortedItems = applyOperationsSort(items);
    const query = el.filterQ.value.trim();
    applyOperationsModeUi();
    renderOperationsActiveFilters();
    if (el.deleteAllOperationsBtn) {
      el.deleteAllOperationsBtn.disabled = isMoneyFlowMode || sortedItems.length === 0;
    }
    const visibleIds = new Set(sortedItems.map((item) => String(item.id)));
    for (const id of Array.from(state.selectedOperationIds)) {
      if (!visibleIds.has(String(id))) {
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
      const row = isMoneyFlowMode
        ? core.createMoneyFlowRow(item, {
          searchQuery: query,
          selectable: false,
          selected: false,
        })
        : core.createOperationRow(item, {
          searchQuery: query,
          category: getOperationDisplayCategory(item),
          categories: getOperationDisplayCategories(item),
          selectable: true,
          selected: state.selectedOperationIds.has(item.id),
        });
      el.operationsBody.appendChild(row);
    }
    getBulkUi().updateOperationsBulkUi?.();
  }

  async function loadOperations(options = {}) {
    await ensureAllTimeBounds();
    applyOperationsModeUi();
    syncOperationsCurrencyScopeUi();
    core.syncSegmentedActive(el.operationsSortTabs, "op-sort", state.operationSortPreset || "date");
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
    const isMoneyFlowMode = state.operationsMode === "money_flow";
    const endpoint = isMoneyFlowMode ? "/api/v1/operations/money-flow" : "/api/v1/operations";
    const cacheKey = `operations:${isMoneyFlowMode ? "money-flow" : "list"}:${params.toString()}`;
    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, OPERATIONS_CACHE_TTL_MS);
      if (cached) {
        applyOperationsPageData(cached, reset, requestPage);
        await loadOperationsSummarySafely({ force: false });
        state.operationsSectionHydrated = true;
        return;
      }
    }

    if (reset && !state.operationsSectionHydrated && state.activeSection === "operations") {
      getLoadingSkeletons().renderOperationsSectionSkeleton?.();
    }
    const refreshState = getInlineRefreshState();
    const shouldRefreshInline = reset && state.operationsSectionHydrated && state.activeSection === "operations";
    if (shouldRefreshInline) {
      refreshState.begin?.(el.operationsSection, "Обновляется");
    }

    state.operationsLoading = true;
    const requestController = new AbortController();
    operationsRequestController = requestController;
    const requestSeq = ++operationsRequestSeq;
    try {
      const data = await core.requestJson(`${endpoint}?${params.toString()}`, {
        headers: core.authHeaders(),
        signal: requestController.signal,
      });
      if (requestSeq !== operationsRequestSeq) {
        return;
      }
      core.setUiRequestCache(cacheKey, data);
      applyOperationsPageData(data, reset, requestPage);
      await loadOperationsSummarySafely({ force });
      state.operationsSectionHydrated = true;
    } catch (err) {
      if (core.isAbortError && core.isAbortError(err)) {
        return;
      }
      throw err;
    } finally {
      if (shouldRefreshInline) {
        refreshState.end?.(el.operationsSection);
      }
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
    state.operationsMode = "operations";
    state.operationsSourceFilter = "all";
    state.operationsQuickView = "all";
    state.operationsCurrencyScope = "all";
    state.operationsCategoryFilterId = null;
    state.operationsCategoryFilterName = "";
    if (el.filterQ) {
      el.filterQ.value = "";
    }
    core.syncSegmentedActive(el.operationsModeTabs, "operations-mode", state.operationsMode);
    core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
    core.syncSegmentedActive(el.operationsSourceTabs, "operations-source", state.operationsSourceFilter);
    core.syncSegmentedActive(el.operationsQuickViewTabs, "operations-quick-view", state.operationsQuickView);
    core.syncSegmentedActive(el.operationsCurrencyScopeTabs, "operations-currency-scope", state.operationsCurrencyScope);
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

  async function setOperationsCurrencyScope(value) {
    state.operationsCurrencyScope = ["base", "foreign"].includes(value) ? value : "all";
    syncOperationsCurrencyScopeUi();
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

  async function setOperationsSourceFilter(value) {
    state.operationsSourceFilter = ["operation", "debt", "fx"].includes(value) ? value : "all";
    core.syncSegmentedActive(el.operationsSourceTabs, "operations-source", state.operationsSourceFilter);
    renderOperationsActiveFilters();
    await loadOperations({ reset: true, force: true });
    await savePreferences();
  }

  async function setOperationsMode(value) {
    state.operationsMode = value === "money_flow" ? "money_flow" : "operations";
    state.selectedOperationIds.clear();
    if (state.operationsMode === "money_flow") {
      state.operationsQuickView = "all";
      state.operationsCategoryFilterId = null;
      state.operationsCategoryFilterName = "";
    } else {
      state.operationsSourceFilter = "all";
    }
    applyOperationsModeUi();
    renderOperationsActiveFilters();
    await loadOperations({ reset: true, force: true });
    await savePreferences();
  }

  async function openMoneyFlowSource({ sourceKind, sourceId, mode = "edit" }) {
    const navigation = getActions();
    const debtsFeature = window.App.getRuntimeModule?.("debts") || {};
    const currencyFeature = window.App.getRuntimeModule?.("currency") || {};
    if (sourceKind === "operation") {
      const resolvedId = Number(sourceId || 0);
      if (!(resolvedId > 0)) {
        return;
      }
      const item = await core.requestJson(`/api/v1/operations/${resolvedId}`, {
        headers: core.authHeaders(),
      });
      navigation.openEditModal?.(item);
      return;
    }
    if (sourceKind === "debt") {
      navigation.pushSectionBackContext?.();
      await navigation.switchSection?.("debts");
      if (mode === "history") {
        await debtsFeature.openDebtHistoryModal?.(Number(sourceId || 0));
        return;
      }
      await debtsFeature.openEditDebtModal?.(Number(sourceId || 0));
      return;
    }
    if (sourceKind === "fx") {
      navigation.pushSectionBackContext?.();
      await navigation.switchSection?.("currency");
      await currencyFeature.openCurrencyTradeEdit?.(Number(sourceId || 0));
    }
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
      getCreateFxSettlementPayload,
      getEditReceiptPayload,
      getEditFxSettlementPayload,
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
    setOperationsMode,
    setOperationsSourceFilter,
    setOperationsQuickView,
    setOperationsCurrencyScope,
    selectVisibleOperations,
    clearVisibleOperationsSelection,
    setOperationsKindFilter,
    loadOperationsSummary,
    openOperationReceiptModal,
    closeOperationReceiptModal,
    openMoneyFlowSource,
    cleanupOperationsRuntime,
  };

  window.App.registerRuntimeModule?.("operations", api);
})();
