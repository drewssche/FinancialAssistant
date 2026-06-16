function createAnalyticsPeriodControls({ state, el, core, actions, coordinator, pickerUtils }) {
  const periodControlUtils = window.App.getRuntimeModule?.("period-control-utils") || {};

  function shiftRelativeBounds(period, direction, currentBounds = null) {
    return periodControlUtils.shiftPeriodBounds?.({
      period,
      direction,
      currentBounds,
      getPeriodBounds: (value) => core.getPeriodBounds(value),
    }) || currentBounds || core.getPeriodBounds(period);
  }

  function closeQuickPeriodPopovers() {
    pickerUtils.setPopoverOpen?.(el.dashboardAnalyticsPeriodPopover, false, {
      owners: [el.dashboardAnalyticsPeriodTabs].filter(Boolean),
    });
    pickerUtils.setPopoverOpen?.(el.analyticsGlobalPeriodPopover, false, {
      owners: [el.analyticsGlobalPeriodTabs].filter(Boolean),
    });
  }

  function renderQuickPeriodOptions(scope, period) {
    const optionsHost = scope === "dashboard" ? el.dashboardAnalyticsPeriodOptions : el.analyticsGlobalPeriodOptions;
    if (!optionsHost) {
      return;
    }
    const periodAttr = scope === "dashboard" ? "dashboard" : "analytics";
    const currentValue = scope === "dashboard" ? state.dashboardAnalyticsPeriod : state.analyticsGlobalPeriod;
    const options = [
      ["day", "День"],
      ["week", "Неделя"],
      ["month", "Месяц"],
      ["year", "Год"],
      ["all_time", "Все время"],
    ];
    optionsHost.innerHTML = [
      ...options.map(([value, label]) => {
        const bounds = core.getPeriodBounds(value);
        return `
          <button class="btn btn-secondary settings-picker-option ${currentValue === value ? "active" : ""}" type="button" data-quick-period-scope="${scope}" data-${periodAttr}-period-choice="${value}">
            ${label}
            <span class="muted-small">${core.formatPeriodLabel(bounds.dateFrom, bounds.dateTo)}</span>
          </button>
        `;
      }),
      `
        <button class="btn btn-secondary settings-picker-option" type="button" data-quick-period-scope="${scope}" data-quick-period="${period}" data-quick-period-action="custom">
          Диапазон
          <span class="muted-small">Открыть ручной диапазон дат</span>
        </button>
      `,
    ].join("");
  }

  function openQuickPeriodPopover(scope, period, trigger) {
    const popover = scope === "dashboard" ? el.dashboardAnalyticsPeriodPopover : el.analyticsGlobalPeriodPopover;
    const tabs = scope === "dashboard" ? el.dashboardAnalyticsPeriodTabs : el.analyticsGlobalPeriodTabs;
    if (!popover || !pickerUtils.setPopoverOpen) {
      return;
    }
    renderQuickPeriodOptions(scope, period);
    const dashboardPopover = el.dashboardAnalyticsPeriodPopover;
    const analyticsPopover = el.analyticsGlobalPeriodPopover;
    if (dashboardPopover && dashboardPopover !== popover) {
      pickerUtils.setPopoverOpen(dashboardPopover, false, { owners: [el.dashboardAnalyticsPeriodTabs].filter(Boolean) });
    }
    if (analyticsPopover && analyticsPopover !== popover) {
      pickerUtils.setPopoverOpen(analyticsPopover, false, { owners: [el.analyticsGlobalPeriodTabs].filter(Boolean) });
    }
    pickerUtils.setPopoverOpen(popover, true, {
      owners: [trigger || tabs].filter(Boolean),
      onClose: () => closeQuickPeriodPopovers(),
    });
  }

  function applyDashboardQuickPeriod(action, period) {
    closeQuickPeriodPopovers();
    if (action === "custom") {
      state.dashboardAnalyticsPendingCustom = true;
      const baseBounds = core.getPeriodBounds(period);
      core.syncDateFieldValue(el.customDateFrom, state.dashboardAnalyticsDateFrom || baseBounds.dateFrom || "");
      core.syncDateFieldValue(el.customDateTo, state.dashboardAnalyticsDateTo || baseBounds.dateTo || "");
      actions.openPeriodCustomModal();
      return;
    }
    const bounds = action === "previous" ? shiftRelativeBounds(period, -1) : core.getPeriodBounds(period);
    coordinator.runPersistedAction({
      errorPrefix: "Ошибка загрузки аналитики дашборда",
      action: async () => {
        if (action === "previous") {
          state.dashboardAnalyticsPeriod = "custom";
          state.dashboardAnalyticsDateFrom = bounds.dateFrom;
          state.dashboardAnalyticsDateTo = bounds.dateTo;
          core.syncSegmentedActive(el.dashboardAnalyticsPeriodTabs, "dashboard-analytics-period", "custom");
        } else {
          state.dashboardAnalyticsPeriod = period;
          state.dashboardAnalyticsDateFrom = "";
          state.dashboardAnalyticsDateTo = "";
          core.syncSegmentedActive(el.dashboardAnalyticsPeriodTabs, "dashboard-analytics-period", period);
        }
        await actions.loadDashboardAnalyticsPreview?.({ force: true });
      },
    });
  }

  function applyDashboardPeriodChoice(period) {
    closeQuickPeriodPopovers();
    if (period === "custom") {
      state.dashboardAnalyticsPendingCustom = true;
      core.syncDateFieldValue(el.customDateFrom, state.dashboardAnalyticsDateFrom || "");
      core.syncDateFieldValue(el.customDateTo, state.dashboardAnalyticsDateTo || "");
      actions.openPeriodCustomModal();
      return;
    }
    state.dashboardAnalyticsPendingCustom = false;
    coordinator.applySegmentedSelection({
      currentValue: state.dashboardAnalyticsPeriod,
      nextValue: period,
      assignValue: (value) => {
        state.dashboardAnalyticsPeriod = value;
        state.dashboardAnalyticsDateFrom = "";
        state.dashboardAnalyticsDateTo = "";
      },
      syncContainer: el.dashboardAnalyticsPeriodTabs,
      syncAttr: "dashboard-analytics-period",
      errorPrefix: "Ошибка загрузки аналитики дашборда",
      action: () => actions.loadDashboardAnalyticsPreview({ force: true }),
    });
  }

  function shiftDashboardPeriod(delta) {
    if (state.dashboardAnalyticsPeriod === "all_time") {
      return;
    }
    const periodValues = ["day", "week", "month", "year"];
    const basePeriod = periodValues.includes(state.dashboardAnalyticsPeriod)
      ? state.dashboardAnalyticsPeriod
      : "month";
    const currentBounds = state.dashboardAnalyticsPeriod === "custom" && state.dashboardAnalyticsDateFrom && state.dashboardAnalyticsDateTo
      ? { dateFrom: state.dashboardAnalyticsDateFrom, dateTo: state.dashboardAnalyticsDateTo }
      : null;
    const bounds = shiftRelativeBounds(basePeriod, delta, currentBounds);
    state.dashboardAnalyticsPeriod = "custom";
    state.dashboardAnalyticsDateFrom = bounds.dateFrom;
    state.dashboardAnalyticsDateTo = bounds.dateTo;
    core.syncSegmentedActive(el.dashboardAnalyticsPeriodTabs, "dashboard-analytics-period", "custom");
    coordinator.runPersistedAction({
      errorPrefix: "Ошибка загрузки аналитики дашборда",
      action: () => actions.loadDashboardAnalyticsPreview?.({ force: true }),
    });
  }

  function applyAnalyticsGlobalQuickPeriod(action, period) {
    closeQuickPeriodPopovers();
    if (action === "custom") {
      state.analyticsGlobalPendingCustom = true;
      const baseBounds = core.getPeriodBounds(period);
      core.syncDateFieldValue(el.customDateFrom, state.analyticsGlobalDateFrom || baseBounds.dateFrom || "");
      core.syncDateFieldValue(el.customDateTo, state.analyticsGlobalDateTo || baseBounds.dateTo || "");
      actions.openPeriodCustomModal();
      return;
    }
    const bounds = action === "previous" ? shiftRelativeBounds(period, -1) : core.getPeriodBounds(period);
    coordinator.runPersistedAction({
      errorPrefix: "Ошибка загрузки аналитики",
      action: async () => {
        if (action === "previous") {
          state.analyticsGlobalPeriod = "custom";
          state.analyticsGlobalDateFrom = bounds.dateFrom;
          state.analyticsGlobalDateTo = bounds.dateTo;
          core.syncSegmentedActive(el.analyticsGlobalPeriodTabs, "analytics-global-period", "custom");
        } else {
          state.analyticsGlobalPeriod = period;
          state.analyticsGlobalDateFrom = "";
          state.analyticsGlobalDateTo = "";
          core.syncSegmentedActive(el.analyticsGlobalPeriodTabs, "analytics-global-period", period);
        }
        if (((action === "current" ? period : "custom") === "year" || (action === "current" ? period : state.analyticsGlobalPeriod) === "all_time") && state.analyticsGranularity === "day") {
          state.analyticsGranularity = "week";
          core.syncSegmentedActive(el.analyticsGranularityTabs, "analytics-granularity", state.analyticsGranularity);
        }
        if (action === "current" && (period === "year" || period === "all_time") && state.analyticsGranularity === "day") {
          state.analyticsGranularity = "week";
          core.syncSegmentedActive(el.analyticsGranularityTabs, "analytics-granularity", state.analyticsGranularity);
        }
        await actions.loadAnalyticsSection?.({ force: true });
      },
    });
  }

  function applyAnalyticsGlobalPeriodChoice(period) {
    closeQuickPeriodPopovers();
    if (period === "custom") {
      state.analyticsGlobalPendingCustom = true;
      core.syncDateFieldValue(el.customDateFrom, state.analyticsGlobalDateFrom || "");
      core.syncDateFieldValue(el.customDateTo, state.analyticsGlobalDateTo || "");
      actions.openPeriodCustomModal();
      return;
    }
    state.analyticsGlobalPendingCustom = false;
    state.analyticsGlobalPeriodStepGranularity = period;
    coordinator.applySegmentedSelection({
      currentValue: state.analyticsGlobalPeriod,
      nextValue: period,
      assignValue: (value) => {
        state.analyticsGlobalPeriod = value;
        state.analyticsGlobalDateFrom = "";
        state.analyticsGlobalDateTo = "";
        if ((value === "year" || value === "all_time") && state.analyticsGranularity === "day") {
          state.analyticsGranularity = "week";
          core.syncSegmentedActive(el.analyticsGranularityTabs, "analytics-granularity", state.analyticsGranularity);
        }
      },
      syncContainer: el.analyticsGlobalPeriodTabs,
      syncAttr: "analytics-global-period",
      errorPrefix: "Ошибка загрузки аналитики",
      action: () => actions.loadAnalyticsSection({ force: true }),
    });
  }

  function shiftAnalyticsGlobalPeriod(delta) {
    if (state.analyticsGlobalPeriod === "all_time") {
      return;
    }
    const periodValues = ["day", "week", "month", "year"];
    const basePeriod = periodValues.includes(state.analyticsGlobalPeriod)
      ? state.analyticsGlobalPeriod
      : (periodValues.includes(state.analyticsGlobalPeriodStepGranularity) ? state.analyticsGlobalPeriodStepGranularity : "day");
    const currentBounds = state.analyticsGlobalPeriod === "custom" && state.analyticsGlobalDateFrom && state.analyticsGlobalDateTo
      ? { dateFrom: state.analyticsGlobalDateFrom, dateTo: state.analyticsGlobalDateTo }
      : null;
    const bounds = shiftRelativeBounds(basePeriod, delta, currentBounds);
    state.analyticsGlobalPeriodStepGranularity = basePeriod;
    state.analyticsGlobalPeriod = "custom";
    state.analyticsGlobalDateFrom = bounds.dateFrom;
    state.analyticsGlobalDateTo = bounds.dateTo;
    core.syncSegmentedActive(el.analyticsGlobalPeriodTabs, "analytics-global-period", "custom");
    coordinator.runPersistedAction({
      errorPrefix: "Ошибка загрузки аналитики",
      action: () => actions.loadAnalyticsSection?.({ force: true }),
    });
  }

  return {
    applyAnalyticsGlobalPeriodChoice,
    applyAnalyticsGlobalQuickPeriod,
    applyDashboardPeriodChoice,
    applyDashboardQuickPeriod,
    openQuickPeriodPopover,
    shiftDashboardPeriod,
    shiftAnalyticsGlobalPeriod,
  };
}

window.App.registerRuntimeModule?.("analytics-period-controls", createAnalyticsPeriodControls);
