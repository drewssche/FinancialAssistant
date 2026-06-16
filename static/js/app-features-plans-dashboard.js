function createPlansDashboardFeature({
  state,
  el,
  core,
  getPickerUtils,
  getPlanItems,
  getSessionFeature,
  summarizePlans,
  renderPlanCard,
  loadPlans,
}) {
  const periodControlUtils = window.App.getRuntimeModule?.("period-control-utils") || {};

  function getDashboardPlansPeriodBounds(period = state.dashboardPlansPeriod || "month", anchor = state.dashboardPlansPeriodAnchor || "current") {
    if (period === "all_time") {
      return null;
    }
    const current = core.getPeriodBounds ? core.getPeriodBounds(period) : null;
    if (!current?.dateFrom || !current?.dateTo || anchor !== "previous") {
      return current;
    }
    return periodControlUtils.shiftPeriodBounds?.({
      period,
      direction: -1,
      currentBounds: current,
      getPeriodBounds: (value) => core.getPeriodBounds(value),
    }) || current;
  }

  function closeDashboardPlansPeriodPopover() {
    getPickerUtils().setPopoverOpen?.(el.dashboardPlansPeriodPopover, false, {
      owners: [el.dashboardPlansPeriodTabs].filter(Boolean),
    });
  }

  function renderDashboardPlansPeriodOptions(period = state.dashboardPlansPeriod || "month") {
    if (!el.dashboardPlansPeriodOptions) {
      return;
    }
    const currentBounds = getDashboardPlansPeriodBounds(period, "current");
    const previousBounds = getDashboardPlansPeriodBounds(period, "previous");
    const currentLabel = period === "week" ? "Эта неделя" : "Этот месяц";
    const previousLabel = period === "week" ? "Прошлая неделя" : "Прошлый месяц";
    el.dashboardPlansPeriodOptions.innerHTML = [
      `
        <button class="btn btn-secondary settings-picker-option active" type="button" data-dashboard-plans-quick-period="${period}" data-dashboard-plans-quick-anchor="current">
          ${currentLabel}
          <span class="muted-small">${core.formatPeriodLabel(currentBounds?.dateFrom || "", currentBounds?.dateTo || "")}</span>
        </button>
      `,
      `
        <button class="btn btn-secondary settings-picker-option" type="button" data-dashboard-plans-quick-period="${period}" data-dashboard-plans-quick-anchor="previous">
          ${previousLabel}
          <span class="muted-small">${core.formatPeriodLabel(previousBounds?.dateFrom || "", previousBounds?.dateTo || "")}</span>
        </button>
      `,
      `
        <button class="btn btn-secondary settings-picker-option" type="button" data-dashboard-plans-quick-period="all_time" data-dashboard-plans-quick-anchor="current">
          Все активные планы
          <span class="muted-small">Без ограничения по периоду</span>
        </button>
      `,
    ].join("");
  }

  function getDashboardPlansPeriodFilteredItems() {
    const period = state.dashboardPlansPeriod || "month";
    const activeItems = getPlanItems().filter((item) => item.status === "due" || item.status === "overdue" || item.status === "upcoming");
    if (period === "all_time") {
      return activeItems;
    }
    const bounds = getDashboardPlansPeriodBounds(period, state.dashboardPlansPeriodAnchor || "current");
    if (!bounds?.dateFrom || !bounds?.dateTo) {
      return activeItems;
    }
    return activeItems.filter((item) => {
      if (item.status === "overdue") {
        return true;
      }
      const dueDate = String(item.scheduled_date || item.due_date || item.operation_date || "");
      return Boolean(dueDate) && dueDate >= bounds.dateFrom && dueDate <= bounds.dateTo;
    });
  }

  function getDashboardPlansPeriodLabel() {
    const period = state.dashboardPlansPeriod || "month";
    if (period === "all_time") {
      return "Все активные планы";
    }
    const anchor = state.dashboardPlansPeriodAnchor || "current";
    const bounds = getDashboardPlansPeriodBounds(period, anchor);
    if (!bounds?.dateFrom || !bounds?.dateTo) {
      return period === "week" ? "Планы на текущую неделю" : "Планы на текущий месяц";
    }
    const base = core.formatPeriodLabel ? core.formatPeriodLabel(bounds.dateFrom, bounds.dateTo) : `${bounds.dateFrom} - ${bounds.dateTo}`;
    if (period === "week") {
      return anchor === "previous" ? `Планы за прошлую неделю: ${base}` : `Планы на неделю: ${base}`;
    }
    return anchor === "previous" ? `Планы за прошлый месяц: ${base}` : `Планы на месяц: ${base}`;
  }

  function renderDashboardPlans() {
    if (!el.dashboardPlansList || !el.dashboardPlansKpi) {
      return;
    }
    const ui = core.getUiSettings ? core.getUiSettings() : null;
    if (el.dashboardPlansPeriodTabs) {
      core.syncSegmentedActive(el.dashboardPlansPeriodTabs, "dashboard-plans-period", state.dashboardPlansPeriod || "month");
    }
    if (el.dashboardPlansPeriodLabel) {
      el.dashboardPlansPeriodLabel.textContent = getDashboardPlansPeriodLabel();
    }
    const items = getDashboardPlansPeriodFilteredItems()
      .sort((a, b) => String(a.scheduled_date || a.due_date || a.operation_date || "").localeCompare(String(b.scheduled_date || b.due_date || b.operation_date || "")))
      .slice(0, ui?.dashboardOperationsLimit || 8);
    const summary = summarizePlans(items);
    el.dashboardPlansKpi.innerHTML = `
      <span class="analytics-kpi-chip analytics-kpi-chip-neutral">Активных: ${summary.activeCount}</span>
      <span class="analytics-kpi-chip analytics-kpi-chip-neutral">Сегодня: ${summary.todayCount}</span>
      <span class="analytics-kpi-chip analytics-kpi-chip-negative">Просрочено: ${summary.overdueCount}</span>
      <span class="analytics-kpi-chip ${summary.netPlanned >= 0 ? "analytics-kpi-chip-positive" : "analytics-kpi-chip-negative"}">Плановый сдвиг: ${summary.netPlanned < 0 ? "-" : "+"}${core.formatMoney(Math.abs(summary.netPlanned))}</span>
    `;
    el.dashboardPlansList.innerHTML = items.length
      ? items.map((item) => renderPlanCard(item, { dashboardCompact: true })).join("")
      : "<div class='muted-small'>Планов пока нет</div>";
  }

  function openDashboardPlansPeriodPopover(period, trigger) {
    if (!["week", "month"].includes(period) || !el.dashboardPlansPeriodPopover) {
      return;
    }
    renderDashboardPlansPeriodOptions(period);
    getPickerUtils().setPopoverOpen?.(el.dashboardPlansPeriodPopover, true, {
      owners: [trigger || el.dashboardPlansPeriodTabs].filter(Boolean),
      onClose: () => closeDashboardPlansPeriodPopover(),
    });
  }

  async function setDashboardPlansPeriod(value, anchor = "current") {
    const next = ["week", "month", "all_time"].includes(value) ? value : "month";
    state.dashboardPlansPeriod = next;
    state.dashboardPlansPeriodAnchor = next === "all_time" ? "current" : (anchor === "previous" ? "previous" : "current");
    core.syncSegmentedActive(el.dashboardPlansPeriodTabs, "dashboard-plans-period", next);
    closeDashboardPlansPeriodPopover();
    if (!getPlanItems().length) {
      await loadPlans({ force: true });
      getSessionFeature().savePreferencesDebounced?.(250);
      return;
    }
    renderDashboardPlans();
    getSessionFeature().savePreferencesDebounced?.(250);
  }

  function bindDashboardPlansPeriodOptions() {
    if (!el.dashboardPlansPeriodOptions || el.dashboardPlansPeriodOptions.__plansDashboardPeriodBound) {
      return;
    }
    el.dashboardPlansPeriodOptions.__plansDashboardPeriodBound = true;
    el.dashboardPlansPeriodOptions.addEventListener("click", (event) => {
      const btn = event.target.closest("[data-dashboard-plans-quick-period][data-dashboard-plans-quick-anchor]");
      if (!btn) {
        return;
      }
      setDashboardPlansPeriod(
        String(btn.dataset.dashboardPlansQuickPeriod || ""),
        String(btn.dataset.dashboardPlansQuickAnchor || "current"),
      ).catch((err) => core.setStatus(String(err)));
    });
  }

  return {
    bindDashboardPlansPeriodOptions,
    openDashboardPlansPeriodPopover,
    renderDashboardPlans,
    setDashboardPlansPeriod,
  };
}

window.App.registerRuntimeModule?.("plans-dashboard", createPlansDashboardFeature);
