(() => {
  const { state, el, core, actions } = window.App;
  let bound = false;

  function bindAnalyticsFeatureHandlers() {
    if (bound) {
      return;
    }
    bound = true;

    if (el.analyticsPrevGridBtn && actions.shiftAnalyticsMonth) {
      el.analyticsPrevGridBtn.addEventListener("click", () => {
        core.runAction({
          errorPrefix: "Ошибка загрузки календаря",
          action: async () => {
            await actions.shiftAnalyticsMonth(-1);
            await actions.savePreferences();
          },
        });
      });
    }
    if (el.analyticsNextGridBtn && actions.shiftAnalyticsMonth) {
      el.analyticsNextGridBtn.addEventListener("click", () => {
        core.runAction({
          errorPrefix: "Ошибка загрузки календаря",
          action: async () => {
            await actions.shiftAnalyticsMonth(1);
            await actions.savePreferences();
          },
        });
      });
    }
    if (el.analyticsTodayGridBtn && actions.resetAnalyticsMonth) {
      el.analyticsTodayGridBtn.addEventListener("click", () => {
        core.runAction({
          errorPrefix: "Ошибка загрузки календаря",
          action: async () => {
            await actions.resetAnalyticsMonth();
            await actions.savePreferences();
          },
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
        if (state.analyticsCalendarView === nextView) {
          return;
        }
        core.runAction({
          errorPrefix: "Ошибка загрузки сетки",
          action: async () => {
            await actions.setAnalyticsCalendarView(nextView);
            await actions.savePreferences();
          },
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
        if (selected === "custom") {
          state.analyticsGlobalPendingCustom = true;
          el.customDateFrom.value = core.normalizeDateInputValue(state.analyticsGlobalDateFrom || "");
          el.customDateTo.value = core.normalizeDateInputValue(state.analyticsGlobalDateTo || "");
          actions.openPeriodCustomModal();
          return;
        }
        if (state.analyticsGlobalPeriod === selected) {
          return;
        }
        state.analyticsGlobalPendingCustom = false;
        state.analyticsGlobalPeriod = selected;
        if (selected !== "custom") {
          state.analyticsGlobalDateFrom = "";
          state.analyticsGlobalDateTo = "";
        }
        if ((state.analyticsGlobalPeriod === "year" || state.analyticsGlobalPeriod === "all_time") && state.analyticsGranularity === "day") {
          state.analyticsGranularity = "week";
          core.syncSegmentedActive(el.analyticsGranularityTabs, "analytics-granularity", state.analyticsGranularity);
        }
        core.syncSegmentedActive(el.analyticsGlobalPeriodTabs, "analytics-global-period", state.analyticsGlobalPeriod);
        core.runAction({
          errorPrefix: "Ошибка загрузки аналитики",
          action: async () => {
            await actions.loadAnalyticsSection({ force: true });
            await actions.savePreferences();
          },
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
        if (state.dashboardAnalyticsPeriod === selected) {
          return;
        }
        state.dashboardAnalyticsPeriod = selected;
        core.syncSegmentedActive(el.dashboardAnalyticsPeriodTabs, "dashboard-analytics-period", state.dashboardAnalyticsPeriod);
        core.runAction({
          errorPrefix: "Ошибка загрузки аналитики дашборда",
          action: async () => {
            await actions.loadDashboardAnalyticsPreview({ force: true });
            await actions.savePreferences();
          },
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
        if (state.analyticsCategoryKind === selected) {
          return;
        }
        state.analyticsCategoryKind = selected;
        core.syncSegmentedActive(el.analyticsCategoryKindTabs, "analytics-category-kind", state.analyticsCategoryKind);
        core.runAction({
          errorPrefix: "Ошибка загрузки структуры категорий",
          action: async () => {
            await actions.loadAnalyticsSection({ force: true });
            await actions.savePreferences();
          },
        });
      });
    }
    if (el.analyticsGridMonthPicker && actions.setAnalyticsGridMonthAnchor) {
      el.analyticsGridMonthPicker.addEventListener("change", () => {
        const nextValue = String(el.analyticsGridMonthPicker.value || "").trim();
        if (!nextValue) {
          return;
        }
        core.runAction({
          errorPrefix: "Ошибка загрузки календаря",
          action: async () => {
            await actions.setAnalyticsGridMonthAnchor(nextValue);
            await actions.savePreferences();
          },
        });
      });
    }
    if (el.analyticsGridYearPicker && actions.setAnalyticsGridYearAnchor) {
      el.analyticsGridYearPicker.addEventListener("change", () => {
        const nextYear = String(el.analyticsGridYearPicker.value || "").trim();
        if (!nextYear) {
          return;
        }
        core.runAction({
          errorPrefix: "Ошибка загрузки календаря",
          action: async () => {
            await actions.setAnalyticsGridYearAnchor(nextYear);
            await actions.savePreferences();
          },
        });
      });
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
        core.runAction({
          errorPrefix: "Ошибка загрузки месяца",
          action: async () => {
            await actions.openAnalyticsMonth(card.dataset.analyticsMonthAnchor);
            await actions.savePreferences();
          },
        });
      });
    }
    if (el.analyticsTopOperationsList && actions.openOperationsForAnalyticsDate) {
      el.analyticsTopOperationsList.addEventListener("click", (event) => {
        const card = event.target.closest("[data-analytics-date]");
        if (!card) {
          return;
        }
        core.runAction({
          errorPrefix: "Ошибка перехода в операции",
          action: () => actions.openOperationsForAnalyticsDate(card.dataset.analyticsDate),
        });
      });
    }
    if (el.analyticsAnomaliesList && actions.openOperationsForAnalyticsDate) {
      el.analyticsAnomaliesList.addEventListener("click", (event) => {
        const card = event.target.closest("[data-analytics-date]");
        if (!card) {
          return;
        }
        core.runAction({
          errorPrefix: "Ошибка перехода в операции",
          action: () => actions.openOperationsForAnalyticsDate(card.dataset.analyticsDate),
        });
      });
    }
    if (actions.openOperationsForAnalyticsCategory) {
      const bindCategoryDrilldown = (container) => {
        if (!container) {
          return;
        }
        container.addEventListener("click", (event) => {
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
      bindCategoryDrilldown(el.analyticsCategoryBreakdownList);
      bindCategoryDrilldown(el.analyticsTopCategoriesList);
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
        if (state.analyticsTab === btn.dataset.analyticsTab) {
          return;
        }
        actions.setAnalyticsTab(btn.dataset.analyticsTab);
        core.runAction({
          errorPrefix: "Ошибка сохранения аналитики",
          action: () => actions.savePreferences(),
        });
      });
    }
    if (el.analyticsGranularityTabs && actions.loadAnalyticsTrend) {
      el.analyticsGranularityTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-analytics-granularity]");
        if (!btn) {
          return;
        }
        if (state.analyticsGranularity === btn.dataset.analyticsGranularity) {
          return;
        }
        state.analyticsGranularity = btn.dataset.analyticsGranularity;
        core.syncSegmentedActive(el.analyticsGranularityTabs, "analytics-granularity", state.analyticsGranularity);
        core.runAction({
          errorPrefix: "Ошибка загрузки тренда",
          action: async () => {
            await actions.loadAnalyticsTrend({ force: true });
            await actions.savePreferences();
          },
        });
      });
    }
  }

  window.App.initFeatureAnalytics = {
    bindAnalyticsFeatureHandlers,
  };
})();
