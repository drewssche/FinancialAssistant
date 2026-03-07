(() => {
  const { state, el, core } = window.App;
  const HIGHLIGHTS_CACHE_TTL_MS = 20000;

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function describeResult(balanceRaw) {
    const balance = Number(balanceRaw || 0);
    if (balance > 0) {
      return { label: "Профицит", tone: "positive", amount: balance };
    }
    if (balance < 0) {
      return { label: "Дефицит", tone: "negative", amount: Math.abs(balance) };
    }
    return { label: "Нулевой баланс", tone: "neutral", amount: 0 };
  }

  function renderInsightList(container, items, renderItem, emptyText) {
    if (!container) {
      return;
    }
    if (!Array.isArray(items) || items.length === 0) {
      container.innerHTML = `<div class="muted-small">${emptyText}</div>`;
      return;
    }
    container.innerHTML = items.map(renderItem).join("");
  }

  function renderAnalyticsHighlights(data) {
    const trendModule = window.App.featureAnalyticsModules?.trend;
    const formatPct = trendModule?.formatPct || ((v) => String(v ?? "нет базы"));

    const topOperationsLimit = [3, 5, 10].includes(Number(state.analyticsTopOperationsLimit))
      ? Number(state.analyticsTopOperationsLimit)
      : 5;
    const topPositionsLimit = [5, 10, 20].includes(Number(state.analyticsTopPositionsLimit))
      ? Number(state.analyticsTopPositionsLimit)
      : 10;

    if (el.analyticsSummaryRangeLabel) {
      const periodLabelMap = { week: "Неделя", month: "Месяц", year: "Год", custom: "Период" };
      const label = periodLabelMap[data.period] || "Период";
      el.analyticsSummaryRangeLabel.textContent = `${label}: ${core.formatDateRu(data.date_from)} - ${core.formatDateRu(data.date_to)}`;
    }

    if (el.analyticsKpiPrimary) {
      const primary = [
        { label: "Доход", value: core.formatMoney(data.income_total), delta: formatPct(data.income_change_pct), tone: "income" },
        { label: "Расход", value: core.formatMoney(data.expense_total), delta: formatPct(data.expense_change_pct), tone: "expense" },
        { label: "Баланс", value: core.formatMoney(data.balance), delta: formatPct(data.balance_change_pct), tone: "balance" },
        { label: "Операции", value: String(data.operations_count || 0), delta: formatPct(data.operations_change_pct), tone: "neutral" },
      ];
      el.analyticsKpiPrimary.innerHTML = primary
        .map((item) => `
          <article class="analytics-kpi-card analytics-kpi-${item.tone}">
            <div class="muted-small">${escapeHtml(item.label)}</div>
            <strong>${escapeHtml(item.value)}</strong>
            <span class="analytics-kpi-delta">${escapeHtml(item.delta)}</span>
          </article>
        `)
        .join("");
    }

    if (el.analyticsKpiSecondary) {
      const result = describeResult(data.balance);
      const chips = [
        { text: `${result.label}: ${core.formatMoney(result.amount)}`, tone: result.tone },
        { text: `Средний расход/день: ${core.formatMoney(data.avg_daily_expense || 0)}`, tone: "neutral" },
        {
          text: data.max_expense_day_date
            ? `Самый затратный день: ${core.formatDateRu(data.max_expense_day_date)} · ${core.formatMoney(data.max_expense_day_total)}`
            : "Самый затратный день: нет данных",
          tone: "neutral",
        },
      ];
      el.analyticsKpiSecondary.innerHTML = chips
        .map((item) => `<span class="analytics-kpi-chip analytics-kpi-chip-${item.tone}">${escapeHtml(item.text)}</span>`)
        .join("");
    }

    renderInsightList(
      el.analyticsTopOperationsList,
      (data.top_operations || []).slice(0, topOperationsLimit),
      (item) => `
        <article class="analytics-insight-item" data-analytics-date="${item.operation_date}">
          <div class="analytics-insight-head">
            <strong>${core.formatMoney(item.amount)}</strong>
            <span class="muted-small">${core.formatDateRu(item.operation_date)}</span>
          </div>
          <div class="muted-small">${item.kind === "income" ? "Доход" : "Расход"}</div>
          <div>${escapeHtml(item.note || "Без комментария")}</div>
        </article>
      `,
      "Нет операций за выбранный период",
    );

    renderInsightList(
      el.analyticsTopCategoriesList,
      data.top_categories,
      (item) => `
        <article class="analytics-insight-item">
          <div class="analytics-insight-head">
            <strong>${escapeHtml(item.category_name || "Без категории")}</strong>
            <span class="muted-small">${core.formatMoney(item.total_expense)}</span>
          </div>
          <div class="muted-small">Доля: ${Number(item.share_pct || 0).toFixed(1)}% · Операций: ${item.operations_count}</div>
          <div class="muted-small">Изм. к прошлому: ${formatPct(item.change_pct)}</div>
        </article>
      `,
      "Нет категорий за выбранный период",
    );

    renderInsightList(
      el.analyticsAnomaliesList,
      data.anomalies,
      (item) => `
        <article class="analytics-insight-item analytics-insight-alert" data-analytics-date="${item.operation_date}">
          <div class="analytics-insight-head">
            <strong>${core.formatMoney(item.amount)}</strong>
            <span class="muted-small">${core.formatDateRu(item.operation_date)}</span>
          </div>
          <div class="muted-small">${escapeHtml(item.category_name)}</div>
          <div class="muted-small">Выше медианы в ${Number(item.ratio_to_median || 0).toFixed(1)}x</div>
          <div>${escapeHtml(item.note || "Без комментария")}</div>
        </article>
      `,
      "Явных аномалий не найдено",
    );

    renderInsightList(
      el.analyticsTopPositionsList,
      (data.top_positions || []).slice(0, topPositionsLimit),
      (item) => `
        <article class="analytics-insight-item">
          <div class="analytics-insight-head">
            <strong>${escapeHtml(item.name)}</strong>
            <span class="muted-small">${core.formatMoney(item.max_unit_price)}</span>
          </div>
          <div class="muted-small">${escapeHtml(item.shop_name || "Без источника")}</div>
          <div class="muted-small">Покупок: ${item.purchases_count} · Потрачено: ${core.formatMoney(item.total_spent)} · Средняя: ${core.formatMoney(item.avg_unit_price)}</div>
        </article>
      `,
      "Нет позиций за выбранный период",
    );

    renderInsightList(
      el.analyticsPriceIncreasesList,
      data.price_increases,
      (item) => `
        <article class="analytics-insight-item analytics-insight-alert">
          <div class="analytics-insight-head">
            <strong>${escapeHtml(item.name)}</strong>
            <span class="analytics-badge-up">↑ ${formatPct(item.change_pct)}</span>
          </div>
          <div class="muted-small">${escapeHtml(item.shop_name || "Без источника")}</div>
          <div class="muted-small">${core.formatMoney(item.previous_avg_unit_price)} → ${core.formatMoney(item.current_avg_unit_price)}</div>
        </article>
      `,
      "Рост цен не обнаружен",
    );
  }

  function buildHighlightsParams(month) {
    const period = state.analyticsSummaryPeriod || "month";
    const params = new URLSearchParams({ period, month });
    if (period === "custom" && state.analyticsSummaryDateFrom && state.analyticsSummaryDateTo) {
      params.set("date_from", state.analyticsSummaryDateFrom);
      params.set("date_to", state.analyticsSummaryDateTo);
    }
    return params;
  }

  async function loadAnalyticsHighlights(options = {}) {
    const force = options.force === true;
    const calendarModule = window.App.featureAnalyticsModules?.calendar;
    const month = state.analyticsMonthAnchor || calendarModule?.serializeMonthAnchor?.(calendarModule.currentAnchorDate()) || "";
    const params = buildHighlightsParams(month);
    const cacheKey = `analytics:highlights:${params.toString()}`;

    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, HIGHLIGHTS_CACHE_TTL_MS);
      if (cached) {
        renderAnalyticsHighlights(cached);
        return cached;
      }
    }

    try {
      const data = await core.requestJson(`/api/v1/dashboard/analytics/highlights?${params.toString()}`, {
        headers: core.authHeaders(),
      });
      core.setUiRequestCache(cacheKey, data);
      renderAnalyticsHighlights(data);
      return data;
    } catch (err) {
      const message = core.errorMessage ? core.errorMessage(err) : String(err);
      if (!String(message).includes("[404]")) {
        throw err;
      }
      const fallback = {
        period: state.analyticsSummaryPeriod || "month",
        date_from: state.analyticsSummaryDateFrom || `${month}-01`,
        date_to: state.analyticsSummaryDateTo || `${month}-01`,
        month,
        month_start: `${month}-01`,
        month_end: `${month}-01`,
        income_total: "0",
        expense_total: "0",
        balance: "0",
        surplus_total: "0",
        deficit_total: "0",
        operations_count: 0,
        avg_daily_expense: "0",
        max_expense_day_date: null,
        max_expense_day_total: "0",
        income_change_pct: 0,
        expense_change_pct: 0,
        balance_change_pct: 0,
        operations_change_pct: 0,
        top_operations: [],
        top_categories: [],
        anomalies: [],
        top_positions: [],
        price_increases: [],
      };
      renderAnalyticsHighlights(fallback);
      return fallback;
    }
  }

  window.App.featureAnalyticsModules = window.App.featureAnalyticsModules || {};
  window.App.featureAnalyticsModules.highlights = {
    loadAnalyticsHighlights,
  };
})();
