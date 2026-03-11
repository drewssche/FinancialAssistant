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
          core.syncDateFieldValue(el.customDateFrom, state.analyticsGlobalDateFrom || "");
          core.syncDateFieldValue(el.customDateTo, state.analyticsGlobalDateTo || "");
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
      const handleMonthPickerChange = () => {
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
        core.runAction({
          errorPrefix: "Ошибка загрузки календаря",
          action: async () => {
            await actions.setAnalyticsGridYearAnchor(nextYear);
            await actions.savePreferences();
          },
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
        core.runAction({
          errorPrefix: "Ошибка загрузки месяца",
          action: async () => {
            await actions.openAnalyticsMonth(card.dataset.analyticsMonthAnchor);
            await actions.savePreferences();
          },
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
      bindCategoryDrilldown(el.analyticsCategoryBreakdownChart);
      bindCategoryDrilldown(el.analyticsCategoryBreakdownList);
    }
    if (actions.setCategoryBreakdownHover && actions.clearCategoryBreakdownHover) {
      const bindCategoryHover = (container) => {
        if (!container) {
          return;
        }
        container.addEventListener("mouseover", (event) => {
          const node = event.target.closest("[data-analytics-category-index]");
          if (!node) {
            return;
          }
          actions.setCategoryBreakdownHover(node.dataset.analyticsCategoryIndex);
        });
        container.addEventListener("focusin", (event) => {
          const node = event.target.closest("[data-analytics-category-index]");
          if (!node) {
            return;
          }
          actions.setCategoryBreakdownHover(node.dataset.analyticsCategoryIndex);
        });
        container.addEventListener("mouseout", (event) => {
          const related = event.relatedTarget instanceof Element ? event.relatedTarget.closest("[data-analytics-category-index]") : null;
          const current = event.target.closest("[data-analytics-category-index]");
          if (!current || (related && related.dataset.analyticsCategoryIndex === current.dataset.analyticsCategoryIndex)) {
            return;
          }
          if (!container.contains(event.relatedTarget)) {
            actions.clearCategoryBreakdownHover();
          }
        });
        container.addEventListener("focusout", (event) => {
          if (container.contains(event.relatedTarget)) {
            return;
          }
          actions.clearCategoryBreakdownHover();
        });
        container.addEventListener("mouseleave", () => {
          actions.clearCategoryBreakdownHover();
        });
      };
      bindCategoryHover(el.analyticsCategoryBreakdownChart);
      bindCategoryHover(el.analyticsCategoryBreakdownList);
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
