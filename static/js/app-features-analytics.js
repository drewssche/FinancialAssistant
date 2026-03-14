(() => {
  const { state, el, core } = window.App;

  function applyAnalyticsTabUi() {
    const tab = state.analyticsTab || "calendar";
    const panels = [
      { id: "structure", node: el.analyticsStructurePanel },
      { id: "calendar", node: el.analyticsCalendarPanel },
      { id: "trends", node: el.analyticsTrendsPanel },
    ];
    for (const item of panels) {
      if (!item.node) {
        continue;
      }
      item.node.classList.toggle("hidden", item.id !== tab);
    }
    if (el.analyticsGlobalScopePanel) {
      el.analyticsGlobalScopePanel.classList.toggle("hidden", tab === "calendar");
    }
    core.syncSegmentedActive(el.analyticsViewTabs, "analytics-tab", tab);
  }

  function setAnalyticsTab(tab) {
    const allowed = new Set(["structure", "calendar", "trends"]);
    state.analyticsTab = allowed.has(tab) ? tab : "calendar";
    applyAnalyticsTabUi();
    if (state.analyticsTab === "structure") {
      highlights?.focusDefaultCategoryBreakdown?.();
    }
  }

  async function loadAnalyticsSection(options = {}) {
    const calendar = window.App.featureAnalyticsModules?.calendar;
    const trend = window.App.featureAnalyticsModules?.trend;
    const highlights = window.App.featureAnalyticsModules?.highlights;

    applyAnalyticsTabUi();
    calendar?.applyCalendarViewUi?.();
    await Promise.all([
      calendar?.loadAnalyticsCalendar?.(options),
      trend?.loadAnalyticsTrend?.(options),
      highlights?.loadAnalyticsHighlights?.(options),
    ]);
  }

  async function openOperationsForAnalyticsDate(dayIso) {
    if (!dayIso || !window.App.actions.switchSection) {
      return;
    }
    window.App.actions.pushSectionBackContext?.();
    state.operationsCategoryFilterId = null;
    state.operationsCategoryFilterName = "";
    state.filterKind = "";
    state.operationsQuickView = "all";
    core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
    core.syncSegmentedActive(el.operationsQuickViewTabs, "operations-quick-view", state.operationsQuickView);
    if (el.filterQ) {
      el.filterQ.value = "";
    }
    state.period = "custom";
    state.customDateFrom = dayIso;
    state.customDateTo = dayIso;
    core.syncAllPeriodTabs("custom");
    await window.App.actions.switchSection("operations");
  }

  async function openOperationsForAnalyticsRange(dateFrom, dateTo) {
    if (!dateFrom || !dateTo || !window.App.actions.switchSection) {
      return;
    }
    window.App.actions.pushSectionBackContext?.();
    state.operationsCategoryFilterId = null;
    state.operationsCategoryFilterName = "";
    state.filterKind = "";
    state.operationsQuickView = "all";
    core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
    core.syncSegmentedActive(el.operationsQuickViewTabs, "operations-quick-view", state.operationsQuickView);
    if (el.filterQ) {
      el.filterQ.value = "";
    }
    state.period = "custom";
    state.customDateFrom = dateFrom;
    state.customDateTo = dateTo;
    core.syncAllPeriodTabs("custom");
    await window.App.actions.switchSection("operations");
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
    if (!window.App.actions.switchSection || !categoryId) {
      return;
    }
    window.App.actions.pushSectionBackContext?.();
    applyAnalyticsScopeToOperations();
    state.operationsQuickView = "all";
    core.syncSegmentedActive(el.operationsQuickViewTabs, "operations-quick-view", state.operationsQuickView);
    state.operationsCategoryFilterId = Number(categoryId);
    state.operationsCategoryFilterName = String(categoryName || "").trim();
    if (el.filterQ) {
      el.filterQ.value = "";
    }
    state.filterKind = categoryKind === "income" || categoryKind === "expense" ? categoryKind : "";
    core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
    await window.App.actions.switchSection("operations");
  }

  const calendar = window.App.featureAnalyticsModules?.calendar || {};
  const trend = window.App.featureAnalyticsModules?.trend || {};
  const highlights = window.App.featureAnalyticsModules?.highlights || {};

  window.App.featureAnalytics = {
    loadAnalyticsCalendar: calendar.loadAnalyticsCalendar,
    loadAnalyticsTrend: trend.loadAnalyticsTrend,
    loadAnalyticsHighlights: highlights.loadAnalyticsHighlights,
    loadDashboardAnalyticsPreview: highlights.loadDashboardAnalyticsPreview,
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
    openOperationsForAnalyticsCategory,
    setCategoryBreakdownHover: highlights.setCategoryBreakdownHover,
    clearCategoryBreakdownHover: highlights.clearCategoryBreakdownHover,
    focusDefaultCategoryBreakdown: highlights.focusDefaultCategoryBreakdown,
    toggleCategoryBreakdownVisibility: highlights.toggleCategoryBreakdownVisibility,
    showAllCategoryBreakdownItems: highlights.showAllCategoryBreakdownItems,
  };
})();
