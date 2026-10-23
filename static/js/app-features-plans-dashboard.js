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
  let forecastGeneration = 0;
  function getDashboardPlansPeriodBounds(period = state.dashboardPlansPeriod || "month") {
    if (period === "all_time") return null;
    const start = core.getTodayIso();
    const end = new Date(start + "T12:00:00Z");
    end.setUTCDate(end.getUTCDate() + (period === "week" ? 6 : 29));
    return { dateFrom: start, dateTo: end.toISOString().slice(0,10) };
  }

  function closeDashboardPlansPeriodPopover() {
    getPickerUtils().setPopoverOpen?.(el.dashboardPlansPeriodPopover, false, {
      owners: [el.dashboardPlansPeriodTabs].filter(Boolean),
    });
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
    const bounds = getDashboardPlansPeriodBounds();
    return bounds ? `${core.formatDateRu(bounds.dateFrom)} — ${core.formatDateRu(bounds.dateTo)}` : "Ближайшие платежи всех активных планов";
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
    const periodItems = getDashboardPlansPeriodFilteredItems();
    const items = [...periodItems]
      .sort((a, b) => String(a.scheduled_date || a.due_date || a.operation_date || "").localeCompare(String(b.scheduled_date || b.due_date || b.operation_date || "")))
      .slice(0, ui?.dashboardOperationsLimit || 8);
    const summary = summarizePlans(periodItems);
    const generation = ++forecastGeneration, owner = state.token;
    const counts = `<p class="muted-small">Планов: ${summary.activeCount}${summary.todayCount ? ` · Сегодня: ${summary.todayCount}` : ""}</p>`;

    el.dashboardPlansKpi.innerHTML = counts;
    if (state.dashboardPlansPeriod === "all_time") {
      el.dashboardPlansKpi.innerHTML += core.renderPlansForecastKpi({ income_total: summary.potentialIncome, expense_total: summary.potentialExpense, occurrences_count: summary.activeCount, overdue_count: summary.overdueCount }, { showDates: false });
    } else {
      const days = state.dashboardPlansPeriod === "week" ? 7 : 30;
      core.requestJson(`/api/v1/plans/forecast?days=${days}`, { headers: core.authHeaders() }).then(data => {
        if (generation !== forecastGeneration || owner !== state.token) return;
        if (data.date_from && data.date_to && el.dashboardPlansPeriodLabel) {
          el.dashboardPlansPeriodLabel.textContent = `${core.formatDateRu(data.date_from)} — ${core.formatDateRu(data.date_to)}`;
        }
        el.dashboardPlansKpi.innerHTML = counts + (data.income_total == null ? '<p class="muted-small">Прогноз недоступен</p>' : core.renderPlansForecastKpi(data, { showDates: false }));
      }).catch(() => { if (generation === forecastGeneration && owner === state.token) el.dashboardPlansKpi.innerHTML = counts + '<p class="muted-small">Прогноз недоступен</p>'; });
    }
    el.dashboardPlansList.innerHTML = items.length
      ? items.map((item) => renderPlanCard(item, { dashboardCompact: true })).join("")
      : "<div class='muted-small'>Планов пока нет</div>";
  }

  function openDashboardPlansPeriodPopover(period) {
    void setDashboardPlansPeriod(period);
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
