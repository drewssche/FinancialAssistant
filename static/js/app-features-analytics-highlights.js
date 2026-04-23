(() => {
  const { state, el, core } = window.App;
  const HIGHLIGHTS_CACHE_TTL_MS = 20000;
  let dashboardAnalyticsPreviewController = null;

  function getHighlightsUi() {
    return window.App.getRuntimeModule?.("analytics-highlights-ui") || {};
  }

  function getAnalyticsModules() {
    return {
      calendar: window.App.getRuntimeModule?.("analytics-calendar-module"),
      trend: window.App.getRuntimeModule?.("analytics-trend-module"),
    };
  }

  function getOperationsFeature() {
    return window.App.getRuntimeModule?.("operations") || {};
  }

  function getLoadingSkeletons() {
    return window.App.getRuntimeModule?.("loading-skeletons") || {};
  }

  function getInlineRefreshState() {
    return window.App.getRuntimeModule?.("inline-refresh-state") || {};
  }

  function getDashboardPeriodBounds() {
    const period = state.dashboardAnalyticsPeriod || "month";
    if (period === "custom" && state.dashboardAnalyticsDateFrom && state.dashboardAnalyticsDateTo) {
      return { dateFrom: state.dashboardAnalyticsDateFrom, dateTo: state.dashboardAnalyticsDateTo };
    }
    return core.getPeriodBounds(period);
  }

  function clearDashboardAnalyticsPreviewController(requestSignal) {
    if (dashboardAnalyticsPreviewController?.signal === requestSignal) {
      dashboardAnalyticsPreviewController = null;
    }
  }

  async function loadDashboardAnalyticsPreview(options = {}) {
    if (dashboardAnalyticsPreviewController) {
      dashboardAnalyticsPreviewController.abort();
    }
    dashboardAnalyticsPreviewController = new AbortController();
    const requestSignal = options.signal || dashboardAnalyticsPreviewController.signal;
    const settings = core.getUiSettings ? core.getUiSettings() : null;
    if (settings && settings.showDashboardAnalytics === false) {
      clearDashboardAnalyticsPreviewController(requestSignal);
      return null;
    }
    if (state.activeSection !== "dashboard") {
      clearDashboardAnalyticsPreviewController(requestSignal);
      return null;
    }
    const operationsFeature = getOperationsFeature();
    if (operationsFeature.ensureAllTimeBounds) {
      await operationsFeature.ensureAllTimeBounds(false, state.dashboardAnalyticsPeriod || "month");
    }
    if (requestSignal.aborted) {
      clearDashboardAnalyticsPreviewController(requestSignal);
      return null;
    }
    const skeletons = getLoadingSkeletons();
    if (!state.dashboardAnalyticsHydrated) {
      skeletons.renderDashboardAnalyticsSkeleton?.();
    }
    const force = options.force === true;
    const period = state.dashboardAnalyticsPeriod || "month";
    const { dateFrom, dateTo } = getDashboardPeriodBounds();
    const params = new URLSearchParams({
      period,
      date_from: dateFrom,
      date_to: dateTo,
      category_kind: state.dashboardCategoryKind || "expense",
      category_breakdown_level: state.dashboardBreakdownLevel || "category",
    });
    const cacheKey = `dashboard:highlights:${params.toString()}`;
    const trendModule = getAnalyticsModules().trend;
    const formatPct = trendModule?.formatPct || ((v) => String(v ?? "нет базы"));
    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, HIGHLIGHTS_CACHE_TTL_MS);
      if (cached) {
        const highlightsUi = getHighlightsUi();
        highlightsUi.renderPeriodKpiBlocks?.(el.dashboardKpiPrimary, el.dashboardKpiSecondary, el.dashboardAnalyticsPeriodLabel, cached, formatPct);
        highlightsUi.renderDashboardBreakdown?.(cached);
        skeletons.clearDashboardAnalyticsSkeletonState?.();
        state.dashboardAnalyticsHydrated = true;
        clearDashboardAnalyticsPreviewController(requestSignal);
        return cached;
      }
    }
    const refreshState = getInlineRefreshState();
    const shouldRefreshInline = state.dashboardAnalyticsHydrated;
    if (shouldRefreshInline) {
      refreshState.begin?.(el.dashboardAnalyticsPanel, "Обновляется");
      refreshState.begin?.(el.dashboardStructurePanel, "Обновляется");
    }
    try {
      const data = await core.requestJson(`/api/v1/dashboard/analytics/highlights?${params.toString()}`, {
        headers: core.authHeaders(),
        signal: requestSignal,
      });
      if (requestSignal.aborted || state.activeSection !== "dashboard") {
        return null;
      }
      core.setUiRequestCache(cacheKey, data);
      const highlightsUi = getHighlightsUi();
      highlightsUi.renderPeriodKpiBlocks?.(el.dashboardKpiPrimary, el.dashboardKpiSecondary, el.dashboardAnalyticsPeriodLabel, data, formatPct);
      highlightsUi.renderDashboardBreakdown?.(data);
      skeletons.clearDashboardAnalyticsSkeletonState?.();
      state.dashboardAnalyticsHydrated = true;
      return data;
    } catch (err) {
      if (core.isAbortError?.(err)) {
        return null;
      }
      throw err;
    } finally {
      clearDashboardAnalyticsPreviewController(requestSignal);
      if (shouldRefreshInline) {
        refreshState.end?.(el.dashboardAnalyticsPanel);
        refreshState.end?.(el.dashboardStructurePanel);
      }
    }
  }

  function abortDashboardAnalyticsPreview() {
    if (dashboardAnalyticsPreviewController) {
      dashboardAnalyticsPreviewController.abort();
      dashboardAnalyticsPreviewController = null;
    }
  }

  function buildHighlightsParams(month) {
    const period = state.analyticsGlobalPeriod || "month";
    const params = new URLSearchParams({
      period,
      month,
      category_kind: state.analyticsCategoryKind || "expense",
      category_breakdown_level: state.analyticsBreakdownLevel || "category",
    });
    if (period === "custom" && state.analyticsGlobalDateFrom && state.analyticsGlobalDateTo) {
      params.set("date_from", state.analyticsGlobalDateFrom);
      params.set("date_to", state.analyticsGlobalDateTo);
    }
    return params;
  }

  async function loadAnalyticsHighlights(options = {}) {
    const force = options.force === true;
    const calendarModule = getAnalyticsModules().calendar;
    const month = state.analyticsMonthAnchor || calendarModule?.serializeMonthAnchor?.(calendarModule.currentAnchorDate()) || "";
    const operationsFeature = getOperationsFeature();
    if (operationsFeature.ensureAllTimeBounds) {
      await operationsFeature.ensureAllTimeBounds(false, state.analyticsGlobalPeriod || "month");
    }
    const params = buildHighlightsParams(month);
    const cacheKey = `analytics:highlights:${params.toString()}`;
    const skeletons = getLoadingSkeletons();
    if (!state.analyticsStructureHydrated && state.activeSection === "analytics" && (state.analyticsTab || "calendar") === "structure") {
      skeletons.renderAnalyticsStructureSkeleton?.();
    }

    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, HIGHLIGHTS_CACHE_TTL_MS);
      if (cached) {
        const highlightsUi = getHighlightsUi();
        highlightsUi.renderAnalyticsHighlights?.(cached);
        skeletons.clearAnalyticsStructureSkeletonState?.();
        state.analyticsStructureHydrated = true;
        return cached;
      }
    }
    const refreshState = getInlineRefreshState();
    const shouldRefreshInline = state.analyticsStructureHydrated;
    if (shouldRefreshInline) {
      refreshState.begin?.(el.analyticsStructurePanel, "Обновляется");
    }

    try {
      const data = await core.requestJson(`/api/v1/dashboard/analytics/highlights?${params.toString()}`, {
        headers: core.authHeaders(),
      });
      core.setUiRequestCache(cacheKey, data);
      const highlightsUi = getHighlightsUi();
      highlightsUi.renderAnalyticsHighlights?.(data);
      skeletons.clearAnalyticsStructureSkeletonState?.();
      state.analyticsStructureHydrated = true;
      return data;
    } catch (err) {
      const message = core.errorMessage ? core.errorMessage(err) : String(err);
      if (!String(message).includes("[404]")) {
        throw err;
      }
      const fallback = {
        period: state.analyticsGlobalPeriod || "month",
        category_breakdown_kind: state.analyticsCategoryKind || "expense",
        category_breakdown_level: state.analyticsBreakdownLevel || "category",
        date_from: state.analyticsGlobalDateFrom || `${month}-01`,
        date_to: state.analyticsGlobalDateTo || `${month}-01`,
        month,
        month_start: `${month}-01`,
        month_end: `${month}-01`,
        income_total: "0",
        expense_total: "0",
        balance: "0",
        debt_cashflow_total: "0",
        fx_cashflow_total: "0",
        cashflow_total: "0",
        prev_income_total: "0",
        prev_expense_total: "0",
        prev_balance: "0",
        prev_debt_cashflow_total: "0",
        prev_fx_cashflow_total: "0",
        prev_cashflow_total: "0",
        prev_operations_count: 0,
        surplus_total: "0",
        deficit_total: "0",
        operations_count: 0,
        avg_daily_expense: "0",
        max_expense_day_date: null,
        max_expense_day_total: "0",
        income_change_pct: 0,
        expense_change_pct: 0,
        balance_change_pct: 0,
        debt_cashflow_change_pct: 0,
        fx_cashflow_change_pct: 0,
        cashflow_change_pct: 0,
        operations_change_pct: 0,
        category_breakdown: [],
        top_operations: [],
        top_categories: [],
        anomalies: [],
        top_positions: [],
        price_increases: [],
      };
      const highlightsUi = getHighlightsUi();
      highlightsUi.renderAnalyticsHighlights?.(fallback);
      skeletons.clearAnalyticsStructureSkeletonState?.();
      state.analyticsStructureHydrated = true;
      return fallback;
    } finally {
      if (shouldRefreshInline) {
        refreshState.end?.(el.analyticsStructurePanel);
      }
    }
  }

  const api = {
    loadAnalyticsHighlights,
    loadDashboardAnalyticsPreview,
    abortDashboardAnalyticsPreview,
    setCategoryBreakdownHover: (...args) => getHighlightsUi().setCategoryBreakdownHover?.(...args),
    clearCategoryBreakdownHover: (...args) => getHighlightsUi().clearCategoryBreakdownHover?.(...args),
    setDashboardBreakdownHover: (...args) => getHighlightsUi().setDashboardBreakdownHover?.(...args),
    clearDashboardBreakdownHover: (...args) => getHighlightsUi().clearDashboardBreakdownHover?.(...args),
    focusDefaultCategoryBreakdown: (...args) => getHighlightsUi().focusDefaultCategoryBreakdown?.(...args),
    toggleCategoryBreakdownVisibility: (...args) => getHighlightsUi().toggleCategoryBreakdownVisibility?.(...args),
    showAllCategoryBreakdownItems: (...args) => getHighlightsUi().showAllCategoryBreakdownItems?.(...args),
    getDashboardPeriodBounds,
  };

  window.App.registerRuntimeModule?.("analytics-highlights-module", api);
})();
