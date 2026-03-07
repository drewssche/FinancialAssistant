(() => {
  const { state, el, core } = window.App;
  const TREND_CACHE_TTL_MS = 20000;

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function pointsToPolyline(points, valueExtractor, width, height, minValue, maxValue) {
    if (!points.length) {
      return "";
    }
    const span = maxValue - minValue || 1;
    const stepX = points.length > 1 ? width / (points.length - 1) : width;
    return points
      .map((point, idx) => {
        const x = idx * stepX;
        const value = Number(valueExtractor(point) || 0);
        const y = height - ((value - minValue) / span) * height;
        return `${x.toFixed(2)},${Math.max(0, Math.min(height, y)).toFixed(2)}`;
      })
      .join(" ");
  }

  function formatPct(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "нет базы";
    }
    const num = Number(value);
    const sign = num > 0 ? "+" : "";
    return `${sign}${num.toFixed(1)}%`;
  }

  function renderTrendChart(svgNode, data, compact = false) {
    if (!svgNode) {
      return;
    }
    const points = Array.isArray(data?.points) ? data.points : [];
    if (!points.length) {
      svgNode.innerHTML = "";
      return;
    }
    const width = compact ? 420 : 980;
    const height = compact ? 110 : 280;
    const values = points.flatMap((p) => [Number(p.income_total || 0), Number(p.expense_total || 0), Number(p.balance || 0)]);
    const minValue = Math.min(0, ...values);
    const maxValue = Math.max(0, ...values);
    const mapY = (value) => {
      const span = maxValue - minValue || 1;
      const y = height - ((Number(value || 0) - minValue) / span) * height;
      return Math.max(0, Math.min(height, y));
    };

    if (compact) {
      const incomeLine = pointsToPolyline(points, (p) => p.income_total, width, height, minValue, maxValue);
      const expenseLine = pointsToPolyline(points, (p) => p.expense_total, width, height, minValue, maxValue);
      const balanceLine = pointsToPolyline(points, (p) => p.balance, width, height, minValue, maxValue);
      svgNode.innerHTML = `
        <polyline points="${incomeLine}" fill="none" stroke="#3bc47b" stroke-width="2" stroke-linecap="round" />
        <polyline points="${expenseLine}" fill="none" stroke="#ff7a7a" stroke-width="2" stroke-linecap="round" />
        <polyline points="${balanceLine}" fill="none" stroke="#6ca7ff" stroke-width="2" stroke-linecap="round" />
      `;
      return;
    }

    const bucketWidth = points.length > 0 ? width / points.length : width;
    const barWidth = Math.max(6, bucketWidth * 0.34);
    const zeroY = mapY(0);
    const barsIncome = [];
    const barsExpense = [];
    const hitboxes = [];

    for (let idx = 0; idx < points.length; idx += 1) {
      const point = points[idx];
      const baseX = idx * bucketWidth + bucketWidth / 2;
      const incomeY = mapY(point.income_total);
      const expenseY = mapY(point.expense_total);
      const incomeHeight = Math.max(1, Math.abs(zeroY - incomeY));
      const expenseHeight = Math.max(1, Math.abs(zeroY - expenseY));
      barsIncome.push(
        `<rect x="${(baseX - barWidth - 1).toFixed(2)}" y="${Math.min(incomeY, zeroY).toFixed(2)}" width="${barWidth.toFixed(2)}" height="${incomeHeight.toFixed(2)}" rx="2" fill="#3bc47b" fill-opacity="0.45" />`,
      );
      barsExpense.push(
        `<rect x="${(baseX + 1).toFixed(2)}" y="${Math.min(expenseY, zeroY).toFixed(2)}" width="${barWidth.toFixed(2)}" height="${expenseHeight.toFixed(2)}" rx="2" fill="#ff7a7a" fill-opacity="0.52" />`,
      );
      const hint = `${point.label}: Доход ${core.formatMoney(point.income_total)}, Расход ${core.formatMoney(point.expense_total)}, Баланс ${core.formatMoney(point.balance)}`;
      hitboxes.push(`
        <rect
          class="analytics-trend-hitbox"
          x="${(idx * bucketWidth).toFixed(2)}"
          y="0"
          width="${bucketWidth.toFixed(2)}"
          height="${height}"
          fill="transparent"
          data-analytics-bucket-start="${point.bucket_start}"
          data-analytics-bucket-end="${point.bucket_end}"
        >
          <title>${escapeHtml(hint)}</title>
        </rect>
      `);
    }

    const balanceLine = pointsToPolyline(points, (p) => p.balance, width, height, minValue, maxValue);
    svgNode.innerHTML = `
      <line x1="0" y1="${zeroY.toFixed(2)}" x2="${width}" y2="${zeroY.toFixed(2)}" stroke="rgba(141,160,190,0.45)" stroke-width="1" />
      ${barsIncome.join("")}
      ${barsExpense.join("")}
      <polyline points="${balanceLine}" fill="none" stroke="#6ca7ff" stroke-width="3" stroke-linecap="round" />
      ${hitboxes.join("")}
    `;
  }

  function trendQueryParams() {
    const params = new URLSearchParams();
    const period = state.analyticsPeriod || "month";
    params.set("period", period);
    params.set("granularity", state.analyticsGranularity || "day");
    if (period === "custom" && state.customDateFrom && state.customDateTo) {
      params.set("date_from", state.customDateFrom);
      params.set("date_to", state.customDateTo);
    }
    return params;
  }

  function renderAnalyticsTrend(data) {
    renderTrendChart(el.analyticsTrendChart, data, false);
    if (el.analyticsTrendRangeLabel) {
      const stepLabel = data.granularity === "day" ? "День" : data.granularity === "week" ? "Неделя" : "Месяц";
      el.analyticsTrendRangeLabel.textContent = `Окно: ${core.formatDateRu(data.date_from)} - ${core.formatDateRu(data.date_to)} · Шаг: ${stepLabel}`;
    }
    if (el.analyticsIncomeDelta) {
      el.analyticsIncomeDelta.textContent = formatPct(data.income_change_pct);
    }
    if (el.analyticsExpenseDelta) {
      el.analyticsExpenseDelta.textContent = formatPct(data.expense_change_pct);
    }
    if (el.analyticsBalanceDelta) {
      el.analyticsBalanceDelta.textContent = formatPct(data.balance_change_pct);
    }
    if (el.analyticsOpsDelta) {
      el.analyticsOpsDelta.textContent = formatPct(data.operations_change_pct);
    }
  }

  async function loadAnalyticsTrend(options = {}) {
    const force = options.force === true;
    const params = trendQueryParams();
    const cacheKey = `analytics:trend:${params.toString()}`;
    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, TREND_CACHE_TTL_MS);
      if (cached) {
        renderAnalyticsTrend(cached);
        return cached;
      }
    }
    const data = await core.requestJson(`/api/v1/dashboard/analytics/trend?${params.toString()}`, {
      headers: core.authHeaders(),
    });
    core.setUiRequestCache(cacheKey, data);
    renderAnalyticsTrend(data);
    return data;
  }

  async function loadDashboardAnalyticsPreview(options = {}) {
    const ui = core.getUiSettings ? core.getUiSettings() : null;
    if (ui && ui.showDashboardAnalytics === false) {
      return null;
    }
    const applyDashboardPreview = (data) => {
      const points = Array.isArray(data?.points) ? data.points : [];
      const operationsCount = Number(data?.operations_count || 0);
      const hasEnoughData = operationsCount >= 3 && points.length >= 2;

      if (hasEnoughData) {
        renderTrendChart(el.dashboardAnalyticsSparkline, data, true);
      } else if (el.dashboardAnalyticsSparkline) {
        el.dashboardAnalyticsSparkline.innerHTML = "";
      }
      if (el.dashboardAnalyticsEmpty) {
        el.dashboardAnalyticsEmpty.classList.toggle("hidden", hasEnoughData);
        if (!hasEnoughData) {
          const periodLabelMap = { day: "день", week: "неделю", month: "месяц", year: "год", all_time: "все время", custom: "период" };
          const periodLabel = periodLabelMap[state.period || "month"] || "период";
          el.dashboardAnalyticsEmpty.innerHTML = `
            <strong>Пока мало данных для тренда</strong>
            <span class="muted-small">Операций за ${periodLabel}: ${operationsCount}</span>
          `;
        }
      }

      if (el.dashboardAnalyticsIncomeDelta) {
        el.dashboardAnalyticsIncomeDelta.textContent = core.formatMoney(data.income_total || 0);
      }
      if (el.dashboardAnalyticsExpenseDelta) {
        el.dashboardAnalyticsExpenseDelta.textContent = core.formatMoney(data.expense_total || 0);
      }
      if (el.dashboardAnalyticsBalanceDelta) {
        el.dashboardAnalyticsBalanceDelta.textContent = core.formatMoney(data.balance || 0);
      }

      const incomeDelta = formatPct(data.income_change_pct);
      const expenseDelta = formatPct(data.expense_change_pct);
      const balanceDelta = formatPct(data.balance_change_pct);
      if (el.dashboardAnalyticsIncomeMeta) {
        el.dashboardAnalyticsIncomeMeta.textContent = incomeDelta === "нет базы" ? "без сравнения" : `к прошлому: ${incomeDelta}`;
      }
      if (el.dashboardAnalyticsExpenseMeta) {
        el.dashboardAnalyticsExpenseMeta.textContent = expenseDelta === "нет базы" ? "без сравнения" : `к прошлому: ${expenseDelta}`;
      }
      if (el.dashboardAnalyticsBalanceMeta) {
        el.dashboardAnalyticsBalanceMeta.textContent = balanceDelta === "нет базы" ? "без сравнения" : `к прошлому: ${balanceDelta}`;
      }
    };

    const force = options.force === true;
    const period = state.period || "month";
    const granularity = period === "year" ? "month" : period === "all_time" ? "month" : "day";
    const cacheKey = `analytics:preview:period=${period}:granularity=${granularity}`;
    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, TREND_CACHE_TTL_MS);
      if (cached) {
        applyDashboardPreview(cached);
        return cached;
      }
    }
    const { dateFrom, dateTo } = core.getPeriodBounds(period);
    const params = new URLSearchParams({ period, granularity, date_from: dateFrom, date_to: dateTo });
    const data = await core.requestJson(`/api/v1/dashboard/analytics/trend?${params.toString()}`, {
      headers: core.authHeaders(),
    });
    core.setUiRequestCache(cacheKey, data);
    applyDashboardPreview(data);
    return data;
  }

  window.App.featureAnalyticsModules = window.App.featureAnalyticsModules || {};
  window.App.featureAnalyticsModules.trend = {
    formatPct,
    loadAnalyticsTrend,
    loadDashboardAnalyticsPreview,
  };
})();
