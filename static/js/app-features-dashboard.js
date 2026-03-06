(() => {
  const { state, el, core } = window.App;
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


  async function loadDashboard() {
    if (window.App.actions.ensureAllTimeBounds) {
      await window.App.actions.ensureAllTimeBounds();
    }
    const { dateFrom, dateTo } = core.getPeriodBounds(state.period);
    const params = new URLSearchParams();
    params.set("period", state.period);
    params.set("date_from", dateFrom);
    params.set("date_to", dateTo);

    const data = await core.requestJson(`/api/v1/dashboard/summary?${params.toString()}`, {
      headers: core.authHeaders(),
    });

    el.incomeTotal.textContent = core.formatMoney(data.income_total);
    el.expenseTotal.textContent = core.formatMoney(data.expense_total);
    el.balanceTotal.textContent = core.formatMoney(data.balance);
    if (el.debtLendTotal) {
      el.debtLendTotal.textContent = core.formatMoney(data.debt_lend_outstanding);
    }
    if (el.debtBorrowTotal) {
      el.debtBorrowTotal.textContent = core.formatMoney(data.debt_borrow_outstanding);
    }
    if (el.debtNetTotal) {
      el.debtNetTotal.textContent = core.formatMoney(data.debt_net_position);
    }

    if (el.dashboardDebtsPanel) {
      el.dashboardDebtsPanel.classList.toggle("hidden", !core.isDashboardDebtsVisible());
    }
    if (!core.isDashboardDebtsVisible()) {
      return;
    }

    if (el.dashboardDebtsList) {
      const cards = await core.requestJson("/api/v1/debts/cards?include_closed=false", { headers: core.authHeaders() });
      el.dashboardDebtsList.innerHTML = "";
      const topCards = cards.slice(0, 6);
      if (!topCards.length) {
        const empty = document.createElement("div");
        empty.className = "muted-small";
        empty.textContent = "Нет активных долгов";
        el.dashboardDebtsList.appendChild(empty);
      } else {
        for (const card of topCards) {
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
                  </div>
                </div>
              `;
            })
            .join("");
          const compact = document.createElement("article");
          compact.className = "panel debt-card debt-card-compact";
          compact.innerHTML = `
            <div class="debt-card-compact-grid">
              <div class="debt-card-compact-col debt-card-compact-main">
                <h3>${core.highlightText(card.counterparty || "", "")}</h3>
                <p class="subtitle">Статус: <span class="debt-status debt-status-${card.status}">${card.status === "active" ? "Активный" : "Закрыт"}</span></p>
              </div>
              <div class="debt-card-compact-col debt-card-compact-rows">${rowsHtml}</div>
            </div>
          `;
          el.dashboardDebtsList.appendChild(compact);
        }
      }
    }
  }

  async function loadDashboardOperations() {
    if (window.App.actions.ensureAllTimeBounds) {
      await window.App.actions.ensureAllTimeBounds();
    }
    const { dateFrom, dateTo } = core.getPeriodBounds(state.period);
    el.dashboardPeriodLabel.textContent = core.formatPeriodLabel(dateFrom, dateTo);
    const params = new URLSearchParams({
      page: "1",
      page_size: "8",
      sort_by: "operation_date",
      sort_dir: "desc",
      date_from: dateFrom,
      date_to: dateTo,
    });

    const data = await core.requestJson(`/api/v1/operations?${params.toString()}`, { headers: core.authHeaders() });
    el.dashboardOperationsBody.innerHTML = "";

    if (!data.items.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="5">Нет операций за выбранный период</td>';
      el.dashboardOperationsBody.appendChild(row);
      return;
    }

    for (const item of data.items) {
      el.dashboardOperationsBody.appendChild(
        core.createOperationRow(item, {
          compact: true,
          selectable: false,
          category: getCategoryMetaById(item.category_id),
        }),
      );
    }
  }

  window.App.featureDashboard = {
    loadDashboard,
    loadDashboardOperations,
  };
})();
