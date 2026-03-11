(() => {
  const { state, el, core } = window.App;
  const debtUi = core.debtUi;
  const formatMoney = debtUi.formatMoney;
  const parseAmount = debtUi.parseAmount;
  const parseIsoDate = debtUi.parseIsoDate;
  const parseIsoDateEnd = debtUi.parseIsoDateEnd;
  const debtCardsRenderer = window.App.debtCardsRenderer;
  let debtsRequestController = null;
  let debtsRequestSeq = 0;
  const DEBTS_CARDS_CACHE_TTL_MS = 20000;

  function resetDebtCardsPagination() {
    state.debtCardsVisibleLimit = Number(state.debtCardsPageSize || 20);
  }

  async function refreshDebtViews() {
    await loadDebtsCards();
    if (window.App.actions?.loadDashboard) {
      await window.App.actions.loadDashboard();
    }
  }

  function renderDebtCards(cards) {
    if (!debtCardsRenderer?.renderDebtCards) {
      return;
    }
    debtCardsRenderer.renderDebtCards(cards);
  }

  function buildDebtsCardsCacheKey() {
    const includeClosed = state.debtStatusFilter === "active" ? "false" : "true";
    const query = String(el.debtSearchQ?.value || "").trim();
    return `debts:cards:include_closed=${includeClosed}:q=${query.toLowerCase()}`;
  }

  async function loadDebtsCards(options = {}) {
    const force = options.force === true;
    const cacheKey = buildDebtsCardsCacheKey();
    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, DEBTS_CARDS_CACHE_TTL_MS);
      if (cached) {
        state.debtCardsCache = cached;
        resetDebtCardsPagination();
        renderDebtCards(cached);
        return;
      }
    }
    if (debtsRequestController) {
      debtsRequestController.abort();
    }
    const requestController = new AbortController();
    debtsRequestController = requestController;
    const requestSeq = ++debtsRequestSeq;
    const params = new URLSearchParams();
    params.set("include_closed", state.debtStatusFilter === "active" ? "false" : "true");
    const query = String(el.debtSearchQ?.value || "").trim();
    if (query) {
      params.set("q", query);
    }
    try {
      const cards = await core.requestJson(`/api/v1/debts/cards?${params.toString()}`, {
        headers: core.authHeaders(),
        signal: requestController.signal,
      });
      if (requestSeq !== debtsRequestSeq) {
        return;
      }
      state.debtCardsCache = cards;
      core.setUiRequestCache(cacheKey, cards);
      resetDebtCardsPagination();
      renderDebtCards(cards);
    } catch (err) {
      if (core.isAbortError && core.isAbortError(err)) {
        return;
      }
      throw err;
    } finally {
      if (debtsRequestController === requestController) {
        debtsRequestController = null;
      }
    }
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
      el.repaymentDirection.textContent = debtUi.debtDirectionActionLabel(debt.direction);
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
      core.syncDateFieldValue(el.repaymentDate, core.getTodayIso());
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
    const enteredState = core.resolveMoneyInput(el.repaymentAmount?.value || 0);
    const entered = !enteredState.empty ? enteredState.previewValue : 0;
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
    const reverseDirection = debtUi.debtDirectionActionLabel(debt.direction === "lend" ? "borrow" : "lend");
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
    const repaymentDate = core.parseDateInputValue(el.repaymentDate.value);
    if (!repaymentDate) {
      core.setStatus("Проверь дату платежа");
      return;
    }
    const amount = core.resolveMoneyInput(el.repaymentAmount.value);
    if (!amount.valid || amount.value <= 0) {
      core.setStatus("Проверь сумму погашения");
      return;
    }
    await core.requestJson(`/api/v1/debts/${debtId}/repayments`, {
      method: "POST",
      headers: core.authHeaders(),
      body: JSON.stringify({
        amount: amount.formatted,
        repayment_date: repaymentDate,
        note: el.repaymentNote.value || null,
      }),
    });
    core.invalidateUiRequestCache("debts");
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
      el.debtHistoryDirection.textContent = debtUi.debtDirectionActionLabel(debt.direction);
      el.debtHistoryDirection.classList.remove("debt-direction-pill-lend", "debt-direction-pill-borrow");
      el.debtHistoryDirection.classList.add(isBorrow ? "debt-direction-pill-borrow" : "debt-direction-pill-lend");
    }
    if (el.debtHistoryOutstanding) {
      el.debtHistoryOutstanding.textContent = formatMoney(debt.outstanding_total);
    }
    if (el.debtHistoryItems) {
      const issuances = debt.issuances || [];
      const events = [];
      for (const issuance of issuances) {
        events.push({
          type: "issuance",
          date: issuance.issuance_date || "",
          amount: Number(issuance.amount || 0),
          note: issuance.note || "",
          id: Number(issuance.id || 0),
          created_at: issuance.created_at || "",
        });
      }
      for (const repayment of debt.repayments || []) {
        events.push({
          type: "repayment",
          date: repayment.repayment_date || "",
          amount: Number(repayment.amount || 0),
          note: repayment.note || "",
          id: Number(repayment.id || 0),
          created_at: repayment.created_at || "",
        });
      }
      events.sort((a, b) => {
        const aTs = parseIsoDate(a.date)?.getTime() || 0;
        const bTs = parseIsoDate(b.date)?.getTime() || 0;
        if (aTs !== bTs) {
          return aTs - bTs;
        }
        const aCreated = Date.parse(a.created_at || "") || 0;
        const bCreated = Date.parse(b.created_at || "") || 0;
        if (aCreated !== bCreated) {
          return aCreated - bCreated;
        }
        if (a.type !== b.type) {
          return a.type === "issuance" ? -1 : 1;
        }
        return a.id - b.id;
      });
      state.debtHistoryEvents = events;
      state.debtHistoryMeta = {
        isBorrow,
      };
      state.debtHistoryVisibleLimit = Number(state.debtHistoryPageSize || 20);
      renderDebtHistoryEvents();
    }
    el.debtHistoryModal.classList.remove("hidden");
  }

  function renderDebtHistoryEvents() {
    if (!el.debtHistoryItems) {
      return;
    }
    const events = state.debtHistoryEvents || [];
    const pageSize = Number(state.debtHistoryPageSize || 20);
    const visibleLimit = Number(state.debtHistoryVisibleLimit || pageSize);
    const visibleEvents = events.slice(0, Math.max(pageSize, visibleLimit));
    state.debtHistoryHasMore = visibleEvents.length < events.length;
    if (el.debtHistoryInfiniteSentinel) {
      el.debtHistoryInfiniteSentinel.classList.toggle("hidden", !state.debtHistoryHasMore);
    }
    if (!visibleEvents.length) {
      el.debtHistoryItems.innerHTML = '<div class="muted-small">Событий пока нет</div>';
      return;
    }
    const isBorrow = state.debtHistoryMeta?.isBorrow === true;
    const firstEvent = events[0];
    let runningOutstanding = 0;
    const eventBlocks = [];
    for (const event of visibleEvents) {
      if (event.type === "issuance") {
        runningOutstanding += Number(event.amount || 0);
      } else {
        runningOutstanding -= Number(event.amount || 0);
      }
      if (runningOutstanding < 0) {
        runningOutstanding = 0;
      }
      const isStart = event.type === "issuance" && event.id === firstEvent.id && event.date === firstEvent.date;
      const eventClass = isStart
        ? "debt-history-event-start"
        : (event.type === "repayment" ? "debt-history-event-repayment" : "debt-history-event-issuance");
      const eventTitle = isStart
        ? (isBorrow ? "Начальная сумма: я взял в долг" : "Начальная сумма: я дал в долг")
        : (event.type === "repayment"
          ? debtUi.debtRepaymentEventLabel(isBorrow ? "borrow" : "lend")
          : debtUi.debtIssuanceEventLabel(isBorrow ? "borrow" : "lend"));
      eventBlocks.push(`<article class="debt-history-event ${eventClass}">
      <div class="row between">
        <strong>${eventTitle}</strong>
        <span class="muted-small">${event.date ? core.formatDateRu(event.date) : "-"}</span>
      </div>
      <div class="debt-history-amount">${formatMoney(event.amount)}</div>
      <div class="muted-small">Остаток после шага: ${formatMoney(runningOutstanding)}</div>
      ${event.note ? `<div class="muted-small">${core.highlightText(event.note, "")}</div>` : ""}
    </article>`);
    }
    el.debtHistoryItems.innerHTML = eventBlocks.join("");
  }

  function closeDebtHistoryModal() {
    if (!el.debtHistoryModal) {
      return;
    }
    el.debtHistoryModal.classList.add("hidden");
    state.debtHistoryEvents = [];
    state.debtHistoryMeta = null;
    state.debtHistoryVisibleLimit = Number(state.debtHistoryPageSize || 20);
    state.debtHistoryHasMore = false;
    if (el.debtHistoryItems) {
      el.debtHistoryItems.innerHTML = "";
    }
    if (el.debtHistoryInfiniteSentinel) {
      el.debtHistoryInfiniteSentinel.classList.add("hidden");
    }
  }

  function setDebtStatusFilter(filterValue) {
    state.debtStatusFilter = filterValue || "active";
    core.syncSegmentedActive(el.debtStatusTabs, "debt-status", state.debtStatusFilter);
    resetDebtCardsPagination();
    loadDebtsCards().catch((err) => core.setStatus(String(err)));
  }

  function setDebtSortPreset(sortValue) {
    state.debtSortPreset = sortValue || "priority";
    core.syncSegmentedActive(el.debtSortTabs, "debt-sort", state.debtSortPreset);
    resetDebtCardsPagination();
    renderDebtCards(state.debtCardsCache || []);
    if (window.App.actions?.savePreferences) {
      window.App.actions.savePreferences().catch(() => {});
    }
  }

  async function applyDebtSearch() {
    resetDebtCardsPagination();
    await loadDebtsCards();
  }

  function loadMoreDebtCards() {
    if (!state.debtCardsHasMore) {
      return;
    }
    state.debtCardsVisibleLimit += Number(state.debtCardsPageSize || 20);
    renderDebtCards(state.debtCardsCache || []);
  }

  function loadMoreDebtHistoryEvents() {
    if (!state.debtHistoryHasMore) {
      return;
    }
    state.debtHistoryVisibleLimit += Number(state.debtHistoryPageSize || 20);
    renderDebtHistoryEvents();
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

  function deleteDebtFlow(debtId) {
    core.runDestructiveAction({
      confirmMessage: "Удалить долг?",
      doDelete: async () => {
        await core.requestJson(`/api/v1/debts/${debtId}`, {
          method: "DELETE",
          headers: core.authHeaders(),
        });
        core.invalidateUiRequestCache("debts");
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
    setDebtSortPreset,
    applyDebtSearch,
    loadMoreDebtCards,
    loadMoreDebtHistoryEvents,
    openEditDebtModal,
    deleteDebtFlow,
  };
})();
