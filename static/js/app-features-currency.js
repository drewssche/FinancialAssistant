(() => {
  const { state, el, core } = window.App;
  const pickerUtils = window.App.getRuntimeModule?.("picker-utils");
  const shared = window.App.analyticsShared || {};
  const escapeHtml = shared.escapeHtml || ((value) => String(value ?? ""));

  function getDashboardFeature() {
    return window.App.getRuntimeModule?.("dashboard") || {};
  }

  function getLoadingSkeletons() {
    return window.App.getRuntimeModule?.("loading-skeletons") || {};
  }

  function getInlineRefreshState() {
    return window.App.getRuntimeModule?.("inline-refresh-state") || {};
  }

  function getAnalyticsCurrencyFeature() {
    return window.App.getRuntimeModule?.("analytics-currency-module") || {};
  }

  function getOperationModal() {
    return window.App.getRuntimeModule?.("operation-modal") || {};
  }

  function getNavigationActions() {
    return window.App.getRuntimeModule?.("navigation") || {};
  }

  function getOperationsFeature() {
    return window.App.getRuntimeModule?.("operations") || {};
  }

  function getResultPresentation(rawValue) {
    const value = Number(rawValue || 0);
    if (value > 0) {
      return { cardClass: "analytics-kpi-income", label: "Прибыль", chipClass: "analytics-kpi-chip-positive" };
    }
    if (value < 0) {
      return { cardClass: "analytics-kpi-expense", label: "Убыток", chipClass: "analytics-kpi-chip-negative" };
    }
    return { cardClass: "analytics-kpi-neutral", label: "Результат", chipClass: "analytics-kpi-chip-neutral" };
  }

  function formatTradeQuoteTotal(item) {
    const quantity = Number(item?.quantity || 0);
    const unitPrice = Number(item?.unit_price || 0);
    const quoteCurrency = core.normalizeCurrencyCode?.(item?.quote_currency, "BYN") || "BYN";
    return core.formatMoney(quantity * unitPrice, { currency: quoteCurrency });
  }

  function formatRateWithQuote(rate, quoteCurrency) {
    const quote = core.normalizeCurrencyCode?.(quoteCurrency, "BYN") || "BYN";
    return `${core.formatRateDisplay?.(rate || 0, 4, 6) || Number(rate || 0).toFixed(6)} ${core.formatCurrencySymbol?.(quote) || quote}`;
  }

  async function refreshAfterTradeMutation() {
    await loadCurrencySection({ force: true });
    core.invalidateUiRequestCache?.("dashboard:summary");
    getDashboardFeature().loadDashboard?.().catch(() => {});
    getAnalyticsCurrencyFeature().loadAnalyticsCurrency?.({ force: true }).catch(() => {});
  }

  async function openLinkedOperation(operationId) {
    const resolvedId = Number(operationId || 0);
    if (!(resolvedId > 0)) {
      return;
    }
    const operationModal = getOperationModal();
    if (!operationModal?.openEditModal) {
      throw new Error("Редактирование операции недоступно");
    }
    const item = await core.requestJson(`/api/v1/operations/${resolvedId}`, {
      headers: core.authHeaders(),
    });
    await getNavigationActions().switchSection?.("operations");
    await operationModal.openEditModal(item);
  }

  async function deleteLinkedOperation(operationId) {
    const resolvedId = Number(operationId || 0);
    if (!(resolvedId > 0)) {
      return;
    }
    const operationsFeature = getOperationsFeature();
    const item = await core.requestJson(`/api/v1/operations/${resolvedId}`, {
      headers: core.authHeaders(),
    });
    if (operationsFeature.deleteOperationFlow) {
      await operationsFeature.deleteOperationFlow(item);
      return;
    }
    await core.requestJson(`/api/v1/operations/${resolvedId}`, {
      method: "DELETE",
      headers: core.authHeaders(),
    });
    await refreshAfterTradeMutation();
  }

  const createPerformanceFeature = window.App.getRuntimeModule?.("currency-performance-factory");
  const performanceFeature = createPerformanceFeature?.({
    state,
    el,
    core,
    pickerUtils,
    escapeHtml,
    reload: () => loadCurrencySection({ force: true }),
  }) || {};
  const syncPerformancePeriodTabs = performanceFeature.syncPeriodTabs || (() => {});
  const fetchPerformanceHistory = performanceFeature.fetchHistory || (async () => ({ points: [] }));
  const renderPerformanceChart = performanceFeature.renderChart || (() => {});

  const createTradesFeature = window.App.getRuntimeModule?.("currency-trades-factory");
  const tradesFeature = createTradesFeature?.({
    state,
    el,
    core,
    pickerUtils,
    formatTradeQuoteTotal,
    formatRateWithQuote,
    openCurrencyTradeEdit,
    deleteCurrencyTrade,
    openLinkedOperation,
    deleteLinkedOperation,
  }) || {};
  const loadCurrencyTradesPage = tradesFeature.loadTradesPage || (async () => {});
  const loadMoreCurrencyTrades = tradesFeature.loadMoreTrades || (async () => {});
  const bindCurrencyTradesInfiniteScroll = tradesFeature.bindInfiniteScroll || (() => {});
  const getCurrencyTradeById = tradesFeature.getTradeById || (() => null);

  function getTrackedCurrencies() {
    const raw = state.preferences?.data?.currency?.tracked_currencies;
    if (!Array.isArray(raw) || !raw.length) {
      return ["USD", "EUR"];
    }
    return Array.from(new Set(
      raw
        .map((item) => core.normalizeCurrencyCode?.(item, "") || "")
        .filter(Boolean),
    ));
  }

  function syncRateAssetOptions(preserveValue = "") {
    if (!el.currencyRateAsset) {
      return;
    }
    const tracked = core.getSelectableCurrencies?.({ includeBase: false }) || getTrackedCurrencies();
    const normalized = Array.from(new Set(
      tracked
        .map((item) => core.normalizeCurrencyCode?.(item, "") || "")
        .filter(Boolean),
    ));
    const nextValue = core.normalizeCurrencyCode?.(preserveValue || el.currencyRateAsset.value || normalized[0] || "", "") || "";
    el.currencyRateAsset.innerHTML = normalized.map((currency) => {
      const selected = currency === nextValue ? " selected" : "";
      return `<option value="${currency}"${selected}>${core.formatCurrencyLabel(currency)}</option>`;
    }).join("");
    if (nextValue) {
      el.currencyRateAsset.value = nextValue;
    }
  }

  function syncFilterTabs() {
    if (!el.currencyFilterTabs) {
      return;
    }
    const tracked = getTrackedCurrencies();
    const tabs = ["all", ...tracked];
    if (!tabs.includes(state.currencyFilter)) {
      state.currencyFilter = "all";
    }
    el.currencyFilterTabs.innerHTML = tabs.map((item) => {
      const isActive = state.currencyFilter === item;
      const label = item === "all" ? "Все" : core.formatCurrencyLabel(item);
      return `<button class="segmented-btn ${isActive ? "active" : ""}" data-currency-filter="${item}" type="button">${label}</button>`;
    }).join("");
  }

  async function openTradePanel() {
    const operationModal = getOperationModal();
    if (operationModal?.openCreateModalForCurrency) {
      await operationModal.openCreateModalForCurrency();
      return;
    }
    if (!operationModal?.openCreateModal || !operationModal?.setCreateEntryMode) {
      return;
    }
    await operationModal.openCreateModal();
    operationModal.setCreateEntryMode("currency");
  }

  function openRatePanel() {
    syncRateAssetOptions();
    el.currencyRatePanel?.classList.remove("hidden");
    el.currencyTradePanel?.classList.add("hidden");
    primeDefaultDates();
    el.currencyRateAsset?.focus();
  }

  function closeRatePanel() {
    el.currencyRatePanel?.classList.add("hidden");
  }

  function renderSummary(data) {
    const unrealizedTone = getResultPresentation(data.total_unrealized_result_value || data.total_result_value || 0);
    const realizedTone = getResultPresentation(data.total_realized_result_value || 0);
    const combinedTone = getResultPresentation(data.total_combined_result_value || data.total_result_value || 0);
    if (el.currencySummaryCurrentValue) {
      el.currencySummaryCurrentValue.textContent = core.formatMoney(data.total_current_value || 0);
    }
    if (el.currencySummaryBookValue) {
      el.currencySummaryBookValue.textContent = core.formatMoney(data.total_book_value || 0);
    }
    if (el.currencySummaryResultValue) {
      el.currencySummaryResultValue.textContent = core.formatMoney(data.total_unrealized_result_value || data.total_result_value || 0);
    }
    if (el.currencySummaryResultCard) {
      el.currencySummaryResultCard.classList.remove("analytics-kpi-income", "analytics-kpi-expense", "analytics-kpi-neutral");
      el.currencySummaryResultCard.classList.add(unrealizedTone.cardClass);
    }
    if (el.currencySummaryResultLabel) {
      el.currencySummaryResultLabel.textContent = "Нереализованный результат";
    }
    if (el.currencySummaryRealizedValue) {
      el.currencySummaryRealizedValue.textContent = core.formatMoney(data.total_realized_result_value || 0);
    }
    if (el.currencySummaryRealizedCard) {
      el.currencySummaryRealizedCard.classList.remove("analytics-kpi-income", "analytics-kpi-expense", "analytics-kpi-neutral");
      el.currencySummaryRealizedCard.classList.add(realizedTone.cardClass);
    }
    if (el.currencySummaryRealizedLabel) {
      el.currencySummaryRealizedLabel.textContent = "Реализованный результат";
    }
    if (el.currencySummaryCombinedValue) {
      el.currencySummaryCombinedValue.textContent = core.formatMoney(data.total_combined_result_value || data.total_result_value || 0);
    }
    if (el.currencySummaryCombinedCard) {
      el.currencySummaryCombinedCard.classList.remove("analytics-kpi-income", "analytics-kpi-expense", "analytics-kpi-neutral");
      el.currencySummaryCombinedCard.classList.add(combinedTone.cardClass);
    }
    if (el.currencySummaryCombinedLabel) {
      el.currencySummaryCombinedLabel.textContent = "Итоговый результат";
    }
    if (el.currencySummaryActiveCount) {
      el.currencySummaryActiveCount.textContent = String(data.active_positions || 0);
    }
  }

  function renderPositions(data) {
    const positions = Array.isArray(data.positions) ? data.positions : [];
    const positionsByCurrency = new Map(positions.map((item) => [core.normalizeCurrencyCode?.(item.currency, "") || "", item]));
    const currentRates = Array.isArray(data.current_rates) ? data.current_rates : [];
    const currentRatesByCurrency = new Map(currentRates.map((item) => [core.normalizeCurrencyCode?.(item.currency, "") || "", item]));
    const trackedCurrencies = Array.isArray(data.tracked_currencies) && data.tracked_currencies.length
      ? data.tracked_currencies.map((item) => core.normalizeCurrencyCode?.(item, "") || "").filter(Boolean)
      : getTrackedCurrencies();
    const baseCurrency = core.normalizeCurrencyCode?.(data.base_currency || (core.getCurrencyConfig?.().code || "BYN"), "BYN") || "BYN";
    if (el.currencyBalancesRow) {
      const positionCards = trackedCurrencies.map((currency) => {
        const item = positionsByCurrency.get(currency) || null;
        const currentRate = currentRatesByCurrency.get(currency) || null;
        const currencyLabel = core.formatCurrencyLabel(currency);
        return `
          <article class="currency-balance-card">
            <div class="muted-small">${core.escapeHtml ? core.escapeHtml(currencyLabel) : currencyLabel}</div>
            <strong>${core.formatAmount(item?.quantity || 0)}</strong>
            <div class="currency-balance-secondary">${core.formatMoney(item?.current_value || 0, { currency: baseCurrency })} по текущему курсу${currentRate?.rate ? ` · ${core.formatRateDisplay?.(currentRate.rate || 0, 4, 6)}` : ""}</div>
          </article>
        `;
      });
      el.currencyBalancesRow.innerHTML = positionCards.join("");
    }
    if (!el.currencyPositionsList) {
      return;
    }
    if (!positions.length) {
      const trackedSummary = trackedCurrencies.length
        ? `Отслеживаются: ${trackedCurrencies.map((currency) => core.formatCurrencyLabel(currency)).join(", ")}.`
        : "Отслеживаемые валюты остаются в карточках выше.";
      el.currencyPositionsList.innerHTML = `
        <div class="muted-small">
          Открытых валютных позиций пока нет. ${trackedSummary}
        </div>
      `;
      return;
    }
    el.currencyPositionsList.innerHTML = positions.map((item) => {
      const unrealizedTone = getResultPresentation(item.result_value || 0);
      const realizedTone = getResultPresentation(item.realized_result_value || 0);
      const totalTone = getResultPresentation(item.total_result_value || 0);
      const currencyLabel = core.formatCurrencyLabel(item.currency);
      return `
        <article class="panel">
          <div class="panel-head row between">
            <div>
              <h3>${core.escapeHtml ? core.escapeHtml(currencyLabel) : currencyLabel}</h3>
              <p class="subtitle">
                <span class="currency-position-primary">${core.formatAmount(item.quantity || 0)}</span>
                <span class="currency-position-secondary">${core.formatMoney(item.current_value || 0)} по текущему курсу</span>
              </p>
            </div>
            <span class="analytics-kpi-chip ${totalTone.chipClass}">Итог: ${core.formatMoney(item.total_result_value || 0)}</span>
          </div>
          <div class="analytics-kpi-grid">
            <article class="analytics-kpi-card analytics-kpi-neutral">
              <div class="muted-small">Средняя цена покупки</div>
              <strong>${core.formatRateDisplay?.(item.average_buy_rate || 0, 4, 6)}</strong>
            </article>
            <article class="analytics-kpi-card analytics-kpi-neutral">
              <div class="muted-small">Вложено в открытые позиции</div>
              <strong>${core.formatMoney(item.book_value || 0)}</strong>
            </article>
            <article class="analytics-kpi-card analytics-kpi-neutral">
              <div class="muted-small">Текущая оценка открытых позиций</div>
              <strong>${core.formatMoney(item.current_value || 0)}</strong>
            </article>
            <article class="analytics-kpi-card analytics-kpi-neutral">
              <div class="muted-small">Текущий курс</div>
              <strong>${core.formatRateDisplay?.(item.current_rate || 0, 4, 6)}</strong>
              <span class="analytics-kpi-delta">${item.current_rate_date ? core.formatDateRu(item.current_rate_date) : "Курс не задан"}</span>
            </article>
            <article class="analytics-kpi-card ${unrealizedTone.cardClass}">
              <div class="muted-small">Нереализованный</div>
              <strong>${core.formatMoney(item.result_value || 0)}</strong>
            </article>
            <article class="analytics-kpi-card ${realizedTone.cardClass}">
              <div class="muted-small">Реализованный</div>
              <strong>${core.formatMoney(item.realized_result_value || 0)}</strong>
            </article>
          </div>
        </article>
      `;
    }).join("");
  }

  function primeDefaultDates() {
    const today = core.getTodayIso();
    if (el.currencyTradeDate && !el.currencyTradeDate.value) {
      core.syncDateFieldValue(el.currencyTradeDate, today);
    }
    if (el.currencyRateDate && !el.currencyRateDate.value) {
      core.syncDateFieldValue(el.currencyRateDate, today);
    }
  }

  async function loadCurrencySection(options = {}) {
    const skeletons = getLoadingSkeletons();
    const refreshState = getInlineRefreshState();
    const coldLoad = !state.currencySectionHydrated && state.activeSection === "currency";
    if (coldLoad) {
      skeletons.renderCurrencySectionSkeleton?.();
    }
    const shouldRefreshInline = !coldLoad && state.currencySectionHydrated && state.activeSection === "currency";
    if (shouldRefreshInline) {
      refreshState.begin?.(el.currencySection, "Обновляется");
    }
    syncFilterTabs();
    syncPerformancePeriodTabs();
    primeDefaultDates();
    try {
      const params = new URLSearchParams({ trades_limit: "1" });
      if (state.currencyFilter && state.currencyFilter !== "all") {
        params.set("currency", state.currencyFilter);
      }
      const data = await core.requestJson(`/api/v1/currency/overview?${params.toString()}`, {
        headers: core.authHeaders(),
      });
      renderSummary(data);
      renderPositions(data);
      await loadCurrencyTradesPage(1, { reset: true });
      const performanceHistory = await fetchPerformanceHistory();
      renderPerformanceChart(performanceHistory);
      skeletons.clearCurrencySectionSkeletonState?.();
      state.currencySectionHydrated = true;
      if (options.force !== false) {
        syncFilterTabs();
      }
      syncRateAssetOptions();
      bindCurrencyTradesInfiniteScroll();
      return data;
    } finally {
      if (shouldRefreshInline) {
        refreshState.end?.(el.currencySection);
      }
    }
  }

  async function submitCurrencyRate(event) {
    event.preventDefault();
    const refreshState = window.App.getRuntimeModule?.("inline-refresh-state") || {};
    await refreshState.withRefresh?.(el.currencyRatePanel || el.currencySection, async () => {
      await core.requestJson("/api/v1/currency/rates/current", {
        method: "PUT",
        headers: core.authHeaders(),
        body: JSON.stringify({
          currency: el.currencyRateAsset?.value || "USD",
          rate: el.currencyRateValue?.value || "0",
          rate_date: el.currencyRateDate?.value || core.getTodayIso(),
          source: el.currencyRateSource?.value || "manual",
        }),
      });
    }, "Обновляется курс");
    if (el.currencyRateValue) {
      el.currencyRateValue.value = "";
    }
    closeRatePanel();
    await loadCurrencySection({ force: true });
    core.setStatus("Текущий курс обновлен");
    core.invalidateUiRequestCache?.("dashboard:summary");
    getDashboardFeature().loadDashboard?.().catch(() => {});
    getAnalyticsCurrencyFeature().loadAnalyticsCurrency?.({ force: true }).catch(() => {});
  }

  async function openCurrencyTradeEdit(tradeId) {
    const trade = getCurrencyTradeById(tradeId);
    if (!trade) {
      core.setStatus("Сделка не найдена");
      return;
    }
    await getOperationModal().openCreateModalForCurrencyEdit?.(trade);
  }

  function deleteCurrencyTrade(tradeId) {
    const trade = getCurrencyTradeById(tradeId);
    if (!trade) {
      core.setStatus("Сделка не найдена");
      return;
    }
    const actionLabel = trade.side === "sell" ? "Продажа" : "Покупка";
    core.runDestructiveAction({
      confirmMessage: `Удалить валютную сделку «${actionLabel} ${core.formatCurrencyLabel(trade.asset_currency)}»?`,
      doDelete: async () => {
        await core.requestJson(`/api/v1/currency/trades/${Number(trade.id)}`, {
          method: "DELETE",
          headers: core.authHeaders(),
        });
        core.invalidateUiRequestCache?.("currency");
      },
      onAfterDelete: async () => {
        await refreshAfterTradeMutation();
      },
      toastMessage: "Валютная сделка удалена",
      onDeleteError: "Не удалось удалить валютную сделку",
    });
  }

  function bind() {
    if (el.currencyFilterTabs) {
      el.currencyFilterTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-currency-filter]");
        if (!btn) {
          return;
        }
        state.currencyFilter = btn.dataset.currencyFilter || "all";
        loadCurrencySection({ force: true }).catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.currencyTradeSideTabs) {
      el.currencyTradeSideTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-currency-side]");
        if (!btn) {
          return;
        }
        const next = btn.dataset.currencySide === "sell" ? "sell" : "buy";
        if (el.currencyTradeSide) {
          el.currencyTradeSide.value = next;
        }
        core.syncSegmentedActive(el.currencyTradeSideTabs, "currency-side", next);
      });
    }
    if (el.openCurrencyTradePanelBtn) {
      el.openCurrencyTradePanelBtn.addEventListener("click", openTradePanel);
    }
    if (el.openCurrencyRatePanelBtn) {
      el.openCurrencyRatePanelBtn.addEventListener("click", openRatePanel);
    }
    if (el.closeCurrencyRatePanelBtn) {
      el.closeCurrencyRatePanelBtn.addEventListener("click", closeRatePanel);
    }
    if (el.currencyRateForm) {
      el.currencyRateForm.addEventListener("submit", (event) => {
        core.runAction({
          button: el.submitCurrencyRateBtn,
          pendingText: "Обновление...",
          errorPrefix: "Ошибка обновления курса",
          action: () => submitCurrencyRate(event),
        });
      });
    }
  }

  bind();

  window.App.registerRuntimeModule?.("currency", {
    loadCurrencySection,
    loadMoreCurrencyTrades,
    syncFilterTabs,
    openTradePanel,
    openRatePanel,
    openCurrencyTradeEdit,
    deleteCurrencyTrade,
  });
})();
