(() => {
  const { state, el, core } = window.App;
  const debtUi = core.debtUi;
  const formatMoney = debtUi.formatMoney;
  const parseAmount = debtUi.parseAmount;
  const parseIsoDate = debtUi.parseIsoDate;
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
    const query = String(el.debtSearchQ?.value || "").trim().toLowerCase();
    const statusFilter = state.debtStatusFilter || "active";
    const filtered = [];

    for (const card of cards) {
      if (statusFilter === "active" && card.status !== "active") {
        continue;
      }
      if (statusFilter === "closed" && card.status !== "closed") {
        continue;
      }
      if (!query) {
        filtered.push(card);
        continue;
      }
      const cpMatch = String(card.counterparty || "").toLowerCase().includes(query);
      const debtMatch = (card.debts || []).some((item) => String(item.note || "").toLowerCase().includes(query));
      if (cpMatch || debtMatch) {
        filtered.push(card);
      }
    }
    return filtered;
  }

  async function refreshDebtViews() {
    await loadDebtsCards();
    if (window.App.actions?.loadDashboard) {
      await window.App.actions.loadDashboard();
    }
  }

  function renderDebtCards(cards) {
    if (!el.debtsCards) {
      return;
    }
    el.debtsCards.innerHTML = "";
    const visibleCards = filterCards(cards);
    const searchQuery = String(el.debtSearchQ?.value || "").trim();
    if (!visibleCards.length) {
      const empty = document.createElement("div");
      empty.className = "muted-small";
      empty.textContent = "Долги не найдены";
      el.debtsCards.appendChild(empty);
      return;
    }

    for (const card of visibleCards) {
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
          const directionLabel = direction === "borrow" ? "Я взял" : "Я дал";
          const repaidClass = debtRepaidClass(debt);
          const noteText = debt.note ? core.highlightText(String(debt.note), searchQuery) : "";
          return `<tr class="debt-row-${dueState} debt-row-${direction}">
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
        <div class="table-wrap">
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

  async function loadDebtsCards() {
    const params = new URLSearchParams();
    params.set("include_closed", state.debtStatusFilter === "active" ? "false" : "true");
    const cards = await core.requestJson(`/api/v1/debts/cards?${params.toString()}`, { headers: core.authHeaders() });
    state.debtCardsCache = cards;
    renderDebtCards(cards);
  }

  function openDebtRepaymentModal(debtId) {
    const found = findDebtById(debtId);
    if (!found) {
      core.setStatus("Долг не найден");
      return;
    }
    const { card, debt } = found;
    const principal = Number(debt.principal || 0);
    const repaid = Number(debt.repaid_total || 0);
    const outstanding = Number(debt.outstanding_total || 0);
    const progress = principal > 0 ? Math.max(0, Math.min(100, (repaid / principal) * 100)) : 0;
    el.repaymentDebtId.value = String(debtId);
    if (el.repaymentCounterparty) {
      el.repaymentCounterparty.textContent = card.counterparty || "Контрагент";
    }
    if (el.repaymentDirection) {
      const isBorrow = debt.direction === "borrow";
      el.repaymentDirection.textContent = isBorrow ? "Я взял" : "Я дал";
      el.repaymentDirection.classList.remove("debt-direction-pill-lend", "debt-direction-pill-borrow");
      el.repaymentDirection.classList.add(isBorrow ? "debt-direction-pill-borrow" : "debt-direction-pill-lend");
    }
    if (el.repaymentOutstanding) {
      el.repaymentOutstanding.textContent = formatMoney(outstanding);
    }
    if (el.repaymentProgressBar) {
      el.repaymentProgressBar.style.width = `${progress}%`;
    }
    if (!el.repaymentDate.value) {
      el.repaymentDate.value = new Date().toISOString().slice(0, 10);
    }
    el.repaymentAmount.value = "";
    el.repaymentNote.value = "";
    updateRepaymentDeltaHint();
    el.debtRepaymentModal.classList.remove("hidden");
  }

  function closeDebtRepaymentModal() {
    el.debtRepaymentModal.classList.add("hidden");
    el.repaymentDebtId.value = "";
  }

  function updateRepaymentDeltaHint() {
    const debtId = Number(el.repaymentDebtId.value || 0);
    const entered = parseAmount(el.repaymentAmount?.value || 0);
    const found = debtId ? findDebtById(debtId) : null;
    if (!found) {
      if (el.repaymentBeforeValue) {
        el.repaymentBeforeValue.textContent = formatMoney(0);
      }
      if (el.repaymentAfterValue) {
        el.repaymentAfterValue.textContent = formatMoney(0);
      }
      if (el.repaymentCarryValue) {
        el.repaymentCarryValue.textContent = formatMoney(0);
      }
      if (el.repaymentCarryRow) {
        el.repaymentCarryRow.classList.add("hidden");
      }
      return;
    }
    const { debt } = found;
    const outstanding = parseAmount(debt.outstanding_total);
    if (el.repaymentBeforeValue) {
      el.repaymentBeforeValue.textContent = formatMoney(outstanding);
    }
    if (entered <= outstanding) {
      const left = Math.max(0, outstanding - entered);
      if (el.repaymentAfterValue) {
        el.repaymentAfterValue.textContent = formatMoney(left);
      }
      if (el.repaymentCarryValue) {
        el.repaymentCarryValue.textContent = formatMoney(0);
      }
      if (el.repaymentCarryRow) {
        el.repaymentCarryRow.classList.add("hidden");
      }
      return;
    }
    const overpay = entered - outstanding;
    const reverseDirection = debt.direction === "lend" ? "Я взял" : "Я дал";
    if (el.repaymentAfterValue) {
      el.repaymentAfterValue.textContent = formatMoney(0);
    }
    if (el.repaymentCarryValue) {
      el.repaymentCarryValue.textContent = `${formatMoney(overpay)} (${reverseDirection})`;
    }
    if (el.repaymentCarryRow) {
      el.repaymentCarryRow.classList.remove("hidden");
    }
  }

  async function submitDebtRepayment(event) {
    event.preventDefault();
    const debtId = Number(el.repaymentDebtId.value || 0);
    if (!debtId) {
      return;
    }
    await core.requestJson(`/api/v1/debts/${debtId}/repayments`, {
      method: "POST",
      headers: core.authHeaders(),
      body: JSON.stringify({
        amount: el.repaymentAmount.value,
        repayment_date: el.repaymentDate.value,
        note: el.repaymentNote.value || null,
      }),
    });
    closeDebtRepaymentModal();
    await refreshDebtViews();
  }

  function openDebtHistoryModal(debtId) {
    if (!el.debtHistoryModal) {
      core.setStatus("Модалка истории недоступна");
      return;
    }
    const found = findDebtById(debtId);
    if (!found) {
      core.setStatus("Долг не найден");
      return;
    }
    const { card, debt } = found;
    const isBorrow = debt.direction === "borrow";
    if (el.debtHistoryCounterparty) {
      el.debtHistoryCounterparty.textContent = card.counterparty || "Контрагент";
    }
    if (el.debtHistoryDirection) {
      el.debtHistoryDirection.textContent = isBorrow ? "Я взял" : "Я дал";
      el.debtHistoryDirection.classList.remove("debt-direction-pill-lend", "debt-direction-pill-borrow");
      el.debtHistoryDirection.classList.add(isBorrow ? "debt-direction-pill-borrow" : "debt-direction-pill-lend");
    }
    if (el.debtHistoryOutstanding) {
      el.debtHistoryOutstanding.textContent = formatMoney(debt.outstanding_total);
    }
    if (el.debtHistoryList) {
      const issuancesDesc = debt.issuances || [];
      const issuancesAsc = issuancesDesc.slice().sort((a, b) => {
        const aTs = parseIsoDate(a.issuance_date)?.getTime() || 0;
        const bTs = parseIsoDate(b.issuance_date)?.getTime() || 0;
        if (aTs !== bTs) {
          return aTs - bTs;
        }
        return Number(a.id || 0) - Number(b.id || 0);
      });
      const startIssuance = issuancesAsc[0] || null;
      const events = [];
      for (const issuance of issuancesDesc) {
        events.push({
          type: "issuance",
          date: issuance.issuance_date || "",
          amount: Number(issuance.amount || 0),
          note: issuance.note || "",
          id: Number(issuance.id || 0),
        });
      }
      for (const repayment of debt.repayments || []) {
        events.push({
          type: "repayment",
          date: repayment.repayment_date || "",
          amount: Number(repayment.amount || 0),
          note: repayment.note || "",
          id: Number(repayment.id || 0),
        });
      }
      events.sort((a, b) => {
        const aTs = parseIsoDateEnd(a.date)?.getTime() || 0;
        const bTs = parseIsoDateEnd(b.date)?.getTime() || 0;
        if (aTs !== bTs) {
          return bTs - aTs;
        }
        return b.id - a.id;
      });
      if (!events.length) {
        el.debtHistoryList.innerHTML = '<div class="muted-small">Событий пока нет</div>';
      } else {
        const startTitle = isBorrow ? "Начало: я взял в долг" : "Начало: я дал в долг";
        const startAmount = startIssuance ? Number(startIssuance.amount || 0) : Number(debt.principal || 0);
        const startDate = startIssuance?.issuance_date || debt.start_date;
        const startNote = startIssuance?.note || debt.note || "";
        const startBlock = `<article class="debt-history-event debt-history-event-start">
          <div class="row between">
            <strong>${startTitle}</strong>
            <span class="muted-small">${startDate ? core.formatDateRu(startDate) : "-"}</span>
          </div>
          <div class="debt-history-amount">${formatMoney(startAmount)}</div>
          ${startNote ? `<div class="muted-small">${core.highlightText(startNote, "")}</div>` : ""}
        </article>`;
        const eventsHtml = events.map((event) => {
            const eventClass = event.type === "repayment" ? "debt-history-event-repayment" : "debt-history-event-issuance";
            const eventTitle = event.type === "repayment" ? "Погашение" : "Добавление";
            return `<article class="debt-history-event ${eventClass}">
              <div class="row between">
                <strong>${eventTitle}</strong>
                <span class="muted-small">${event.date ? core.formatDateRu(event.date) : "-"}</span>
              </div>
              <div class="debt-history-amount">${formatMoney(event.amount)}</div>
              ${event.note ? `<div class="muted-small">${core.highlightText(event.note, "")}</div>` : ""}
            </article>`;
          }).join("");
        el.debtHistoryList.innerHTML = `${startBlock}${eventsHtml}`;
      }
    }
    el.debtHistoryModal.classList.remove("hidden");
  }

  function closeDebtHistoryModal() {
    if (!el.debtHistoryModal) {
      return;
    }
    el.debtHistoryModal.classList.add("hidden");
    if (el.debtHistoryList) {
      el.debtHistoryList.innerHTML = "";
    }
  }

  function setDebtStatusFilter(filterValue) {
    state.debtStatusFilter = filterValue || "active";
    core.syncSegmentedActive(el.debtStatusTabs, "debt-status", state.debtStatusFilter);
    loadDebtsCards().catch((err) => core.setStatus(String(err)));
  }

  async function applyDebtSearch() {
    await loadDebtsCards();
  }

  function findDebtById(debtId) {
    for (const card of state.debtCardsCache || []) {
      for (const debt of card.debts || []) {
        if (Number(debt.id) === Number(debtId)) {
          return { card, debt };
        }
      }
    }
    return null;
  }

  function openEditDebtModal(debtId) {
    const found = findDebtById(debtId);
    if (!found) {
      core.setStatus("Долг не найден");
      return;
    }
    const { card, debt } = found;
    if (window.App.actions?.openCreateModalForDebtEdit) {
      window.App.actions.openCreateModalForDebtEdit({
        id: debt.id,
        counterparty: card.counterparty || "",
        direction: debt.direction || "lend",
        principal: debt.principal || "",
        start_date: debt.start_date || "",
        due_date: debt.due_date || "",
        note: debt.note || "",
      });
      return;
    }
    core.setStatus("Редактирование долга недоступно");
  }

  function closeEditDebtModal() {
    el.editDebtModal.classList.add("hidden");
    el.editDebtId.value = "";
  }

  async function submitEditDebt(event) {
    event.preventDefault();
    const debtId = Number(el.editDebtId.value || 0);
    if (!debtId) {
      return;
    }
    await core.requestJson(`/api/v1/debts/${debtId}`, {
      method: "PATCH",
      headers: core.authHeaders(),
      body: JSON.stringify({
        counterparty: el.editDebtCounterparty.value.trim(),
        direction: el.editDebtDirection.value,
        principal: el.editDebtPrincipal.value,
        start_date: el.editDebtStartDate.value,
        due_date: el.editDebtDueDate.value || null,
        note: el.editDebtNote.value.trim() || null,
      }),
    });
    closeEditDebtModal();
    await refreshDebtViews();
  }

  function deleteDebtFlow(debtId) {
    core.runDestructiveAction({
      confirmMessage: "Удалить долг?",
      doDelete: async () => {
        await core.requestJson(`/api/v1/debts/${debtId}`, {
          method: "DELETE",
          headers: core.authHeaders(),
        });
      },
      onAfterDelete: async () => {
        await refreshDebtViews();
      },
      onDeleteError: "Не удалось удалить долг",
    });
  }

  window.App.featureDebts = {
    loadDebtsCards,
    openDebtRepaymentModal,
    closeDebtRepaymentModal,
    submitDebtRepayment,
    updateRepaymentDeltaHint,
    openDebtHistoryModal,
    closeDebtHistoryModal,
    setDebtStatusFilter,
    applyDebtSearch,
    openEditDebtModal,
    closeEditDebtModal,
    submitEditDebt,
    deleteDebtFlow,
  };
})();
