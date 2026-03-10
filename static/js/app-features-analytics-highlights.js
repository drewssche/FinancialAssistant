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

  function categoryKindLabel(kind) {
    if (kind === "income") {
      return "доходов";
    }
    if (kind === "all") {
      return "всех операций";
    }
    return "расходов";
  }

  function categoryKindShort(kind) {
    return kind === "income" ? "Доход" : kind === "all" ? "Все" : "Расход";
  }

  function renderCategoryBreakdown(data, formatPct) {
    const items = Array.isArray(data.category_breakdown) ? data.category_breakdown : [];
    const selectedKind = data.category_breakdown_kind || state.analyticsCategoryKind || "expense";
    const visibleItems = items.slice(0, 8);
    const chartTotal = items.reduce((acc, item) => acc + Number(item.total_amount || 0), 0);
    const totalOps = items.reduce((acc, item) => acc + Number(item.operations_count || 0), 0);
    const palette = ["#ff8f6b", "#5fd3bc", "#7aa8ff", "#ffd166", "#c084fc", "#5eead4", "#fb7185", "#93c5fd", "#a3e635"];
    let accShare = 0;
    const gradientParts = visibleItems
      .map((item, idx) => {
        const share = Math.max(0, Number(item.share_pct || 0));
        const start = accShare;
        const end = Math.min(100, accShare + share);
        accShare = end;
        return `${palette[idx % palette.length]} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
      })
      .filter(Boolean);
    const remainder = Math.max(0, 100 - accShare);
    if (remainder > 0.05) {
      gradientParts.push(`rgba(116, 136, 173, 0.22) ${accShare.toFixed(2)}% 100%`);
    }

    if (el.analyticsCategoryBreakdownLabel) {
      el.analyticsCategoryBreakdownLabel.textContent = `Доли по сумме для ${categoryKindLabel(selectedKind)} в выбранном периоде`;
    }
    if (el.analyticsTopCategoriesSubtitle) {
      el.analyticsTopCategoriesSubtitle.textContent = `Топ-5 категорий ${categoryKindLabel(selectedKind)}`;
    }
    if (el.analyticsTopCategoriesTitle) {
      el.analyticsTopCategoriesTitle.textContent = selectedKind === "income"
        ? "Категории доходов"
        : selectedKind === "all"
          ? "Категории периода"
          : "Категории расходов";
    }
    core.syncSegmentedActive(el.analyticsCategoryKindTabs, "analytics-category-kind", selectedKind);

    if (el.analyticsCategoryBreakdownChart) {
      if (visibleItems.length) {
        el.analyticsCategoryBreakdownChart.style.background = `conic-gradient(${gradientParts.join(", ")})`;
        el.analyticsCategoryBreakdownChart.classList.remove("analytics-category-donut-empty");
      } else {
        el.analyticsCategoryBreakdownChart.style.background = "rgba(116, 136, 173, 0.18)";
        el.analyticsCategoryBreakdownChart.classList.add("analytics-category-donut-empty");
      }
    }
    if (el.analyticsCategoryBreakdownChartValue) {
      el.analyticsCategoryBreakdownChartValue.textContent = core.formatMoney(chartTotal);
    }
    if (el.analyticsCategoryBreakdownChartMeta) {
      el.analyticsCategoryBreakdownChartMeta.textContent = visibleItems.length
        ? `${visibleItems.length} кат. · ${totalOps} опер.`
        : "Нет данных за период";
    }

    renderInsightList(
      el.analyticsCategoryBreakdownList,
      visibleItems,
      (item, idx) => `
        <article class="analytics-insight-item" data-analytics-category-id="${item.category_id ?? ""}" data-analytics-category-name="${escapeHtml(item.category_name || "Без категории")}" data-analytics-category-kind="${item.category_kind || selectedKind}">
          <div class="analytics-insight-head">
            <div class="analytics-category-row-title">
              <span class="analytics-category-color" style="background:${palette[idx % palette.length]}"></span>
              <strong>${escapeHtml(item.category_name || "Без категории")}</strong>
            </div>
            <span class="muted-small">${core.formatMoney(item.total_amount || 0)}</span>
          </div>
          <div class="muted-small">
            Доля: ${Number(item.share_pct || 0).toFixed(1)}% · Операций: ${item.operations_count}
            ${selectedKind === "all" ? ` · Тип: ${categoryKindShort(item.category_kind)}` : ""}
          </div>
          <div class="muted-small">Изм. к прошлому: ${formatPct(item.change_pct)}</div>
        </article>
      `,
      "Нет категорий за выбранный период",
    );
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
      const periodLabelMap = { week: "Эта неделя", month: "Этот месяц", year: "Этот год", all_time: "Все время", custom: "Период" };
      const label = periodLabelMap[data.period] || "Период";
      el.analyticsSummaryRangeLabel.textContent = `${label}: ${core.formatDateRu(data.date_from)} - ${core.formatDateRu(data.date_to)}`;
    }
    if (el.analyticsGlobalRangeLabel) {
      el.analyticsGlobalRangeLabel.textContent = `${core.formatDateRu(data.date_from)} - ${core.formatDateRu(data.date_to)}`;
    }

    if (el.analyticsKpiPrimary) {
      const primary = [
        {
          label: "Доход",
          value: core.formatMoney(data.income_total),
          delta: formatPct(data.income_change_pct),
          previous: core.formatMoney(data.prev_income_total || 0),
          tone: "income",
        },
        {
          label: "Расход",
          value: core.formatMoney(data.expense_total),
          delta: formatPct(data.expense_change_pct),
          previous: core.formatMoney(data.prev_expense_total || 0),
          tone: "expense",
        },
        {
          label: "Баланс",
          value: core.formatMoney(data.balance),
          delta: formatPct(data.balance_change_pct),
          previous: core.formatMoney(data.prev_balance || 0),
          tone: "balance",
        },
        {
          label: "Операций за период",
          value: String(data.operations_count || 0),
          delta: formatPct(data.operations_change_pct),
          previous: String(data.prev_operations_count || 0),
          tone: "neutral",
        },
      ];
      el.analyticsKpiPrimary.innerHTML = primary
        .map((item) => `
          <article class="analytics-kpi-card analytics-kpi-${item.tone}">
            <div class="muted-small">${escapeHtml(item.label)}</div>
            <strong>${escapeHtml(item.value)}</strong>
            <span class="analytics-kpi-delta">К прошлому периоду: ${escapeHtml(item.delta)}</span>
            <span class="muted-small">Было: ${escapeHtml(item.previous)}</span>
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

    renderCategoryBreakdown(data, formatPct);

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
        <article class="analytics-insight-item" data-analytics-category-id="${item.category_id ?? ""}" data-analytics-category-name="${escapeHtml(item.category_name || "Без категории")}" data-analytics-category-kind="${item.category_kind || data.category_breakdown_kind || "expense"}">
          <div class="analytics-insight-head">
            <strong>${escapeHtml(item.category_name || "Без категории")}</strong>
            <span class="muted-small">${core.formatMoney(item.total_amount || item.total_expense || 0)}</span>
          </div>
          <div class="muted-small">
            Доля: ${Number(item.share_pct || 0).toFixed(1)}% · Операций: ${item.operations_count}
            ${(data.category_breakdown_kind || "expense") === "all" ? ` · Тип: ${categoryKindShort(item.category_kind)}` : ""}
          </div>
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
    const period = state.analyticsGlobalPeriod || "month";
    const params = new URLSearchParams({ period, month, category_kind: state.analyticsCategoryKind || "expense" });
    if (period === "custom" && state.analyticsGlobalDateFrom && state.analyticsGlobalDateTo) {
      params.set("date_from", state.analyticsGlobalDateFrom);
      params.set("date_to", state.analyticsGlobalDateTo);
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
        period: state.analyticsGlobalPeriod || "month",
        category_breakdown_kind: state.analyticsCategoryKind || "expense",
        date_from: state.analyticsGlobalDateFrom || `${month}-01`,
        date_to: state.analyticsGlobalDateTo || `${month}-01`,
        month,
        month_start: `${month}-01`,
        month_end: `${month}-01`,
        income_total: "0",
        expense_total: "0",
        balance: "0",
        prev_income_total: "0",
        prev_expense_total: "0",
        prev_balance: "0",
        prev_operations_count: 0,
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
        category_breakdown: [],
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
