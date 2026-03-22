(() => {
  const { state, el, core } = window.App;
  const shared = window.App.analyticsShared || {};
  const BREAKDOWN_PALETTE = ["#ff8f6b", "#5fd3bc", "#7aa8ff", "#ffd166", "#c084fc", "#5eead4", "#fb7185", "#93c5fd", "#a3e635"];
  const DONUT_CENTER = 130;
  const DONUT_OUTER_RADIUS = 118;
  const DONUT_INNER_RADIUS = 62;
  const escapeHtml = shared.escapeHtml || ((value) => String(value ?? ""));
  const renderInsightList = shared.renderInsightList || (() => {});
  const renderPeriodKpiBlocks = shared.renderPeriodKpiBlocks || (() => {});
  const categoryKindLabel = shared.categoryKindLabel || ((kind) => kind);
  const categoryKindShort = shared.categoryKindShort || ((kind) => kind);
  const breakdownEntityLabel = shared.breakdownEntityLabel || ((level) => level);
  const breakdownEntityCountLabel = shared.breakdownEntityCountLabel || ((level) => level);
  const breakdownTitle = shared.breakdownTitle || ((level) => level);
  const breakdownItemKey = shared.breakdownItemKey || ((level, item) => `${level}:${item?.id ?? "none"}`);
  const buildDonutSegmentPath = shared.buildDonutSegmentPath || (() => "");
  let activeBreakdown = {
    items: [],
    listItems: [],
    kind: "expense",
    level: "category",
    total: 0,
    totalOps: 0,
    defaultIndex: null,
    hoveredIndex: null,
  };
  let activeDashboardBreakdown = {
    items: [],
    kind: "expense",
    level: "category",
    total: 0,
    totalOps: 0,
    defaultIndex: null,
    hoveredIndex: null,
  };

  function getSessionFeature() {
    return window.App.getRuntimeModule?.("session") || {};
  }

  function getBreakdownUiCoordinator() {
    return window.App.getRuntimeModule?.("analytics-breakdown-ui-coordinator") || {};
  }

  function getHoverStateCoordinator() {
    return window.App.getRuntimeModule?.("analytics-hover-state-coordinator") || {};
  }

  function getVisibilityCoordinator() {
    return window.App.getRuntimeModule?.("analytics-breakdown-visibility-coordinator") || {};
  }

  function getSnapshotCoordinator() {
    return window.App.getRuntimeModule?.("analytics-breakdown-snapshot-coordinator") || {};
  }

  function getRenderCoordinator() {
    return window.App.getRuntimeModule?.("analytics-breakdown-render-coordinator") || {};
  }

  function hiddenBreakdownKeys(level, kind) {
    return getVisibilityCoordinator().hiddenBreakdownKeys?.({ state, level, kind }) || new Set();
  }

  function applyCategoryBreakdownHover(index = null) {
    getHoverStateCoordinator().applyBreakdownHoverState?.({
      snapshot: activeBreakdown,
      index,
      chartNode: el.analyticsCategoryBreakdownChart,
      indexSelector: "[data-analytics-category-index]",
      indexDatasetName: "analyticsCategoryIndex",
      titleNode: el.analyticsCategoryBreakdownChartTitle,
      periodNode: el.analyticsCategoryBreakdownChartPeriod,
      valueNode: el.analyticsCategoryBreakdownChartValue,
      metaNode: el.analyticsCategoryBreakdownChartMeta,
      palette: BREAKDOWN_PALETTE,
      formatMoney: core.formatMoney,
      countLabel: breakdownEntityCountLabel,
    });
  }

  function applyDashboardBreakdownHover(index = null) {
    getHoverStateCoordinator().applyBreakdownHoverState?.({
      snapshot: activeDashboardBreakdown,
      index,
      chartNode: el.dashboardCategoryBreakdownChart,
      indexSelector: "[data-dashboard-category-index]",
      indexDatasetName: "dashboardCategoryIndex",
      titleNode: el.dashboardCategoryBreakdownChartTitle,
      periodNode: el.dashboardCategoryBreakdownChartPeriod,
      valueNode: el.dashboardCategoryBreakdownChartValue,
      metaNode: el.dashboardCategoryBreakdownChartMeta,
      palette: BREAKDOWN_PALETTE,
      formatMoney: core.formatMoney,
      countLabel: breakdownEntityCountLabel,
    });
  }

  function setCategoryBreakdownHover(indexValue) {
    const index = Number(indexValue);
    if (!Number.isInteger(index) || index < 0 || index >= activeBreakdown.items.length) {
      applyCategoryBreakdownHover(null);
      return;
    }
    applyCategoryBreakdownHover(index);
  }

  function clearCategoryBreakdownHover() {
    applyCategoryBreakdownHover(null);
  }

  function setDashboardBreakdownHover(indexValue) {
    const index = Number(indexValue);
    if (!Number.isInteger(index) || index < 0 || index >= activeDashboardBreakdown.items.length) {
      applyDashboardBreakdownHover(null);
      return;
    }
    applyDashboardBreakdownHover(index);
  }

  function clearDashboardBreakdownHover() {
    applyDashboardBreakdownHover(null);
  }

  function toggleCategoryBreakdownVisibility(key) {
    getVisibilityCoordinator().toggleCategoryBreakdownVisibility?.({
      key,
      activeBreakdown,
      state,
      renderCategoryBreakdown,
      savePreferencesDebounced: getSessionFeature().savePreferencesDebounced,
    });
  }

  function showAllCategoryBreakdownItems() {
    getVisibilityCoordinator().showAllCategoryBreakdownItems?.({
      activeBreakdown,
      state,
      renderCategoryBreakdown,
      savePreferencesDebounced: getSessionFeature().savePreferencesDebounced,
    });
  }

  function focusDefaultCategoryBreakdown() {
    applyCategoryBreakdownHover(null);
  }

  function renderCategoryBreakdown(data, formatPct) {
    activeBreakdown = {
      ...getSnapshotCoordinator().buildCategoryBreakdownSnapshot?.({
        data,
        state,
        hiddenBreakdownKeys,
        breakdownItemKey,
        formatDateRu: core.formatDateRu,
      }),
      payload: data,
      formatPct,
    };
    getRenderCoordinator().renderAnalyticsCategoryBreakdownView?.({
      snapshot: activeBreakdown,
      el,
      palette: BREAKDOWN_PALETTE,
      categoryKindLabel,
      categoryKindShort,
      breakdownEntityLabel,
      breakdownEntityCountLabel,
      breakdownTitle,
      renderInsightList,
      escapeHtml,
      formatMoney: core.formatMoney,
      syncSegmentedActive: core.syncSegmentedActive,
      breakdownUiCoordinator: getBreakdownUiCoordinator(),
      setCategoryBreakdownHover,
      clearCategoryBreakdownHover,
      buildDonutSegmentPath,
      donutCenter: DONUT_CENTER,
      donutOuterRadius: DONUT_OUTER_RADIUS,
      donutInnerRadius: DONUT_INNER_RADIUS,
    });
    focusDefaultCategoryBreakdown();
  }

  function renderAnalyticsHighlights(data) {
    const trendModule = window.App.getRuntimeModule?.("analytics-trend-module");
    const formatPct = trendModule?.formatPct || ((v) => String(v ?? "нет базы"));
    if (el.analyticsGlobalRangeLabel) {
      el.analyticsGlobalRangeLabel.textContent = `${core.formatDateRu(data.date_from)} - ${core.formatDateRu(data.date_to)}`;
    }
    renderCategoryBreakdown(data, formatPct);
  }

  function renderDashboardBreakdown(data) {
    activeDashboardBreakdown = getSnapshotCoordinator().buildDashboardBreakdownSnapshot?.({
      data,
      state,
      formatDateRu: core.formatDateRu,
    }) || activeDashboardBreakdown;
    getRenderCoordinator().renderDashboardBreakdownView?.({
      snapshot: activeDashboardBreakdown,
      data: {
        ...data,
        date_from: core.formatDateRu(data.date_from),
        date_to: core.formatDateRu(data.date_to),
      },
      el,
      palette: BREAKDOWN_PALETTE,
      escapeHtml,
      renderInsightList,
      formatMoney: core.formatMoney,
      syncSegmentedActive: core.syncSegmentedActive,
      categoryKindLabel,
      categoryKindShort,
      breakdownEntityLabel,
      breakdownEntityCountLabel,
      breakdownUiCoordinator: getBreakdownUiCoordinator(),
      setDashboardBreakdownHover,
      clearDashboardBreakdownHover,
      buildDonutSegmentPath,
      donutCenter: DONUT_CENTER,
      donutOuterRadius: DONUT_OUTER_RADIUS,
      donutInnerRadius: DONUT_INNER_RADIUS,
    });
    applyDashboardBreakdownHover(null);
  }

  const api = {
    renderPeriodKpiBlocks,
    renderCategoryBreakdown,
    renderAnalyticsHighlights,
    renderDashboardBreakdown,
    setCategoryBreakdownHover,
    clearCategoryBreakdownHover,
    setDashboardBreakdownHover,
    clearDashboardBreakdownHover,
    focusDefaultCategoryBreakdown,
    toggleCategoryBreakdownVisibility,
    showAllCategoryBreakdownItems,
  };

  window.App.registerRuntimeModule?.("analytics-highlights-ui", api);
})();
