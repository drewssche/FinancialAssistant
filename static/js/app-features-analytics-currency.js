(() => {
  const { state, el, core } = window.App;
  const shared = window.App.analyticsShared || {};
  const pickerUtils = window.App.getRuntimeModule?.("picker-utils");
  const escapeHtml = shared.escapeHtml || ((value) => String(value ?? ""));

  function getLoadingSkeletons() {
    return window.App.getRuntimeModule?.("loading-skeletons") || {};
  }

  function getInlineRefreshState() {
    return window.App.getRuntimeModule?.("inline-refresh-state") || {};
  }

  function getTrackedCurrencies() {
    const raw = state.preferences?.data?.currency?.tracked_currencies;
    if (!Array.isArray(raw) || !raw.length) {
      return ["USD", "EUR"];
    }
    return raw.map((item) => String(item || "").toUpperCase()).filter(Boolean);
  }

  function syncCurrencyTabs() {
    if (!el.analyticsCurrencyTabs) {
      return;
    }
    const tracked = getTrackedCurrencies();
    const tabs = ["all", ...tracked];
    if (!tabs.includes(state.analyticsCurrencyFilter)) {
      state.analyticsCurrencyFilter = tracked[0] || "all";
    }
    el.analyticsCurrencyTabs.innerHTML = tabs.map((item) => {
      const label = item === "all" ? "Все" : core.formatCurrencyLabel(item);
      return `<button class="segmented-btn ${state.analyticsCurrencyFilter === item ? "active" : ""}" data-analytics-currency-filter="${item}" type="button">${label}</button>`;
    }).join("");
  }

  function syncCurrencyPeriodTabs() {
    if (!el.analyticsCurrencyPeriodTabs) {
      return;
    }
    core.syncSegmentedActive(el.analyticsCurrencyPeriodTabs, "analytics-currency-period", state.analyticsCurrencyPeriod || "30d");
  }

  function getHistoryRange() {
    const today = core.getTodayIso();
    if (state.analyticsCurrencyPeriod === "all_time") {
      return { dateFrom: "", dateTo: today };
    }
    const daysMap = {
      "7d": 7,
      "30d": 30,
      "90d": 90,
      "365d": 365,
    };
    const days = daysMap[state.analyticsCurrencyPeriod] || 30;
    const end = new Date(`${today}T00:00:00`);
    const start = new Date(end);
    if (state.analyticsCurrencyPeriodAnchor === "previous") {
      end.setDate(end.getDate() - days);
    }
    start.setDate(start.getDate() - (days - 1));
    const format = (value) => value.toISOString().slice(0, 10);
    return { dateFrom: format(start), dateTo: format(end) };
  }

  function closeAnalyticsCurrencyPeriodPopover() {
    pickerUtils?.setPopoverOpen?.(el.analyticsCurrencyPeriodPopover, false, {
      owners: [el.analyticsCurrencyPeriodTabs].filter(Boolean),
    });
  }

  function getAnalyticsCurrencyQuickCopy(period) {
    const labels = {
      "7d": { current: "Текущие 7 дней", previous: "Предыдущие 7 дней" },
      "30d": { current: "Текущие 30 дней", previous: "Предыдущие 30 дней" },
      "90d": { current: "Текущие 3 месяца", previous: "Предыдущие 3 месяца" },
      "365d": { current: "Текущие 12 месяцев", previous: "Предыдущие 12 месяцев" },
    };
    return labels[period] || { current: "Текущий период", previous: "Предыдущий период" };
  }

  function renderAnalyticsCurrencyPeriodOptions(period = state.analyticsCurrencyPeriod || "30d") {
    if (!el.analyticsCurrencyPeriodOptions) {
      return;
    }
    const currentAnchor = state.analyticsCurrencyPeriodAnchor === "previous" ? "previous" : "current";
    const copy = getAnalyticsCurrencyQuickCopy(period);
    const currentRange = (() => {
      const prevAnchor = state.analyticsCurrencyPeriodAnchor;
      state.analyticsCurrencyPeriodAnchor = "current";
      const range = getHistoryRange();
      state.analyticsCurrencyPeriodAnchor = prevAnchor;
      return range;
    })();
    const previousRange = (() => {
      const prevAnchor = state.analyticsCurrencyPeriodAnchor;
      state.analyticsCurrencyPeriodAnchor = "previous";
      const range = getHistoryRange();
      state.analyticsCurrencyPeriodAnchor = prevAnchor;
      return range;
    })();
    el.analyticsCurrencyPeriodOptions.innerHTML = [
      `
        <button class="btn btn-secondary settings-picker-option ${currentAnchor === "current" ? "active" : ""}" type="button" data-analytics-currency-quick-period="${period}" data-analytics-currency-quick-anchor="current">
          ${copy.current}
          <span class="muted-small">${core.formatPeriodLabel(currentRange.dateFrom, currentRange.dateTo)}</span>
        </button>
      `,
      `
        <button class="btn btn-secondary settings-picker-option ${currentAnchor === "previous" ? "active" : ""}" type="button" data-analytics-currency-quick-period="${period}" data-analytics-currency-quick-anchor="previous">
          ${copy.previous}
          <span class="muted-small">${core.formatPeriodLabel(previousRange.dateFrom, previousRange.dateTo)}</span>
        </button>
      `,
      `
        <button class="btn btn-secondary settings-picker-option" type="button" data-analytics-currency-quick-period="all_time" data-analytics-currency-quick-anchor="current">
          Все время
          <span class="muted-small">Полная история по валюте</span>
        </button>
      `,
    ].join("");
  }

  function openAnalyticsCurrencyPeriodPopover(period, trigger) {
    if (!pickerUtils?.setPopoverOpen || !["7d", "30d", "90d", "365d"].includes(period)) {
      return;
    }
    renderAnalyticsCurrencyPeriodOptions(period);
    pickerUtils.setPopoverOpen(el.analyticsCurrencyPeriodPopover, true, {
      owners: [trigger || el.analyticsCurrencyPeriodTabs].filter(Boolean),
      onClose: () => closeAnalyticsCurrencyPeriodPopover(),
    });
  }

  function applyAnalyticsCurrencyPeriod(period, anchor = "current") {
    state.analyticsCurrencyPeriod = period === "all_time" ? "all_time" : (["7d", "30d", "90d", "365d"].includes(period) ? period : "30d");
    state.analyticsCurrencyPeriodAnchor = state.analyticsCurrencyPeriod === "all_time" ? "current" : (anchor === "previous" ? "previous" : "current");
    syncCurrencyPeriodTabs();
    closeAnalyticsCurrencyPeriodPopover();
    loadAnalyticsCurrency({ force: true }).catch((err) => core.setStatus(String(err)));
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

  function formatRateWithQuote(rate, quoteCurrency) {
    const quote = core.normalizeCurrencyCode?.(quoteCurrency, "BYN") || "BYN";
    return `${core.formatRateDisplay?.(rate || 0, 4, 6) || Number(rate || 0).toFixed(6)} ${core.formatCurrencySymbol?.(quote) || quote}`;
  }

  const createTradesFeature = window.App.getRuntimeModule?.("analytics-currency-trades-factory");
  const tradesFeature = createTradesFeature?.({
    state,
    el,
    core,
    escapeHtml,
    formatRateWithQuote,
  }) || {};
  const loadAnalyticsCurrencyTradesPage = tradesFeature.loadTradesPage || (async () => {});
  const loadMoreAnalyticsCurrencyTrades = tradesFeature.loadMoreTrades || (async () => {});
  const bindAnalyticsCurrencyTradesInfiniteScroll = tradesFeature.bindInfiniteScroll || (() => {});
  const createChartFeature = window.App.getRuntimeModule?.("analytics-currency-chart-factory");
  const chartFeature = createChartFeature?.({
    el,
    core,
    escapeHtml,
  }) || {};
  const getSeriesColor = chartFeature.getSeriesColor || (() => "#6ea8ff");
  const renderMultiCurrencyChart = chartFeature.renderMulti || (() => {});
  const renderChart = chartFeature.renderSingle || (() => {});

  function normalizeHistoryPoints(points, targetDate) {
    const raw = Array.isArray(points) ? points.filter((item) => item?.rate_date && item?.rate !== undefined && item?.rate !== null) : [];
    if (!raw.length) {
      return [];
    }
    const sorted = [...raw].sort((left, right) => String(left.rate_date).localeCompare(String(right.rate_date)));
    const last = sorted[sorted.length - 1];
    if (targetDate && String(last.rate_date) < String(targetDate)) {
      sorted.push({
        ...last,
        rate_date: targetDate,
        synthetic: true,
      });
    }
    return sorted;
  }

  function renderSummary(overview) {
    const unrealizedTone = getResultPresentation(overview.total_unrealized_result_value || overview.total_result_value || 0);
    const realizedTone = getResultPresentation(overview.total_realized_result_value || 0);
    const combinedTone = getResultPresentation(overview.total_combined_result_value || overview.total_result_value || 0);
    if (el.analyticsCurrencyCurrentValue) {
      el.analyticsCurrencyCurrentValue.textContent = core.formatMoney(overview.total_current_value || 0);
    }
    if (el.analyticsCurrencyBookValue) {
      el.analyticsCurrencyBookValue.textContent = core.formatMoney(overview.total_book_value || 0);
    }
    if (el.analyticsCurrencyResultValue) {
      el.analyticsCurrencyResultValue.textContent = core.formatMoney(overview.total_unrealized_result_value || overview.total_result_value || 0);
    }
    if (el.analyticsCurrencyResultCard) {
      el.analyticsCurrencyResultCard.classList.remove("analytics-kpi-income", "analytics-kpi-expense", "analytics-kpi-neutral");
      el.analyticsCurrencyResultCard.classList.add(unrealizedTone.cardClass);
    }
    if (el.analyticsCurrencyResultLabel) {
      el.analyticsCurrencyResultLabel.textContent = "Нереализованный результат";
    }
    if (el.analyticsCurrencyRealizedValue) {
      el.analyticsCurrencyRealizedValue.textContent = core.formatMoney(overview.total_realized_result_value || 0);
    }
    if (el.analyticsCurrencyRealizedCard) {
      el.analyticsCurrencyRealizedCard.classList.remove("analytics-kpi-income", "analytics-kpi-expense", "analytics-kpi-neutral");
      el.analyticsCurrencyRealizedCard.classList.add(realizedTone.cardClass);
    }
    if (el.analyticsCurrencyRealizedLabel) {
      el.analyticsCurrencyRealizedLabel.textContent = "Реализованный результат";
    }
    if (el.analyticsCurrencyCombinedValue) {
      el.analyticsCurrencyCombinedValue.textContent = core.formatMoney(overview.total_combined_result_value || overview.total_result_value || 0);
    }
    if (el.analyticsCurrencyCombinedCard) {
      el.analyticsCurrencyCombinedCard.classList.remove("analytics-kpi-income", "analytics-kpi-expense", "analytics-kpi-neutral");
      el.analyticsCurrencyCombinedCard.classList.add(combinedTone.cardClass);
    }
    if (el.analyticsCurrencyCombinedLabel) {
      el.analyticsCurrencyCombinedLabel.textContent = "Итоговый результат";
    }
    if (el.analyticsCurrencyActiveCount) {
      el.analyticsCurrencyActiveCount.textContent = String(overview.active_positions || 0);
    }
    if (el.analyticsCurrencyRangeLabel) {
      const periodLabels = {
        "7d": state.analyticsCurrencyPeriodAnchor === "previous" ? "за предыдущие 7 дней" : "за 7 дней",
        "30d": state.analyticsCurrencyPeriodAnchor === "previous" ? "за предыдущие 30 дней" : "за 30 дней",
        "90d": state.analyticsCurrencyPeriodAnchor === "previous" ? "за предыдущие 3 месяца" : "за 3 месяца",
        "365d": state.analyticsCurrencyPeriodAnchor === "previous" ? "за предыдущие 12 месяцев" : "за 12 месяцев",
        all_time: "за все время",
      };
      el.analyticsCurrencyRangeLabel.textContent = state.analyticsCurrencyFilter === "all"
        ? "Сводка по всем отслеживаемым валютам"
        : `Курс, позиция и сделки по ${core.formatCurrencyLabel(state.analyticsCurrencyFilter)} ${periodLabels[state.analyticsCurrencyPeriod] || ""}`.trim();
    }
    if (el.analyticsCurrencyBalancesRow) {
      const positions = Array.isArray(overview.positions) ? overview.positions : [];
      const positionsByCurrency = new Map(positions.map((item) => [core.normalizeCurrencyCode?.(item.currency, "") || "", item]));
      const currentRates = Array.isArray(overview.current_rates) ? overview.current_rates : [];
      const currentRatesByCurrency = new Map(currentRates.map((item) => [core.normalizeCurrencyCode?.(item.currency, "") || "", item]));
      const trackedCurrencies = Array.isArray(overview.tracked_currencies) && overview.tracked_currencies.length
        ? overview.tracked_currencies.map((item) => core.normalizeCurrencyCode?.(item, "") || "").filter(Boolean)
        : getTrackedCurrencies();
      const baseCurrency = core.normalizeCurrencyCode?.(overview.base_currency || (core.getCurrencyConfig?.().code || "BYN"), "BYN") || "BYN";
      const bynCard = `
        <article class="currency-balance-card">
          <div class="muted-small">${core.formatCurrencyLabel(baseCurrency)}</div>
          <strong>${core.formatMoney(overview.total_current_value || 0, { currency: baseCurrency })}</strong>
          <div class="currency-balance-secondary">Текущая оценка валютных позиций в аналитике</div>
        </article>
      `;
      const positionCards = trackedCurrencies.map((currency) => {
        const item = positionsByCurrency.get(currency) || null;
        const currentRate = currentRatesByCurrency.get(currency) || null;
        return `
        <article class="currency-balance-card">
          <div class="muted-small">${core.formatCurrencyLabel(currency)}</div>
          <strong>${core.formatAmount(item?.quantity || 0)}</strong>
          <div class="currency-balance-secondary">${core.formatMoney(item?.current_value || 0, { currency: baseCurrency })} по текущему курсу${currentRate?.rate ? ` · ${core.formatRateDisplay?.(currentRate.rate || 0, 4, 6)}` : ""}</div>
        </article>
      `;
      });
      el.analyticsCurrencyBalancesRow.innerHTML = [bynCard, ...positionCards].join("");
    }
    if (el.analyticsCurrencySecondary) {
      const positions = Array.isArray(overview.positions) ? overview.positions : [];
      if (!positions.length) {
        const trackedCurrencies = Array.isArray(overview.tracked_currencies) && overview.tracked_currencies.length
          ? overview.tracked_currencies.map((item) => core.formatCurrencyLabel(item)).join(", ")
          : getTrackedCurrencies().map((item) => core.formatCurrencyLabel(item)).join(", ");
        el.analyticsCurrencySecondary.innerHTML = `
          <span class="analytics-kpi-chip analytics-kpi-chip-neutral">
            Открытых позиций пока нет. Отслеживаются: ${trackedCurrencies}
          </span>
        `;
        return;
      }
      el.analyticsCurrencySecondary.innerHTML = positions.map((item) => {
        const resultTone = getResultPresentation(item.result_value || 0);
        const currentRateDate = item.current_rate_date ? core.formatDateRu(item.current_rate_date) : "курс не задан";
        return `
          <span class="analytics-kpi-chip currency-position-compact ${resultTone.chipClass}">
            <span class="currency-position-primary">${core.formatCurrencyLabel(item.currency)}: ${core.formatAmount(item.quantity || 0)}</span>
            <span class="currency-position-secondary">${core.formatMoney(item.current_value || 0)} · средняя ${core.formatRateDisplay?.(item.average_buy_rate || 0, 4, 6)} · текущий ${core.formatRateDisplay?.(item.current_rate || 0, 4, 6)} · ${currentRateDate}</span>
          </span>
        `;
      }).concat([
        `<span class="analytics-kpi-chip analytics-kpi-chip-neutral">Покупки: ${core.formatMoney(overview.buy_volume_base || 0)} · ${String(overview.buy_trades_count || 0)} сделок · средняя ${core.formatRateDisplay?.(overview.buy_average_rate || 0, 4, 6)}</span>`,
        `<span class="analytics-kpi-chip analytics-kpi-chip-neutral">Продажи: ${core.formatMoney(overview.sell_volume_base || 0)} · ${String(overview.sell_trades_count || 0)} сделок · средняя ${core.formatRateDisplay?.(overview.sell_average_rate || 0, 4, 6)}</span>`,
      ]).join("");
    }
  }

  async function backfillAnalyticsCurrencyHistory() {
    const { dateFrom, dateTo } = getHistoryRange();
    const currencies = state.analyticsCurrencyFilter === "all"
      ? getTrackedCurrencies()
      : [state.analyticsCurrencyFilter].filter(Boolean);
    if (!currencies.length) {
      core.setStatus("Нет валют для подгрузки истории");
      return;
    }
    const refreshState = window.App.getRuntimeModule?.("inline-refresh-state") || {};
    await refreshState.withRefresh?.(el.analyticsCurrencyPanel, async () => {
      await Promise.all(currencies.map((currency) => core.requestJson(
        `/api/v1/currency/rates/history/fill?currency=${encodeURIComponent(currency)}&date_from=${encodeURIComponent(dateFrom)}&date_to=${encodeURIComponent(dateTo)}`,
        {
          method: "POST",
          headers: core.authHeaders(),
        },
      )));
      await loadAnalyticsCurrency({ force: true });
      core.invalidateUiRequestCache?.("dashboard:summary");
      window.App.getRuntimeModule?.("dashboard")?.loadDashboard?.().catch(() => {});
    }, currencies.length > 1 ? "Подгружается история по валютам" : "Подгружается история курса");
    core.setStatus(currencies.length > 1 ? "История по валютам подгружена" : "История курса подгружена");
  }

  async function fetchCurrencyHistory(currency, range) {
    const historyParams = new URLSearchParams({ currency, limit: range.dateFrom ? "365" : "1000" });
    if (range.dateFrom) {
      historyParams.set("date_from", range.dateFrom);
    }
    if (range.dateTo) {
      historyParams.set("date_to", range.dateTo);
    }
    return core.requestJson(`/api/v1/currency/rates/history?${historyParams.toString()}`, {
      headers: core.authHeaders(),
    });
  }

  async function loadAnalyticsCurrency(options = {}) {
    const skeletons = getLoadingSkeletons();
    const refreshState = getInlineRefreshState();
    const coldLoad = !state.analyticsCurrencyHydrated && state.activeSection === "analytics" && state.analyticsTab === "currency";
    if (coldLoad) {
      skeletons.renderAnalyticsCurrencySkeleton?.();
    }
    const shouldRefreshInline = !coldLoad && state.analyticsCurrencyHydrated && state.activeSection === "analytics" && state.analyticsTab === "currency";
    if (shouldRefreshInline) {
      refreshState.begin?.(el.analyticsCurrencyPanel, "Обновляется");
    }
    syncCurrencyTabs();
    syncCurrencyPeriodTabs();
    try {
      const params = new URLSearchParams({ trades_limit: "1" });
      if (state.analyticsCurrencyFilter && state.analyticsCurrencyFilter !== "all") {
        params.set("currency", state.analyticsCurrencyFilter);
      }
      const overview = await core.requestJson(`/api/v1/currency/overview?${params.toString()}`, {
        headers: core.authHeaders(),
      });
      renderSummary(overview);
      await loadAnalyticsCurrencyTradesPage(1, { reset: true });
      if (state.analyticsCurrencyFilter === "all") {
        const range = getHistoryRange();
        const tracked = getTrackedCurrencies();
        const histories = await Promise.all(tracked.map(async (currency, index) => ({
          currency,
          color: getSeriesColor(index),
          points: normalizeHistoryPoints(await fetchCurrencyHistory(currency, range), range.dateTo),
        })));
        const seriesList = histories.map((item) => ({
          currency: item.currency,
          color: item.color,
          points: Array.isArray(item.points) ? item.points : [],
          pointsByDate: new Map((Array.isArray(item.points) ? item.points : []).map((point) => [point.rate_date, point])),
        }));
        renderMultiCurrencyChart(seriesList);
      } else {
        const range = getHistoryRange();
        const history = normalizeHistoryPoints(await fetchCurrencyHistory(state.analyticsCurrencyFilter, range), range.dateTo);
        renderChart(history);
      }
      skeletons.clearAnalyticsCurrencySkeletonState?.();
      state.analyticsCurrencyHydrated = true;
      if (options.force !== false) {
        syncCurrencyTabs();
      }
      bindAnalyticsCurrencyTradesInfiniteScroll();
      return overview;
    } finally {
      if (shouldRefreshInline) {
        refreshState.end?.(el.analyticsCurrencyPanel);
      }
    }
  }

  function bind() {
    if (el.analyticsCurrencyTabs) {
      el.analyticsCurrencyTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-analytics-currency-filter]");
        if (!btn) {
          return;
        }
        state.analyticsCurrencyFilter = btn.dataset.analyticsCurrencyFilter || "all";
        window.App.getRuntimeModule?.("session")?.savePreferencesDebounced?.(250);
        loadAnalyticsCurrency({ force: true }).catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.analyticsCurrencyPeriodTabs) {
      el.analyticsCurrencyPeriodTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-analytics-currency-period]");
        if (!btn) {
          return;
        }
        const period = String(btn.dataset.analyticsCurrencyPeriod || "30d");
        if (period === state.analyticsCurrencyPeriod && ["7d", "30d", "90d", "365d"].includes(period)) {
          openAnalyticsCurrencyPeriodPopover(period, btn);
          return;
        }
        applyAnalyticsCurrencyPeriod(period, "current");
      });
    }
    if (el.analyticsCurrencyPeriodOptions) {
      el.analyticsCurrencyPeriodOptions.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-analytics-currency-quick-period][data-analytics-currency-quick-anchor]");
        if (!btn) {
          return;
        }
        applyAnalyticsCurrencyPeriod(
          String(btn.dataset.analyticsCurrencyQuickPeriod || "30d"),
          String(btn.dataset.analyticsCurrencyQuickAnchor || "current"),
        );
      });
    }
    if (el.analyticsCurrencyBackfillBtn) {
      el.analyticsCurrencyBackfillBtn.addEventListener("click", () => {
        core.runAction({
          button: el.analyticsCurrencyBackfillBtn,
          pendingText: "Подгружается...",
          errorPrefix: "Ошибка подгрузки истории курса",
          action: async () => {
            await backfillAnalyticsCurrencyHistory();
          },
        });
      });
    }
  }

  bind();

  window.App.registerRuntimeModule?.("analytics-currency-module", {
    loadAnalyticsCurrency,
    loadMoreAnalyticsCurrencyTrades,
    syncCurrencyTabs,
  });
})();
