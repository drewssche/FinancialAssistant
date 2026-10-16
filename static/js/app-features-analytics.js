(() => {
  const { state, el, core } = window.App;

  function getNavigationActions() {
    return window.App.getRuntimeModule?.("navigation") || {};
  }

  function getAnalyticsModules() {
    return {
      calendar: window.App.getRuntimeModule?.("analytics-calendar-module"),
      highlights: window.App.getRuntimeModule?.("analytics-highlights-module"),
      positions: window.App.getRuntimeModule?.("analytics-positions-module"),
      commerce: window.App.getRuntimeModule?.("analytics-commerce-module"),
      currency: window.App.getRuntimeModule?.("analytics-currency-module"),
    };
  }

  function clearOperationsBrandFilter() {
    state.operationsBrandFilterId = null;
    state.operationsBrandFilterName = "";
  }

  function applyAnalyticsTabUi() {
    const tab = state.analyticsTab === "calendar" ? "calendar" : "structure";
    state.analyticsTab = tab;
    el.analyticsStructurePanel?.classList.toggle("hidden", tab !== "structure");
    el.analyticsCalendarPanel?.classList.toggle("hidden", tab !== "calendar");
    if (state.activeSection !== "item_catalog") {
      el.analyticsStructurePanel?.before(el.analyticsGlobalScopePanel);
      el.analyticsGlobalScopePanel?.classList.toggle("hidden", tab !== "structure");
    }
    core.syncSegmentedActive(el.analyticsViewTabs, "analytics-tab", tab);
  }

  function setAnalyticsTab(tab) {
    state.analyticsTab = tab === "calendar" ? "calendar" : "structure";
    applyAnalyticsTabUi();
    if (state.analyticsTab === "structure") {
      getAnalyticsModules().highlights?.focusDefaultCategoryBreakdown?.();
    }
  }

  async function loadAnalyticsSection(options = {}) {
    const { calendar, highlights, positions } = getAnalyticsModules();
    if (state.activeSection === "item_catalog") {
      return state.itemCatalogView === "purchases"
        ? positions?.loadAnalyticsPositions?.(options)
        : highlights?.loadAnalyticsHighlights?.(options);
    }
    applyAnalyticsTabUi();
    calendar?.applyCalendarViewUi?.();
    if (state.analyticsTab === "calendar") return calendar?.loadAnalyticsCalendar?.(options) || null;
    return highlights?.loadAnalyticsHighlights?.(options) || null;
  }

  async function openOperationsForAnalyticsDate(dayIso) {
    const navigation = getNavigationActions();
    if (!dayIso || !navigation.switchSection) {
      return;
    }
    navigation.pushSectionBackContext?.();
    state.operationsCategoryFilterId = null;
    state.operationsCategoryFilterName = "";
    state.filterKind = "";
    state.operationsQuickView = "all";
    state.operationsCurrencyScope = "all";
    state.operationsItemTemplateFilterId = null;
    state.operationsItemTemplateFilterName = "";
    state.operationsProductFilterId = null;
    state.operationsProductFilterName = "";
    clearOperationsBrandFilter();
    core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
    core.syncSegmentedActive(el.operationsQuickViewTabs, "operations-quick-view", state.operationsQuickView);
    core.syncSegmentedActive(el.operationsCurrencyScopeTabs, "operations-currency-scope", state.operationsCurrencyScope);
    if (el.filterQ) {
      el.filterQ.value = "";
    }
    state.period = "custom";
    state.customDateFrom = dayIso;
    state.customDateTo = dayIso;
    core.syncAllPeriodTabs("custom");
    await navigation.switchSection("operations", { preserveBackStack: true, scrollToTop: true });
  }

  async function openOperationsForAnalyticsPositionRange(templateId, productId, positionName, dateFrom, dateTo) {
    const navigation = getNavigationActions();
    if (!navigation.switchSection || !dateFrom || !dateTo) {
      return;
    }
    navigation.pushSectionBackContext?.();
    state.period = "custom";
    state.customDateFrom = dateFrom;
    state.customDateTo = dateTo;
    state.filterKind = "expense";
    state.operationsSourceFilter = "operation";
    state.operationsQuickView = "all";
    state.operationsCurrencyScope = "all";
    state.operationsCategoryFilterId = null;
    state.operationsCategoryFilterName = "";
    state.operationsProductFilterId = Number(productId || 0) || null;
    state.operationsProductFilterName = state.operationsProductFilterId ? String(positionName || "").trim() : "";
    state.operationsItemTemplateFilterId = state.operationsProductFilterId ? null : (Number(templateId || 0) || null);
    state.operationsItemTemplateFilterName = state.operationsProductFilterId ? "" : String(positionName || "").trim();
    clearOperationsBrandFilter();
    if (el.filterQ) {
      el.filterQ.value = state.operationsItemTemplateFilterId || state.operationsProductFilterId ? "" : state.operationsItemTemplateFilterName;
    }
    core.syncAllPeriodTabs("custom");
    core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
    core.syncSegmentedActive(el.operationsSourceTabs, "operations-source", state.operationsSourceFilter);
    core.syncSegmentedActive(el.operationsQuickViewTabs, "operations-quick-view", state.operationsQuickView);
    core.syncSegmentedActive(el.operationsCurrencyScopeTabs, "operations-currency-scope", state.operationsCurrencyScope);
    await navigation.switchSection("operations", { preserveBackStack: true, scrollToTop: true });
  }

  async function openPositionsAnalyticsFromDashboard() {
    const navigation = getNavigationActions();
    const allowed = new Set(["day", "week", "month", "year"]);
    const dashboardPeriod = state.dashboardAnalyticsPeriod || "month";
    const period = allowed.has(dashboardPeriod) ? dashboardPeriod : "month";
    const bounds = dashboardPeriod === "custom" && state.dashboardAnalyticsDateFrom && state.dashboardAnalyticsDateTo
      ? { dateFrom: state.dashboardAnalyticsDateFrom, dateTo: state.dashboardAnalyticsDateTo }
      : core.getPeriodBounds?.(period) || {};
    state.analyticsPositionsPeriod = period;
    state.analyticsPositionsAnchor = bounds.dateFrom || bounds.dateTo || "";
    navigation.pushSectionBackContext?.();
    state.itemCatalogView = "purchases";
    await navigation.switchSection?.("item_catalog", { preserveBackStack: true, scrollToTop: true });
  }

  function applyAnalyticsScopeToOperations() {
    const period = state.analyticsGlobalPeriod || "month";
    if (period === "custom" && state.analyticsGlobalDateFrom && state.analyticsGlobalDateTo) {
      state.period = "custom";
      state.customDateFrom = state.analyticsGlobalDateFrom;
      state.customDateTo = state.analyticsGlobalDateTo;
    } else if (["week", "month", "year", "all_time"].includes(period)) {
      state.period = period;
      if (period !== "custom") {
        state.customDateFrom = "";
        state.customDateTo = "";
      }
    } else {
      state.period = "month";
      state.customDateFrom = "";
      state.customDateTo = "";
    }
    core.syncAllPeriodTabs(state.period);
  }

  async function openOperationsForAnalyticsCategory(categoryId, categoryName, categoryKind) {
    const navigation = getNavigationActions();
    if (!navigation.switchSection || !categoryId) {
      return;
    }
    navigation.pushSectionBackContext?.();
    applyAnalyticsScopeToOperations();
    state.operationsQuickView = "all";
    state.operationsCurrencyScope = "all";
    state.operationsItemTemplateFilterId = null;
    state.operationsItemTemplateFilterName = "";
    state.operationsProductFilterId = null;
    state.operationsProductFilterName = "";
    clearOperationsBrandFilter();
    core.syncSegmentedActive(el.operationsQuickViewTabs, "operations-quick-view", state.operationsQuickView);
    core.syncSegmentedActive(el.operationsCurrencyScopeTabs, "operations-currency-scope", state.operationsCurrencyScope);
    state.operationsCategoryFilterId = Number(categoryId);
    state.operationsCategoryFilterName = String(categoryName || "").trim();
    if (el.filterQ) {
      el.filterQ.value = "";
    }
    state.filterKind = categoryKind === "income" || categoryKind === "expense" ? categoryKind : "";
    core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
    await navigation.switchSection("operations", { preserveBackStack: true, scrollToTop: true });
  }

  const { calendar = {}, highlights = {}, positions = {}, currency = {} } = getAnalyticsModules();

  const api = {
    loadAnalyticsCalendar: calendar.loadAnalyticsCalendar,
    loadAnalyticsHighlights: highlights.loadAnalyticsHighlights,
    loadAnalyticsPositions: positions.loadAnalyticsPositions,
    loadAnalyticsCurrency: currency.loadAnalyticsCurrency,
    loadDashboardAnalyticsPreview: highlights.loadDashboardAnalyticsPreview,
    abortDashboardAnalyticsPreview: highlights.abortDashboardAnalyticsPreview,
    loadAnalyticsSection,
    shiftAnalyticsMonth: calendar.shiftAnalyticsMonth,
    resetAnalyticsMonth: calendar.resetAnalyticsMonth,
    applyAnalyticsTabUi,
    setAnalyticsTab,
    setAnalyticsCalendarView: calendar.setAnalyticsCalendarView,
    setAnalyticsGridMonthAnchor: calendar.setAnalyticsGridMonthAnchor,
    setAnalyticsGridYearAnchor: calendar.setAnalyticsGridYearAnchor,
    openAnalyticsMonth: calendar.openAnalyticsMonth,
    openOperationsForAnalyticsDate,
    openOperationsForAnalyticsPositionRange,
    openPositionsAnalyticsFromDashboard,
    openOperationsForAnalyticsCategory,
    setCategoryBreakdownHover: highlights.setCategoryBreakdownHover,
    clearCategoryBreakdownHover: highlights.clearCategoryBreakdownHover,
    focusDefaultCategoryBreakdown: highlights.focusDefaultCategoryBreakdown,
    toggleCategoryBreakdownVisibility: highlights.toggleCategoryBreakdownVisibility,
    showAllCategoryBreakdownItems: highlights.showAllCategoryBreakdownItems,
    renderAnalyticsPositions: positions.renderPositions,
    setAnalyticsPositionsPeriod: positions.setPeriod,
    shiftAnalyticsPositionsPeriod: positions.shiftPeriod,
    resetAnalyticsPositionsPeriod: positions.resetPeriod,
    toggleAnalyticsPositionsSort: positions.toggleSort,
    renderAnalyticsPositionsPeriodOptions: positions.renderPeriodOptions,
  };

  window.App.registerRuntimeModule?.("analytics", api);
})();
