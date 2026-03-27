(() => {
  const { state, el, core } = window.App;
  const shared = window.App.analyticsShared || {};
  const TREND_CACHE_TTL_MS = 20000;
  const escapeHtml = shared.escapeHtml || ((value) => String(value ?? ""));
  const sharedFormatPct = shared.formatPct || ((value) => String(value ?? ""));

  function getLoadingSkeletons() {
    return window.App.getRuntimeModule?.("loading-skeletons") || {};
  }

  function getInlineRefreshState() {
    return window.App.getRuntimeModule?.("inline-refresh-state") || {};
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
    return sharedFormatPct(value);
  }

  function formatBucketLabel(point) {
    const start = String(point?.bucket_start || "").trim();
    const end = String(point?.bucket_end || "").trim();
    if (!start && !end) {
      return String(point?.label || "").trim();
    }
    if (start && end && start !== end) {
      return `${core.formatDateRu(start)} - ${core.formatDateRu(end)}`;
    }
    return core.formatDateRu(start || end);
  }

  function createTrendTooltipHost(svgNode) {
    const wrapper = svgNode?.parentElement;
    if (!wrapper) {
      return null;
    }
    let tooltip = wrapper.querySelector(".analytics-chart-tooltip");
    if (!tooltip) {
      tooltip = document.createElement("div");
      tooltip.className = "analytics-chart-tooltip hidden";
      wrapper.appendChild(tooltip);
    }
    return tooltip;
  }

  function positionTrendTooltip(svgNode, tooltip, clientX, clientY) {
    if (!svgNode || !tooltip) {
      return;
    }
    const rect = svgNode.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    const left = Math.max(8, Math.min(rect.width - tooltipRect.width - 8, clientX - rect.left + 12));
    const top = Math.max(8, Math.min(rect.height - tooltipRect.height - 8, clientY - rect.top - tooltipRect.height - 10));
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  }

  function renderTrendTooltip(point, compact = false) {
    const ops = Number(point.operations_count || 0);
    return `
      <div class="analytics-chart-tooltip-title">${escapeHtml(formatBucketLabel(point) || point.label || "")}</div>
      <div class="analytics-chart-tooltip-grid${compact ? " analytics-chart-tooltip-grid-compact" : ""}">
        <span class="analytics-chart-tooltip-income">Доход: ${escapeHtml(core.formatMoney(point.income_total || 0))}</span>
        <span class="analytics-chart-tooltip-expense">Расход: ${escapeHtml(core.formatMoney(point.expense_total || 0))}</span>
        <span class="analytics-chart-tooltip-balance">Баланс: ${escapeHtml(core.formatMoney(point.balance || 0))}</span>
        <span class="analytics-chart-tooltip-ops">Операций: ${ops}</span>
      </div>
    `;
  }

  function bindTrendTooltip(svgNode, points, compact = false) {
    if (!svgNode) {
      return;
    }
    const tooltip = createTrendTooltipHost(svgNode);
    if (!tooltip) {
      return;
    }
    svgNode.onmousemove = (event) => {
      const bucket = event.target.closest(".trend-bucket");
      if (!bucket) {
        tooltip.classList.add("hidden");
        return;
      }
      const index = Number(bucket.dataset.analyticsBucketIndex || -1);
      const point = points[index];
      if (!point) {
        tooltip.classList.add("hidden");
        return;
      }
      tooltip.innerHTML = renderTrendTooltip(point, compact);
      tooltip.classList.remove("hidden");
      positionTrendTooltip(svgNode, tooltip, event.clientX, event.clientY);
    };
    svgNode.onmouseleave = () => {
      tooltip.classList.add("hidden");
    };
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

    const bucketWidth = points.length > 0 ? width / points.length : width;
    const barWidth = Math.max(compact ? 4 : 6, bucketWidth * (compact ? 0.24 : 0.34));
    const zeroY = mapY(0);
    const bucketGroups = [];

    for (let idx = 0; idx < points.length; idx += 1) {
      const point = points[idx];
      const baseX = idx * bucketWidth + bucketWidth / 2;
      const incomeY = mapY(point.income_total);
      const expenseY = mapY(point.expense_total);
      const balanceY = mapY(point.balance);
      const incomeHeight = Math.max(1, Math.abs(zeroY - incomeY));
      const expenseHeight = Math.max(1, Math.abs(zeroY - expenseY));
      bucketGroups.push(`
        <g
          class="trend-bucket"
          data-analytics-bucket-index="${idx}"
          data-analytics-bucket-start="${point.bucket_start}"
          data-analytics-bucket-end="${point.bucket_end}"
        >
          <rect
            class="trend-bucket-band"
            x="${(idx * bucketWidth).toFixed(2)}"
            y="0"
            width="${bucketWidth.toFixed(2)}"
            height="${height}"
            rx="${compact ? 8 : 10}"
            fill="rgba(108, 167, 255, 0.12)"
          ></rect>
          <rect
            class="trend-bar trend-bar-income"
            x="${(baseX - barWidth - 1).toFixed(2)}"
            y="${Math.min(incomeY, zeroY).toFixed(2)}"
            width="${barWidth.toFixed(2)}"
            height="${incomeHeight.toFixed(2)}"
            rx="2"
            fill="#3bc47b"
            fill-opacity="${compact ? "0.62" : "0.45"}"
          />
          <rect
            class="trend-bar trend-bar-expense"
            x="${(baseX + 1).toFixed(2)}"
            y="${Math.min(expenseY, zeroY).toFixed(2)}"
            width="${barWidth.toFixed(2)}"
            height="${expenseHeight.toFixed(2)}"
            rx="2"
            fill="#ff7a7a"
            fill-opacity="${compact ? "0.68" : "0.52"}"
          />
          <circle
            class="trend-balance-marker"
            cx="${baseX.toFixed(2)}"
            cy="${balanceY.toFixed(2)}"
            r="${compact ? "2.8" : "4.2"}"
            fill="#6ca7ff"
          />
          <rect
            class="analytics-trend-hitbox"
            x="${(idx * bucketWidth).toFixed(2)}"
            y="0"
            width="${bucketWidth.toFixed(2)}"
            height="${height}"
            fill="transparent"
          ></rect>
        </g>
      `);
    }

    const balanceLine = pointsToPolyline(points, (p) => p.balance, width, height, minValue, maxValue);
    svgNode.innerHTML = `
      <line x1="0" y1="${zeroY.toFixed(2)}" x2="${width}" y2="${zeroY.toFixed(2)}" stroke="rgba(141,160,190,0.45)" stroke-width="1" />
      <polyline points="${balanceLine}" fill="none" stroke="#6ca7ff" stroke-width="${compact ? "2.4" : "3"}" stroke-linecap="round" />
      ${bucketGroups.join("")}
    `;
    bindTrendTooltip(svgNode, points, compact);
  }

  function trendQueryParams() {
    const params = new URLSearchParams();
    const period = state.analyticsGlobalPeriod || "month";
    params.set("period", period);
    params.set("granularity", state.analyticsGranularity || "day");
    if (period === "custom" && state.analyticsGlobalDateFrom && state.analyticsGlobalDateTo) {
      params.set("date_from", state.analyticsGlobalDateFrom);
      params.set("date_to", state.analyticsGlobalDateTo);
    }
    return params;
  }

  function renderAnalyticsTrend(data) {
    renderTrendChart(el.analyticsTrendChart, data, false);
    if (el.analyticsTrendRangeLabel) {
      const stepLabel = data.granularity === "day" ? "По дням" : data.granularity === "week" ? "По неделям" : data.granularity === "month" ? "По месяцам" : "По годам";
      el.analyticsTrendRangeLabel.textContent = `Окно: ${core.formatDateRu(data.date_from)} - ${core.formatDateRu(data.date_to)} · Шаг: ${stepLabel}`;
    }
    if (el.analyticsIncomeDelta) {
      el.analyticsIncomeDelta.textContent = core.formatMoney(data.income_total || 0);
    }
    if (el.analyticsExpenseDelta) {
      el.analyticsExpenseDelta.textContent = core.formatMoney(data.expense_total || 0);
    }
    if (el.analyticsBalanceDelta) {
      el.analyticsBalanceDelta.textContent = core.formatMoney(data.balance || 0);
    }
    if (el.analyticsOpsDelta) {
      el.analyticsOpsDelta.textContent = String(data.operations_count || 0);
    }
  }

  async function loadAnalyticsTrend(options = {}) {
    const force = options.force === true;
    const skeletons = getLoadingSkeletons();
    if (!state.analyticsTrendHydrated && state.activeSection === "analytics" && (state.analyticsTab || "calendar") === "trends") {
      skeletons.renderAnalyticsTrendSkeleton?.();
    }
    const refreshState = getInlineRefreshState();
    const shouldRefreshInline = state.analyticsTrendHydrated;
    if (shouldRefreshInline) {
      refreshState.begin?.(el.analyticsTrendsPanel, "Обновляется");
    }
    const params = trendQueryParams();
    const cacheKey = `analytics:trend:${params.toString()}`;
    try {
      if (!force) {
        const cached = core.getUiRequestCache(cacheKey, TREND_CACHE_TTL_MS);
        if (cached) {
          renderAnalyticsTrend(cached);
          skeletons.clearAnalyticsTrendSkeletonState?.();
          state.analyticsTrendHydrated = true;
          return cached;
        }
      }
      const data = await core.requestJson(`/api/v1/dashboard/analytics/trend?${params.toString()}`, {
        headers: core.authHeaders(),
      });
      core.setUiRequestCache(cacheKey, data);
      renderAnalyticsTrend(data);
      skeletons.clearAnalyticsTrendSkeletonState?.();
      state.analyticsTrendHydrated = true;
      return data;
    } finally {
      if (shouldRefreshInline) {
        refreshState.end?.(el.analyticsTrendsPanel);
      }
    }
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
          const periodLabel = periodLabelMap[state.dashboardAnalyticsPeriod || "month"] || "период";
          el.dashboardAnalyticsEmpty.innerHTML = `
            <strong>Пока мало данных для тренда</strong>
            <span class="muted-small">Операций за ${periodLabel}: ${operationsCount}</span>
          `;
        }
      }
      if (el.dashboardAnalyticsPeriodLabel) {
        el.dashboardAnalyticsPeriodLabel.textContent = `${core.formatDateRu(data.date_from)} - ${core.formatDateRu(data.date_to)}`;
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
        el.dashboardAnalyticsIncomeMeta.textContent = incomeDelta === "нет базы"
          ? `было: ${core.formatMoney(data.prev_income_total || 0)}`
          : `к прошлому: ${incomeDelta} · было ${core.formatMoney(data.prev_income_total || 0)}`;
      }
      if (el.dashboardAnalyticsExpenseMeta) {
        el.dashboardAnalyticsExpenseMeta.textContent = expenseDelta === "нет базы"
          ? `было: ${core.formatMoney(data.prev_expense_total || 0)}`
          : `к прошлому: ${expenseDelta} · было ${core.formatMoney(data.prev_expense_total || 0)}`;
      }
      if (el.dashboardAnalyticsBalanceMeta) {
        el.dashboardAnalyticsBalanceMeta.textContent = balanceDelta === "нет базы"
          ? `было: ${core.formatMoney(data.prev_balance || 0)}`
          : `к прошлому: ${balanceDelta} · было ${core.formatMoney(data.prev_balance || 0)}`;
      }
    };

    const force = options.force === true;
    const period = state.dashboardAnalyticsPeriod || "month";
    const operationsFeature = window.App.getRuntimeModule?.("operations") || {};
    if (operationsFeature.ensureAllTimeBounds) {
      await operationsFeature.ensureAllTimeBounds(false, period);
    }
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

  const api = {
    formatPct,
    loadAnalyticsTrend,
    loadDashboardAnalyticsPreview,
  };

  window.App.registerRuntimeModule?.("analytics-trend-module", api);
})();
