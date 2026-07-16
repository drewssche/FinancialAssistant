(() => {
  const { state, el, core } = window.App;

  function getNavigationActions() {
    return window.App.getRuntimeModule?.("navigation") || {};
  }

  function getAnalyticsModules() {
    return {
      calendar: window.App.getRuntimeModule?.("analytics-calendar-module"),
      trend: window.App.getRuntimeModule?.("analytics-trend-module"),
      highlights: window.App.getRuntimeModule?.("analytics-highlights-module"),
      positions: window.App.getRuntimeModule?.("analytics-positions-module"),
      commerce: window.App.getRuntimeModule?.("analytics-commerce-module"),
      currency: window.App.getRuntimeModule?.("analytics-currency-module"),
    };
  }

  function applyAnalyticsTabUi() {
    const tab = state.analyticsTab || "calendar";
    const panels = [
      { id: "structure", node: el.analyticsStructurePanel },
      { id: "positions", node: el.analyticsPositionsPanel },
      { id: "commerce", node: el.analyticsCommercePanel },
      { id: "calendar", node: el.analyticsCalendarPanel },
      { id: "trends", node: el.analyticsTrendsPanel },
      { id: "currency", node: el.analyticsCurrencyPanel },
    ];
    for (const item of panels) {
      if (!item.node) {
        continue;
      }
      item.node.classList.toggle("hidden", item.id !== tab);
    }
    if (el.analyticsGlobalScopePanel) {
      el.analyticsGlobalScopePanel.classList.toggle("hidden", tab === "calendar" || tab === "currency" || tab === "positions");
    }
    core.syncSegmentedActive(el.analyticsViewTabs, "analytics-tab", tab);
  }

  function setAnalyticsTab(tab) {
    const allowed = new Set(["structure", "positions", "commerce", "calendar", "trends", "currency"]);
    state.analyticsTab = allowed.has(tab) ? tab : "calendar";
    applyAnalyticsTabUi();
    if (state.analyticsTab === "structure") {
      getAnalyticsModules().highlights?.focusDefaultCategoryBreakdown?.();
    }
  }

  async function loadAnalyticsSection(options = {}) {
    const { calendar, trend, highlights, positions, currency } = getAnalyticsModules();
    const tab = state.analyticsTab || "calendar";

    applyAnalyticsTabUi();
    calendar?.applyCalendarViewUi?.();
    if (tab === "calendar") {
      return calendar?.loadAnalyticsCalendar?.(options) || null;
    }
    if (tab === "trends") {
      return trend?.loadAnalyticsTrend?.(options) || null;
    }
    if (tab === "positions") {
      return positions?.loadAnalyticsPositions?.(options) || null;
    }
    if (tab === "commerce") {
      return highlights?.loadAnalyticsHighlights?.(options) || null;
    }
    if (tab === "currency") {
      return currency?.loadAnalyticsCurrency?.(options) || null;
    }
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

  async function openOperationsForAnalyticsRange(dateFrom, dateTo) {
    const navigation = getNavigationActions();
    if (!dateFrom || !dateTo || !navigation.switchSection) {
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
    core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
    core.syncSegmentedActive(el.operationsQuickViewTabs, "operations-quick-view", state.operationsQuickView);
    core.syncSegmentedActive(el.operationsCurrencyScopeTabs, "operations-currency-scope", state.operationsCurrencyScope);
    if (el.filterQ) {
      el.filterQ.value = "";
    }
    state.period = "custom";
    state.customDateFrom = dateFrom;
    state.customDateTo = dateTo;
    core.syncAllPeriodTabs("custom");
    await navigation.switchSection("operations", { preserveBackStack: true, scrollToTop: true });
  }

  async function openOperationsForAnalyticsPositionRange(templateId, positionName, dateFrom, dateTo) {
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
    state.operationsItemTemplateFilterId = Number(templateId || 0) || null;
    state.operationsItemTemplateFilterName = String(positionName || "").trim();
    if (el.filterQ) {
      el.filterQ.value = state.operationsItemTemplateFilterId ? "" : state.operationsItemTemplateFilterName;
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
    setAnalyticsTab("positions");
    await navigation.switchSection?.("analytics", { preserveBackStack: true, scrollToTop: true });
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

  const { calendar = {}, trend = {}, highlights = {}, positions = {}, currency = {} } = getAnalyticsModules();

  const api = {
    loadAnalyticsCalendar: calendar.loadAnalyticsCalendar,
    loadAnalyticsTrend: trend.loadAnalyticsTrend,
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
    openOperationsForAnalyticsRange,
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
