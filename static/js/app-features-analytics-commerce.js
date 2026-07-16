(() => {
  const { state, el, core } = window.App;
  const PRICE_METRICS = [
    ["change_pct", "Рост, %"],
    ["change_amount", "Рост цены"],
    ["current_price", "Текущая цена"],
  ];
  const DISCOUNT_METRICS = [
    ["savings_total", "Экономия"],
    ["discount_pct", "Скидка, %"],
    ["purchases_count", "Покупки"],
  ];

  function itemKey(item) {
    return String(item.template_id || `${item.name || ""}|${item.shop_name || ""}`);
  }

  function activeMetrics() {
    return state.analyticsCommerceMode === "discounts" ? DISCOUNT_METRICS : PRICE_METRICS;
  }

  function ensureMetric() {
    const allowed = new Set(activeMetrics().map(([value]) => value));
    if (!allowed.has(state.analyticsCommerceMetric)) {
      state.analyticsCommerceMetric = state.analyticsCommerceMode === "discounts" ? "savings_total" : "change_pct";
    }
  }

  function discountRows(data) {
    const discountType = state.analyticsCommerceDiscountType || "all";
    return (data.top_discount_savings || []).map((item) => {
      if (discountType === "all") return item;
      const breakdown = (item.type_breakdown || []).find((part) => part.discount_type === discountType);
      return breakdown
        ? { ...item, ...breakdown, timeline: (item.timeline || []).filter((point) => point.discount_type === discountType) }
        : null;
    }).filter(Boolean);
  }

  function metricValue(item) {
    const metric = state.analyticsCommerceMetric;
    if (metric === "current_price") return Number(item.current_avg_unit_price || 0);
    return Number(item[metric] || 0);
  }

  function formatMetric(value) {
    const metric = state.analyticsCommerceMetric;
    if (metric === "change_pct" || metric === "discount_pct") return `${core.formatAmount(value)}%`;
    if (metric === "purchases_count") return core.formatAmount(value);
    return core.formatMoney(value);
  }

  function formatPercent(value) {
    return Number(value || 0).toLocaleString("ru-RU", { maximumFractionDigits: 2 });
  }

  function visibleRows(data = state.analyticsHighlightsData || {}) {
    ensureMetric();
    const rows = state.analyticsCommerceMode === "discounts"
      ? discountRows(data)
      : (data.price_increases || []);
    const direction = state.analyticsCommerceSort === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => (metricValue(a) - metricValue(b)) * direction);
  }

  function renderMetricTabs() {
    if (!el.analyticsCommerceMetricTabs) return;
    ensureMetric();
    el.analyticsCommerceMetricTabs.innerHTML = activeMetrics().map(([value, label]) => (
      `<button class="segmented-btn${state.analyticsCommerceMetric === value ? " active" : ""}" data-analytics-commerce-metric="${value}" type="button">${label}</button>`
    )).join("");
  }

  function renderSummary(data, rows) {
    if (!el.analyticsCommerceSummary) return;
    if (state.analyticsCommerceMode === "discounts") {
      const savings = rows.reduce((sum, item) => sum + Number(item.savings_total || 0), 0);
      const purchases = rows.reduce((sum, item) => sum + Number(item.purchases_count || 0), 0);
      el.analyticsCommerceSummary.innerHTML = `
        <span class="analytics-position-kpi"><span>Позиций</span><strong>${rows.length}</strong></span>
        <span class="analytics-position-kpi"><span>Экономия</span><strong>${core.formatMoney(savings)}</strong></span>
        <span class="analytics-position-kpi"><span>Покупок</span><strong>${purchases}</strong></span>
        <span class="analytics-position-kpi"><span>Доля расходов</span><strong>${data.discount_savings_rate_pct == null ? "Нет базы" : `${formatPercent(data.discount_savings_rate_pct)}%`}</strong></span>
      `;
      return;
    }
    const reliable = rows.filter((item) => Number(item.current_purchases_count || 0) >= 2 && Number(item.previous_purchases_count || 0) >= 2).length;
    const averageChange = rows.length
      ? rows.reduce((sum, item) => sum + Number(item.change_pct || 0), 0) / rows.length
      : 0;
    el.analyticsCommerceSummary.innerHTML = `
      <span class="analytics-position-kpi"><span>Подорожаний</span><strong>${rows.length}</strong></span>
      <span class="analytics-position-kpi"><span>Средний рост</span><strong>${core.formatAmount(averageChange)}%</strong></span>
      <span class="analytics-position-kpi"><span>С повторными покупками</span><strong>${reliable}</strong></span>
    `;
  }

  function renderRanking(rows) {
    if (!el.analyticsCommerceRanking) return;
    const max = Math.max(1, ...rows.map(metricValue));
    const descending = state.analyticsCommerceSort !== "asc";
    if (el.analyticsCommerceSortBtn) {
      el.analyticsCommerceSortBtn.textContent = descending ? "↓" : "↑";
      el.analyticsCommerceSortBtn.title = descending ? "Сначала больше" : "Сначала меньше";
      el.analyticsCommerceSortBtn.setAttribute("aria-label", `Сортировка: ${descending ? "сначала больше" : "сначала меньше"}`);
    }
    if (el.analyticsCommerceRankingTitle) {
      el.analyticsCommerceRankingTitle.textContent = state.analyticsCommerceMode === "discounts" ? "Лучшие скидки" : "Топ подорожаний";
    }
    el.analyticsCommerceRanking.innerHTML = rows.map((item, index) => {
      const key = itemKey(item);
      const width = Math.max(5, Math.round((metricValue(item) / max) * 100));
      return `<button class="analytics-position-ranking-row analytics-commerce-ranking-row${key === state.analyticsCommerceSelectedKey ? " active" : ""}" type="button" data-commerce-select-key="${core.escapeHtml(key)}">
        <span class="analytics-position-ranking-index">${index + 1}</span>
        <span class="analytics-position-ranking-copy"><strong>${core.escapeHtml(item.name || "Позиция")}</strong><small>${core.escapeHtml(item.shop_name || "Без источника")}</small><i style="--ranking-width:${width}%"></i></span>
        <strong class="analytics-position-ranking-value">${core.escapeHtml(formatMetric(metricValue(item)))}</strong>
      </button>`;
    }).join("");
  }

  function renderTimeline(item, mode) {
    const rawTimeline = item.timeline || [];
    const timeline = mode === "discounts"
      ? Array.from(rawTimeline.reduce((buckets, point) => {
          const current = buckets.get(point.date) || { ...point, savings_total: 0, purchases_count: 0 };
          current.savings_total += Number(point.savings_total || 0);
          current.purchases_count += Number(point.purchases_count || 0);
          buckets.set(point.date, current);
          return buckets;
        }, new Map()).values())
      : rawTimeline;
    if (!timeline.length) return '<div class="muted-small">Для выбранного периода нет временного ряда</div>';
    const values = timeline.map((point) => Number(mode === "discounts" ? point.savings_total : point.avg_unit_price));
    const max = Math.max(1, ...values);
    return `<div class="analytics-commerce-timeline" aria-label="Динамика по датам">
      ${timeline.map((point, index) => {
        const height = Math.max(8, Math.round((values[index] / max) * 100));
        const label = core.formatDateRu(point.date);
        return `<button type="button" class="analytics-commerce-timeline-bar" style="--bar-height:${height}%" data-commerce-date="${point.date}" title="${core.escapeHtml(label)} · ${core.escapeHtml(mode === "discounts" ? core.formatMoney(values[index]) : core.formatMoney(values[index]))}"><i></i><span>${core.escapeHtml(label.slice(0, 5))}</span></button>`;
      }).join("")}
    </div>`;
  }

  function renderFocus(data, rows) {
    if (!el.analyticsCommerceFocus) return;
    const selected = rows.find((item) => itemKey(item) === state.analyticsCommerceSelectedKey) || rows[0];
    if (!selected) {
      el.analyticsCommerceFocus.innerHTML = '<div class="muted-small">Выберите позицию в рейтинге</div>';
      return;
    }
    state.analyticsCommerceSelectedKey = itemKey(selected);
    const isDiscount = state.analyticsCommerceMode === "discounts";
    const details = isDiscount
      ? `Экономия ${core.formatMoney(selected.savings_total || 0)} · Скидка ${formatPercent(selected.discount_pct)}% · Покупок ${selected.purchases_count || 0}`
      : `${core.formatMoney(selected.previous_avg_unit_price || 0)} → ${core.formatMoney(selected.current_avg_unit_price || 0)} · Наблюдений ${selected.previous_samples_count || 0}/${selected.current_samples_count || 0}`;
    el.analyticsCommerceFocus.innerHTML = `
      <div class="analytics-commerce-focus-head">
        <div><strong>${core.escapeHtml(selected.name || "Позиция")}</strong><span class="muted-small">${core.escapeHtml(selected.shop_name || "Без источника")}</span></div>
        <button class="btn btn-secondary analytics-commerce-open-btn" type="button" data-commerce-open-operations="true">Открыть операции</button>
      </div>
      <p class="muted-small analytics-commerce-focus-meta">${core.escapeHtml(details)}</p>
      ${renderTimeline(selected, state.analyticsCommerceMode)}
    `;
  }

  function renderCommerce(data = state.analyticsHighlightsData || {}) {
    state.analyticsHighlightsData = data;
    const rows = visibleRows(data);
    if (el.analyticsCommerceRangeLabel) {
      el.analyticsCommerceRangeLabel.textContent = data.date_from
        ? `${core.formatDateRu(data.date_from)} - ${core.formatDateRu(data.date_to)}`
        : "Нет периода";
    }
    core.syncSegmentedActive(el.analyticsCommerceModeTabs, "analytics-commerce-mode", state.analyticsCommerceMode || "prices");
    core.syncSegmentedActive(el.analyticsCommerceDiscountTypeTabs, "analytics-commerce-discount-type", state.analyticsCommerceDiscountType || "all");
    el.analyticsCommerceDiscountTypeTabs?.classList.toggle("hidden", state.analyticsCommerceMode !== "discounts");
    renderMetricTabs();
    renderSummary(data, rows);
    renderRanking(rows);
    renderFocus(data, rows);
    el.analyticsCommerceEmpty?.classList.toggle("hidden", rows.length !== 0);
    document.querySelector(".analytics-commerce-layout")?.classList.toggle("hidden", rows.length === 0);
  }

  function selectedItem() {
    return visibleRows().find((item) => itemKey(item) === state.analyticsCommerceSelectedKey) || visibleRows()[0] || null;
  }

  const api = { renderCommerce, visibleRows, selectedItem };
  window.App.registerRuntimeModule?.("analytics-commerce-module", api);
})();
