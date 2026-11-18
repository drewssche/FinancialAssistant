(() => {
  const { state, el, core } = window.App;
  const pickerUtils = window.App.getRuntimeModule?.("picker-utils");
  const { escapeHtml } = window.App.analyticsShared;

  function getDashboardFeature() {
    return window.App.getRuntimeModule?.("dashboard") || {};
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

  function formatTradeQuoteTotal(item) {
    const quantity = Number(item?.quantity || 0);
    const unitPrice = Number(item?.unit_price || 0);
    const quoteCurrency = core.normalizeCurrencyCode?.(item?.quote_currency, "BYN") || "BYN";
    const fee = Number(item.fee || 0);
    const total = quantity * unitPrice + (item.side === "sell" ? -fee : fee);
    return `${total.toLocaleString("ru-RU", { maximumFractionDigits: 2 })} ${quoteCurrency}`;
  }

  function formatRateWithQuote(rate, quoteCurrency) {
    const quote = core.normalizeCurrencyCode?.(quoteCurrency, "BYN") || "BYN";
    return `${core.formatRateDisplay?.(rate || 0, 4, 6) || Number(rate || 0).toFixed(6)} ${core.formatCurrencySymbol?.(quote) || quote}`;
  }

  async function refreshAfterTradeMutation() {
    await loadCurrencySection({ force: true });
    core.invalidateUiRequestCache?.("dashboard:summary");
    if (state.activeSection === "dashboard") getDashboardFeature().loadDashboard?.().catch(() => {});
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
    reload: () => loadExchangeResult(),
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
    escapeHtml,
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
      const label = item === "all" ? "Все" : item;
      return `<button class="segmented-btn ${isActive ? "active" : ""}" data-currency-filter="${item}" type="button">${label}</button>`;
    }).join("");
  }

  async function openTradePanel() {
    const operationModal = getOperationModal();
    if (operationModal?.openCreateModalForCurrency) {
      const selected = state.currencyView === "rates" ? state.currencyQuoteAsset : state.currencyFilter;
      await operationModal.openCreateModalForCurrency(selected);
      return;
    }
    if (!operationModal?.openCreateModal || !operationModal?.setCreateEntryMode) {
      return;
    }
    await operationModal.openCreateModal();
    operationModal.setCreateEntryMode("currency");
  }

  function openRatePanel() {
    syncRateAssetOptions(state.currencyQuoteAsset);
    el.currencyRatePanel?.classList.remove("hidden");
    el.currencyTradePanel?.classList.add("hidden");
    primeDefaultDates();
    el.currencyRateAsset?.focus();
  }

  function closeRatePanel() {
    el.currencyRatePanel?.classList.add("hidden");
  }

  let quotesRequest = 0;
  let resultRequest = 0;

  function renderQuotes(data) {
    const target = document.getElementById("currencyQuotesList");
    const providerMap = new Map(data.providers.map((bank) => [bank.bank_code, bank]));
    const quoteMap = new Map(data.bank_rates.map((bank) => [bank.bank_code, bank]));
    const codes = state.preferences?.data?.currency?.bank_rate_banks ?? [...providerMap.keys()];
    const scale = Number(data.display_scale);
    const unit = `${data.base_currency} за ${scale} ${data.currency}`;
    const format = (unitRate) => Number(unitRate) > 0 ? core.formatRateDisplay(Number(unitRate) * scale, 4, 6) : "—";
    const rows = codes.map((code) => {
      const bank = providerMap.get(code);
      const quote = quoteMap.get(code);
      const stamp = quote?.quoted_at || quote?.fetched_at;
      const time = stamp ? `${quote.quoted_at ? "котировка" : "проверено"} ${core.formatDateTimeRu(stamp)}` : "";
      const meta = [bank?.channel_label || quote?.channel_label, time, quote ? (quote.stale ? "Курс устарел" : "") : "Нет котировки"];
      return `<tr><th scope="row">${escapeHtml(bank?.bank_name || quote?.bank_name || code)}
        <small>${escapeHtml(meta.filter(Boolean).join(" · "))}</small></th>
        <td>${format(quote?.sell_unit_rate)}</td><td>${format(quote?.buy_unit_rate)}</td></tr>`;
    });
    const nbrb = data.nbrb_rate;
    target.innerHTML = `<table class="fx-quotes"><caption>${escapeHtml(unit)}</caption>
      <thead><tr><th scope="col">Банк</th><th scope="col">Я покупаю</th><th scope="col">Я продаю</th></tr></thead>
      <tbody>${rows.join("") || '<tr><td colspan="3">Выберите банки в настройках валюты.</td></tr>'}</tbody></table>
      <p class="muted-small">НБРБ · ${nbrb ? `${format(nbrb.unit_rate)} ${escapeHtml(unit)} · ${core.formatDateRu(nbrb.rate_date)}` : "Нет курса"}</p>`;
  }

  async function loadQuotes() {
    const seq = ++quotesRequest;
    const target = document.getElementById("currencyQuotesList");
    const tabs = document.getElementById("currencyQuotesTabs");
    const currencies = getTrackedCurrencies().filter((code) => code !== "BYN");
    if (!currencies.includes(state.currencyQuoteAsset)) {
      state.currencyQuoteAsset = currencies[0] || "";
      state.analyticsCurrencyChartCurrency = state.currencyQuoteAsset;
    }
    const currency = state.currencyQuoteAsset;
    tabs.innerHTML = currencies.map((code) =>
      `<button type="button" data-quote-currency="${escapeHtml(code)}" aria-pressed="${code === currency}" class="segmented-btn ${code === currency ? "active" : ""}">${escapeHtml(code)}</button>`
    ).join("");
    document.getElementById("currencyRefreshQuotesBtn").disabled = !currency;
    if (!currency) {
      target.textContent = "Выберите валюты в настройках.";
      return;
    }
    if (target.dataset.currency !== currency) target.textContent = "Загружаются курсы…";
    target.dataset.currency = currency;
    try {
      const params = new URLSearchParams({ currency, base_currency: "BYN" });
      const data = await core.requestJson(`/api/v1/currency/rate-options?${params}`, { headers: core.authHeaders() });
      if (seq === quotesRequest) renderQuotes(data);
    } catch (error) {
      if (seq !== quotesRequest) return;
      target.textContent = "Не удалось загрузить курсы. Нажмите «Обновить курсы».";
      throw error;
    }
  }

  async function loadExchangeResult() {
    const seq = ++resultRequest;
    if (state.currencyView !== "portfolio" || !document.getElementById("currencyResultDetails").open) return;
    const params = new URLSearchParams({ trades_limit: "1" });
    if (state.currencyFilter !== "all") params.set("currency", state.currencyFilter);
    syncPerformancePeriodTabs();
    const target = document.getElementById("currencyExchangeResult");
    target.textContent = "Загружается результат…";
    const overview = core.requestJson(`/api/v1/currency/overview?${params}`, { headers: core.authHeaders() }).then((data) => {
      if (seq !== resultRequest) return;
      const money = (value) => core.formatMoney(value, { currency: data.base_currency });
      const results = data.exchange_results || [];
      target.innerHTML = results.length ? `<p>Результат продаж <strong>${money(data.total_realized_result_value)}</strong></p>
        <ul class="fx-result-list">${results.map((item) => `<li><strong>${escapeHtml(item.currency)}</strong>
          <span>Средний курс покупки · ${item.average_buy_rate ? formatRateWithQuote(item.average_buy_rate, data.base_currency) : "—"}</span>
          <span>Результат продаж · ${money(item.realized_result_value)}</span></li>`).join("")}</ul>`
        : "Пока нет записанных обменов.";
    }).catch((error) => {
      if (seq === resultRequest) target.textContent = "Не удалось загрузить результат.";
      throw error;
    });
    const chart = fetchPerformanceHistory().then((history) => {
      if (seq === resultRequest) renderPerformanceChart(history);
    });
    await Promise.all([overview, chart]);
  }

  function primeDefaultDates() {
    const today = core.getPeriodBounds("day").dateTo;
    if (el.currencyTradeDate && !el.currencyTradeDate.value) {
      core.syncDateFieldValue(el.currencyTradeDate, today);
    }
    if (el.currencyRateDate && !el.currencyRateDate.value) {
      core.syncDateFieldValue(el.currencyRateDate, today);
    }
  }

  function setCurrencyView(view, { load = true } = {}) {
    state.currencyView = view === "portfolio" ? "portfolio" : "rates";
    document.getElementById("currencyPortfolioView")?.classList.toggle("hidden", state.currencyView !== "portfolio");
    el.analyticsCurrencyPanel?.classList.toggle("hidden", state.currencyView !== "rates");
    const tabs = document.getElementById("currencyWorkspaceTabs");
    core.syncSegmentedActive(tabs, "currency-view", state.currencyView);
    tabs?.querySelectorAll("[data-currency-view]").forEach((btn) => btn.setAttribute("aria-pressed", String(btn.dataset.currencyView === state.currencyView)));
    if (load) loadCurrencySection({ force: true }).catch((err) => core.setStatus(String(err)));
  }

  async function loadCurrencySection() {
    setCurrencyView(state.currencyView, { load: false });
    primeDefaultDates();
    if (state.currencyView === "rates") {
      ++resultRequest;
      await Promise.all([loadQuotes(), getAnalyticsCurrencyFeature().loadAnalyticsCurrency?.()]);
      return;
    }
    ++quotesRequest;
    syncFilterTabs();
    document.getElementById("currencyTradesPeriod").value = state.currencyTradesPeriod;
    const trades = loadCurrencyTradesPage(1, { reset: true }).then(bindCurrencyTradesInfiniteScroll);
    await Promise.all([trades, loadExchangeResult()]);
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
          rate_date: el.currencyRateDate?.value || core.getPeriodBounds("day").dateTo,
          source: el.currencyRateSource?.value || "manual",
        }),
      });
    }, "Обновляется курс");
    if (el.currencyRateValue) {
      el.currencyRateValue.value = "";
    }
    closeRatePanel();
    await loadCurrencySection({ force: true });
    core.setStatus("Курс сохранён");
    core.invalidateUiRequestCache?.("dashboard:summary");
    if (state.activeSection === "dashboard") getDashboardFeature().loadDashboard?.().catch(() => {});
  }

  async function openCurrencyTradeEdit(tradeId) {
    const id = Number(tradeId);
    if (!(id > 0)) return;
    const trade = getCurrencyTradeById(id) || await core.requestJson(`/api/v1/currency/trades/${id}`, { headers: core.authHeaders() });
    if (trade.trade_kind === "card_payment" && trade.linked_operation_id) {
      await openLinkedOperation(trade.linked_operation_id);
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

  function selectQuoteCurrency(code) {
    state.currencyQuoteAsset = code;
    state.analyticsCurrencyChartCurrency = code;
    state.analyticsCurrencyFilter = code;
  }

  function bind() {
    const showError = (err) => core.setStatus(String(err));
    el.dashboardCurrencyRates?.addEventListener("click", (event) => {
      const code = event.target.closest("[data-dashboard-quote]")?.dataset.dashboardQuote;
      if (!code) return;
      selectQuoteCurrency(code);
      state.currencyView = "rates";
      getNavigationActions().switchSection("currency", { scrollToTop: true }).catch(showError);
    });
    document.getElementById("currencyQuotesTabs")?.addEventListener("click", (event) => {
      const code = event.target.closest("[data-quote-currency]")?.dataset.quoteCurrency;
      if (!code || code === state.currencyQuoteAsset) return;
      selectQuoteCurrency(code);
      loadCurrencySection().catch(showError);
    });
    document.getElementById("currencyChartDetails")?.addEventListener("toggle", () =>
      getAnalyticsCurrencyFeature().loadAnalyticsCurrency?.().catch(showError));
    document.getElementById("currencyResultDetails")?.addEventListener("toggle", () => loadExchangeResult().catch(showError));
    document.getElementById("currencyTradesPeriod")?.addEventListener("change", (event) => {
      state.currencyTradesPeriod = event.target.value;
      loadCurrencyTradesPage(1, { reset: true }).catch(showError);
    });
    const refresh = document.getElementById("currencyRefreshQuotesBtn");
    refresh?.addEventListener("click", () => {
      const currency = state.currencyQuoteAsset;
      if (!currency || refresh.disabled) return;
      core.runAction({ button: refresh, pendingText: "Обновление…", errorPrefix: "Не удалось обновить курсы", action: async () => {
        await core.requestJson(`/api/v1/currency/rates/refresh?currency=${encodeURIComponent(currency)}`,
          { method: "POST", headers: core.authHeaders() });
        core.invalidateUiRequestCache?.("dashboard:summary");
        if (state.currencyView === "rates") await loadCurrencySection();
      } });
    });
    document.getElementById("currencyWorkspaceTabs")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-currency-view]");
      if (button) setCurrencyView(button.dataset.currencyView);
    });
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
    setCurrencyView,
    loadMoreCurrencyTrades,
    syncFilterTabs,
    openTradePanel,
    openRatePanel,
    openCurrencyTradeEdit,
    deleteCurrencyTrade,
  });
})();
