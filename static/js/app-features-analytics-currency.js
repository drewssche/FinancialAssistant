(() => {
  const { state, el, core } = window.App;
  const shared = window.App.analyticsShared || {};
  const pickerUtils = window.App.getRuntimeModule?.("picker-utils");
  const escapeHtml = shared.escapeHtml || ((value) => String(value ?? ""));
  const BANK_CHART_BANKS = [
    { code: "priorbank", name: "Приорбанк", channelLabel: "онлайн", color: "#9b8cff" },
    { code: "technobank", name: "Технобанк", channelLabel: "наличные", color: "#ff9a52" },
    { code: "bsb", name: "БСБ Банк", channelLabel: "наличные", color: "#58d39b" },
    { code: "sber", name: "Сбер Банк", channelLabel: "наличные", color: "#45c9dc" },
  ];
  const BANK_CHART_RATE_KINDS = {
    buy: { label: "Покупка банком", shortLabel: "покупка", dashArray: "" },
    sell: { label: "Продажа банком", shortLabel: "продажа", dashArray: "8 5" },
  };
  let currencyChartLoadSequence = 0;
  let currentChartSnapshot = null;
  let bankBackfillStatusChecked = false;
  let bankBackfillCoverageNote = "";

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
    const [year, month, day] = today.split("-").map(Number);
    const end = new Date(Date.UTC(year, month - 1, day));
    if (state.analyticsCurrencyPeriodAnchor === "previous") {
      end.setUTCDate(end.getUTCDate() - days);
    }
    const start = new Date(end);
    start.setUTCDate(start.getUTCDate() - (days - 1));
    const format = (value) => value.toISOString().slice(0, 10);
    return { dateFrom: format(start), dateTo: format(end) };
  }

  function getBackfillHistoryRange() {
    const range = getHistoryRange();
    if (range.dateFrom) {
      return range;
    }
    const [year, month, day] = range.dateTo.split("-").map(Number);
    const start = new Date(Date.UTC(year, month - 1, day));
    start.setUTCDate(start.getUTCDate() - 364);
    return { dateFrom: start.toISOString().slice(0, 10), dateTo: range.dateTo };
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
  const renderEmptyChart = chartFeature.renderEmpty || (() => {});
  const renderMultiCurrencyChart = chartFeature.renderMulti || (() => {});
  const renderBankComparisonChart = chartFeature.renderComparison || (() => {});
  const renderChart = chartFeature.renderSingle || (() => {});

  function getConfiguredBankCodes() {
    const raw = state.preferences?.data?.currency?.bank_rate_banks;
    const allowed = new Set(BANK_CHART_BANKS.map((bank) => bank.code));
    const source = Array.isArray(raw) ? raw : BANK_CHART_BANKS.map((bank) => bank.code);
    return Array.from(new Set(source.map((item) => String(item || "").trim().toLowerCase())))
      .filter((item) => allowed.has(item));
  }

  function getBankChartCurrencies() {
    const tracked = getTrackedCurrencies().filter((currency) => currency && currency !== "BYN");
    return tracked.length ? tracked : ["USD", "EUR", "RUB"];
  }

  function getBankChartScale(currency = state.analyticsCurrencyChartCurrency) {
    return String(currency || "").toUpperCase() === "RUB" ? 100 : 1;
  }

  function getChartCurrencyLabel(currency) {
    const normalized = String(currency || "").toUpperCase();
    const scale = getBankChartScale(normalized);
    return `${scale > 1 ? `${scale} ` : ""}${core.formatCurrencyLabel(normalized)}`;
  }

  function getHiddenChartSeries() {
    return new Set(Array.isArray(state.analyticsCurrencyChartHiddenSeries)
      ? state.analyticsCurrencyChartHiddenSeries.map((item) => String(item || "")).filter(Boolean)
      : []);
  }

  function setHiddenChartSeries(hidden) {
    state.analyticsCurrencyChartHiddenSeries = Array.from(hidden).sort();
  }

  function formatCoverageDate(value) {
    return value ? core.formatDateRu(value) : "—";
  }

  function renderChartCoverage(seriesList, { source = "НБРБ", loadingText = "" } = {}) {
    if (!el.analyticsCurrencyChartCoverage) {
      return;
    }
    if (loadingText) {
      el.analyticsCurrencyChartCoverage.textContent = loadingText;
      return;
    }
    const dates = Array.from(new Set((Array.isArray(seriesList) ? seriesList : [])
      .flatMap((series) => (Array.isArray(series.points) ? series.points : []).map((point) => point.rate_date))
      .filter(Boolean))).sort();
    const note = source === "Банки" && bankBackfillCoverageNote ? ` ${bankBackfillCoverageNote}` : "";
    if (!dates.length) {
      el.analyticsCurrencyChartCoverage.textContent = (source === "Банки"
        ? "История банков пока не загружена. Приорбанк и БСБ можно подгрузить кнопкой выше; Технобанк накапливает историю с обновлений, источник Сбер сейчас недоступен."
        : "История НБРБ за выбранный период не найдена.") + note;
      return;
    }
    if (dates.length === 1) {
      el.analyticsCurrencyChartCoverage.textContent = `${source}: только ${formatCoverageDate(dates[0])} · 1 день. Линия появится после второй котировки.${note}`;
      return;
    }
    el.analyticsCurrencyChartCoverage.textContent = `${source}: ${formatCoverageDate(dates[0])} — ${formatCoverageDate(dates[dates.length - 1])} · ${dates.length} дн.${note}`;
  }

  function ensureBankChartState() {
    const currencies = getBankChartCurrencies();
    const preferredCurrency = currencies.includes("EUR") ? "EUR" : currencies[0];
    if (!state.analyticsCurrencyHydrated && state.analyticsCurrencyFilter !== "all" && currencies.includes(state.analyticsCurrencyFilter)) {
      state.analyticsCurrencyChartCurrency = state.analyticsCurrencyFilter;
    }
    if (!currencies.includes(state.analyticsCurrencyChartCurrency)) {
      state.analyticsCurrencyChartCurrency = preferredCurrency;
    }
    state.analyticsCurrencyChartMode = state.analyticsCurrencyChartMode === "nbrb" ? "nbrb" : "banks";
    if (!Array.isArray(state.analyticsCurrencyChartHiddenSeries)) {
      state.analyticsCurrencyChartHiddenSeries = [];
    }
  }

  function syncBankChartControls() {
    ensureBankChartState();
    const currency = state.analyticsCurrencyChartCurrency;
    const scale = getBankChartScale(currency);
    const isBankMode = state.analyticsCurrencyChartMode === "banks";
    core.syncSegmentedActive?.(el.analyticsCurrencyChartModeTabs, "analytics-currency-chart-mode", state.analyticsCurrencyChartMode);
    el.analyticsCurrencyChartBankOptions?.classList.toggle("hidden", !isBankMode);
    if (el.analyticsCurrencyChartCurrencyTabs) {
      el.analyticsCurrencyChartCurrencyTabs.innerHTML = getBankChartCurrencies().map((item) => `
        <button class="segmented-btn ${currency === item ? "active" : ""}" data-analytics-bank-chart-currency="${escapeHtml(item)}" type="button" aria-pressed="${currency === item ? "true" : "false"}">${escapeHtml(core.formatCurrencyLabel(item))}</button>
      `).join("");
    }
    if (el.analyticsCurrencyBackfillBtn) {
      const idleText = isBankMode ? "Подгрузить историю банков" : "Подгрузить историю НБРБ";
      if (el.analyticsCurrencyBackfillBtn.dataset.loading === "1") {
        // runAction restores dataset.originalText in finally. Keep that value
        // aligned with the currently selected chart mode even when a bank job
        // continues polling in the background.
        el.analyticsCurrencyBackfillBtn.dataset.originalText = idleText;
        if (!isBankMode) {
          el.analyticsCurrencyBackfillBtn.textContent = "Идёт подгрузка истории банков";
        }
      } else {
        el.analyticsCurrencyBackfillBtn.textContent = idleText;
      }
    }
    if (el.analyticsCurrencyChartContext) {
      el.analyticsCurrencyChartContext.textContent = isBankMode
        ? `BYN за ${scale} ${currency} · сплошная — покупка банком, пунктир и ромб — продажа банком`
        : state.analyticsCurrencyFilter === "all"
          ? "Официальные курсы НБРБ: USD и EUR за 1, RUB за 100"
          : `Официальный курс НБРБ: BYN за ${getChartCurrencyLabel(state.analyticsCurrencyFilter)}`;
    }
  }

  function renderChartLegend(seriesList, mode = state.analyticsCurrencyChartMode) {
    if (!el.analyticsCurrencyChartLegend) {
      return;
    }
    const series = Array.isArray(seriesList) ? seriesList : [];
    const hidden = getHiddenChartSeries();
    if (mode === "banks") {
      const seriesById = new Map(series.map((item) => [item.id, item]));
      const configured = new Set(getConfiguredBankCodes());
      const bankGroups = BANK_CHART_BANKS.filter((bank) => configured.has(bank.code)).map((bank) => {
        const availableIds = ["buy", "sell"].map((kind) => `${bank.code}-${kind}`).filter((id) => seriesById.has(id));
        const visibleCount = availableIds.filter((id) => !hidden.has(id)).length;
        const groupState = visibleCount === 0 ? "off" : visibleCount === availableIds.length ? "on" : "mixed";
        const unavailable = !availableIds.length;
        return `
          <div class="currency-chart-legend-bank ${unavailable ? "is-unavailable" : ""}" style="--bank-series-color:${bank.color}">
            <button class="currency-chart-legend-bank-name ${groupState === "on" ? "active" : ""} ${groupState === "mixed" ? "is-mixed" : ""}" type="button"
              data-analytics-chart-bank-toggle="${bank.code}" aria-pressed="${groupState === "on" ? "true" : groupState === "off" ? "false" : "mixed"}"
              ${unavailable ? "disabled" : ""} title="${escapeHtml(unavailable ? `${bank.name}: нет истории за выбранный период` : `Показать или скрыть все курсы ${bank.name}`)}">
              <i></i><span>${escapeHtml(bank.name)}</span><small>${escapeHtml(bank.channelLabel)}</small>
            </button>
            ${["buy", "sell"].map((kind) => {
              const item = seriesById.get(`${bank.code}-${kind}`);
              const active = Boolean(item) && !hidden.has(item.id);
              return `
                <button class="currency-chart-legend-series ${kind === "sell" ? "is-sell" : "is-buy"} ${active ? "active" : ""}" type="button"
                  data-analytics-chart-series-toggle="${bank.code}-${kind}" aria-pressed="${active ? "true" : "false"}" ${item ? "" : "disabled"}>
                  <i></i><span>${kind === "buy" ? "Покупка" : "Продажа"}</span>
                </button>
              `;
            }).join("")}
          </div>
        `;
      }).join("");
      const nbrb = seriesById.get("nbrb-reference");
      const nbrbActive = Boolean(nbrb) && !hidden.has("nbrb-reference");
      el.analyticsCurrencyChartLegend.innerHTML = `${bankGroups}
        <button class="currency-chart-legend-item is-reference ${nbrbActive ? "active" : ""}" type="button"
          data-analytics-chart-series-toggle="nbrb-reference" aria-pressed="${nbrbActive ? "true" : "false"}" ${nbrb ? "" : "disabled"}>
          <i></i><span>НБРБ · ориентир</span>
        </button>`;
    } else {
      el.analyticsCurrencyChartLegend.innerHTML = series.map((item) => {
        const available = Array.isArray(item.points) && item.points.length > 0;
        const active = available && !hidden.has(item.id);
        return `
          <button class="currency-chart-legend-item ${active ? "active" : ""} ${available ? "" : "is-unavailable"}" type="button" data-analytics-chart-series-toggle="${escapeHtml(item.id)}"
            aria-pressed="${active ? "true" : "false"}" style="--legend-color:${item.color}" ${available ? "" : "disabled"}>
            <i></i><span>${escapeHtml(item.legendLabel || item.label)}</span>
          </button>
        `;
      }).join("");
    }
    const availableIds = series.filter((item) => Array.isArray(item.points) && item.points.length).map((item) => item.id);
    const allHidden = Boolean(availableIds.length) && availableIds.every((id) => hidden.has(id));
    el.analyticsCurrencyChartShowAllBtn?.classList.toggle("hidden", !allHidden);
  }

  async function fetchBankCurrencyHistory(currency, range, bankCodes) {
    const params = new URLSearchParams({
      currency,
      limit: "3660",
    });
    if (range.dateFrom) {
      params.set("date_from", range.dateFrom);
    }
    if (range.dateTo) {
      params.set("date_to", range.dateTo);
    }
    bankCodes.forEach((code) => params.append("bank_code", code));
    return core.requestJson(`/api/v1/currency/bank-rates/history?${params.toString()}`, {
      headers: core.authHeaders(),
    });
  }

  function buildBankChartSeries(rows, nbrbPoints = []) {
    const selectedKinds = ["buy", "sell"];
    const selectedBanks = getConfiguredBankCodes();
    const series = [];
    const bankByCode = new Map(BANK_CHART_BANKS.map((bank) => [bank.code, bank]));
    selectedBanks.forEach((bankCode) => {
      const bank = bankByCode.get(bankCode);
      if (!bank) {
        return;
      }
      const bankRows = rows.filter((item) => String(item?.bank_code || "").toLowerCase() === bankCode);
      selectedKinds.forEach((kind) => {
        const kindConfig = BANK_CHART_RATE_KINDS[kind];
        const rateField = `${kind}_rate`;
        const points = bankRows.map((item) => ({
          rate_date: item.rate_date,
          rate: Number(item[rateField] || 0),
          quoted_at: item.quoted_at || null,
          fetched_at: item.fetched_at || null,
        })).filter((item) => item.rate_date && Number.isFinite(item.rate) && item.rate > 0)
          .sort((left, right) => String(left.rate_date).localeCompare(String(right.rate_date)));
        if (!points.length) {
          return;
        }
        series.push({
          id: `${bankCode}-${kind}`,
          bankCode,
          rateKind: kind,
          label: `${bank.name} · ${kindConfig.label}`,
          legendLabel: `${bank.name} · ${kindConfig.shortLabel}`,
          color: bank.color,
          dashArray: kindConfig.dashArray,
          markerShape: kind === "sell" ? "diamond" : "circle",
          markerFill: kind === "sell" ? "hollow" : "filled",
          channelLabel: bankRows.find((item) => item?.channel_label)?.channel_label || bank.channelLabel,
          valueSuffix: `BYN за ${getChartCurrencyLabel(state.analyticsCurrencyChartCurrency)}`,
          points,
          pointsByDate: new Map(points.map((point) => [point.rate_date, point])),
        });
      });
    });
    if (nbrbPoints.length) {
      series.push({
        id: "nbrb-reference",
        label: "НБРБ · официальный курс",
        legendLabel: "НБРБ · ориентир",
        color: "#c9d4ec",
        dashArray: "2 5",
        markerShape: "circle",
        markerFill: "hollow",
        valueSuffix: `BYN за ${getChartCurrencyLabel(state.analyticsCurrencyChartCurrency)}`,
        points: nbrbPoints,
        pointsByDate: new Map(nbrbPoints.map((point) => [point.rate_date, point])),
      });
    }
    return series;
  }

  function renderCurrentChartSnapshot() {
    const snapshot = currentChartSnapshot;
    if (!snapshot) {
      return;
    }
    const hidden = getHiddenChartSeries();
    const visibleSeries = snapshot.series.filter((item) => !hidden.has(item.id));
    renderChartLegend(snapshot.series, snapshot.mode);
    renderChartCoverage(
      snapshot.mode === "banks" ? snapshot.series.filter((item) => item.bankCode) : snapshot.series,
      { source: snapshot.mode === "banks" ? "Банки" : "НБРБ" },
    );
    if (!visibleSeries.length) {
      renderEmptyChart("Все ряды скрыты. Выберите нужные в легенде или нажмите «Показать все».");
      return;
    }
    if (snapshot.mode === "banks") {
      renderBankComparisonChart(visibleSeries);
      return;
    }
    if (snapshot.single) {
      const series = visibleSeries[0];
      renderChart(series?.points || [], {
        label: series?.legendLabel || series?.label || "Курс НБРБ",
        valueSuffix: series?.valueSuffix || "BYN",
      });
      return;
    }
    renderMultiCurrencyChart(visibleSeries);
  }

  async function renderBankCurrencyChart(range, requestSequence) {
    ensureBankChartState();
    const currency = state.analyticsCurrencyChartCurrency;
    const bankCodes = getConfiguredBankCodes();
    const scale = getBankChartScale(currency);
    const nbrbPromise = fetchCurrencyHistory(currency, range);
    const [bankResult, nbrbResult] = await Promise.allSettled([
      fetchBankCurrencyHistory(currency, range, bankCodes),
      nbrbPromise,
    ]);
    if (requestSequence !== currencyChartLoadSequence) {
      return;
    }
    const bankRows = bankResult.status === "fulfilled" ? bankResult.value : [];
    const nbrbRaw = nbrbResult.status === "fulfilled" ? nbrbResult.value : [];
    if (bankResult.status === "rejected") {
      console.warn("Bank currency history is unavailable", bankResult.reason);
    }
    if (nbrbResult.status === "rejected") {
      console.warn("NBRB currency history is unavailable", nbrbResult.reason);
    }
    const normalizedRows = Array.isArray(bankRows) ? bankRows : [];
    syncBankChartControls();
    const nbrbPoints = normalizeHistoryPoints(nbrbRaw, range.dateTo).map((point) => ({
      ...point,
      rate: Number(point.rate || 0) * scale,
    }));
    const series = buildBankChartSeries(normalizedRows, nbrbPoints);
    currentChartSnapshot = { mode: "banks", series, single: false };
    renderCurrentChartSnapshot();
    resumeBankHistoryBackfillOnce().catch((err) => console.warn("Bank history backfill status is unavailable", err));
  }

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

  function buildNbrbChartSeries(currency, points, index = 0) {
    const normalizedCurrency = String(currency || "").toUpperCase();
    const scale = getBankChartScale(normalizedCurrency);
    const normalizedPoints = (Array.isArray(points) ? points : []).map((point) => ({
      ...point,
      rate: Number(point.rate || 0) * scale,
    }));
    return {
      id: `nbrb-${normalizedCurrency}`,
      currency: normalizedCurrency,
      label: `НБРБ · ${getChartCurrencyLabel(normalizedCurrency)}`,
      legendLabel: getChartCurrencyLabel(normalizedCurrency),
      valueSuffix: `BYN за ${getChartCurrencyLabel(normalizedCurrency)}`,
      color: getSeriesColor(index),
      points: normalizedPoints,
      pointsByDate: new Map(normalizedPoints.map((point) => [point.rate_date, point])),
    };
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

  function updateBankBackfillProgress(job) {
    const processed = Math.max(0, Number(job?.processed_steps || 0));
    const total = Math.max(0, Number(job?.total_steps || 0));
    const percent = total > 0 ? Math.min(100, Math.round((processed / total) * 100)) : 0;
    const providerDetails = Object.values(job?.progress || {}).filter((item) => item?.capability === "backfill")
      .map((item) => `${item.bank_name}: ${Number(item.processed_days || 0)}/${Number(item.total_days || 0)}`)
      .join(" · ");
    const progressText = `История банков: ${percent}%${providerDetails ? ` · ${providerDetails}` : ""}`;
    // The polling job may outlive the bank chart view. Do not overwrite NBRB
    // coverage or its contextual button while the bank import keeps running.
    if (state.analyticsCurrencyChartMode !== "banks") {
      return;
    }
    if (el.analyticsCurrencyBackfillBtn?.dataset.loading === "1") {
      el.analyticsCurrencyBackfillBtn.textContent = `Подгрузка банков · ${percent}%`;
    }
    renderChartCoverage([], { source: "Банки", loadingText: progressText });
  }

  function rememberBankBackfillResult(job) {
    const status = String(job?.status || "").toLowerCase();
    const processed = Number(job?.processed_steps || 0);
    const total = Number(job?.total_steps || 0);
    const label = status === "completed"
      ? "последняя подгрузка завершена"
      : status === "partial"
        ? "последняя подгрузка частичная"
        : status === "interrupted"
          ? "подгрузку можно продолжить"
          : status === "failed"
            ? "последняя подгрузка завершилась ошибкой"
            : "";
    const providerNotes = Object.values(job?.progress || {})
      .filter((item) => item?.capability === "accumulating" || item?.capability === "unavailable")
      .map((item) => item.capability === "accumulating"
        ? `${item.bank_name}: история накапливается с обновлений`
        : `${item.bank_name}: архив недоступен`);
    const importNote = label
      ? `Последний импорт: ${label}${total > 0 ? ` (${processed}/${total})` : ""}.`
      : "";
    bankBackfillCoverageNote = [importNote, providerNotes.length ? `${providerNotes.join("; ")}.` : ""]
      .filter(Boolean)
      .join(" ");
  }

  async function pollBankHistoryBackfill(initialJob) {
    const terminalStatuses = new Set(["completed", "partial", "failed", "interrupted"]);
    let job = initialJob || {};
    for (let attempt = 0; attempt < 600; attempt += 1) {
      updateBankBackfillProgress(job);
      if (terminalStatuses.has(String(job.status || "").toLowerCase())) {
        return job;
      }
      await new Promise((resolve) => window.setTimeout(resolve, 1000));
      const next = await core.requestJson("/api/v1/currency/bank-rates/history/fill/status", {
        headers: core.authHeaders(),
      });
      if (!next || (job.id && next.id && Number(next.id) !== Number(job.id))) {
        throw new Error("Статус подгрузки банковской истории потерян");
      }
      job = next;
    }
    throw new Error("Подгрузка банковской истории продолжается слишком долго. Её статус сохранён, можно обновить страницу позже");
  }

  async function backfillBankCurrencyHistory(dateFrom, dateTo, isAllTime) {
    const params = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
    getConfiguredBankCodes().forEach((code) => params.append("bank_code", code));
    const initialJob = await core.requestJson(`/api/v1/currency/bank-rates/history/fill?${params.toString()}`, {
      method: "POST",
      headers: core.authHeaders(),
    });
    const job = await pollBankHistoryBackfill(initialJob);
    rememberBankBackfillResult(job);
    const status = String(job?.status || "").toLowerCase();
    if (status === "failed") {
      throw new Error(job?.last_error || "Не удалось подгрузить историю банков");
    }
    await loadAnalyticsCurrency({ force: true });
    syncBankChartControls();
    const suffix = isAllTime ? " за последние 365 дней" : "";
    if (status === "partial" || status === "interrupted") {
      core.setStatus(`История банков подгружена частично${suffix}. Можно повторить загрузку для продолжения`);
      return;
    }
    core.setStatus(`История банков подгружена${suffix}`);
  }

  async function resumeBankHistoryBackfillOnce() {
    if (bankBackfillStatusChecked) {
      return;
    }
    bankBackfillStatusChecked = true;
    const job = await core.requestJson("/api/v1/currency/bank-rates/history/fill/status", {
      headers: core.authHeaders(),
    });
    if (!job) {
      return;
    }
    const status = String(job.status || "").toLowerCase();
    if (status !== "queued" && status !== "running") {
      rememberBankBackfillResult(job);
      renderCurrentChartSnapshot();
      return;
    }
    await core.runAction({
      button: el.analyticsCurrencyBackfillBtn,
      pendingText: "Подгрузка банков...",
      errorPrefix: "Ошибка фоновой подгрузки банковской истории",
      action: async () => {
        const completed = await pollBankHistoryBackfill(job);
        rememberBankBackfillResult(completed);
        if (String(completed.status || "").toLowerCase() === "failed") {
          throw new Error(completed.last_error || "Не удалось продолжить подгрузку истории банков");
        }
        await loadAnalyticsCurrency({ force: true });
        syncBankChartControls();
        core.setStatus("Фоновая подгрузка банковской истории завершена");
      },
    });
  }

  async function backfillAnalyticsCurrencyHistory() {
    const isAllTime = state.analyticsCurrencyPeriod === "all_time";
    const { dateFrom, dateTo } = getBackfillHistoryRange();
    if (state.analyticsCurrencyChartMode === "banks") {
      await backfillBankCurrencyHistory(dateFrom, dateTo, isAllTime);
      return;
    }
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
    if (isAllTime) {
      core.setStatus("История НБРБ подгружена за последние 365 дней");
      return;
    }
    core.setStatus(currencies.length > 1 ? "История по валютам подгружена" : "История курса подгружена");
  }

  async function fetchCurrencyHistory(currency, range) {
    const historyParams = new URLSearchParams({ currency, limit: range.dateFrom ? "365" : "3660" });
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
    const chartLoadSequence = ++currencyChartLoadSequence;
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
    syncBankChartControls();
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
      const range = getHistoryRange();
      if (state.analyticsCurrencyChartMode === "banks") {
        await renderBankCurrencyChart(range, chartLoadSequence);
      } else if (state.analyticsCurrencyFilter === "all") {
        const tracked = getTrackedCurrencies();
        const histories = await Promise.all(tracked.map(async (currency, index) => ({
          currency,
          index,
          points: normalizeHistoryPoints(await fetchCurrencyHistory(currency, range), range.dateTo),
        })));
        const seriesList = histories.map((item) => buildNbrbChartSeries(item.currency, item.points, item.index));
        if (chartLoadSequence === currencyChartLoadSequence) {
          currentChartSnapshot = { mode: "nbrb", series: seriesList, single: false };
          renderCurrentChartSnapshot();
        }
      } else {
        const history = normalizeHistoryPoints(await fetchCurrencyHistory(state.analyticsCurrencyFilter, range), range.dateTo);
        if (chartLoadSequence === currencyChartLoadSequence) {
          currentChartSnapshot = {
            mode: "nbrb",
            series: [buildNbrbChartSeries(state.analyticsCurrencyFilter, history, 0)],
            single: true,
          };
          renderCurrentChartSnapshot();
        }
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
    if (el.analyticsCurrencyChartModeTabs) {
      el.analyticsCurrencyChartModeTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-analytics-currency-chart-mode]");
        if (!btn) {
          return;
        }
        state.analyticsCurrencyChartMode = btn.dataset.analyticsCurrencyChartMode === "nbrb" ? "nbrb" : "banks";
        syncBankChartControls();
        loadAnalyticsCurrency({ force: true }).catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.analyticsCurrencyChartCurrencyTabs) {
      el.analyticsCurrencyChartCurrencyTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-analytics-bank-chart-currency]");
        if (!btn) {
          return;
        }
        state.analyticsCurrencyChartCurrency = String(btn.dataset.analyticsBankChartCurrency || "EUR").toUpperCase();
        syncBankChartControls();
        loadAnalyticsCurrency({ force: true }).catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.analyticsCurrencyChartLegend) {
      el.analyticsCurrencyChartLegend.addEventListener("click", (event) => {
        const bankButton = event.target.closest("button[data-analytics-chart-bank-toggle]");
        const seriesButton = event.target.closest("button[data-analytics-chart-series-toggle]");
        if ((!bankButton && !seriesButton) || event.target.closest("button")?.disabled || !currentChartSnapshot) {
          return;
        }
        const hidden = getHiddenChartSeries();
        if (bankButton) {
          const bankCode = String(bankButton.dataset.analyticsChartBankToggle || "");
          const ids = currentChartSnapshot.series
            .filter((item) => item.bankCode === bankCode)
            .map((item) => item.id);
          const everyHidden = ids.length > 0 && ids.every((id) => hidden.has(id));
          ids.forEach((id) => everyHidden ? hidden.delete(id) : hidden.add(id));
        } else {
          const id = String(seriesButton.dataset.analyticsChartSeriesToggle || "");
          if (!id) {
            return;
          }
          if (hidden.has(id)) {
            hidden.delete(id);
          } else {
            hidden.add(id);
          }
        }
        setHiddenChartSeries(hidden);
        renderCurrentChartSnapshot();
      });
    }
    if (el.analyticsCurrencyChartShowAllBtn) {
      el.analyticsCurrencyChartShowAllBtn.addEventListener("click", () => {
        if (!currentChartSnapshot) {
          return;
        }
        const hidden = getHiddenChartSeries();
        currentChartSnapshot.series.forEach((item) => hidden.delete(item.id));
        setHiddenChartSeries(hidden);
        renderCurrentChartSnapshot();
      });
    }
    if (el.analyticsCurrencyTabs) {
      el.analyticsCurrencyTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-analytics-currency-filter]");
        if (!btn) {
          return;
        }
        state.analyticsCurrencyFilter = btn.dataset.analyticsCurrencyFilter || "all";
        if (state.analyticsCurrencyFilter !== "all" && getBankChartCurrencies().includes(state.analyticsCurrencyFilter)) {
          state.analyticsCurrencyChartCurrency = state.analyticsCurrencyFilter;
          syncBankChartControls();
        }
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
