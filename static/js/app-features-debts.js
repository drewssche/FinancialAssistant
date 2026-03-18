(() => {
  const { state, el, core } = window.App;
  const debtUi = core.debtUi;
  const formatMoney = debtUi.formatMoney;
  const parseAmount = debtUi.parseAmount;
  const parseIsoDate = debtUi.parseIsoDate;
  const debtCardsRenderer = window.App.debtCardsRenderer;
  const debtModalsFeature = window.App.createDebtModalsFeature
    ? window.App.createDebtModalsFeature({
      state,
      el,
      core,
      debtUi,
      refreshDebtViews,
      findDebtById,
      syncDebtsControls,
      getCurrentDebtIds,
    })
    : null;
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
    syncDebtsControls();
  }

  function getCurrentDebtIds() {
    const cards = Array.isArray(state.debtCardsCache) ? state.debtCardsCache : [];
    const statusFilter = state.debtStatusFilter || "active";
    const filteredCards = cards.filter((card) => {
      if (statusFilter === "active") {
        return card?.status === "active";
      }
      if (statusFilter === "closed") {
        return card?.status === "closed";
      }
      return true;
    });
    return filteredCards.flatMap((card) => (Array.isArray(card?.debts) ? card.debts : []))
      .map((debt) => Number(debt?.id || 0))
      .filter((id) => id > 0);
  }

  function syncDebtsControls() {
    if (!el.deleteAllDebtsBtn) {
      return;
    }
    el.deleteAllDebtsBtn.disabled = getCurrentDebtIds().length === 0;
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

  window.App.featureDebts = {
    loadDebtsCards,
    renderDebtCards,
    openDebtRepaymentModal: debtModalsFeature?.openDebtRepaymentModal,
    closeDebtRepaymentModal: debtModalsFeature?.closeDebtRepaymentModal,
    submitDebtRepayment: debtModalsFeature?.submitDebtRepayment,
    updateRepaymentDeltaHint: debtModalsFeature?.updateRepaymentDeltaHint,
    openDebtHistoryModal: debtModalsFeature?.openDebtHistoryModal,
    closeDebtHistoryModal: debtModalsFeature?.closeDebtHistoryModal,
    setDebtStatusFilter,
    setDebtSortPreset,
    applyDebtSearch,
    loadMoreDebtCards,
    loadMoreDebtHistoryEvents: debtModalsFeature?.loadMoreDebtHistoryEvents,
    openEditDebtModal: debtModalsFeature?.openEditDebtModal,
    deleteDebtFlow: debtModalsFeature?.deleteDebtFlow,
    deleteAllDebtsFlow: debtModalsFeature?.deleteAllDebtsFlow,
  };
})();
