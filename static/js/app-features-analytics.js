(() => {
  const { state, el, core } = window.App;

  function applyAnalyticsTabUi() {
    const tab = state.analyticsTab || "overview";
    const panels = [
      { id: "overview", node: el.analyticsOverviewPanel },
      { id: "calendar", node: el.analyticsCalendarPanel },
      { id: "operations", node: el.analyticsOperationsPanel },
      { id: "trends", node: el.analyticsTrendsPanel },
    ];
    for (const item of panels) {
      if (!item.node) {
        continue;
      }
      item.node.classList.toggle("hidden", item.id !== tab);
    }
    core.syncSegmentedActive(el.analyticsViewTabs, "analytics-tab", tab);
  }

  function setAnalyticsTab(tab) {
    const allowed = new Set(["overview", "calendar", "operations", "trends"]);
    state.analyticsTab = allowed.has(tab) ? tab : "overview";
    applyAnalyticsTabUi();
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
    state.period = "custom";
    state.customDateFrom = dateFrom;
    state.customDateTo = dateTo;
    core.syncAllPeriodTabs("custom");
    await window.App.actions.switchSection("operations");
  }

  const calendar = window.App.featureAnalyticsModules?.calendar || {};
  const trend = window.App.featureAnalyticsModules?.trend || {};
  const highlights = window.App.featureAnalyticsModules?.highlights || {};

  window.App.featureAnalytics = {
    loadAnalyticsCalendar: calendar.loadAnalyticsCalendar,
    loadAnalyticsTrend: trend.loadAnalyticsTrend,
    loadAnalyticsHighlights: highlights.loadAnalyticsHighlights,
    loadDashboardAnalyticsPreview: trend.loadDashboardAnalyticsPreview,
    loadAnalyticsSection,
    shiftAnalyticsMonth: calendar.shiftAnalyticsMonth,
    resetAnalyticsMonth: calendar.resetAnalyticsMonth,
    applyAnalyticsTabUi,
    setAnalyticsTab,
    setAnalyticsCalendarView: calendar.setAnalyticsCalendarView,
    openAnalyticsMonth: calendar.openAnalyticsMonth,
    openOperationsForAnalyticsDate,
    openOperationsForAnalyticsRange,
  };
})();
