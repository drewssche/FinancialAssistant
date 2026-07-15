(() => {
  const { state, el, core } = window.App;
  const CACHE_TTL_MS = 30000;
  const PERIOD_OPTIONS = [
    ["day", "День"],
    ["week", "Неделя"],
    ["month", "Месяц"],
    ["year", "Год"],
  ];

  function positionKey(item) {
    return item?.template_id
      ? `template:${Number(item.template_id)}`
      : `legacy:${String(item?.name || "").toLowerCase()}:${String(item?.shop_name || "").toLowerCase()}`;
  }

  function metricValue(item, metric = state.analyticsPositionsMetric) {
    if (metric === "quantity") return Number(item?.quantity_total || 0);
    if (metric === "amount") return Number(item?.amount_total || 0);
    return Number(item?.purchases_count || 0);
  }

  function formatMetric(value, metric = state.analyticsPositionsMetric) {
    if (metric === "amount") return core.formatMoney(value || 0);
    if (metric === "quantity") return core.formatAmount(value || 0);
    return String(Number(value || 0));
  }

  function formatCompactPeriodLabel(dateFrom, dateTo) {
    if (!dateFrom || !dateTo) return "Нет периода";
    const [fromYear, fromMonth, fromDay] = String(dateFrom).split("-");
    const [toYear, toMonth, toDay] = String(dateTo).split("-");
    if (dateFrom === dateTo) return `${fromDay}.${fromMonth}.${fromYear}`;
    if (fromYear === toYear) return `${fromDay}.${fromMonth}-${toDay}.${toMonth}.${toYear}`;
    return `${fromDay}.${fromMonth}.${fromYear}-${toDay}.${toMonth}.${toYear}`;
  }

  function isoToday() {
    return core.getTodayIso?.() || new Date().toISOString().slice(0, 10);
  }

  function currentAnchor() {
    return state.analyticsPositionsAnchor || isoToday();
  }

  function shiftAnchor(delta) {
    const period = state.analyticsPositionsPeriod || "month";
    const data = state.analyticsPositionsData || {};
    const currentBounds = data.period === period && data.date_from && data.date_to
      ? { dateFrom: data.date_from, dateTo: data.date_to }
      : core.getPeriodBounds?.(period);
    const periodUtils = window.App.getRuntimeModule?.("period-control-utils") || {};
    const shifted = periodUtils.shiftPeriodBounds?.({
      period,
      direction: delta,
      currentBounds,
      getPeriodBounds: (value) => core.getPeriodBounds?.(value),
    });
    return shifted?.dateFrom || currentAnchor();
  }

  function filteredPositions() {
    const data = state.analyticsPositionsData || {};
    const positionQuery = String(el.analyticsPositionsSearch?.value || "").trim().toLowerCase();
    const sourceQuery = String(el.analyticsPositionsSourceSearch?.value || "").trim().toLowerCase();
    const rows = (data.positions || []).filter((item) => {
      const nameMatches = !positionQuery || String(item.name || "").toLowerCase().includes(positionQuery);
      const sourceMatches = !sourceQuery || String(item.shop_name || "").toLowerCase().includes(sourceQuery);
      return nameMatches && sourceMatches;
    });
    const direction = state.analyticsPositionsSort === "asc" ? 1 : -1;
    rows.sort((a, b) => direction * (metricValue(a) - metricValue(b)) || String(a.name || "").localeCompare(String(b.name || ""), "ru"));
    return state.analyticsPositionsLimit === "all" ? rows : rows.slice(0, 10);
  }

  function rankingTitle() {
    const ascending = state.analyticsPositionsSort === "asc";
    if (state.analyticsPositionsMetric === "quantity") return ascending ? "Меньше всего единиц" : "Больше всего единиц";
    if (state.analyticsPositionsMetric === "amount") return ascending ? "Меньше всего потратили" : "Больше всего потратили";
    return ascending ? "Реже всего покупали" : "Чаще всего покупали";
  }

  function renderRanking(rows) {
    if (!el.analyticsPositionsRanking) return;
    const maxValue = Math.max(1, ...rows.map((item) => metricValue(item)));
    if (el.analyticsPositionsRankingTitle) el.analyticsPositionsRankingTitle.textContent = rankingTitle();
    if (el.analyticsPositionsSortBtn) {
      const ascending = state.analyticsPositionsSort === "asc";
      el.analyticsPositionsSortBtn.textContent = ascending ? "↑" : "↓";
      el.analyticsPositionsSortBtn.title = ascending ? "Сначала меньше" : "Сначала больше";
      el.analyticsPositionsSortBtn.setAttribute("aria-label", `Сортировка: ${ascending ? "сначала меньше" : "сначала больше"}`);
    }
    el.analyticsPositionsRanking.innerHTML = rows.map((item, index) => {
      const value = metricValue(item);
      const width = value > 0 ? Math.max(5, Math.round((value / maxValue) * 100)) : 0;
      const key = positionKey(item);
      return `<button class="analytics-position-ranking-row${key === state.analyticsPositionsSelectedKey ? " active" : ""}" type="button" data-position-select-key="${core.escapeHtml(key)}">
        <span class="analytics-position-ranking-index">${index + 1}</span>
        <span class="analytics-position-ranking-copy"><strong>${core.escapeHtml(item.name || "Позиция")}</strong><small>${core.escapeHtml(item.shop_name || "Без источника")}</small><i style="--ranking-width:${width}%"></i></span>
        <strong class="analytics-position-ranking-value">${formatMetric(value)}</strong>
      </button>`;
    }).join("");
  }

  function renderSummary(data, rows) {
    if (!el.analyticsPositionsSummary) return;
    const allRows = data.positions || [];
    const purchases = allRows.reduce((sum, item) => sum + Number(item.purchases_count || 0), 0);
    const quantity = allRows.reduce((sum, item) => sum + Number(item.quantity_total || 0), 0);
    const amount = allRows.reduce((sum, item) => sum + Number(item.amount_total || 0), 0);
    el.analyticsPositionsSummary.innerHTML = `
      <span class="analytics-position-kpi"><span>Позиций</span><strong>${allRows.length}</strong></span>
      <span class="analytics-position-kpi"><span>Покупок</span><strong>${purchases}</strong></span>
      <span class="analytics-position-kpi"><span>Количество</span><strong>${core.formatAmount(quantity)}</strong></span>
      <span class="analytics-position-kpi"><span>Сумма</span><strong>${core.formatMoney(amount)}</strong></span>
      <span class="analytics-position-kpi"><span>Показано</span><strong>${rows.length}</strong></span>
    `;
  }

  function renderMobileFocus(data, rows) {
    if (!el.analyticsPositionsMobileFocus) return;
    if (!rows.length) {
      el.analyticsPositionsMobileFocus.innerHTML = "";
      return;
    }
    const selected = rows.find((item) => positionKey(item) === state.analyticsPositionsSelectedKey) || rows[0];
    state.analyticsPositionsSelectedKey = positionKey(selected);
    const max = Math.max(1, ...(selected.buckets || []).map((bucket) => metricValue(bucket)));
    el.analyticsPositionsMobileFocus.innerHTML = `
      <div class="analytics-positions-focus-head">
        <div><strong>${core.escapeHtml(selected.name || "Позиция")}</strong><span class="muted-small">${core.escapeHtml(selected.shop_name || "Без источника")}</span></div>
        <strong>${formatMetric(metricValue(selected))}</strong>
      </div>
      <div class="analytics-positions-focus-chart">
        ${(selected.buckets || []).map((bucket, index) => {
          const value = metricValue(bucket);
          const height = value > 0 ? Math.max(8, Math.round((value / max) * 100)) : 2;
          const meta = data.buckets?.[index] || {};
          return `<button class="analytics-position-focus-bar" type="button" style="--bar-height:${height}%" data-position-template-id="${selected.template_id || ""}" data-position-name="${core.escapeHtml(selected.name || "")}" data-position-date-from="${meta.date_from || ""}" data-position-date-to="${meta.date_to || ""}" title="${core.escapeHtml(meta.label || "")} · ${core.escapeHtml(formatMetric(value))}"${value > 0 ? "" : " disabled"}><i></i><span>${core.escapeHtml(meta.label || "")}</span></button>`;
        }).join("")}
      </div>
    `;
  }

  function renderMatrix(data, rows) {
    const buckets = data.buckets || [];
    if (!el.analyticsPositionsMatrixHead || !el.analyticsPositionsMatrixBody) return;
    el.analyticsPositionsMatrixHead.innerHTML = `<tr><th class="analytics-position-sticky-name">Позиция</th>${buckets.map((bucket) => `<th>${core.escapeHtml(bucket.label || "")}</th>`).join("")}<th class="analytics-position-sticky-total">Итого</th></tr>`;
    const bucketMax = Math.max(1, ...rows.flatMap((item) => (item.buckets || []).map((bucket) => metricValue(bucket))));
    const totalMax = Math.max(1, ...rows.map((item) => metricValue(item)));
    el.analyticsPositionsMatrixBody.innerHTML = rows.map((item) => {
      const key = positionKey(item);
      return `<tr class="${key === state.analyticsPositionsSelectedKey ? "is-selected" : ""}">
        <td class="analytics-position-sticky-name"><button type="button" class="analytics-position-name-btn" data-position-select-key="${core.escapeHtml(key)}"><strong>${core.escapeHtml(item.name || "Позиция")}</strong><span>${core.escapeHtml(item.shop_name || "Без источника")}</span></button></td>
        ${(item.buckets || []).map((bucket, index) => {
          const value = metricValue(bucket);
          const intensity = value > 0 ? Math.max(0.12, value / bucketMax) : 0;
          const meta = buckets[index] || {};
          return `<td><button class="analytics-position-cell${value > 0 ? " has-value" : ""}" type="button" style="--cell-intensity:${intensity.toFixed(3)}" data-position-template-id="${item.template_id || ""}" data-position-name="${core.escapeHtml(item.name || "")}" data-position-date-from="${meta.date_from || ""}" data-position-date-to="${meta.date_to || ""}" title="${core.escapeHtml(item.name || "")} · ${core.escapeHtml(meta.label || "")} · ${core.escapeHtml(formatMetric(value))}"${value > 0 ? "" : " disabled"}><i></i><span>${value > 0 ? core.escapeHtml(formatMetric(value)) : "·"}</span></button></td>`;
        }).join("")}
        <td class="analytics-position-sticky-total"><div class="analytics-position-total" style="--total-width:${Math.max(4, Math.round((metricValue(item) / totalMax) * 100))}%"><i></i><strong>${formatMetric(metricValue(item))}</strong></div></td>
      </tr>`;
    }).join("");
  }

  function renderPositions() {
    const data = state.analyticsPositionsData || { buckets: [], positions: [] };
    const rows = filteredPositions();
    if (!state.analyticsPositionsSelectedKey && rows[0]) state.analyticsPositionsSelectedKey = positionKey(rows[0]);
    core.syncSegmentedActive(el.analyticsPositionsMetricTabs, "analytics-positions-metric", state.analyticsPositionsMetric || "purchases");
    core.syncSegmentedActive(el.analyticsPositionsLimitTabs, "analytics-positions-limit", state.analyticsPositionsLimit || "top");
    const periodLabel = data.date_from ? `${core.formatDateRu(data.date_from)} - ${core.formatDateRu(data.date_to)}` : "Нет периода";
    if (el.analyticsPositionsRangeLabel) el.analyticsPositionsRangeLabel.textContent = periodLabel;
    if (el.analyticsPositionsPeriodControlLabel) {
      el.analyticsPositionsPeriodControlLabel.textContent = formatCompactPeriodLabel(data.date_from, data.date_to);
    }
    renderSummary(data, rows);
    renderRanking(rows);
    renderMobileFocus(data, rows);
    renderMatrix(data, rows);
    el.analyticsPositionsMatrixWrap?.classList.toggle("hidden", rows.length === 0);
    el.analyticsPositionsEmpty?.classList.toggle("hidden", rows.length !== 0);
  }

  async function loadAnalyticsPositions(options = {}) {
    const period = state.analyticsPositionsPeriod || "month";
    const anchor = currentAnchor();
    const cacheKey = `analytics:positions:${period}:${anchor}`;
    if (!options.force) {
      const cached = core.getUiRequestCache(cacheKey, CACHE_TTL_MS);
      if (cached) {
        state.analyticsPositionsData = cached;
        state.analyticsPositionsAnchor = cached.date_from || anchor;
        state.analyticsPositionsHydrated = true;
        renderPositions();
        return cached;
      }
    }
    if (el.analyticsPositionsMatrixBody) el.analyticsPositionsMatrixBody.innerHTML = '<tr><td class="muted-small">Загрузка…</td></tr>';
    const params = new URLSearchParams({ period, anchor });
    const data = await core.requestJson(`/api/v1/dashboard/analytics/positions?${params.toString()}`, { headers: core.authHeaders() });
    core.setUiRequestCache(cacheKey, data);
    state.analyticsPositionsData = data;
    state.analyticsPositionsAnchor = data.date_from || anchor;
    state.analyticsPositionsHydrated = true;
    renderPositions();
    return data;
  }

  function setPeriod(period) {
    state.analyticsPositionsPeriod = ["day", "week", "month", "year"].includes(period) ? period : "month";
    state.analyticsPositionsAnchor = isoToday();
  }

  function shiftPeriod(delta) {
    state.analyticsPositionsAnchor = shiftAnchor(delta);
  }

  function resetPeriod() {
    state.analyticsPositionsAnchor = isoToday();
  }

  function toggleSort() {
    state.analyticsPositionsSort = state.analyticsPositionsSort === "asc" ? "desc" : "asc";
    renderPositions();
  }

  function renderPeriodOptions() {
    if (!el.analyticsPositionsPeriodOptions) return;
    el.analyticsPositionsPeriodOptions.innerHTML = PERIOD_OPTIONS.map(([value, label]) => {
      const bounds = core.getPeriodBounds?.(value) || {};
      return `<button class="btn btn-secondary settings-picker-option${state.analyticsPositionsPeriod === value ? " active" : ""}" type="button" data-analytics-positions-period-choice="${value}">
        ${label}<span class="muted-small">${core.formatPeriodLabel?.(bounds.dateFrom, bounds.dateTo) || ""}</span>
      </button>`;
    }).join("");
  }

  function renderDashboardRanking(data) {
    if (!el.dashboardPositionsRanking) return;
    const rows = (data?.frequent_positions || []).slice(0, 5);
    const maxValue = Math.max(1, ...rows.map((item) => Number(item.purchases_count || 0)));
    if (el.dashboardPositionsPeriodLabel && data?.date_from) {
      el.dashboardPositionsPeriodLabel.textContent = `${core.formatDateRu(data.date_from)} - ${core.formatDateRu(data.date_to)}`;
    }
    el.dashboardPositionsRanking.innerHTML = rows.map((item, index) => {
      const purchases = Number(item.purchases_count || 0);
      const width = Math.max(5, Math.round((purchases / maxValue) * 100));
      return `<button class="analytics-position-ranking-row" type="button" data-dashboard-position-template-id="${item.template_id || ""}" data-dashboard-position-name="${core.escapeHtml(item.name || "")}" data-dashboard-position-date-from="${data.date_from || ""}" data-dashboard-position-date-to="${data.date_to || ""}">
        <span class="analytics-position-ranking-index">${index + 1}</span>
        <span class="analytics-position-ranking-copy"><strong>${core.escapeHtml(item.name || "Позиция")}</strong><small>${core.escapeHtml(item.shop_name || "Без источника")} · ${core.formatAmount(item.quantity_total || 0)} ед. · ${core.formatMoney(item.amount_total || 0)}</small><i style="--ranking-width:${width}%"></i></span>
        <strong class="analytics-position-ranking-value">${purchases}</strong>
      </button>`;
    }).join("");
    el.dashboardPositionsEmpty?.classList.toggle("hidden", rows.length > 0);
    el.dashboardPositionsRanking.classList.toggle("hidden", rows.length === 0);
  }

  window.App.registerRuntimeModule?.("analytics-positions-module", {
    loadAnalyticsPositions,
    renderPositions,
    setPeriod,
    shiftPeriod,
    resetPeriod,
    toggleSort,
    renderPeriodOptions,
    renderDashboardRanking,
  });
})();
