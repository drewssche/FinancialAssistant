(() => {
  const { state, el, core } = window.App;
  const dashboardData = window.App.dashboardData || {};
  const operationModal = window.App.operationModal;
  const debtUi = core.debtUi;
  const getCategoryMetaById = operationModal.getCategoryMetaById;

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

    window.App.featurePlans?.renderDashboardPlans?.();

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
    }
  }

  async function loadDashboardPlans() {
    const ui = core.getUiSettings ? core.getUiSettings() : null;
    if (ui && ui.showDashboardOperations === false) {
      return;
    }
    await window.App.featurePlans?.loadPlans?.();
  }

  window.App.featureDashboard = {
    loadDashboard,
    loadDashboardOperations: loadDashboardPlans,
    loadDashboardPlans,
  };
})();
