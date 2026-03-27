(() => {
  const { state, el, core } = window.App;
  const operationModal = window.App.getRuntimeModule?.("operation-modal");
  const debtUi = core.debtUi;
  const getCategoryMetaById = operationModal.getCategoryMetaById;

  function getPlansFeature() {
    return window.App.getRuntimeModule?.("plans");
  }

  function getDashboardData() {
    return window.App.getRuntimeModule?.("dashboard-data");
  }

  function getLoadingSkeletons() {
    return window.App.getRuntimeModule?.("loading-skeletons") || {};
  }

  function getInlineRefreshState() {
    return window.App.getRuntimeModule?.("inline-refresh-state") || {};
  }

  function dueBadgeLabel(stateValue, dueDate) {
    if (stateValue === "overdue") {
      return "Просрочено";
    }
    if (stateValue === "soon") {
      return core.formatDateRu(dueDate);
    }
    if (stateValue === "future" && dueDate) {
      return core.formatDateRu(dueDate);
    }
    return "Без срока";
  }

  function duePriorityRank(stateValue) {
    if (stateValue === "overdue") {
      return 0;
    }
    if (stateValue === "soon") {
      return 1;
    }
    if (stateValue === "future") {
      return 2;
    }
    if (stateValue === "none") {
      return 3;
    }
    return 4;
  }

  function renderDashboardCurrencySummary(summary) {
    const currencyPrefs = state.preferences?.data?.currency || {};
    if (el.dashboardCurrencyPanel) {
      el.dashboardCurrencyPanel.classList.toggle("hidden", currencyPrefs.show_dashboard_kpi === false);
    }
    if (el.dashboardCurrencyKpiGrid) {
      el.dashboardCurrencyKpiGrid.innerHTML = `
        <article class="analytics-kpi-card analytics-kpi-neutral">
          <div class="muted-small">Текущая оценка</div>
          <strong>${core.formatMoney(summary.currency_current_value || 0)}</strong>
        </article>
        <article class="analytics-kpi-card analytics-kpi-balance">
          <div class="muted-small">Вложено</div>
          <strong>${core.formatMoney(summary.currency_book_value || 0)}</strong>
        </article>
        <article class="analytics-kpi-card analytics-kpi-income">
          <div class="muted-small">Прибыль / убыток</div>
          <strong>${core.formatMoney(summary.currency_result_value || 0)}</strong>
        </article>
        <article class="analytics-kpi-card analytics-kpi-neutral">
          <div class="muted-small">Открытых позиций</div>
          <strong>${String(summary.active_currency_positions || 0)}</strong>
        </article>
      `;
    }
    if (el.dashboardCurrencyPositions) {
      const positions = Array.isArray(summary.tracked_currency_positions) ? summary.tracked_currency_positions : [];
      if (!positions.length) {
        el.dashboardCurrencyPositions.innerHTML = `<span class="analytics-kpi-chip analytics-kpi-chip-neutral">Пока нет открытых валютных позиций</span>`;
        return;
      }
      el.dashboardCurrencyPositions.innerHTML = positions.map((item) => {
        const signClass = Number(item.result_value || 0) >= 0 ? "analytics-kpi-chip-positive" : "analytics-kpi-chip-negative";
        const rateDate = item.current_rate_date ? ` · курс ${core.formatDateRu(item.current_rate_date)}` : "";
        return `
          <span class="analytics-kpi-chip ${signClass}">
            ${core.escapeHtml ? core.escapeHtml(item.currency) : item.currency}: ${core.formatMoney(item.current_value || 0)}
            <span class="muted-small">остаток ${core.formatAmount(item.quantity || 0)} · ср. вход ${Number(item.average_buy_rate || 0).toFixed(4)} · текущий ${Number(item.current_rate || 0).toFixed(4)}${rateDate}</span>
          </span>
        `;
      }).join("");
    }
  }

  function renderDashboardCurrencyRates(currentRates = [], trackedCurrencies = []) {
    if (!el.dashboardCurrencyRates) {
      return;
    }
    const tracked = Array.isArray(trackedCurrencies) ? trackedCurrencies : [];
    const rows = Array.isArray(currentRates)
      ? currentRates.filter((item) => tracked.includes(String(item.currency || "").toUpperCase()))
      : [];
    if (!rows.length) {
      el.dashboardCurrencyRates.innerHTML = `<span class="analytics-kpi-chip analytics-kpi-chip-neutral">Курсы пока не заданы</span>`;
      return;
    }
    el.dashboardCurrencyRates.innerHTML = rows.map((item) => `
      <span class="analytics-kpi-chip analytics-kpi-chip-neutral">
        ${core.escapeHtml ? core.escapeHtml(item.currency) : item.currency}: ${Number(item.rate || 0).toFixed(4)}
        <span class="muted-small">${item.rate_date ? core.formatDateRu(item.rate_date) : "без даты"}</span>
      </span>
    `).join("");
  }

  function formatDateTimeRu(value) {
    if (!value) {
      return "";
    }
    try {
      const date = value instanceof Date ? value : new Date(value);
      if (Number.isNaN(date.getTime())) {
        return "";
      }
      return new Intl.DateTimeFormat("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      }).format(date);
    } catch {
      return "";
    }
  }


  async function loadDashboard() {
    const skeletons = getLoadingSkeletons();
    const refreshState = getInlineRefreshState();
    const ui = core.getUiSettings ? core.getUiSettings() : null;
    if (el.dashboardAnalyticsPanel && ui) {
      el.dashboardAnalyticsPanel.classList.toggle("hidden", ui.showDashboardAnalytics === false);
    }
    if (el.dashboardStructurePanel && ui) {
      el.dashboardStructurePanel.classList.toggle("hidden", ui.showDashboardAnalytics === false);
    }
    if (el.dashboardPlansPanel && ui) {
      el.dashboardPlansPanel.classList.toggle("hidden", ui.showDashboardOperations === false);
    }
    if (el.dashboardDebtsPanel && ui) {
      el.dashboardDebtsPanel.classList.toggle("hidden", ui.showDashboardDebts === false);
    }
    if (!state.dashboardDebtSummaryLoaded) {
      skeletons.renderDashboardDebtsSkeleton?.();
    }
    if (!state.dashboardPlansHydrated) {
      skeletons.renderDashboardPlansSkeleton?.();
    }
    const dashboardData = getDashboardData();
    const shouldRefreshDebts = state.dashboardDebtSummaryLoaded || state.dashboardDebtsHydrated;
    const shouldRefreshPlans = state.dashboardPlansHydrated;
    if (shouldRefreshDebts && el.dashboardDebtsPanel && core.isDashboardDebtsVisible()) {
      refreshState.begin?.(el.dashboardDebtsPanel, "Обновляется");
    }
    if (shouldRefreshPlans && el.dashboardPlansPanel && ui?.showDashboardOperations !== false) {
      refreshState.begin?.(el.dashboardPlansPanel, "Обновляется");
    }
    try {
      const data = await (dashboardData.loadAllTimeSummary
        ? dashboardData.loadAllTimeSummary()
        : core.requestJson("/api/v1/dashboard/summary?period=all_time", { headers: core.authHeaders() }));
      if (el.debtLendTotal) {
        el.debtLendTotal.textContent = core.formatMoney(data.debt_lend_outstanding);
      }
      if (el.debtBorrowTotal) {
        el.debtBorrowTotal.textContent = core.formatMoney(data.debt_borrow_outstanding);
      }
      if (el.debtNetTotal) {
        el.debtNetTotal.textContent = core.formatMoney(data.debt_net_position);
      }
      if (el.dashboardDebtKpiGrid) {
        const lendTotal = Number(data.debt_lend_outstanding || 0);
        const borrowTotal = Number(data.debt_borrow_outstanding || 0);
        const netTotal = Number(data.debt_net_position || 0);
        const hasDebtKpi = Math.abs(lendTotal) > 0.000001 || Math.abs(borrowTotal) > 0.000001 || Math.abs(netTotal) > 0.000001;
        el.dashboardDebtKpiGrid.classList.toggle("hidden", !hasDebtKpi);
      }
      renderDashboardCurrencySummary(data);
      try {
        const currencyOverview = await core.requestJson("/api/v1/currency/overview?trades_limit=10", {
          headers: core.authHeaders(),
        });
        renderDashboardCurrencyRates(currencyOverview.current_rates, currencyOverview.tracked_currencies);
      } catch {
        renderDashboardCurrencyRates([], []);
      }
      state.dashboardDebtSummaryLoaded = true;

      if (el.dashboardPlansPanel && ui?.showDashboardOperations !== false) {
        await getPlansFeature().loadPlans?.();
      } else {
        getPlansFeature().renderDashboardPlans?.();
      }

      if (!core.isDashboardDebtsVisible()) {
        return;
      }

      if (el.dashboardDebtsList) {
        const cards = await (dashboardData.loadDebtPreview
          ? dashboardData.loadDebtPreview({ limit: 6 })
          : core.requestJson("/api/v1/dashboard/debts/preview?limit=6", { headers: core.authHeaders() }));
        el.dashboardDebtsList.innerHTML = "";
        if (!cards.length) {
          const empty = document.createElement("div");
          empty.className = "muted-small";
          empty.textContent = "Нет активных долгов";
          el.dashboardDebtsList.appendChild(empty);
        } else {
          for (const card of cards) {
          const now = new Date();
          const activeDebts = (card.debts || []).filter((debt) => Number(debt.outstanding_total || 0) > 0);
          activeDebts.sort((a, b) => {
            const aState = debtUi.debtDueState(a, now);
            const bState = debtUi.debtDueState(b, now);
            const rankDiff = duePriorityRank(aState) - duePriorityRank(bState);
            if (rankDiff !== 0) {
              return rankDiff;
            }
            const aDue = debtUi.parseIsoDateEnd(a.due_date);
            const bDue = debtUi.parseIsoDateEnd(b.due_date);
            if (aDue && bDue) {
              return aDue.getTime() - bDue.getTime();
            }
            if (aDue) {
              return -1;
            }
            if (bDue) {
              return 1;
            }
            return Number(b.id || 0) - Number(a.id || 0);
          });
          const visibleDebts = activeDebts.slice(0, 2);
          const rowsHtml = visibleDebts
            .map((debt) => {
              const principal = debtUi.parseAmount(debt.principal || 0);
              const outstanding = debtUi.parseAmount(debt.outstanding_total || 0);
              const repaid = debtUi.parseAmount(debt.repaid_total || 0);
              const repayPercent = principal > 0 ? Math.max(0, Math.min(100, Math.round((repaid / principal) * 100))) : 0;
              const direction = debt.direction === "borrow" ? "borrow" : "lend";
              const directionLabel = debtUi.debtDirectionBalanceLabel(direction);
              const repayTone = direction === "borrow" ? (repayPercent >= 100 ? "borrow-ok" : repayPercent >= 40 ? "borrow-warn" : "borrow-danger") : (repayPercent >= 100 ? "lend-ok" : "lend-warn");
              const dueState = debtUi.debtDueState(debt, now);
              const dueProgress = debtUi.debtDueProgress(debt, dueState, now);
              const dueDays = debtUi.debtDueDaysBadge(debt, dueState, now);
              return `
                <div class="dashboard-debt-row">
                  <div class="dashboard-debt-row-col">
                    <div class="muted-small">${directionLabel}</div>
                    <div class="debt-amount-principal ${direction === "borrow" ? "debt-amount-principal-borrow" : "debt-amount-principal-lend"}">${debtUi.formatMoney(outstanding)}</div>
                  </div>
                  <div class="dashboard-debt-row-col">
                    <div class="muted-small">Погашение</div>
                    <div class="debt-repay-progress">
                      <div class="debt-repay-progress-track">
                        <span class="debt-repay-progress-bar debt-repay-progress-bar-${repayTone}" style="width:${repayPercent}%"></span>
                      </div>
                      <span class="muted-small">${repayPercent}% (${debtUi.formatMoney(repaid)} из ${debtUi.formatMoney(principal)})</span>
                    </div>
                  </div>
                  <div class="dashboard-debt-row-col">
                    <div class="row debt-due-head">
                      <span class="dashboard-debt-due-label dashboard-debt-due-label-${dueState}">${dueBadgeLabel(dueState, debt.due_date || "")}</span>
                      ${dueDays ? `<span class="debt-due-days-badge debt-due-days-badge-${dueState}">${dueDays}</span>` : ""}
                    </div>
                    ${
                      dueProgress
                        ? `<div class="debt-due-progress"><div class="debt-due-progress-track"><span class="debt-due-progress-bar debt-due-progress-bar-${dueProgress.tone}" style="width:${dueProgress.percent}%"></span></div><span class="muted-small">Срок: ${dueProgress.percent}%</span></div>`
                        : `<span class="muted-small">Срок не задан</span>`
                    }
                    <div class="dashboard-debt-actions">
                      <button class="btn btn-repay btn-xs" type="button" data-dashboard-repay-debt-id="${debt.id}" ${outstanding <= 0 ? "disabled" : ""}>Погашение</button>
                      <button class="btn btn-secondary btn-xs" type="button" data-dashboard-history-debt-id="${debt.id}">История</button>
                    </div>
                  </div>
                </div>
              `;
            })
            .join("");
          const createdAt = visibleDebts[0]?.created_at ? formatDateTimeRu(visibleDebts[0].created_at) : "";
          const compact = document.createElement("article");
          compact.className = "panel debt-card debt-card-compact";
          compact.innerHTML = `
            <div class="debt-card-compact-grid">
              <div class="debt-card-compact-col debt-card-compact-main">
                <div class="debt-card-compact-head">
                  <div class="debt-card-compact-title-block">
                    <h3>${core.highlightText(card.counterparty || "", "")}</h3>
                    <span class="debt-status debt-status-${card.status}">${card.status === "active" ? "Активный" : "Закрыт"}</span>
                    ${createdAt ? `<span class="muted-small">Создано: ${createdAt}</span>` : ""}
                  </div>
                </div>
              </div>
              <div class="debt-card-compact-col debt-card-compact-rows debt-child-zone">${rowsHtml}</div>
            </div>
          `;
            el.dashboardDebtsList.appendChild(compact);
          }
        }
        state.dashboardDebtsHydrated = true;
      }
    } finally {
      if (shouldRefreshDebts && el.dashboardDebtsPanel) {
        refreshState.end?.(el.dashboardDebtsPanel);
      }
      if (shouldRefreshPlans && el.dashboardPlansPanel) {
        refreshState.end?.(el.dashboardPlansPanel);
      }
    }
  }

  async function loadDashboardPlans() {
    const ui = core.getUiSettings ? core.getUiSettings() : null;
    if (ui && ui.showDashboardOperations === false) {
      return;
    }
    await getPlansFeature().loadPlans?.();
  }

  const api = {
    loadDashboard,
    loadDashboardOperations: loadDashboardPlans,
    loadDashboardPlans,
  };

  window.App.registerRuntimeModule?.("dashboard", api);
})();
