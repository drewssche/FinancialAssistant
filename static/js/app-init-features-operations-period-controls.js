function createOperationsPeriodControls({
  state,
  el,
  core,
  pickerUtils,
  getOperationsFeature,
  getOperationModal,
  refreshOperationsPeriodViews,
}) {
  const periodControlUtils = window.App.getRuntimeModule?.("period-control-utils") || {};

  function shiftOperationsBounds(period, direction, currentBounds = null) {
    return periodControlUtils.shiftPeriodBounds?.({
      period,
      direction,
      currentBounds,
      getPeriodBounds: (value) => core.getPeriodBounds(value),
    }) || currentBounds || core.getPeriodBounds(period);
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
    const options = [
      ["day", "День"],
      ["week", "Неделя"],
      ["month", "Месяц"],
      ["year", "Год"],
      ["all_time", "Все время"],
    ];
    el.operationsPeriodOptions.innerHTML = [
      ...options.map(([value, label]) => {
        const bounds = core.getPeriodBounds(value);
        return `
          <button class="btn btn-secondary settings-picker-option ${state.period === value ? "active" : ""}" type="button" data-operations-period-choice="${value}">
            ${label}
            <span class="muted-small">${core.formatPeriodLabel(bounds.dateFrom, bounds.dateTo)}</span>
          </button>
        `;
      }),
      `
        <button class="btn btn-secondary settings-picker-option" type="button" data-operations-quick-period="${period}" data-operations-quick-action="custom">
          Диапазон
          <span class="muted-small">Открыть ручной диапазон дат</span>
        </button>
      `,
    ].join("");
  }

  function openQuickPeriodPopover(period, trigger) {
    if (!el.operationsPeriodPopover || !pickerUtils.setPopoverOpen) {
      return;
    }
    renderOperationsPeriodOptions(period);
    pickerUtils.setPopoverOpen(el.operationsPeriodPopover, true, {
      owners: [trigger].filter(Boolean),
      onClose: () => closeOperationsPeriodPopover(),
    });
  }

  function openCustomRange(basePeriod = state.period || "month") {
    const baseBounds = core.getPeriodBounds(basePeriod);
    core.syncDateFieldValue(el.customDateFrom, state.customDateFrom || baseBounds.dateFrom || "");
    core.syncDateFieldValue(el.customDateTo, state.customDateTo || baseBounds.dateTo || "");
    getOperationModal().openPeriodCustomModal?.();
  }

  function applyPeriodChoice(period) {
    closeOperationsPeriodPopover();
    if (period === "custom") {
      openCustomRange();
      return;
    }
    state.operationsPeriodStepGranularity = period;
    state.period = period;
    state.customDateFrom = "";
    state.customDateTo = "";
    core.syncAllPeriodTabs(state.period);
    getOperationsFeature().invalidateAllTimeAnchor?.();
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
  }

  function shiftPeriod(delta) {
    if (state.period === "all_time") {
      return;
    }
    const periodValues = ["day", "week", "month", "year"];
    const basePeriod = periodValues.includes(state.period)
      ? state.period
      : (periodValues.includes(state.operationsPeriodStepGranularity) ? state.operationsPeriodStepGranularity : "day");
    const currentBounds = state.period === "custom" && state.customDateFrom && state.customDateTo
      ? { dateFrom: state.customDateFrom, dateTo: state.customDateTo }
      : null;
    const bounds = shiftOperationsBounds(basePeriod, delta, currentBounds);
    state.operationsPeriodStepGranularity = basePeriod;
    state.period = "custom";
    state.customDateFrom = bounds.dateFrom;
    state.customDateTo = bounds.dateTo;
    core.syncAllPeriodTabs("custom");
    getOperationsFeature().invalidateAllTimeAnchor?.();
    core.runAction({
      errorPrefix: "Ошибка сохранения периода",
      action: () => refreshOperationsPeriodViews(),
    });
  }

  function applyQuickPeriod(action, period) {
    closeOperationsPeriodPopover();
    if (action === "custom") {
      openCustomRange(period);
      return;
    }
    const bounds = action === "previous" ? shiftOperationsBounds(period, -1) : core.getPeriodBounds(period);
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

  return {
    applyPeriodChoice,
    applyQuickPeriod,
    closeOperationsPeriodPopover,
    openCustomRange,
    openQuickPeriodPopover,
    shiftPeriod,
  };
}

window.App.registerRuntimeModule?.("operations-period-controls", createOperationsPeriodControls);
