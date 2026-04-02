(() => {
  const { state, el, core, actions } = window.App;
  let bound = false;
  let operationsObserver = null;
  let categoriesObserver = null;

  function getSessionFeature() {
    return window.App.getRuntimeModule?.("session") || {};
  }

  function getCategoryActions() {
    return window.App.getRuntimeModule?.("category-actions") || {};
  }

  function getDashboardFeature() {
    return window.App.getRuntimeModule?.("dashboard") || {};
  }

  function getAnalyticsFeature() {
    return window.App.getRuntimeModule?.("analytics") || {};
  }

  function getOperationsFeature() {
    return window.App.getRuntimeModule?.("operations") || {};
  }

  function getPlansFeature() {
    return window.App.getRuntimeModule?.("plans") || {};
  }

  function getItemCatalogFeature() {
    return window.App.getRuntimeModule?.("item-catalog") || {};
  }

  function getOperationModal() {
    return window.App.getRuntimeModule?.("operation-modal") || {};
  }

  function bindFeatureHandlers() {
    async function refreshOperationsPeriodViews() {
      const sessionFeature = getSessionFeature();
      const operationsFeature = getOperationsFeature();
      await sessionFeature.savePreferences?.();
      await operationsFeature.loadOperations?.({ reset: true, force: true });
    }

    function getCreateFormActionMeta() {
      if (state.createFlowMode === "plan") {
        const isEditPlan = Number(state.editPlanId || 0) > 0;
        return {
          pendingText: isEditPlan ? "Сохранение..." : "Добавление...",
          successMessage: isEditPlan ? "План обновлён" : "План создан",
          errorPrefix: isEditPlan ? "Ошибка сохранения плана" : "Ошибка создания плана",
        };
      }
      const isDebt = el.opEntryMode?.value === "debt";
      const isCurrency = el.opEntryMode?.value === "currency";
      if (isCurrency) {
        return {
          pendingText: "Сохранение...",
          successMessage: "Валютная сделка сохранена",
          errorPrefix: "Ошибка сохранения валютной сделки",
        };
      }
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
      const plansFeature = getPlansFeature();
      const operationsFeature = getOperationsFeature();
      core.runAction({
        button: event.submitter || document.getElementById("submitCreateOperationBtn"),
        pendingText: meta.pendingText,
        successMessage: meta.successMessage,
        errorPrefix: meta.errorPrefix,
        action: () => (
          state.createFlowMode === "plan"
            ? plansFeature.submitPlanForm?.(event)
            : operationsFeature.createOperation?.(event)
        ),
      });
    });

    el.editForm.addEventListener("submit", (event) => {
      const operationsFeature = getOperationsFeature();
      core.runAction({
        button: event.submitter || document.getElementById("submitEditOperationBtn"),
        pendingText: "Сохранение...",
        successMessage: "Операция обновлена",
        errorPrefix: "Ошибка сохранения операции",
        action: () => operationsFeature.updateOperation?.(event),
      });
    });

    el.categoryModalForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitCreateCategoryBtn"),
        pendingText: "Добавление...",
        successMessage: "Категория добавлена",
        errorPrefix: "Ошибка добавления категории",
        action: () => getCategoryActions().createCategory?.(event),
      });
    });

    el.editCategoryForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitEditCategoryBtn"),
        pendingText: "Сохранение...",
        successMessage: "Категория обновлена",
        errorPrefix: "Ошибка обновления категории",
        action: () => getCategoryActions().updateCategory?.(event),
      });
    });

    el.editGroupForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitEditGroupBtn"),
        pendingText: "Сохранение...",
        successMessage: "Группа обновлена",
        errorPrefix: "Ошибка обновления группы",
        action: () => getCategoryActions().updateGroup?.(event),
      });
    });

    if (el.itemTemplateForm && getItemCatalogFeature().submitItemTemplateForm) {
      el.itemTemplateForm.addEventListener("submit", (event) => {
        const itemCatalogFeature = getItemCatalogFeature();
        core.runAction({
          button: event.submitter || document.getElementById("submitItemTemplateBtn"),
          pendingText: "Сохранение...",
          successMessage: "Позиция сохранена",
          errorPrefix: "Ошибка сохранения позиции",
          action: () => itemCatalogFeature.submitItemTemplateForm?.(event),
        });
      });
    }
    if (el.sourceGroupForm && getItemCatalogFeature().submitSourceGroupForm) {
      el.sourceGroupForm.addEventListener("submit", (event) => {
        const itemCatalogFeature = getItemCatalogFeature();
        core.runAction({
          button: event.submitter || document.getElementById("submitSourceGroupBtn"),
          pendingText: "Сохранение...",
          successMessage: "Источник создан",
          errorPrefix: "Ошибка создания источника",
          action: () => itemCatalogFeature.submitSourceGroupForm?.(event),
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
          getOperationModal().openPeriodCustomModal?.();
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
            const operationsFeature = getOperationsFeature();
            if (state.period === "all_time" && operationsFeature.ensureAllTimeBounds) {
              await operationsFeature.ensureAllTimeBounds();
            }
            await refreshOperationsPeriodViews();
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
            const analyticsFeature = getAnalyticsFeature();
            const sessionFeature = getSessionFeature();
            const operationModal = getOperationModal();
            await analyticsFeature.loadAnalyticsSection?.({ force: true });
            await sessionFeature.savePreferences?.();
            operationModal.closePeriodCustomModal?.();
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
            const analyticsFeature = getAnalyticsFeature();
            const dashboardFeature = getDashboardFeature();
            const sessionFeature = getSessionFeature();
            const operationModal = getOperationModal();
            await analyticsFeature.loadDashboardAnalyticsPreview?.({ force: true });
            await dashboardFeature.loadDashboardOperations?.();
            await sessionFeature.savePreferences?.();
            operationModal.closePeriodCustomModal?.();
          },
        });
        return;
      }
      state.customDateFrom = from;
      state.customDateTo = to;
      state.period = "custom";
      core.syncAllPeriodTabs("custom");
      getOperationsFeature().invalidateAllTimeAnchor?.();
      core.runAction({
        button: event.submitter || document.getElementById("submitPeriodCustomBtn"),
        pendingText: "Применение...",
        errorPrefix: "Ошибка сохранения периода",
        action: async () => {
          const operationModal = getOperationModal();
          await refreshOperationsPeriodViews();
          operationModal.closePeriodCustomModal?.();
        },
      });
    });

    const featureOperations = window.App.getFeatureInitModule?.("operations") || window.App.initFeatureOperations;
    if (featureOperations?.bindOperationsFeatureHandlers) {
      featureOperations.bindOperationsFeatureHandlers(
        () => operationsObserver,
        (observer) => {
          operationsObserver = observer;
        },
      );
    }

    const featureCatalog = window.App.getFeatureInitModule?.("catalog") || window.App.initFeatureCatalog;
    if (featureCatalog?.bindCatalogFeatureHandlers) {
      featureCatalog.bindCatalogFeatureHandlers(
        () => categoriesObserver,
        (observer) => {
          categoriesObserver = observer;
        },
      );
    }

    const featureAnalytics = window.App.getFeatureInitModule?.("analytics") || window.App.initFeatureAnalytics;
    if (featureAnalytics?.bindAnalyticsFeatureHandlers) {
      featureAnalytics.bindAnalyticsFeatureHandlers();
    }
    const featureAdmin = window.App.getFeatureInitModule?.("admin") || window.App.initFeatureAdmin;
    if (featureAdmin?.bindAdminFeatureHandlers) {
      featureAdmin.bindAdminFeatureHandlers();
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

    const featureDebts = window.App.getFeatureInitModule?.("debts") || window.App.initFeatureDebts;
    if (featureDebts?.bindDebtFeatureHandlers) {
      featureDebts.bindDebtFeatureHandlers();
    }
    const featurePickers = window.App.getFeatureInitModule?.("pickers") || window.App.initFeaturePickers;
    if (featurePickers?.bindPickerFeatureHandlers) {
      featurePickers.bindPickerFeatureHandlers();
    }
  }

  function bindFeatureInit() {
    if (bound) return;
    bound = true;
    bindFeatureHandlers();
  }

  const api = {
    bindFeatureInit,
  };

  window.App.initFeatures = api;
  window.App.registerBootstrapModule?.("features", api);
})();
