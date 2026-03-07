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
    if (el.analyticsSummaryPeriodTabs && actions.loadAnalyticsHighlights) {
      el.analyticsSummaryPeriodTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-analytics-summary-period]");
        if (!btn) {
          return;
        }
        const selected = btn.dataset.analyticsSummaryPeriod;
        if (selected === "custom") {
          state.analyticsSummaryPendingCustom = true;
          el.customDateFrom.value = state.analyticsSummaryDateFrom || "";
          el.customDateTo.value = state.analyticsSummaryDateTo || "";
          actions.openPeriodCustomModal();
          return;
        }
        if (state.analyticsSummaryPeriod === selected) {
          return;
        }
        state.analyticsSummaryPendingCustom = false;
        state.analyticsSummaryPeriod = selected;
        if (selected !== "custom") {
          state.analyticsSummaryDateFrom = "";
          state.analyticsSummaryDateTo = "";
        }
        core.syncSegmentedActive(el.analyticsSummaryPeriodTabs, "analytics-summary-period", state.analyticsSummaryPeriod);
        core.runAction({
          errorPrefix: "Ошибка загрузки KPI",
          action: async () => {
            await actions.loadAnalyticsHighlights({ force: true });
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
    if (el.analyticsPeriodTabs && actions.loadAnalyticsTrend) {
      el.analyticsPeriodTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-analytics-period]");
        if (!btn) {
          return;
        }
        if (state.analyticsPeriod === btn.dataset.analyticsPeriod) {
          return;
        }
        state.analyticsPeriod = btn.dataset.analyticsPeriod;
        if ((state.analyticsPeriod === "year" || state.analyticsPeriod === "all_time") && state.analyticsGranularity === "day") {
          state.analyticsGranularity = "week";
          core.syncSegmentedActive(el.analyticsGranularityTabs, "analytics-granularity", state.analyticsGranularity);
        }
        core.syncSegmentedActive(el.analyticsPeriodTabs, "analytics-period", state.analyticsPeriod);
        core.runAction({
          errorPrefix: "Ошибка загрузки тренда",
          action: async () => {
            await actions.loadAnalyticsTrend({ force: true });
            await actions.savePreferences();
          },
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
