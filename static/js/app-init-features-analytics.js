(() => {
  const { state, el, core, actions } = window.App;
  const hoverCoordinator = getAnalyticsHoverCoordinator();
  const coordinator = getAnalyticsUiCoordinator();
  const pickerUtils = getPickerUtils();
  let bound = false;

  function parseIsoDate(value) {
    const raw = String(value || "").trim();
    if (!raw) {
      return null;
    }
    const date = new Date(`${raw}T00:00:00Z`);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function toIsoDate(date) {
    return date instanceof Date && !Number.isNaN(date.getTime()) ? date.toISOString().slice(0, 10) : "";
  }

  function addDaysIso(value, deltaDays) {
    const parsed = parseIsoDate(value);
    if (!parsed) {
      return "";
    }
    parsed.setUTCDate(parsed.getUTCDate() + deltaDays);
    return toIsoDate(parsed);
  }

  function previousRelativeBounds(period) {
    const current = core.getPeriodBounds(period);
    if (period === "day") {
      const dateFrom = addDaysIso(current.dateFrom, -1);
      return { dateFrom, dateTo: dateFrom };
    }
    if (period === "week") {
      return {
        dateFrom: addDaysIso(current.dateFrom, -7),
        dateTo: addDaysIso(current.dateTo, -7),
      };
    }
    if (period === "month") {
      const currentStart = parseIsoDate(current.dateFrom);
      if (!currentStart) {
        return current;
      }
      const prevMonthStart = new Date(Date.UTC(currentStart.getUTCFullYear(), currentStart.getUTCMonth() - 1, 1));
      const prevMonthEnd = new Date(Date.UTC(currentStart.getUTCFullYear(), currentStart.getUTCMonth(), 0));
      return { dateFrom: toIsoDate(prevMonthStart), dateTo: toIsoDate(prevMonthEnd) };
    }
    if (period === "year") {
      const currentStart = parseIsoDate(current.dateFrom);
      if (!currentStart) {
        return current;
      }
      const prevYear = currentStart.getUTCFullYear() - 1;
      return {
        dateFrom: `${prevYear}-01-01`,
        dateTo: `${prevYear}-12-31`,
      };
    }
    return current;
  }

  function getQuickPeriodCopy(period) {
    if (period === "day") {
      return { current: "Сегодня", previous: "Вчера" };
    }
    if (period === "week") {
      return { current: "Эта неделя", previous: "Прошлая неделя" };
    }
    if (period === "month") {
      return { current: "Этот месяц", previous: "Прошлый месяц" };
    }
    if (period === "year") {
      return { current: "Этот год", previous: "Прошлый год" };
    }
    return { current: "Текущий период", previous: "Предыдущий период" };
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
    const copy = getQuickPeriodCopy(period);
    const currentBounds = core.getPeriodBounds(period);
    const previousBounds = previousRelativeBounds(period);
    optionsHost.innerHTML = [
      `
        <button class="btn btn-secondary settings-picker-option active" type="button" data-quick-period-scope="${scope}" data-quick-period="${period}" data-quick-period-action="current">
          ${copy.current}
          <span class="muted-small">${core.formatPeriodLabel(currentBounds.dateFrom, currentBounds.dateTo)}</span>
        </button>
      `,
      `
        <button class="btn btn-secondary settings-picker-option" type="button" data-quick-period-scope="${scope}" data-quick-period="${period}" data-quick-period-action="previous">
          ${copy.previous}
          <span class="muted-small">${core.formatPeriodLabel(previousBounds.dateFrom, previousBounds.dateTo)}</span>
        </button>
      `,
      `
        <button class="btn btn-secondary settings-picker-option" type="button" data-quick-period-scope="${scope}" data-quick-period="${period}" data-quick-period-action="custom">
          Выбрать диапазон
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
    const bounds = action === "previous" ? previousRelativeBounds(period) : core.getPeriodBounds(period);
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
    const bounds = action === "previous" ? previousRelativeBounds(period) : core.getPeriodBounds(period);
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

  function bindAnalyticsFeatureHandlers() {
    if (bound) {
      return;
    }
    bound = true;

    if (el.analyticsPrevGridBtn && actions.shiftAnalyticsMonth) {
      el.analyticsPrevGridBtn.addEventListener("click", () => {
        coordinator.runPersistedAction({
          errorPrefix: "Ошибка загрузки календаря",
          action: () => actions.shiftAnalyticsMonth(-1),
        });
      });
    }
    if (el.analyticsNextGridBtn && actions.shiftAnalyticsMonth) {
      el.analyticsNextGridBtn.addEventListener("click", () => {
        coordinator.runPersistedAction({
          errorPrefix: "Ошибка загрузки календаря",
          action: () => actions.shiftAnalyticsMonth(1),
        });
      });
    }
    if (el.analyticsTodayGridBtn && actions.resetAnalyticsMonth) {
      el.analyticsTodayGridBtn.addEventListener("click", () => {
        coordinator.runPersistedAction({
          errorPrefix: "Ошибка загрузки календаря",
          action: () => actions.resetAnalyticsMonth(),
        });
      });
    }
    if (el.analyticsCalendarViewTabs && actions.setAnalyticsCalendarView) {
      el.analyticsCalendarViewTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-analytics-calendar-view]");
        if (!btn) {
          return;
        }
        const nextView = btn.dataset.analyticsCalendarView;
        coordinator.applySegmentedSelection({
          currentValue: state.analyticsCalendarView,
          nextValue: nextView,
          assignValue: (value) => {
            state.analyticsCalendarView = value;
          },
          syncContainer: el.analyticsCalendarViewTabs,
          syncAttr: "analytics-calendar-view",
          errorPrefix: "Ошибка загрузки сетки",
          action: () => actions.setAnalyticsCalendarView(nextView),
        });
      });
    }
    if (el.analyticsGlobalPeriodTabs && actions.loadAnalyticsSection) {
      el.analyticsGlobalPeriodTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-analytics-global-period]");
        if (!btn) {
          return;
        }
        const selected = btn.dataset.analyticsGlobalPeriod;
        if (selected === state.analyticsGlobalPeriod && ["week", "month", "year"].includes(selected)) {
          openQuickPeriodPopover("analytics", selected, btn);
          return;
        }
        if (selected === "custom") {
          state.analyticsGlobalPendingCustom = true;
          core.syncDateFieldValue(el.customDateFrom, state.analyticsGlobalDateFrom || "");
          core.syncDateFieldValue(el.customDateTo, state.analyticsGlobalDateTo || "");
          actions.openPeriodCustomModal();
          return;
        }
        state.analyticsGlobalPendingCustom = false;
        coordinator.applySegmentedSelection({
          currentValue: state.analyticsGlobalPeriod,
          nextValue: selected,
          assignValue: (value) => {
            state.analyticsGlobalPeriod = value;
            if (value !== "custom") {
              state.analyticsGlobalDateFrom = "";
              state.analyticsGlobalDateTo = "";
            }
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
      });
    }
    if (el.dashboardAnalyticsPeriodTabs && actions.loadDashboardAnalyticsPreview) {
      el.dashboardAnalyticsPeriodTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-dashboard-analytics-period]");
        if (!btn) {
          return;
        }
        const selected = btn.dataset.dashboardAnalyticsPeriod;
        if (selected === state.dashboardAnalyticsPeriod && ["day", "week", "month", "year"].includes(selected)) {
          openQuickPeriodPopover("dashboard", selected, btn);
          return;
        }
        if (selected === "custom") {
          state.dashboardAnalyticsPendingCustom = true;
          core.syncDateFieldValue(el.customDateFrom, state.dashboardAnalyticsDateFrom || "");
          core.syncDateFieldValue(el.customDateTo, state.dashboardAnalyticsDateTo || "");
          actions.openPeriodCustomModal();
          return;
        }
        state.dashboardAnalyticsPendingCustom = false;
        coordinator.applySegmentedSelection({
          currentValue: state.dashboardAnalyticsPeriod,
          nextValue: selected,
          assignValue: (value) => {
            state.dashboardAnalyticsPeriod = value;
            if (value !== "custom") {
              state.dashboardAnalyticsDateFrom = "";
              state.dashboardAnalyticsDateTo = "";
            }
          },
          syncContainer: el.dashboardAnalyticsPeriodTabs,
          syncAttr: "dashboard-analytics-period",
          errorPrefix: "Ошибка загрузки аналитики дашборда",
          action: () => actions.loadDashboardAnalyticsPreview({ force: true }),
        });
      });
    }
    if (el.dashboardAnalyticsPeriodOptions) {
      el.dashboardAnalyticsPeriodOptions.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-quick-period-scope='dashboard'][data-quick-period-action]");
        if (!btn) {
          return;
        }
        applyDashboardQuickPeriod(
          String(btn.dataset.quickPeriodAction || ""),
          String(btn.dataset.quickPeriod || ""),
        );
      });
    }
    if (el.analyticsGlobalPeriodOptions) {
      el.analyticsGlobalPeriodOptions.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-quick-period-scope='analytics'][data-quick-period-action]");
        if (!btn) {
          return;
        }
        applyAnalyticsGlobalQuickPeriod(
          String(btn.dataset.quickPeriodAction || ""),
          String(btn.dataset.quickPeriod || ""),
        );
      });
    }
    if (el.dashboardCategoryKindTabs && actions.loadDashboardAnalyticsPreview) {
      el.dashboardCategoryKindTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-dashboard-category-kind]");
        if (!btn) {
          return;
        }
        const selected = btn.dataset.dashboardCategoryKind;
        coordinator.applySegmentedSelection({
          currentValue: state.dashboardCategoryKind,
          nextValue: selected,
          assignValue: (value) => {
            state.dashboardCategoryKind = value;
          },
          syncContainer: el.dashboardCategoryKindTabs,
          syncAttr: "dashboard-category-kind",
          errorPrefix: "Ошибка загрузки структуры дашборда",
          action: () => actions.loadDashboardAnalyticsPreview({ force: true }),
        });
      });
    }
    if (el.dashboardBreakdownLevelTabs && actions.loadDashboardAnalyticsPreview) {
      el.dashboardBreakdownLevelTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-dashboard-breakdown-level]");
        if (!btn) {
          return;
        }
        const selected = btn.dataset.dashboardBreakdownLevel;
        coordinator.applySegmentedSelection({
          currentValue: state.dashboardBreakdownLevel,
          nextValue: selected,
          assignValue: (value) => {
            state.dashboardBreakdownLevel = value;
          },
          syncContainer: el.dashboardBreakdownLevelTabs,
          syncAttr: "dashboard-breakdown-level",
          errorPrefix: "Ошибка загрузки структуры дашборда",
          action: () => actions.loadDashboardAnalyticsPreview({ force: true }),
        });
      });
    }
    if (el.analyticsCategoryKindTabs && actions.loadAnalyticsSection) {
      el.analyticsCategoryKindTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-analytics-category-kind]");
        if (!btn) {
          return;
        }
        const selected = btn.dataset.analyticsCategoryKind;
        coordinator.applySegmentedSelection({
          currentValue: state.analyticsCategoryKind,
          nextValue: selected,
          assignValue: (value) => {
            state.analyticsCategoryKind = value;
          },
          syncContainer: el.analyticsCategoryKindTabs,
          syncAttr: "analytics-category-kind",
          errorPrefix: "Ошибка загрузки структуры категорий",
          action: () => actions.loadAnalyticsSection({ force: true }),
        });
      });
    }
    if (el.analyticsBreakdownLevelTabs && actions.loadAnalyticsSection) {
      el.analyticsBreakdownLevelTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-analytics-breakdown-level]");
        if (!btn) {
          return;
        }
        const selected = btn.dataset.analyticsBreakdownLevel;
        coordinator.applySegmentedSelection({
          currentValue: state.analyticsBreakdownLevel,
          nextValue: selected,
          assignValue: (value) => {
            state.analyticsBreakdownLevel = value;
          },
          syncContainer: el.analyticsBreakdownLevelTabs,
          syncAttr: "analytics-breakdown-level",
          errorPrefix: "Ошибка загрузки структуры",
          action: () => actions.loadAnalyticsSection({ force: true }),
        });
      });
    }
    if (el.analyticsGridMonthPicker && actions.setAnalyticsGridMonthAnchor) {
      const handleMonthPickerChange = () => {
        const nextValue = String(el.analyticsGridMonthPicker.value || "").trim();
        if (!nextValue) {
          return;
        }
        coordinator.runPersistedAction({
          errorPrefix: "Ошибка загрузки календаря",
          action: () => actions.setAnalyticsGridMonthAnchor(nextValue),
        });
      };
      el.analyticsGridMonthPicker.addEventListener("input", handleMonthPickerChange);
      el.analyticsGridMonthPicker.addEventListener("change", handleMonthPickerChange);
    }
    if (el.analyticsGridYearPicker && actions.setAnalyticsGridYearAnchor) {
      const handleYearPickerChange = () => {
        const nextYear = String(el.analyticsGridYearPicker.value || "").trim();
        if (!nextYear) {
          return;
        }
        coordinator.runPersistedAction({
          errorPrefix: "Ошибка загрузки календаря",
          action: () => actions.setAnalyticsGridYearAnchor(nextYear),
        });
      };
      el.analyticsGridYearPicker.addEventListener("input", handleYearPickerChange);
      el.analyticsGridYearPicker.addEventListener("change", handleYearPickerChange);
    }
    if (el.analyticsCalendarBody && actions.openOperationsForAnalyticsDate) {
      el.analyticsCalendarBody.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-analytics-date]");
        if (!btn) {
          return;
        }
        core.runAction({
          errorPrefix: "Ошибка перехода в операции",
          action: () => actions.openOperationsForAnalyticsDate(btn.dataset.analyticsDate),
        });
      });
    }
    if (el.analyticsYearGrid && actions.openAnalyticsMonth) {
      el.analyticsYearGrid.addEventListener("click", (event) => {
        const card = event.target.closest("[data-analytics-month-anchor]");
        if (!card) {
          return;
        }
        coordinator.runPersistedAction({
          errorPrefix: "Ошибка загрузки месяца",
          action: () => actions.openAnalyticsMonth(card.dataset.analyticsMonthAnchor),
        });
      });
    }
    if (actions.openOperationsForAnalyticsCategory) {
      const bindCategoryDrilldown = (container) => {
        if (!container) {
          return;
        }
        container.addEventListener("click", (event) => {
          if (event.target.closest("[data-analytics-breakdown-toggle]")) {
            return;
          }
          const card = event.target.closest("[data-analytics-category-id]");
          if (!card) {
            return;
          }
          const categoryId = String(card.dataset.analyticsCategoryId || "").trim();
          if (!categoryId) {
            return;
          }
          core.runAction({
            errorPrefix: "Ошибка перехода в операции",
            action: () => actions.openOperationsForAnalyticsCategory(
              categoryId,
              card.dataset.analyticsCategoryName || "",
              card.dataset.analyticsCategoryKind || "",
            ),
          });
        });
      };
      bindCategoryDrilldown(el.analyticsCategoryBreakdownChart);
      bindCategoryDrilldown(el.analyticsCategoryBreakdownList);
    }
    if (actions.toggleCategoryBreakdownVisibility && el.analyticsCategoryBreakdownList) {
      el.analyticsCategoryBreakdownList.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-analytics-breakdown-toggle]");
        if (!btn) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        actions.toggleCategoryBreakdownVisibility(String(btn.dataset.analyticsBreakdownToggle || ""));
      });
    }
    if (actions.showAllCategoryBreakdownItems && el.analyticsBreakdownShowAllBtn) {
      el.analyticsBreakdownShowAllBtn.addEventListener("click", () => {
        actions.showAllCategoryBreakdownItems();
      });
    }
    if (actions.setCategoryBreakdownHover && actions.clearCategoryBreakdownHover) {
      const bindCategoryHover = (container) => {
        hoverCoordinator.bindIndexedHover({
          container,
          itemSelector: "[data-analytics-category-index]",
          getIndex: (node) => node.dataset.analyticsCategoryIndex,
          setHover: (index) => actions.setCategoryBreakdownHover(index),
          clearHover: () => actions.clearCategoryBreakdownHover(),
        });
      };
      bindCategoryHover(el.analyticsCategoryBreakdownChart);
      bindCategoryHover(el.analyticsCategoryBreakdownList);
    }
    if (el.dashboardCategoryBreakdownList && actions.loadDashboardAnalyticsPreview) {
      const bindDashboardBreakdownHover = (container) => {
        hoverCoordinator.bindIndexedHover({
          container,
          itemSelector: "[data-dashboard-category-index]",
          getIndex: (node) => node.dataset.dashboardCategoryIndex,
          setHover: (index) => getAnalyticsHighlightsModule()?.setDashboardBreakdownHover?.(index),
          clearHover: () => getAnalyticsHighlightsModule()?.clearDashboardBreakdownHover?.(),
        });
      };
      bindDashboardBreakdownHover(el.dashboardCategoryBreakdownChart);
      bindDashboardBreakdownHover(el.dashboardCategoryBreakdownList);
    }
    if (el.analyticsTrendChart && actions.openOperationsForAnalyticsRange) {
      el.analyticsTrendChart.addEventListener("click", (event) => {
        const node = event.target.closest("[data-analytics-bucket-start][data-analytics-bucket-end]");
        if (!node) {
          return;
        }
        core.runAction({
          errorPrefix: "Ошибка перехода в операции",
          action: () => actions.openOperationsForAnalyticsRange(node.dataset.analyticsBucketStart, node.dataset.analyticsBucketEnd),
        });
      });
    }
    if (el.analyticsViewTabs && actions.setAnalyticsTab) {
      el.analyticsViewTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-analytics-tab]");
        if (!btn) {
          return;
        }
        coordinator.applySegmentedSelection({
          currentValue: state.analyticsTab,
          nextValue: btn.dataset.analyticsTab,
          assignValue: (value) => {
            actions.setAnalyticsTab(value);
          },
          errorPrefix: "Ошибка загрузки аналитики",
          action: () => actions.loadAnalyticsSection({ force: true }),
        });
      });
    }
    if (el.analyticsGranularityTabs && actions.loadAnalyticsTrend) {
      el.analyticsGranularityTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-analytics-granularity]");
        if (!btn) {
          return;
        }
        coordinator.applySegmentedSelection({
          currentValue: state.analyticsGranularity,
          nextValue: btn.dataset.analyticsGranularity,
          assignValue: (value) => {
            state.analyticsGranularity = value;
          },
          syncContainer: el.analyticsGranularityTabs,
          syncAttr: "analytics-granularity",
          errorPrefix: "Ошибка загрузки тренда",
          action: () => actions.loadAnalyticsTrend({ force: true }),
        });
      });
    }
  }

  const api = {
    bindAnalyticsFeatureHandlers,
  };

  window.App.initFeatureAnalytics = api;
  window.App.registerFeatureInitModule?.("analytics", api);
})();

function getAnalyticsUiCoordinator() {
  function getCore() {
    return window.App.core;
  }

  function getSessionFeature() {
    return window.App.getRuntimeModule?.("session") || {};
  }

  return (
    window.App.getRuntimeModule?.("analytics-ui-coordinator") || {
      runPersistedAction({ errorPrefix, action }) {
        return getCore().runAction({
          errorPrefix,
          action: async () => {
            await action();
            await getSessionFeature().savePreferences?.();
          },
        });
      },
      applySegmentedSelection({ currentValue, nextValue, assignValue, syncContainer, syncAttr, errorPrefix, action }) {
        if (currentValue === nextValue) {
          return;
        }
        assignValue(nextValue);
        if (syncContainer && syncAttr) {
          getCore().syncSegmentedActive(syncContainer, syncAttr, nextValue);
        }
        return getCore().runAction({
          errorPrefix,
          action: async () => {
            await action();
            await getSessionFeature().savePreferences?.();
          },
        });
      },
    }
  );
}

function getPickerUtils() {
  return window.App.getRuntimeModule?.("picker-utils") || {};
}

function getAnalyticsHoverCoordinator() {
  return (
    window.App.getRuntimeModule?.("analytics-hover-coordinator") || {
      bindIndexedHover({ container, itemSelector, getIndex, setHover, clearHover }) {
        if (!container) {
          return;
        }
        container.addEventListener("mouseover", (event) => {
          const node = event.target.closest(itemSelector);
          if (!node) {
            return;
          }
          setHover(getIndex(node));
        });
        container.addEventListener("focusin", (event) => {
          const node = event.target.closest(itemSelector);
          if (!node) {
            return;
          }
          setHover(getIndex(node));
        });
        container.addEventListener("mouseout", (event) => {
          const current = event.target.closest(itemSelector);
          const related = event.relatedTarget instanceof Element ? event.relatedTarget.closest(itemSelector) : null;
          if (!current || (related && getIndex(related) === getIndex(current))) {
            return;
          }
          if (!container.contains(event.relatedTarget)) {
            clearHover();
          }
        });
        container.addEventListener("focusout", (event) => {
          if (container.contains(event.relatedTarget)) {
            return;
          }
          clearHover();
        });
        container.addEventListener("mouseleave", () => {
          clearHover();
        });
      },
    }
  );
}

function getAnalyticsHighlightsModule() {
  return window.App.getRuntimeModule?.("analytics-highlights-module");
}
