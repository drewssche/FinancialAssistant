(() => {
  const { state, el, core } = window.App;
  const tradeItemsById = new Map();
  const pickerUtils = window.App.getRuntimeModule?.("picker-utils");
  const shared = window.App.analyticsShared || {};
  const escapeHtml = shared.escapeHtml || ((value) => String(value ?? ""));
  let currencyTradesObserver = null;

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

  function getActions() {
    return window.App.actions || {};
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

  function getPerformanceRange() {
    const today = core.getTodayIso();
    if (state.currencyPerformancePeriod === "all_time") {
      return { dateFrom: "", dateTo: today };
    }
    const daysMap = {
      "30d": 30,
      "90d": 90,
      "365d": 365,
    };
    const days = daysMap[state.currencyPerformancePeriod] || 90;
    const end = new Date(`${today}T00:00:00`);
    const start = new Date(end);
    if (state.currencyPerformancePeriodAnchor === "previous") {
      end.setDate(end.getDate() - days);
    }
    start.setDate(start.getDate() - (days - 1));
    const format = (value) => value.toISOString().slice(0, 10);
    return { dateFrom: format(start), dateTo: format(end) };
  }

  function closeCurrencyPerformancePopover() {
    pickerUtils?.setPopoverOpen?.(el.currencyPerformancePeriodPopover, false, {
      owners: [el.currencyPerformancePeriodTabs].filter(Boolean),
    });
  }

  function getCurrencyPerformanceQuickCopy(period) {
    const labels = {
      "30d": { current: "Текущие 30 дней", previous: "Предыдущие 30 дней" },
      "90d": { current: "Текущие 3 месяца", previous: "Предыдущие 3 месяца" },
      "365d": { current: "Текущие 12 месяцев", previous: "Предыдущие 12 месяцев" },
    };
    return labels[period] || { current: "Текущий период", previous: "Предыдущий период" };
  }

  function renderCurrencyPerformancePeriodOptions(period = state.currencyPerformancePeriod || "90d") {
    if (!el.currencyPerformancePeriodOptions) {
      return;
    }
    const currentAnchor = state.currencyPerformancePeriodAnchor === "previous" ? "previous" : "current";
    const copy = getCurrencyPerformanceQuickCopy(period);
    const currentRange = (() => {
      const prevAnchor = state.currencyPerformancePeriodAnchor;
      state.currencyPerformancePeriodAnchor = "current";
      const range = getPerformanceRange();
      state.currencyPerformancePeriodAnchor = prevAnchor;
      return range;
    })();
    const previousRange = (() => {
      const prevAnchor = state.currencyPerformancePeriodAnchor;
      state.currencyPerformancePeriodAnchor = "previous";
      const range = getPerformanceRange();
      state.currencyPerformancePeriodAnchor = prevAnchor;
      return range;
    })();
    el.currencyPerformancePeriodOptions.innerHTML = [
      `
        <button class="btn btn-secondary settings-picker-option ${currentAnchor === "current" ? "active" : ""}" type="button" data-currency-performance-quick-period="${period}" data-currency-performance-quick-anchor="current">
          ${copy.current}
          <span class="muted-small">${core.formatPeriodLabel(currentRange.dateFrom, currentRange.dateTo)}</span>
        </button>
      `,
      `
        <button class="btn btn-secondary settings-picker-option ${currentAnchor === "previous" ? "active" : ""}" type="button" data-currency-performance-quick-period="${period}" data-currency-performance-quick-anchor="previous">
          ${copy.previous}
          <span class="muted-small">${core.formatPeriodLabel(previousRange.dateFrom, previousRange.dateTo)}</span>
        </button>
      `,
      `
        <button class="btn btn-secondary settings-picker-option" type="button" data-currency-performance-quick-period="all_time" data-currency-performance-quick-anchor="current">
          Все время
          <span class="muted-small">Полная история результата</span>
        </button>
      `,
    ].join("");
  }

  function openCurrencyPerformancePopover(period, trigger) {
    if (!pickerUtils?.setPopoverOpen || !["30d", "90d", "365d"].includes(period)) {
      return;
    }
    renderCurrencyPerformancePeriodOptions(period);
    pickerUtils.setPopoverOpen(el.currencyPerformancePeriodPopover, true, {
      owners: [trigger || el.currencyPerformancePeriodTabs].filter(Boolean),
      onClose: () => closeCurrencyPerformancePopover(),
    });
  }

  function applyCurrencyPerformancePeriod(period, anchor = "current") {
    state.currencyPerformancePeriod = period === "all_time" ? "all_time" : (["30d", "90d", "365d"].includes(period) ? period : "90d");
    state.currencyPerformancePeriodAnchor = state.currencyPerformancePeriod === "all_time" ? "current" : (anchor === "previous" ? "previous" : "current");
    syncPerformancePeriodTabs();
    closeCurrencyPerformancePopover();
    loadCurrencySection({ force: true }).catch((err) => core.setStatus(String(err)));
  }

  function syncPerformancePeriodTabs() {
    if (!el.currencyPerformancePeriodTabs) {
      return;
    }
    core.syncSegmentedActive(
      el.currencyPerformancePeriodTabs,
      "currency-performance-period",
      state.currencyPerformancePeriod || "90d",
    );
  }

  function formatTradeQuoteTotal(item) {
    const quantity = Number(item?.quantity || 0);
    const unitPrice = Number(item?.unit_price || 0);
    const quoteCurrency = core.normalizeCurrencyCode?.(item?.quote_currency, "BYN") || "BYN";
    return core.formatMoney(quantity * unitPrice, { currency: quoteCurrency });
  }

  function formatRateWithQuote(rate, quoteCurrency) {
    const quote = core.normalizeCurrencyCode?.(quoteCurrency, "BYN") || "BYN";
    return `${Number(rate || 0).toFixed(4)} ${core.formatCurrencySymbol?.(quote) || quote}`;
  }

  function toggleTableMenu(trigger) {
    const menuId = String(trigger?.dataset.tableMenuTrigger || "");
    const menu = menuId ? document.querySelector(`.table-kebab-popover[data-table-menu="${CSS.escape(menuId)}"]`) : null;
    const ownerRow = trigger.closest("tr");
    const ownerCell = trigger.closest("td");
    if (!menu || !pickerUtils?.setPopoverOpen) {
      return false;
    }
    const owners = [trigger, trigger.parentElement].filter(Boolean);
    const clearOpenState = () => {
      ownerCell?.classList.remove("table-menu-open-cell");
      ownerRow?.classList.remove("table-menu-open-row");
    };
    const shouldOpen = menu.classList.contains("hidden");
    document.querySelectorAll(".table-kebab-popover:not(.hidden)").forEach((node) => {
      if (node !== menu) {
        pickerUtils.setPopoverOpen(node, false, {
          owners: Array.isArray(node.__appPopoverOwners) ? node.__appPopoverOwners : [],
        });
        (Array.isArray(node.__appPopoverOwners) ? node.__appPopoverOwners : []).forEach((owner) => owner?.blur?.());
        node.closest(".table-menu-open-cell")?.classList.remove("table-menu-open-cell");
        node.closest(".table-menu-open-row")?.classList.remove("table-menu-open-row");
      }
    });
    pickerUtils.setPopoverOpen(menu, shouldOpen, { owners, onClose: clearOpenState });
    ownerCell?.classList.toggle("table-menu-open-cell", shouldOpen);
    ownerRow?.classList.toggle("table-menu-open-row", shouldOpen);
    if (!shouldOpen) {
      clearOpenState();
      trigger?.blur?.();
    }
    return true;
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
    await getActions().switchSection?.("operations");
    await operationModal.openEditModal(item);
  }

  async function deleteLinkedOperation(operationId) {
    const resolvedId = Number(operationId || 0);
    if (!(resolvedId > 0)) {
      return;
    }
    const actions = getActions();
    const item = await core.requestJson(`/api/v1/operations/${resolvedId}`, {
      headers: core.authHeaders(),
    });
    if (actions.deleteOperationFlow) {
      await actions.deleteOperationFlow(item);
      return;
    }
    await core.requestJson(`/api/v1/operations/${resolvedId}`, {
      method: "DELETE",
      headers: core.authHeaders(),
    });
    await refreshAfterTradeMutation();
  }

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
            <div class="currency-balance-secondary">${core.formatMoney(item?.current_value || 0, { currency: baseCurrency })} по текущему курсу${currentRate?.rate ? ` · ${Number(currentRate.rate || 0).toFixed(4)}` : ""}</div>
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
              <strong>${Number(item.average_buy_rate || 0).toFixed(4)}</strong>
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
              <strong>${Number(item.current_rate || 0).toFixed(4)}</strong>
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

  function renderPerformanceEmpty(message) {
    if (!el.currencyPerformanceChart) {
      return;
    }
    el.currencyPerformanceChart.innerHTML = `
      <text x="490" y="140" text-anchor="middle" class="analytics-chart-empty">${escapeHtml(message)}</text>
    `;
  }

  async function fetchPerformanceHistory() {
    const range = getPerformanceRange();
    const params = new URLSearchParams();
    if (state.currencyFilter && state.currencyFilter !== "all") {
      params.set("currency", state.currencyFilter);
    }
    if (range.dateFrom) {
      params.set("date_from", range.dateFrom);
    }
    if (range.dateTo) {
      params.set("date_to", range.dateTo);
    }
    return core.requestJson(`/api/v1/currency/performance/history?${params.toString()}`, {
      headers: core.authHeaders(),
    });
  }

  function renderPerformanceChart(history) {
    if (!el.currencyPerformanceChart) {
      return;
    }
    const points = Array.isArray(history?.points) ? history.points : [];
    if (el.currencyPerformanceRangeLabel) {
      const scopeLabel = history?.currency
        ? core.formatCurrencyLabel(history.currency)
        : "Все валюты";
      const from = history?.date_from ? core.formatDateRu(history.date_from) : "—";
      const to = history?.date_to ? core.formatDateRu(history.date_to) : "—";
      const rangeLabel = state.currencyPerformancePeriodAnchor === "previous" ? "Предыдущее окно" : "Текущее окно";
      el.currencyPerformanceRangeLabel.textContent = `${scopeLabel} · ${rangeLabel}: ${from} - ${to}`;
    }
    if (points.length < 2) {
      renderPerformanceEmpty("Недостаточно истории результата по валютным сделкам");
      return;
    }
    const width = 980;
    const height = 280;
    const padX = 56;
    const padY = 28;
    const values = points.map((item) => Number(item.total_result_value || 0)).filter((value) => Number.isFinite(value));
    if (values.length < 2) {
      renderPerformanceEmpty("Недостаточно истории результата по валютным сделкам");
      return;
    }
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const yRange = maxValue - minValue || 1;
    const xStep = (width - padX * 2) / Math.max(1, points.length - 1);
    const toX = (index) => padX + index * xStep;
    const toY = (value) => height - padY - ((value - minValue) / yRange) * (height - padY * 2);
    const lineColor = Number(points[points.length - 1]?.total_result_value || 0) >= 0 ? "#62d39a" : "#ff7c98";
    const polyline = points.map((item, index) => `${toX(index)},${toY(Number(item.total_result_value || 0))}`).join(" ");
    const pointDots = points.map((item, index) => `
      <circle cx="${toX(index)}" cy="${toY(Number(item.total_result_value || 0))}" r="2.8" fill="rgba(255,255,255,0.82)"></circle>
    `).join("");
    const last = points[points.length - 1];
    const middle = points[Math.floor(points.length / 2)];
    const yMarks = [minValue, minValue + yRange / 2, maxValue].map((value) => `
      <line x1="${width - padX - 8}" y1="${toY(value)}" x2="${width - padX}" y2="${toY(value)}" stroke="rgba(207, 219, 245, 0.28)" stroke-width="1"></line>
      <text x="${width - padX}" y="${Math.max(padY + 10, toY(value) - 8)}" text-anchor="end" class="analytics-chart-empty">${escapeHtml(core.formatMoney(value))}</text>
    `).join("");
    const bucketWidth = points.length > 1 ? xStep : width - padX * 2;
    const hitboxes = points.map((item, index) => `
      <g class="trend-bucket" data-currency-performance-index="${index}">
        <rect class="analytics-trend-hitbox" x="${Math.max(0, toX(index) - bucketWidth / 2).toFixed(2)}" y="0" width="${Math.max(bucketWidth, 24).toFixed(2)}" height="${height}" fill="transparent"></rect>
      </g>
    `).join("");
    el.currencyPerformanceChart.innerHTML = `
      <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" class="analytics-axis-line"></line>
      <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height - padY}" class="analytics-axis-line"></line>
      <polyline fill="none" stroke="${lineColor}" stroke-width="4" points="${polyline}"></polyline>
      ${pointDots}
      <circle cx="${toX(points.length - 1)}" cy="${toY(Number(last.total_result_value || 0))}" r="5" fill="${lineColor}"></circle>
      ${yMarks}
      ${hitboxes}
      <text x="${padX}" y="${height - 8}" class="analytics-chart-empty">${escapeHtml(core.formatDateRu(points[0].point_date))}</text>
      <text x="${toX(Math.floor(points.length / 2))}" y="${height - 8}" text-anchor="middle" class="analytics-chart-empty">${escapeHtml(core.formatDateRu(middle.point_date))}</text>
      <text x="${width - padX}" y="${height - 8}" text-anchor="end" class="analytics-chart-empty">${escapeHtml(core.formatDateRu(last.point_date))}</text>
    `;
    const wrapper = el.currencyPerformanceChart?.parentElement;
    let tooltip = wrapper?.querySelector(".analytics-chart-tooltip");
    if (wrapper && !tooltip) {
      tooltip = document.createElement("div");
      tooltip.className = "analytics-chart-tooltip hidden";
      wrapper.appendChild(tooltip);
    }
    el.currencyPerformanceChart.onmousemove = (event) => {
      const bucket = event.target.closest(".trend-bucket");
      if (!bucket || !tooltip) {
        tooltip?.classList.add("hidden");
        return;
      }
      const index = Number(bucket.dataset.currencyPerformanceIndex || -1);
      const point = points[index];
      if (!point) {
        tooltip.classList.add("hidden");
        return;
      }
      tooltip.innerHTML = `
        <div class="analytics-chart-tooltip-title">${escapeHtml(core.formatDateRu(point.point_date))}</div>
        <div class="analytics-chart-tooltip-grid">
          <span class="analytics-chart-tooltip-balance">Итог: ${escapeHtml(core.formatMoney(point.total_result_value || 0))}</span>
          <span class="analytics-chart-tooltip-income">Реализованный: ${escapeHtml(core.formatMoney(point.realized_result_value || 0))}</span>
          <span class="analytics-chart-tooltip-expense">Нереализованный: ${escapeHtml(core.formatMoney(point.unrealized_result_value || 0))}</span>
          <span class="analytics-chart-tooltip-ops">Оценка: ${escapeHtml(core.formatMoney(point.current_value || 0))}</span>
        </div>
      `;
      tooltip.classList.remove("hidden");
      const rect = el.currencyPerformanceChart.getBoundingClientRect();
      const tooltipRect = tooltip.getBoundingClientRect();
      const left = Math.max(8, Math.min(rect.width - tooltipRect.width - 8, event.clientX - rect.left + 12));
      const top = Math.max(8, Math.min(rect.height - tooltipRect.height - 8, event.clientY - rect.top - tooltipRect.height - 10));
      tooltip.style.left = `${left}px`;
      tooltip.style.top = `${top}px`;
    };
    el.currencyPerformanceChart.onmouseleave = () => {
      tooltip?.classList.add("hidden");
    };
  }

  function renderTrades(data) {
    if (!el.currencyTradesBody) {
      return;
    }
    const trades = Array.isArray(data.recent_trades) ? data.recent_trades : [];
    tradeItemsById.clear();
    trades.forEach((item) => {
      if (item?.id) {
        tradeItemsById.set(Number(item.id), item);
      }
    });
    if (!trades.length) {
      const emptyLabel = state.currencyFilter && state.currencyFilter !== "all"
        ? `Сделок по ${core.formatCurrencyLabel(state.currencyFilter)} пока нет`
        : "Сделок по отслеживаемым валютам пока нет";
      el.currencyTradesBody.innerHTML = `<tr><td colspan="7" class="muted-small">${emptyLabel}</td></tr>`;
      if (el.currencyTradesInfiniteSentinel) {
        el.currencyTradesInfiniteSentinel.classList.add("hidden");
      }
      return;
    }
    el.currencyTradesBody.innerHTML = trades.map((item) => {
      const isLinkedSettlement = item.trade_kind === "card_payment" && Number(item.linked_operation_id || 0) > 0;
      const sideClass = isLinkedSettlement ? "expense" : item.side === "sell" ? "expense" : "income";
      const sideLabel = isLinkedSettlement ? "Оплата картой" : item.side === "sell" ? "Продажа" : "Покупка";
      const linkedMeta = isLinkedSettlement
        ? `
          <div class="currency-trade-meta">
            <span class="meta-chip meta-chip-info">Связано с операцией</span>
            <button class="meta-chip-btn meta-chip-btn-neutral" type="button" data-open-linked-operation-id="${Number(item.linked_operation_id)}">Открыть</button>
          </div>
        `
        : "";
      const menuItems = isLinkedSettlement
        ? [
          `<button class="btn btn-secondary" type="button" data-open-linked-operation-id="${Number(item.linked_operation_id)}">Открыть операцию</button>`,
          `<button class="btn btn-danger" type="button" data-delete-linked-operation-id="${Number(item.linked_operation_id)}">Удалить операцию</button>`,
        ].join("")
        : [
          `<button class="btn btn-secondary" type="button" data-edit-currency-trade-id="${Number(item.id)}">Редактировать</button>`,
          `<button class="btn btn-danger" type="button" data-delete-currency-trade-id="${Number(item.id)}">Удалить</button>`,
        ].join("");
      return `
      <tr class="table-record-open-row" data-currency-trade-row-id="${Number(item.id)}">
        <td data-label="Дата">${core.formatDateRu(item.trade_date)}</td>
        <td data-label="Действие"><span class="kind-pill kind-pill-${sideClass}">${sideLabel}</span></td>
        <td data-label="Валюта">${core.escapeHtml ? core.escapeHtml(core.formatCurrencyLabel(item.asset_currency)) : core.formatCurrencyLabel(item.asset_currency)}</td>
        <td data-label="Количество">${core.formatAmount(item.quantity || 0)} ${core.escapeHtml ? core.escapeHtml(item.asset_currency || "") : (item.asset_currency || "")}<div class="muted-small">≈ ${formatTradeQuoteTotal(item)}</div></td>
        <td data-label="Курс">${formatRateWithQuote(item.unit_price || 0, item.quote_currency || "BYN")}</td>
        <td class="mobile-note-cell" data-label="Комментарий">
          <div class="currency-trade-note">
            ${linkedMeta}
            ${core.escapeHtml ? core.escapeHtml(item.note || "") : (item.note || "")}
          </div>
        </td>
        <td class="mobile-actions-cell table-kebab-cell" data-label="Действия">
          ${core.renderInlineKebabMenu?.(`currency-trade-${Number(item.id)}`, menuItems, "Действия валютной сделки", "operation-row-kebab") || '<span class="muted-small">Через операцию</span>'}
        </td>
      </tr>
    `;
    }).join("");
    if (el.currencyTradesInfiniteSentinel) {
      el.currencyTradesInfiniteSentinel.classList.toggle("hidden", !state.currencyTradesHasMore);
    }
  }

  function appendUniqueTrades(items) {
    const existing = new Set((state.currencyTradesItems || []).map((item) => Number(item?.id || 0)).filter((id) => id > 0));
    const nextItems = Array.isArray(state.currencyTradesItems) ? [...state.currencyTradesItems] : [];
    for (const item of Array.isArray(items) ? items : []) {
      const tradeId = Number(item?.id || 0);
      if (tradeId > 0 && existing.has(tradeId)) {
        continue;
      }
      if (tradeId > 0) {
        existing.add(tradeId);
      }
      nextItems.push(item);
    }
    state.currencyTradesItems = nextItems;
  }

  async function loadCurrencyTradesPage(page, options = {}) {
    const reset = options.reset === true;
    if (state.currencyTradesLoading && !reset) {
      return;
    }
    state.currencyTradesLoading = true;
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(state.currencyTradesPageSize || 20),
      });
      if (state.currencyFilter && state.currencyFilter !== "all") {
        params.set("currency", state.currencyFilter);
      }
      const data = await core.requestJson(`/api/v1/currency/trades?${params.toString()}`, {
        headers: core.authHeaders(),
      });
      if (reset) {
        state.currencyTradesItems = Array.isArray(data.items) ? data.items : [];
      } else {
        appendUniqueTrades(data.items);
      }
      state.currencyTradesPage = Number(data.page || page);
      state.currencyTradesTotal = Number(data.total || 0);
      state.currencyTradesHasMore = state.currencyTradesItems.length < state.currencyTradesTotal;
      renderTrades({ recent_trades: state.currencyTradesItems });
    } finally {
      state.currencyTradesLoading = false;
    }
  }

  async function loadMoreCurrencyTrades() {
    if (!state.currencyTradesHasMore || state.currencyTradesLoading) {
      return;
    }
    await loadCurrencyTradesPage(Number(state.currencyTradesPage || 1) + 1);
  }

  function bindCurrencyTradesInfiniteScroll() {
    if (!el.currencyTradesInfiniteSentinel || !("IntersectionObserver" in window)) {
      return;
    }
    if (currencyTradesObserver) {
      currencyTradesObserver.disconnect();
    }
    currencyTradesObserver = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (!entry?.isIntersecting) {
          return;
        }
        if (state.activeSection !== "currency") {
          return;
        }
        if (!state.currencyTradesHasMore || state.currencyTradesLoading) {
          return;
        }
        loadMoreCurrencyTrades().catch((err) => core.setStatus(String(err)));
      },
      { root: null, rootMargin: "240px 0px", threshold: 0 },
    );
    currencyTradesObserver.observe(el.currencyTradesInfiniteSentinel);
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
    const trade = tradeItemsById.get(Number(tradeId));
    if (!trade) {
      core.setStatus("Сделка не найдена");
      return;
    }
    await getOperationModal().openCreateModalForCurrencyEdit?.(trade);
  }

  function deleteCurrencyTrade(tradeId) {
    const trade = tradeItemsById.get(Number(tradeId));
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
    function handleCurrencyTradeActionClick(event) {
      const editBtn = event.target.closest("[data-edit-currency-trade-id]");
      if (editBtn) {
        const tradeId = Number(editBtn.dataset.editCurrencyTradeId || 0);
        core.runAction({
          errorPrefix: "Ошибка открытия валютной сделки",
          action: () => openCurrencyTradeEdit(tradeId),
        });
        return true;
      }
      const deleteBtn = event.target.closest("[data-delete-currency-trade-id]");
      if (deleteBtn) {
        const tradeId = Number(deleteBtn.dataset.deleteCurrencyTradeId || 0);
        deleteCurrencyTrade(tradeId);
        return true;
      }
      const linkedOperationBtn = event.target.closest("[data-open-linked-operation-id]");
      if (linkedOperationBtn) {
        const operationId = Number(linkedOperationBtn.dataset.openLinkedOperationId || 0);
        core.runAction({
          errorPrefix: "Ошибка открытия связанной операции",
          action: () => openLinkedOperation(operationId),
        });
        return true;
      }
      const deleteLinkedOperationBtn = event.target.closest("[data-delete-linked-operation-id]");
      if (deleteLinkedOperationBtn) {
        const operationId = Number(deleteLinkedOperationBtn.dataset.deleteLinkedOperationId || 0);
        core.runAction({
          errorPrefix: "Ошибка удаления связанной операции",
          action: () => deleteLinkedOperation(operationId),
        });
        return true;
      }
      return false;
    }

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
    if (el.currencyPerformancePeriodTabs) {
      el.currencyPerformancePeriodTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-currency-performance-period]");
        if (!btn) {
          return;
        }
        const period = String(btn.dataset.currencyPerformancePeriod || "90d");
        if (period === state.currencyPerformancePeriod && ["30d", "90d", "365d"].includes(period)) {
          openCurrencyPerformancePopover(period, btn);
          return;
        }
        applyCurrencyPerformancePeriod(period, "current");
      });
    }
    if (el.currencyPerformancePeriodOptions) {
      el.currencyPerformancePeriodOptions.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-currency-performance-quick-period][data-currency-performance-quick-anchor]");
        if (!btn) {
          return;
        }
        applyCurrencyPerformancePeriod(
          String(btn.dataset.currencyPerformanceQuickPeriod || "90d"),
          String(btn.dataset.currencyPerformanceQuickAnchor || "current"),
        );
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
    if (el.currencyTradesBody) {
      el.currencyTradesBody.addEventListener("click", (event) => {
        const trigger = event.target.closest("[data-table-menu-trigger]");
        if (trigger) {
          event.preventDefault();
          event.stopPropagation();
          toggleTableMenu(trigger);
          return;
        }
        if (handleCurrencyTradeActionClick(event)) {
          return;
        }
        const row = event.target.closest("tr[data-currency-trade-row-id]");
        if (!row) {
          return;
        }
        if (event.target.closest("button, a, input, select, textarea, label, .app-popover")) {
          return;
        }
        const tradeId = Number(row.dataset.currencyTradeRowId || 0);
        if (tradeId > 0) {
          const trade = tradeItemsById.get(tradeId);
          if (trade?.trade_kind === "card_payment" && Number(trade.linked_operation_id || 0) > 0) {
            core.runAction({
              errorPrefix: "Ошибка открытия связанной операции",
              action: () => openLinkedOperation(Number(trade.linked_operation_id)),
            });
            return;
          }
          core.runAction({
            errorPrefix: "Ошибка открытия валютной сделки",
            action: () => openCurrencyTradeEdit(tradeId),
          });
        }
      });
    }
    document.addEventListener("click", (event) => {
      if (!event.target.closest(".table-kebab-popover[data-table-menu^=\"currency-trade-\"]")) {
        return;
      }
      handleCurrencyTradeActionClick(event);
    });
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
