(() => {
  const { state, el, core } = window.App;
  const shared = window.App.analyticsShared || {};
  const escapeHtml = shared.escapeHtml || ((value) => String(value ?? ""));

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
    start.setDate(start.getDate() - (days - 1));
    const format = (value) => value.toISOString().slice(0, 10);
    return { dateFrom: format(start), dateTo: format(end) };
  }

  function renderSummary(overview) {
    if (el.analyticsCurrencyCurrentValue) {
      el.analyticsCurrencyCurrentValue.textContent = core.formatMoney(overview.total_current_value || 0);
    }
    if (el.analyticsCurrencyBookValue) {
      el.analyticsCurrencyBookValue.textContent = core.formatMoney(overview.total_book_value || 0);
    }
    if (el.analyticsCurrencyResultValue) {
      el.analyticsCurrencyResultValue.textContent = core.formatMoney(overview.total_result_value || 0);
    }
    if (el.analyticsCurrencyActiveCount) {
      el.analyticsCurrencyActiveCount.textContent = String(overview.active_positions || 0);
    }
    if (el.analyticsCurrencyBuyVolume) {
      el.analyticsCurrencyBuyVolume.textContent = core.formatMoney(overview.buy_volume_base || 0);
    }
    if (el.analyticsCurrencyBuyCount) {
      el.analyticsCurrencyBuyCount.textContent = `${String(overview.buy_trades_count || 0)} сделок · ср. курс ${Number(overview.buy_average_rate || 0).toFixed(4)}`;
    }
    if (el.analyticsCurrencySellVolume) {
      el.analyticsCurrencySellVolume.textContent = core.formatMoney(overview.sell_volume_base || 0);
    }
    if (el.analyticsCurrencySellCount) {
      el.analyticsCurrencySellCount.textContent = `${String(overview.sell_trades_count || 0)} сделок · ср. курс ${Number(overview.sell_average_rate || 0).toFixed(4)}`;
    }
    if (el.analyticsCurrencyRangeLabel) {
      const periodLabels = {
        "7d": "за 7 дней",
        "30d": "за 30 дней",
        "90d": "за 3 месяца",
        "365d": "за 12 месяцев",
        all_time: "за все время",
      };
      el.analyticsCurrencyRangeLabel.textContent = state.analyticsCurrencyFilter === "all"
        ? "Сводка по всем отслеживаемым валютам"
        : `Курс, позиция и сделки по ${core.formatCurrencyLabel(state.analyticsCurrencyFilter)} ${periodLabels[state.analyticsCurrencyPeriod] || ""}`.trim();
    }
    if (el.analyticsCurrencySecondary) {
      const positions = Array.isArray(overview.positions) ? overview.positions : [];
      if (!positions.length) {
        el.analyticsCurrencySecondary.innerHTML = `<span class="analytics-kpi-chip analytics-kpi-chip-neutral">Позиция пока не открыта</span>`;
        return;
      }
      el.analyticsCurrencySecondary.innerHTML = positions.map((item) => {
        const resultTone = Number(item.result_value || 0) >= 0 ? "analytics-kpi-chip-positive" : "analytics-kpi-chip-negative";
        const currentRateDate = item.current_rate_date ? core.formatDateRu(item.current_rate_date) : "курс не задан";
        const currencyLabel = core.formatCurrencyLabel(item.currency);
        return `
          <span class="analytics-kpi-chip ${resultTone}">
            ${currencyLabel}: ${core.formatMoney(item.current_value || 0)}
            <span class="muted-small">остаток ${core.formatAmount(item.quantity || 0)} · средняя ${Number(item.average_buy_rate || 0).toFixed(4)} · текущий ${Number(item.current_rate || 0).toFixed(4)} · ${currentRateDate}</span>
          </span>
        `;
      }).join("");
    }
  }

  async function backfillAnalyticsCurrencyHistory() {
    if (!state.analyticsCurrencyFilter || state.analyticsCurrencyFilter === "all") {
      core.setStatus("Выбери валюту, чтобы подгрузить историю курса");
      return;
    }
    const { dateFrom, dateTo } = getHistoryRange();
    const refreshState = window.App.getRuntimeModule?.("inline-refresh-state") || {};
    await refreshState.withRefresh?.(el.analyticsCurrencyPanel, async () => {
      await core.requestJson(
        `/api/v1/currency/rates/history/fill?currency=${encodeURIComponent(state.analyticsCurrencyFilter)}&date_from=${encodeURIComponent(dateFrom)}&date_to=${encodeURIComponent(dateTo)}`,
        {
          method: "POST",
          headers: core.authHeaders(),
        },
      );
      await loadAnalyticsCurrency({ force: true });
      core.invalidateUiRequestCache?.("dashboard:summary");
      window.App.getRuntimeModule?.("dashboard")?.loadDashboard?.().catch(() => {});
    }, "Подгружается история курса");
    core.setStatus("История курса подгружена");
  }

  function renderTrades(overview) {
    if (!el.analyticsCurrencyTradesBody) {
      return;
    }
    const trades = Array.isArray(overview.recent_trades) ? overview.recent_trades : [];
    if (!trades.length) {
      el.analyticsCurrencyTradesBody.innerHTML = `<tr><td colspan="7" class="muted-small">Сделок пока нет</td></tr>`;
      return;
    }
    el.analyticsCurrencyTradesBody.innerHTML = trades.map((item) => `
      <tr>
        <td>${core.formatDateRu(item.trade_date)}</td>
        <td>${item.side === "sell" ? "Продажа" : "Покупка"}</td>
        <td>${core.formatCurrencyLabel(item.asset_currency)}</td>
        <td>${core.formatAmount(item.quantity || 0)}</td>
        <td>${Number(item.unit_price || 0).toFixed(4)}</td>
        <td>${core.formatMoney(item.fee || 0, { currency: item.quote_currency || "BYN" })}</td>
        <td>${core.escapeHtml ? core.escapeHtml(item.note || "") : (item.note || "")}</td>
      </tr>
    `).join("");
  }

  function renderEmptyChart(message) {
    if (!el.analyticsCurrencyChart) {
      return;
    }
    el.analyticsCurrencyChart.innerHTML = `
      <text x="490" y="140" text-anchor="middle" class="analytics-chart-empty">${message}</text>
    `;
  }

  function createCurrencyTooltipHost(svgNode) {
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

  function positionCurrencyTooltip(svgNode, tooltip, clientX, clientY) {
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

  function bindCurrencyChartTooltip(svgNode, points) {
    if (!svgNode) {
      return;
    }
    const tooltip = createCurrencyTooltipHost(svgNode);
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
      tooltip.innerHTML = `
        <div class="analytics-chart-tooltip-title">${escapeHtml(core.formatDateRu(point.rate_date))}</div>
        <div class="analytics-chart-tooltip-grid analytics-chart-tooltip-grid-compact">
          <span class="analytics-chart-tooltip-balance">Курс: ${escapeHtml(Number(point.rate || 0).toFixed(4))}</span>
        </div>
      `;
      tooltip.classList.remove("hidden");
      positionCurrencyTooltip(svgNode, tooltip, event.clientX, event.clientY);
    };
    svgNode.onmouseleave = () => {
      tooltip.classList.add("hidden");
    };
  }

  function renderChart(points) {
    if (!el.analyticsCurrencyChart) {
      return;
    }
    if (!Array.isArray(points) || points.length < 2) {
      renderEmptyChart("Недостаточно истории курса");
      return;
    }
    const width = 980;
    const height = 280;
    const padX = 56;
    const padY = 28;
    const rates = points.map((item) => Number(item.rate || 0)).filter((value) => Number.isFinite(value));
    if (rates.length < 2) {
      renderEmptyChart("Недостаточно истории курса");
      return;
    }
    const minRate = Math.min(...rates);
    const maxRate = Math.max(...rates);
    const yRange = maxRate - minRate || 1;
    const xStep = (width - padX * 2) / Math.max(1, points.length - 1);
    const toX = (index) => padX + index * xStep;
    const toY = (value) => height - padY - ((value - minRate) / yRange) * (height - padY * 2);
    const polyline = points.map((item, index) => `${toX(index)},${toY(Number(item.rate || 0))}`).join(" ");
    const last = points[points.length - 1];
    const first = points[0];
    const middle = points[Math.floor(points.length / 2)];
    const midRate = minRate + yRange / 2;
    const bucketWidth = points.length > 1 ? xStep : width - padX * 2;
    const hitboxes = points.map((item, index) => `
      <g class="trend-bucket" data-analytics-bucket-index="${index}">
        <rect
          class="analytics-trend-hitbox"
          x="${Math.max(0, toX(index) - bucketWidth / 2).toFixed(2)}"
          y="0"
          width="${Math.max(bucketWidth, 24).toFixed(2)}"
          height="${height}"
          fill="transparent"
        ></rect>
      </g>
    `).join("");
    el.analyticsCurrencyChart.innerHTML = `
      <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" class="analytics-axis-line"></line>
      <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height - padY}" class="analytics-axis-line"></line>
      <polyline fill="none" stroke="var(--accent, #6ea8ff)" stroke-width="4" points="${polyline}"></polyline>
      <circle cx="${toX(points.length - 1)}" cy="${toY(Number(last.rate || 0))}" r="5" fill="var(--accent, #6ea8ff)"></circle>
      ${hitboxes}
      <text x="${padX}" y="${height - 8}" class="analytics-chart-empty">${core.formatDateRu(first.rate_date)}</text>
      <text x="${toX(Math.floor(points.length / 2))}" y="${height - 8}" text-anchor="middle" class="analytics-chart-empty">${core.formatDateRu(middle.rate_date)}</text>
      <text x="${width - padX}" y="${height - 8}" text-anchor="end" class="analytics-chart-empty">${core.formatDateRu(last.rate_date)}</text>
      <text x="${width - padX}" y="${padY + 4}" text-anchor="end" class="analytics-chart-empty">${Number(maxRate).toFixed(4)}</text>
      <text x="${width - padX}" y="${((padY + height - padY) / 2).toFixed(2)}" text-anchor="end" class="analytics-chart-empty">${Number(midRate).toFixed(4)}</text>
      <text x="${width - padX}" y="${height - padY - 8}" text-anchor="end" class="analytics-chart-empty">${Number(minRate).toFixed(4)}</text>
      <text x="${Math.min(width - padX, toX(points.length - 1) + 12)}" y="${Math.max(padY + 16, toY(Number(last.rate || 0)) - 12)}" class="analytics-chart-empty">Текущий курс ${Number(last.rate || 0).toFixed(4)}</text>
    `;
    bindCurrencyChartTooltip(el.analyticsCurrencyChart, points);
  }

  async function loadAnalyticsCurrency(options = {}) {
    syncCurrencyTabs();
    syncCurrencyPeriodTabs();
    const params = new URLSearchParams({ trades_limit: "100" });
    if (state.analyticsCurrencyFilter && state.analyticsCurrencyFilter !== "all") {
      params.set("currency", state.analyticsCurrencyFilter);
    }
    const overview = await core.requestJson(`/api/v1/currency/overview?${params.toString()}`, {
      headers: core.authHeaders(),
    });
    renderSummary(overview);
    renderTrades(overview);
    if (state.analyticsCurrencyFilter === "all") {
      renderEmptyChart("Выбери валюту, чтобы увидеть историю курса");
    } else {
      const { dateFrom, dateTo } = getHistoryRange();
      const historyParams = new URLSearchParams({ currency: state.analyticsCurrencyFilter, limit: "365" });
      if (dateFrom) {
        historyParams.set("date_from", dateFrom);
      }
      if (dateTo) {
        historyParams.set("date_to", dateTo);
      }
      const history = await core.requestJson(
        `/api/v1/currency/rates/history?${historyParams.toString()}`,
        { headers: core.authHeaders() },
      );
      renderChart(history);
    }
    state.analyticsCurrencyHydrated = true;
    if (options.force !== false) {
      syncCurrencyTabs();
    }
    return overview;
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
        state.analyticsCurrencyPeriod = btn.dataset.analyticsCurrencyPeriod || "30d";
        syncCurrencyPeriodTabs();
        loadAnalyticsCurrency({ force: true }).catch((err) => core.setStatus(String(err)));
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
    syncCurrencyTabs,
  });
})();
