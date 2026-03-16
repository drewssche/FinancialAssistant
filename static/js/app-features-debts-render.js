(() => {
  const { state, el, core } = window.App;
  const debtUi = core.debtUi;
  const formatMoney = debtUi.formatMoney;
  const parseIsoDateEnd = debtUi.parseIsoDateEnd;
  const debtDueState = debtUi.debtDueState;
  const debtDueProgress = debtUi.debtDueProgress;
  const debtDueDaysBadge = debtUi.debtDueDaysBadge;
  const debtRepaymentProgress = debtUi.debtRepaymentProgress;

  function debtDueLabel(stateValue, dueDate) {
    if (stateValue === "overdue") {
      return "Просрочено";
    }
    if (stateValue === "soon") {
      return `Скоро срок: ${core.formatDateRu(dueDate)}`;
    }
    if (stateValue === "future" && dueDate) {
      return `Срок: ${core.formatDateRu(dueDate)}`;
    }
    if (stateValue === "closed") {
      return "Закрыт";
    }
    return "Без срока";
  }

  function debtRepaidClass(debt) {
    const direction = debt.direction === "borrow" ? "borrow" : "lend";
    const repaid = Number(debt.repaid_total || 0);
    const outstanding = Number(debt.outstanding_total || 0);
    if (direction === "borrow") {
      if (repaid <= 0) {
        return "debt-amount-repaid-borrow-zero";
      }
      if (outstanding > 0) {
        return "debt-amount-repaid-borrow-partial";
      }
      return "debt-amount-repaid-borrow-closed";
    }
    return "debt-amount-repaid-lend";
  }

  function debtPriorityRank(stateValue) {
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

  function filterCards(cards) {
    const statusFilter = state.debtStatusFilter || "active";
    const filtered = [];

    for (const card of cards) {
      if (statusFilter === "active" && card.status !== "active") {
        continue;
      }
      if (statusFilter === "closed" && card.status !== "closed") {
        continue;
      }
      filtered.push(card);
    }
    return filtered;
  }

  function cardPriorityInfo(card, now) {
    let rank = 9;
    let dueTs = Number.POSITIVE_INFINITY;
    for (const debt of card.debts || []) {
      if (Number(debt.outstanding_total || 0) <= 0) {
        continue;
      }
      const dueState = debtDueState(debt, now);
      const dueRank = debtPriorityRank(dueState);
      if (dueRank < rank) {
        rank = dueRank;
      }
      const due = parseIsoDateEnd(debt.due_date);
      if (due && due.getTime() < dueTs) {
        dueTs = due.getTime();
      }
    }
    return { rank, dueTs };
  }

  function sortCards(cards) {
    const preset = state.debtSortPreset || "priority";
    const now = new Date();
    const sorted = cards.slice();
    if (preset === "name") {
      sorted.sort((a, b) => String(a.counterparty || "").localeCompare(String(b.counterparty || ""), "ru"));
      return sorted;
    }
    if (preset === "amount") {
      sorted.sort((a, b) => {
        const diff = Number(b.outstanding_total || 0) - Number(a.outstanding_total || 0);
        if (diff !== 0) {
          return diff;
        }
        return String(a.counterparty || "").localeCompare(String(b.counterparty || ""), "ru");
      });
      return sorted;
    }
    sorted.sort((a, b) => {
      const aStatus = a.status === "active" ? 0 : 1;
      const bStatus = b.status === "active" ? 0 : 1;
      if (aStatus !== bStatus) {
        return aStatus - bStatus;
      }
      const aInfo = cardPriorityInfo(a, now);
      const bInfo = cardPriorityInfo(b, now);
      if (aInfo.rank !== bInfo.rank) {
        return aInfo.rank - bInfo.rank;
      }
      if (aInfo.dueTs !== bInfo.dueTs) {
        return aInfo.dueTs - bInfo.dueTs;
      }
      return String(a.counterparty || "").localeCompare(String(b.counterparty || ""), "ru");
    });
    return sorted;
  }

  function renderDebtCards(cards) {
    if (!el.debtsCards) {
      return;
    }
    el.debtsCards.innerHTML = "";
    const visibleCards = sortCards(filterCards(cards));
    const pageSize = Number(state.debtCardsPageSize || 20);
    const visibleLimit = Number(state.debtCardsVisibleLimit || pageSize);
    const renderedCards = visibleCards.slice(0, Math.max(pageSize, visibleLimit));
    state.debtCardsVisibleTotal = visibleCards.length;
    state.debtCardsHasMore = renderedCards.length < visibleCards.length;
    if (el.debtsInfiniteSentinel) {
      el.debtsInfiniteSentinel.classList.toggle("hidden", !state.debtCardsHasMore);
    }
    const searchQuery = String(el.debtSearchQ?.value || "").trim();
    if (!renderedCards.length) {
      const empty = document.createElement("div");
      empty.className = "muted-small";
      empty.textContent = "Долги не найдены";
      el.debtsCards.appendChild(empty);
      return;
    }

    for (const card of renderedCards) {
      const item = document.createElement("article");
      item.className = "panel debt-card";
      const now = new Date();
      const sortedDebts = (card.debts || []).slice().sort((a, b) => {
        const aState = debtDueState(a, now);
        const bState = debtDueState(b, now);
        const rankDiff = debtPriorityRank(aState) - debtPriorityRank(bState);
        if (rankDiff !== 0) {
          return rankDiff;
        }
        const aDue = parseIsoDateEnd(a.due_date);
        const bDue = parseIsoDateEnd(b.due_date);
        if (aDue && bDue) {
          return aDue.getTime() - bDue.getTime();
        }
        if (aDue) {
          return -1;
        }
        if (bDue) {
          return 1;
        }
        return b.id - a.id;
      });

      const debtsRows = sortedDebts
        .map((debt) => {
          const dueState = debtDueState(debt, now);
          const dueProgress = debtDueProgress(debt, dueState, now);
          const dueDays = debtDueDaysBadge(debt, dueState, now);
          const repayProgress = debtRepaymentProgress(debt);
          const repayments = debt.repayments || [];
          const issuances = debt.issuances || [];
          const lastRepayment = repayments.length ? repayments[0].repayment_date : null;
          const lastIssuance = issuances.length ? issuances[0].issuance_date : null;
          const direction = debt.direction === "borrow" ? "borrow" : "lend";
          const directionLabel = debtUi.debtDirectionActionLabel(direction);
          const repaidClass = debtRepaidClass(debt);
          const noteText = debt.note ? core.highlightText(String(debt.note), searchQuery) : "";
          return `<tr class="debt-row-${dueState} debt-row-${direction} debt-record-row">
            <td>${core.formatDateRu(debt.start_date)}</td>
            <td><span class="debt-direction-pill debt-direction-pill-${direction}">${directionLabel}</span></td>
            <td><span class="debt-amount-principal debt-amount-principal-${direction}">${formatMoney(debt.principal)}</span></td>
            <td><span class="debt-amount-repaid ${repaidClass}">${formatMoney(debt.repaid_total)}</span></td>
            <td>
              <span class="debt-amount-outstanding debt-amount-outstanding-${direction}">${formatMoney(debt.outstanding_total)}</span>
              <div class="debt-repay-progress">
                <div class="debt-repay-progress-track">
                  <span class="debt-repay-progress-bar debt-repay-progress-bar-${repayProgress.tone}" style="width:${repayProgress.percent}%"></span>
                </div>
                <span class="muted-small">Погашено: ${repayProgress.percent}%</span>
              </div>
            </td>
            <td>
              <div class="row debt-due-head">
                <span class="muted-small">${debtDueLabel(dueState, debt.due_date)}</span>
                ${dueDays ? `<span class="debt-due-days-badge debt-due-days-badge-${dueState}">${dueDays}</span>` : ""}
              </div>
              ${
                dueProgress
                  ? `<div class="debt-due-progress"><div class="debt-due-progress-track"><span class="debt-due-progress-bar debt-due-progress-bar-${dueProgress.tone}" style="width:${dueProgress.percent}%"></span></div><span class="muted-small">Прогресс срока: ${dueProgress.percent}%</span></div>`
                  : ""
              }
              <div class="muted-small">Добавлений: ${issuances.length}${lastIssuance ? ` • Последнее: ${core.formatDateRu(lastIssuance)}` : ""}</div>
              <div class="muted-small">Платежей: ${repayments.length}${lastRepayment ? ` • Последний: ${core.formatDateRu(lastRepayment)}` : ""}</div>
              ${noteText ? `<div class="muted-small">${noteText}</div>` : ""}
            </td>
            <td>
              <div class="actions row-actions debt-actions-grid">
                <button class="btn btn-repay btn-xs" type="button" data-repay-debt-id="${debt.id}" ${Number(debt.outstanding_total) <= 0 ? "disabled" : ""}>Погашение</button>
                <button class="btn btn-secondary btn-xs" type="button" data-edit-debt-id="${debt.id}">Редактировать</button>
                <button class="btn btn-secondary btn-xs" type="button" data-history-debt-id="${debt.id}">История</button>
                <button class="btn btn-danger btn-xs" type="button" data-delete-debt-id="${debt.id}">Удалить</button>
              </div>
            </td>
          </tr>`;
        })
        .join("");

      item.innerHTML = `
        <div class="row between">
          <div>
            <h3>${core.highlightText(card.counterparty, searchQuery)}</h3>
            <p class="subtitle">Статус: <span class="debt-status debt-status-${card.status}">${card.status === "active" ? "Активный" : "Закрыт"}</span></p>
          </div>
        </div>
        <div class="table-wrap debt-card-children-wrap">
          <table class="table table-hover">
            <thead>
              <tr>
                <th>Дата</th>
                <th>Направление</th>
                <th>Сумма</th>
                <th>Погашено</th>
                <th>Остаток</th>
                <th>Срок/История</th>
                <th></th>
              </tr>
            </thead>
            <tbody>${debtsRows}</tbody>
          </table>
        </div>
      `;
      el.debtsCards.appendChild(item);
    }
  }

  window.App.debtCardsRenderer = {
    renderDebtCards,
  };
})();
