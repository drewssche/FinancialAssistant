(() => {
  const { state, el, core, actions } = window.App;
  const hoverCoordinator = getAnalyticsHoverCoordinator();
  const coordinator = getAnalyticsUiCoordinator();
  const pickerUtils = getPickerUtils();
  const periodControls = getAnalyticsPeriodControls({
    state,
    el,
    core,
    actions,
    coordinator,
    pickerUtils,
  });
  let bound = false;

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
          periodControls.openQuickPeriodPopover("analytics", selected, btn);
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
    if (el.analyticsGlobalPeriodTrigger) {
      el.analyticsGlobalPeriodTrigger.addEventListener("click", () => {
        periodControls.openQuickPeriodPopover("analytics", state.analyticsGlobalPeriod || "month", el.analyticsGlobalPeriodTrigger);
      });
    }
    document.querySelectorAll("[data-analytics-period-step]").forEach((btn) => {
      btn.addEventListener("click", () => {
        periodControls.shiftAnalyticsGlobalPeriod(Number(btn.dataset.analyticsPeriodStep || 0));
      });
    });
    if (el.dashboardAnalyticsPeriodTabs && actions.loadDashboardAnalyticsPreview) {
      el.dashboardAnalyticsPeriodTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-dashboard-analytics-period]");
        if (!btn) {
          return;
        }
        const selected = btn.dataset.dashboardAnalyticsPeriod;
        if (selected === state.dashboardAnalyticsPeriod && ["day", "week", "month", "year"].includes(selected)) {
          periodControls.openQuickPeriodPopover("dashboard", selected, btn);
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
    if (el.dashboardAnalyticsPeriodTrigger) {
      el.dashboardAnalyticsPeriodTrigger.addEventListener("click", () => {
        periodControls.openQuickPeriodPopover("dashboard", state.dashboardAnalyticsPeriod || "month", el.dashboardAnalyticsPeriodTrigger);
      });
    }
    document.querySelectorAll("[data-dashboard-analytics-period-step]").forEach((btn) => {
      btn.addEventListener("click", () => {
        periodControls.shiftDashboardPeriod(Number(btn.dataset.dashboardAnalyticsPeriodStep || 0));
      });
    });
    if (el.dashboardAnalyticsPeriodOptions) {
      el.dashboardAnalyticsPeriodOptions.addEventListener("click", (event) => {
        const choiceBtn = event.target.closest("[data-dashboard-period-choice]");
        if (choiceBtn) {
          periodControls.applyDashboardPeriodChoice(String(choiceBtn.dataset.dashboardPeriodChoice || "month"));
          return;
        }
        const btn = event.target.closest("[data-quick-period-scope='dashboard'][data-quick-period-action]");
        if (!btn) {
          return;
        }
        periodControls.applyDashboardQuickPeriod(
          String(btn.dataset.quickPeriodAction || ""),
          String(btn.dataset.quickPeriod || ""),
        );
      });
    }
    if (el.analyticsGlobalPeriodOptions) {
      el.analyticsGlobalPeriodOptions.addEventListener("click", (event) => {
        const choiceBtn = event.target.closest("[data-analytics-period-choice]");
        if (choiceBtn) {
          periodControls.applyAnalyticsGlobalPeriodChoice(String(choiceBtn.dataset.analyticsPeriodChoice || "month"));
          return;
        }
        const btn = event.target.closest("[data-quick-period-scope='analytics'][data-quick-period-action]");
        if (!btn) {
          return;
        }
        periodControls.applyAnalyticsGlobalQuickPeriod(
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
    el.analyticsPositionsPeriodTrigger?.addEventListener("click", () => {
      actions.renderAnalyticsPositionsPeriodOptions?.();
      pickerUtils.setPopoverOpen?.(el.analyticsPositionsPeriodPopover, true, {
        owners: [el.analyticsPositionsPeriodTrigger],
      });
    });
    el.analyticsPositionsPeriodPopover?.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-analytics-positions-period-choice]");
      if (!btn) return;
      actions.setAnalyticsPositionsPeriod?.(btn.dataset.analyticsPositionsPeriodChoice);
      pickerUtils.setPopoverOpen?.(el.analyticsPositionsPeriodPopover, false, {
        owners: [el.analyticsPositionsPeriodTrigger],
      });
      window.App.getRuntimeModule?.("session")?.savePreferencesDebounced?.(250);
      core.runAction({ errorPrefix: "Ошибка загрузки позиций", action: () => actions.loadAnalyticsPositions({ force: true }) });
    });
    el.analyticsPositionsPrevBtn?.addEventListener("click", () => {
      actions.shiftAnalyticsPositionsPeriod?.(-1);
      window.App.getRuntimeModule?.("session")?.savePreferencesDebounced?.(250);
      core.runAction({ errorPrefix: "Ошибка загрузки позиций", action: () => actions.loadAnalyticsPositions({ force: true }) });
    });
    el.analyticsPositionsNextBtn?.addEventListener("click", () => {
      actions.shiftAnalyticsPositionsPeriod?.(1);
      window.App.getRuntimeModule?.("session")?.savePreferencesDebounced?.(250);
      core.runAction({ errorPrefix: "Ошибка загрузки позиций", action: () => actions.loadAnalyticsPositions({ force: true }) });
    });
    el.analyticsPositionsSortBtn?.addEventListener("click", () => {
      actions.toggleAnalyticsPositionsSort?.();
      window.App.getRuntimeModule?.("session")?.savePreferencesDebounced?.(250);
    });
    el.analyticsPositionsMetricTabs?.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-analytics-positions-metric]");
      if (!btn) return;
      state.analyticsPositionsMetric = btn.dataset.analyticsPositionsMetric;
      actions.renderAnalyticsPositions?.();
      window.App.getRuntimeModule?.("session")?.savePreferencesDebounced?.(250);
    });
    el.analyticsPositionsLimitTabs?.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-analytics-positions-limit]");
      if (!btn) return;
      state.analyticsPositionsLimit = btn.dataset.analyticsPositionsLimit;
      actions.renderAnalyticsPositions?.();
      window.App.getRuntimeModule?.("session")?.savePreferencesDebounced?.(250);
    });
    [el.analyticsPositionsSearch, el.analyticsPositionsSourceSearch].filter(Boolean).forEach((input) => {
      input.addEventListener("input", () => actions.renderAnalyticsPositions?.());
    });
    el.analyticsPositionsPanel?.addEventListener("click", (event) => {
      const selectBtn = event.target.closest("button[data-position-select-key]");
      if (selectBtn) {
        state.analyticsPositionsSelectedKey = selectBtn.dataset.positionSelectKey || "";
        actions.renderAnalyticsPositions?.();
        return;
      }
      const cell = event.target.closest("button[data-position-date-from][data-position-date-to]");
      if (!cell) return;
      core.runAction({
        errorPrefix: "Ошибка перехода в операции",
        action: () => actions.openOperationsForAnalyticsPositionRange?.(
          cell.dataset.positionTemplateId,
          cell.dataset.positionName,
          cell.dataset.positionDateFrom,
          cell.dataset.positionDateTo,
        ),
      });
    });
    el.analyticsCommerceModeTabs?.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-analytics-commerce-mode]");
      if (!btn) return;
      state.analyticsCommerceMode = btn.dataset.analyticsCommerceMode === "discounts" ? "discounts" : "prices";
      state.analyticsCommerceMetric = state.analyticsCommerceMode === "discounts" ? "savings_total" : "change_pct";
      state.analyticsCommerceSelectedKey = "";
      window.App.getRuntimeModule?.("analytics-commerce-module")?.renderCommerce?.();
      window.App.getRuntimeModule?.("session")?.savePreferencesDebounced?.(250);
    });
    el.analyticsCommerceMetricTabs?.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-analytics-commerce-metric]");
      if (!btn) return;
      state.analyticsCommerceMetric = btn.dataset.analyticsCommerceMetric || state.analyticsCommerceMetric;
      window.App.getRuntimeModule?.("analytics-commerce-module")?.renderCommerce?.();
      window.App.getRuntimeModule?.("session")?.savePreferencesDebounced?.(250);
    });
    el.analyticsCommerceDiscountTypeTabs?.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-analytics-commerce-discount-type]");
      if (!btn) return;
      state.analyticsCommerceDiscountType = btn.dataset.analyticsCommerceDiscountType || "all";
      state.analyticsCommerceSelectedKey = "";
      window.App.getRuntimeModule?.("analytics-commerce-module")?.renderCommerce?.();
      window.App.getRuntimeModule?.("session")?.savePreferencesDebounced?.(250);
    });
    el.analyticsCommerceSortBtn?.addEventListener("click", () => {
      state.analyticsCommerceSort = state.analyticsCommerceSort === "asc" ? "desc" : "asc";
      window.App.getRuntimeModule?.("analytics-commerce-module")?.renderCommerce?.();
      window.App.getRuntimeModule?.("session")?.savePreferencesDebounced?.(250);
    });
    el.analyticsCommercePanel?.addEventListener("click", (event) => {
      const selectBtn = event.target.closest("button[data-commerce-select-key]");
      if (selectBtn) {
        state.analyticsCommerceSelectedKey = selectBtn.dataset.commerceSelectKey || "";
        window.App.getRuntimeModule?.("analytics-commerce-module")?.renderCommerce?.();
        return;
      }
      const commerce = window.App.getRuntimeModule?.("analytics-commerce-module");
      const selected = commerce?.selectedItem?.();
      if (!selected) return;
      const timelineBtn = event.target.closest("button[data-commerce-date]");
      const openBtn = event.target.closest("button[data-commerce-open-operations]");
      if (!timelineBtn && !openBtn) return;
      const dateFrom = timelineBtn?.dataset.commerceDate || state.analyticsHighlightsData?.date_from;
      const dateTo = timelineBtn?.dataset.commerceDate || state.analyticsHighlightsData?.date_to;
      core.runAction({
        errorPrefix: "Ошибка перехода в операции",
        action: () => actions.openOperationsForAnalyticsPositionRange?.(
          selected.template_id,
          selected.name,
          dateFrom,
          dateTo,
        ),
      });
    });
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

function getAnalyticsPeriodControls(deps) {
  const factory = window.App.getRuntimeModule?.("analytics-period-controls") || createAnalyticsPeriodControlsFallback;
  return factory(deps);
}

function createAnalyticsPeriodControlsFallback() {
  return {
    applyAnalyticsGlobalPeriodChoice() {},
    applyAnalyticsGlobalQuickPeriod() {},
    applyDashboardPeriodChoice() {},
    applyDashboardQuickPeriod() {},
    openQuickPeriodPopover() {},
    shiftAnalyticsGlobalPeriod() {},
  };
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
