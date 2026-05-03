(() => {
  const { state, el, core, actions } = window.App;
  let bound = false;
  let operationsObserver = null;
  let categoriesObserver = null;
  const pickerUtils = getPickerUtils();

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

    function previousOperationsBounds(period) {
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

    function getOperationsQuickPeriodCopy(period) {
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

    function closeOperationsPeriodPopover() {
      pickerUtils.setPopoverOpen?.(el.operationsPeriodPopover, false, {
        owners: Array.from(el.periodTabGroups || []).filter(Boolean),
      });
    }

    function renderOperationsPeriodOptions(period) {
      if (!el.operationsPeriodOptions) {
        return;
      }
      const copy = getOperationsQuickPeriodCopy(period);
      const currentBounds = core.getPeriodBounds(period);
      const previousBounds = previousOperationsBounds(period);
      el.operationsPeriodOptions.innerHTML = [
        `
          <button class="btn btn-secondary settings-picker-option active" type="button" data-operations-quick-period="${period}" data-operations-quick-action="current">
            ${copy.current}
            <span class="muted-small">${core.formatPeriodLabel(currentBounds.dateFrom, currentBounds.dateTo)}</span>
          </button>
        `,
        `
          <button class="btn btn-secondary settings-picker-option" type="button" data-operations-quick-period="${period}" data-operations-quick-action="previous">
            ${copy.previous}
            <span class="muted-small">${core.formatPeriodLabel(previousBounds.dateFrom, previousBounds.dateTo)}</span>
          </button>
        `,
        `
          <button class="btn btn-secondary settings-picker-option" type="button" data-operations-quick-period="${period}" data-operations-quick-action="custom">
            Выбрать диапазон
            <span class="muted-small">Открыть ручной диапазон дат</span>
          </button>
        `,
      ].join("");
    }

    function openOperationsQuickPeriodPopover(period, trigger) {
      if (!el.operationsPeriodPopover || !pickerUtils.setPopoverOpen) {
        return;
      }
      renderOperationsPeriodOptions(period);
      pickerUtils.setPopoverOpen(el.operationsPeriodPopover, true, {
        owners: [trigger].filter(Boolean),
        onClose: () => closeOperationsPeriodPopover(),
      });
    }

    function openOperationsCustomRange(basePeriod = state.period || "month") {
      const baseBounds = core.getPeriodBounds(basePeriod);
      core.syncDateFieldValue(el.customDateFrom, state.customDateFrom || baseBounds.dateFrom || "");
      core.syncDateFieldValue(el.customDateTo, state.customDateTo || baseBounds.dateTo || "");
      getOperationModal().openPeriodCustomModal?.();
    }

    function setPeriodCustomMode(mode) {
      const nextMode = mode === "range" ? "range" : "day";
      if (el.customPeriodMode) {
        el.customPeriodMode.value = nextMode;
      }
      if (el.periodCustomModeTabs) {
        core.syncSegmentedActive(el.periodCustomModeTabs, "period-custom-mode", nextMode);
      }
      const today = core.getTodayIso();
      if (nextMode === "day") {
        const fromValue = el.customDateFrom?.value || "";
        const toValue = el.customDateTo?.value || "";
        const nextDay = fromValue && fromValue === toValue
          ? fromValue
          : (fromValue || state.customDateFrom || today);
        core.syncDateFieldValue(el.customDayDate, nextDay);
      } else {
        const dayValue = el.customDayDate?.value || state.customDateFrom || today;
        if (!el.customDateFrom?.value || el.customDateFrom.value === el.customDateTo?.value) {
          core.syncDateFieldValue(el.customDateFrom, dayValue);
        }
        if (!el.customDateTo?.value) {
          core.syncDateFieldValue(el.customDateTo, dayValue);
        }
      }
      el.customDayField?.classList.toggle("hidden", nextMode !== "day");
      el.customRangeFields?.classList.toggle("hidden", nextMode !== "range");
      if (el.submitPeriodCustomBtn) {
        el.submitPeriodCustomBtn.textContent = nextMode === "day" ? "Показать день" : "Применить период";
      }
    }

    function resolvePeriodCustomBounds() {
      const mode = el.customPeriodMode?.value === "range" ? "range" : "day";
      if (mode === "day") {
        const day = core.parseDateInputValue(el.customDayDate?.value || "");
        return day ? { from: day, to: day, mode } : { from: "", to: "", mode };
      }
      return {
        from: core.parseDateInputValue(el.customDateFrom.value),
        to: core.parseDateInputValue(el.customDateTo.value),
        mode,
      };
    }

    function applyOperationsQuickPeriod(action, period) {
      closeOperationsPeriodPopover();
      if (action === "custom") {
        openOperationsCustomRange(period);
        return;
      }
      const bounds = action === "previous" ? previousOperationsBounds(period) : core.getPeriodBounds(period);
      if (action === "previous") {
        state.customDateFrom = bounds.dateFrom;
        state.customDateTo = bounds.dateTo;
        state.period = "custom";
        core.syncAllPeriodTabs("custom");
      } else {
        state.customDateFrom = "";
        state.customDateTo = "";
        state.period = period;
        core.syncAllPeriodTabs(period);
      }
      getOperationsFeature().invalidateAllTimeAnchor?.();
      core.runAction({
        errorPrefix: "Ошибка сохранения периода",
        action: async () => {
          const operationsFeature = getOperationsFeature();
          if (action === "current" && state.period === "all_time" && operationsFeature.ensureAllTimeBounds) {
            await operationsFeature.ensureAllTimeBounds();
          }
          await refreshOperationsPeriodViews();
        },
      });
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
        const isEdit = Boolean(String(state.editItemSourceName || "").trim());
        core.runAction({
          button: event.submitter || document.getElementById("submitSourceGroupBtn"),
          pendingText: "Сохранение...",
          successMessage: isEdit ? "Источник сохранен" : "Источник создан",
          errorPrefix: isEdit ? "Ошибка сохранения источника" : "Ошибка создания источника",
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
        if (btn.dataset.period === state.period && ["day", "week", "month", "year"].includes(btn.dataset.period || "")) {
          openOperationsQuickPeriodPopover(btn.dataset.period, btn);
          return;
        }
        if (btn.dataset.period === "custom") {
          openOperationsCustomRange();
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

    if (el.quickCustomRangeBtn) {
      el.quickCustomRangeBtn.addEventListener("click", () => {
        openOperationsCustomRange();
      });
    }

    if (el.operationsPeriodOptions) {
      el.operationsPeriodOptions.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-operations-quick-action][data-operations-quick-period]");
        if (!btn) {
          return;
        }
        applyOperationsQuickPeriod(
          String(btn.dataset.operationsQuickAction || ""),
          String(btn.dataset.operationsQuickPeriod || ""),
        );
      });
    }

    if (el.periodCustomModeTabs) {
      el.periodCustomModeTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-period-custom-mode]");
        if (!btn) {
          return;
        }
        setPeriodCustomMode(String(btn.dataset.periodCustomMode || "day"));
      });
    }

    if (el.customDayTodayBtn) {
      el.customDayTodayBtn.addEventListener("click", () => {
        core.syncDateFieldValue(el.customDayDate, core.getTodayIso());
      });
    }

    el.periodCustomForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const { from, to, mode } = resolvePeriodCustomBounds();
      if (!from || !to || from > to) {
        core.setStatus(mode === "day" ? "Проверь дату" : "Проверь диапазон дат");
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

function getPickerUtils() {
  return window.App.getRuntimeModule?.("picker-utils") || {};
}
