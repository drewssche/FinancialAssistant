(() => {
  const { state, el, core, actions } = window.App;
  let bound = false;
  let operationsObserver = null;
  let categoriesObserver = null;

  function bindFeatureHandlers() {
    function getCreateFormActionMeta() {
      const isDebt = el.opEntryMode?.value === "debt";
      if (!isDebt) {
        return {
          pendingText: "Добавление...",
          successMessage: "Операция добавлена",
          errorPrefix: "Ошибка добавления операции",
        };
      }
      const isDebtEdit = Number(state.editDebtCreateId || 0) > 0;
      return {
        pendingText: isDebtEdit ? "Сохранение..." : "Добавление...",
        successMessage: isDebtEdit ? "Долг обновлён" : "Долг создан",
        errorPrefix: isDebtEdit ? "Ошибка сохранения долга" : "Ошибка создания долга",
      };
    }

    el.createForm.addEventListener("submit", (event) => {
      const meta = getCreateFormActionMeta();
      core.runAction({
        button: event.submitter || document.getElementById("submitCreateOperationBtn"),
        pendingText: meta.pendingText,
        successMessage: meta.successMessage,
        errorPrefix: meta.errorPrefix,
        action: () => actions.createOperation(event),
      });
    });

    el.editForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitEditOperationBtn"),
        pendingText: "Сохранение...",
        successMessage: "Операция обновлена",
        errorPrefix: "Ошибка сохранения операции",
        action: () => actions.updateOperation(event),
      });
    });

    el.categoryModalForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitCreateCategoryBtn"),
        pendingText: "Добавление...",
        successMessage: "Категория добавлена",
        errorPrefix: "Ошибка добавления категории",
        action: () => actions.createCategory(event),
      });
    });

    el.editCategoryForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitEditCategoryBtn"),
        pendingText: "Сохранение...",
        successMessage: "Категория обновлена",
        errorPrefix: "Ошибка обновления категории",
        action: () => actions.updateCategory(event),
      });
    });

    el.editGroupForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitEditGroupBtn"),
        pendingText: "Сохранение...",
        successMessage: "Группа обновлена",
        errorPrefix: "Ошибка обновления группы",
        action: () => actions.updateGroup(event),
      });
    });

    if (el.itemTemplateForm && actions.submitItemTemplateForm) {
      el.itemTemplateForm.addEventListener("submit", (event) => {
        core.runAction({
          button: event.submitter || document.getElementById("submitItemTemplateBtn"),
          pendingText: "Сохранение...",
          successMessage: "Позиция сохранена",
          errorPrefix: "Ошибка сохранения позиции",
          action: () => actions.submitItemTemplateForm(event),
        });
      });
    }
    if (el.sourceGroupForm && actions.submitSourceGroupForm) {
      el.sourceGroupForm.addEventListener("submit", (event) => {
        core.runAction({
          button: event.submitter || document.getElementById("submitSourceGroupBtn"),
          pendingText: "Сохранение...",
          successMessage: "Источник создан",
          errorPrefix: "Ошибка создания источника",
          action: () => actions.submitSourceGroupForm(event),
        });
      });
    }

    for (const container of el.periodTabGroups) {
      container.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-period]");
        if (!btn) {
          return;
        }
        if (btn.dataset.period === "custom") {
          actions.openPeriodCustomModal();
          return;
        }
        if (btn.dataset.period === state.period) {
          return;
        }
        state.period = btn.dataset.period;
        core.syncAllPeriodTabs(state.period);
        core.runAction({
          errorPrefix: "Ошибка сохранения периода",
          action: async () => {
            if (state.period === "all_time" && actions.ensureAllTimeBounds) {
              await actions.ensureAllTimeBounds();
            }
            await actions.savePreferences();
            const jobs = [actions.loadDashboard(), actions.loadDashboardOperations(), actions.loadOperations()];
            if (actions.loadDashboardAnalyticsPreview) {
              jobs.push(actions.loadDashboardAnalyticsPreview({ force: true }));
            }
            await Promise.all(jobs);
          },
        });
      });
    }

    el.periodCustomForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const from = core.parseDateInputValue(el.customDateFrom.value);
      const to = core.parseDateInputValue(el.customDateTo.value);
      if (!from || !to || from > to) {
        core.setStatus("Проверь диапазон дат");
        return;
      }
      if (state.analyticsGlobalPendingCustom && state.activeSection === "analytics") {
        state.analyticsGlobalPendingCustom = false;
        state.analyticsGlobalPeriod = "custom";
        state.analyticsGlobalDateFrom = from;
        state.analyticsGlobalDateTo = to;
        core.syncSegmentedActive(el.analyticsGlobalPeriodTabs, "analytics-global-period", state.analyticsGlobalPeriod);
        core.runAction({
          button: event.submitter || document.getElementById("submitPeriodCustomBtn"),
          pendingText: "Применение...",
          errorPrefix: "Ошибка сохранения периода",
          action: async () => {
            if (actions.loadAnalyticsSection) {
              await actions.loadAnalyticsSection({ force: true });
            }
            await actions.savePreferences();
            actions.closePeriodCustomModal();
          },
        });
        return;
      }
      if (state.dashboardAnalyticsPendingCustom && state.activeSection === "dashboard") {
        state.dashboardAnalyticsPendingCustom = false;
        state.dashboardAnalyticsPeriod = "custom";
        state.dashboardAnalyticsDateFrom = from;
        state.dashboardAnalyticsDateTo = to;
        core.syncSegmentedActive(el.dashboardAnalyticsPeriodTabs, "dashboard-analytics-period", state.dashboardAnalyticsPeriod);
        core.runAction({
          button: event.submitter || document.getElementById("submitPeriodCustomBtn"),
          pendingText: "Применение...",
          errorPrefix: "Ошибка сохранения периода",
          action: async () => {
            if (actions.loadDashboardAnalyticsPreview) {
              await actions.loadDashboardAnalyticsPreview({ force: true });
            }
            if (actions.loadDashboardOperations) {
              await actions.loadDashboardOperations();
            }
            await actions.savePreferences();
            actions.closePeriodCustomModal();
          },
        });
        return;
      }
      state.customDateFrom = from;
      state.customDateTo = to;
      state.period = "custom";
      core.syncAllPeriodTabs("custom");
      if (actions.invalidateAllTimeAnchor) {
        actions.invalidateAllTimeAnchor();
      }
      core.runAction({
        button: event.submitter || document.getElementById("submitPeriodCustomBtn"),
        pendingText: "Применение...",
        errorPrefix: "Ошибка сохранения периода",
        action: async () => {
          await actions.savePreferences();
          const jobs = [actions.loadDashboard(), actions.loadDashboardOperations(), actions.loadOperations()];
          if (actions.loadDashboardAnalyticsPreview) {
            jobs.push(actions.loadDashboardAnalyticsPreview({ force: true }));
          }
          await Promise.all(jobs);
          actions.closePeriodCustomModal();
        },
      });
    });

    if (window.App.initFeatureOperations?.bindOperationsFeatureHandlers) {
      window.App.initFeatureOperations.bindOperationsFeatureHandlers(
        () => operationsObserver,
        (observer) => {
          operationsObserver = observer;
        },
      );
    }

    if (window.App.initFeatureCatalog?.bindCatalogFeatureHandlers) {
      window.App.initFeatureCatalog.bindCatalogFeatureHandlers(
        () => categoriesObserver,
        (observer) => {
          categoriesObserver = observer;
        },
      );
    }

    if (window.App.initFeatureAnalytics?.bindAnalyticsFeatureHandlers) {
      window.App.initFeatureAnalytics.bindAnalyticsFeatureHandlers();
    }
    if (window.App.initFeatureAdmin?.bindAdminFeatureHandlers) {
      window.App.initFeatureAdmin.bindAdminFeatureHandlers();
    }

    el.toastArea.addEventListener("click", (event) => {
      const closeBtn = event.target.closest("button[data-toast-close]");
      if (closeBtn && core.dismissToast) {
        core.dismissToast(closeBtn.dataset.toastClose);
        return;
      }
      const btn = event.target.closest("button[data-toast-undo]");
      if (!btn) {
        return;
      }
      core.handleUndoClick(btn.dataset.toastUndo);
    });

    if (window.App.initFeatureDebts?.bindDebtFeatureHandlers) {
      window.App.initFeatureDebts.bindDebtFeatureHandlers();
    }
    if (window.App.initFeaturePickers?.bindPickerFeatureHandlers) {
      window.App.initFeaturePickers.bindPickerFeatureHandlers();
    }
  }

  function bindFeatureInit() {
    if (bound) return;
    bound = true;
    bindFeatureHandlers();
  }

  window.App.initFeatures = {
    bindFeatureInit,
  };
})();
