(() => {
  const { state, el, core } = window.App;
  const shared = window.App.analyticsShared || {};
  const escapeHtml = shared.escapeHtml || ((value) => String(value ?? ""));
  const MULTI_SERIES_COLORS = ["#ff8a2b", "#6ea8ff", "#62d39a", "#f7c65b", "#d78cff", "#ff7c98"];

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
    const quote = String(quoteCurrency || "BYN").toUpperCase();
    return `${Number(rate || 0).toFixed(4)} ${quote}`;
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
    if (el.analyticsCurrencyBalancesRow) {
      const positions = Array.isArray(overview.positions) ? overview.positions : [];
      const positionsByCurrency = new Map(positions.map((item) => [String(item.currency || "").toUpperCase(), item]));
      const currentRates = Array.isArray(overview.current_rates) ? overview.current_rates : [];
      const currentRatesByCurrency = new Map(currentRates.map((item) => [String(item.currency || "").toUpperCase(), item]));
      const trackedCurrencies = Array.isArray(overview.tracked_currencies) && overview.tracked_currencies.length
        ? overview.tracked_currencies.map((item) => String(item || "").toUpperCase()).filter(Boolean)
        : getTrackedCurrencies();
      const baseCurrency = String(overview.base_currency || (core.getCurrencyConfig?.().code || "BYN")).toUpperCase();
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
          <div class="currency-balance-secondary">${core.formatMoney(item?.current_value || 0, { currency: baseCurrency })} по текущему курсу${currentRate?.rate ? ` · ${Number(currentRate.rate || 0).toFixed(4)}` : ""}</div>
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
            <span class="currency-position-secondary">${core.formatMoney(item.current_value || 0)} · средняя ${Number(item.average_buy_rate || 0).toFixed(4)} · текущий ${Number(item.current_rate || 0).toFixed(4)} · ${currentRateDate}</span>
          </span>
        `;
      }).concat([
        `<span class="analytics-kpi-chip analytics-kpi-chip-neutral">Покупки: ${core.formatMoney(overview.buy_volume_base || 0)} · ${String(overview.buy_trades_count || 0)} сделок · средняя ${Number(overview.buy_average_rate || 0).toFixed(4)}</span>`,
        `<span class="analytics-kpi-chip analytics-kpi-chip-neutral">Продажи: ${core.formatMoney(overview.sell_volume_base || 0)} · ${String(overview.sell_trades_count || 0)} сделок · средняя ${Number(overview.sell_average_rate || 0).toFixed(4)}</span>`,
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

  function renderTrades(overview) {
    if (!el.analyticsCurrencyTradesBody) {
      return;
    }
    const trades = Array.isArray(overview.recent_trades) ? overview.recent_trades : [];
    if (!trades.length) {
      const emptyLabel = state.analyticsCurrencyFilter && state.analyticsCurrencyFilter !== "all"
        ? `Сделок по ${core.formatCurrencyLabel(state.analyticsCurrencyFilter)} пока нет`
        : "Сделок по отслеживаемым валютам пока нет";
      el.analyticsCurrencyTradesBody.innerHTML = `<tr><td colspan="6" class="muted-small">${emptyLabel}</td></tr>`;
      return;
    }
    el.analyticsCurrencyTradesBody.innerHTML = trades.map((item) => `
      <tr>
        <td>${core.formatDateRu(item.trade_date)}</td>
        <td>${item.side === "sell" ? "Продажа" : "Покупка"}</td>
        <td>${core.formatCurrencyLabel(item.asset_currency)}</td>
        <td>${core.formatAmount(item.quantity || 0)} ${escapeHtml(item.asset_currency || "")}</td>
        <td>${formatRateWithQuote(item.unit_price || 0, item.quote_currency || "BYN")}</td>
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

  function bindCurrencyChartTooltip(svgNode, points, helpers = {}) {
    if (!svgNode) {
      return;
    }
    const tooltip = createCurrencyTooltipHost(svgNode);
    if (!tooltip) {
      return;
    }
    const hoverGroup = svgNode.querySelector(".currency-chart-hover");
    const hoverXLine = svgNode.querySelector(".currency-chart-hover-x");
    const hoverYLine = svgNode.querySelector(".currency-chart-hover-y");
    const hoverDot = svgNode.querySelector(".currency-chart-hover-dot");
    const hoverXLabel = svgNode.querySelector(".currency-chart-hover-x-label");
    const hoverYLabel = svgNode.querySelector(".currency-chart-hover-y-label");
    const { toX = () => 0, toY = () => 0, width = 980, height = 280, padX = 56, padY = 28 } = helpers;
    svgNode.onmousemove = (event) => {
      const bucket = event.target.closest(".trend-bucket");
      if (!bucket) {
        tooltip.classList.add("hidden");
        hoverGroup?.classList.add("hidden");
        return;
      }
      const index = Number(bucket.dataset.analyticsBucketIndex || -1);
      const point = points[index];
      if (!point) {
        tooltip.classList.add("hidden");
        hoverGroup?.classList.add("hidden");
        return;
      }
      const x = toX(index);
      const y = toY(Number(point.rate || 0));
      if (hoverGroup && hoverXLine && hoverYLine && hoverDot && hoverXLabel && hoverYLabel) {
        hoverGroup.classList.remove("hidden");
        hoverXLine.setAttribute("x1", String(padX));
        hoverXLine.setAttribute("x2", String(width - padX));
        hoverXLine.setAttribute("y1", String(y));
        hoverXLine.setAttribute("y2", String(y));
        hoverYLine.setAttribute("x1", String(x));
        hoverYLine.setAttribute("x2", String(x));
        hoverYLine.setAttribute("y1", String(padY));
        hoverYLine.setAttribute("y2", String(height - padY));
        hoverDot.setAttribute("cx", String(x));
        hoverDot.setAttribute("cy", String(y));
        hoverXLabel.setAttribute("x", String(x));
        hoverXLabel.setAttribute("y", String(height - 10));
        hoverXLabel.textContent = core.formatDateRu(point.rate_date);
        hoverYLabel.setAttribute("x", String(width - padX));
        hoverYLabel.setAttribute("y", String(Math.max(padY + 12, y - 8)));
        hoverYLabel.textContent = Number(point.rate || 0).toFixed(4);
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
      hoverGroup?.classList.add("hidden");
    };
  }

  function getSeriesColor(index) {
    return MULTI_SERIES_COLORS[index % MULTI_SERIES_COLORS.length];
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

  function bindMultiCurrencyChartTooltip(svgNode, seriesList, orderedDates, helpers = {}) {
    if (!svgNode) {
      return;
    }
    const tooltip = createCurrencyTooltipHost(svgNode);
    if (!tooltip) {
      return;
    }
    const hoverGroup = svgNode.querySelector(".currency-chart-hover");
    const hoverYLine = svgNode.querySelector(".currency-chart-hover-y");
    const hoverDotsGroup = svgNode.querySelector(".currency-chart-hover-dots");
    const hoverXLabel = svgNode.querySelector(".currency-chart-hover-x-label");
    const { toX = () => 0, toY = () => 0, height = 280, padY = 28 } = helpers;
    svgNode.onmousemove = (event) => {
      const bucket = event.target.closest(".trend-bucket");
      if (!bucket) {
        tooltip.classList.add("hidden");
        hoverGroup?.classList.add("hidden");
        return;
      }
      const index = Number(bucket.dataset.analyticsBucketIndex || -1);
      const rateDate = orderedDates[index];
      if (!rateDate) {
        tooltip.classList.add("hidden");
        hoverGroup?.classList.add("hidden");
        return;
      }
      const x = toX(index);
      const rows = seriesList
        .map((series) => {
          const point = series.pointsByDate.get(rateDate);
          if (!point) {
            return null;
          }
          return {
            currency: series.currency,
            color: series.color,
            rate: Number(point.rate || 0),
          };
        })
        .filter(Boolean)
        .sort((left, right) => right.rate - left.rate);
      if (!rows.length) {
        tooltip.classList.add("hidden");
        hoverGroup?.classList.add("hidden");
        return;
      }
      if (hoverGroup && hoverYLine && hoverDotsGroup && hoverXLabel) {
        hoverGroup.classList.remove("hidden");
        hoverYLine.setAttribute("x1", String(x));
        hoverYLine.setAttribute("x2", String(x));
        hoverYLine.setAttribute("y1", String(padY));
        hoverYLine.setAttribute("y2", String(height - padY));
        hoverXLabel.setAttribute("x", String(x));
        hoverXLabel.setAttribute("y", String(height - 10));
        hoverXLabel.textContent = core.formatDateRu(rateDate);
        hoverDotsGroup.innerHTML = rows.map((row) => `
          <circle cx="${x}" cy="${toY(row.rate)}" r="5" fill="${row.color}" stroke="#fff" stroke-width="2"></circle>
        `).join("");
      }
      tooltip.innerHTML = `
        <div class="analytics-chart-tooltip-title">${escapeHtml(core.formatDateRu(rateDate))}</div>
        <div class="analytics-chart-tooltip-grid">
          ${rows.map((row) => `
            <span class="analytics-chart-tooltip-balance">
              <span style="color:${escapeHtml(row.color)}">●</span> ${escapeHtml(core.formatCurrencyLabel(row.currency))}: ${escapeHtml(row.rate.toFixed(4))}
            </span>
          `).join("")}
        </div>
      `;
      tooltip.classList.remove("hidden");
      positionCurrencyTooltip(svgNode, tooltip, event.clientX, event.clientY);
    };
    svgNode.onmouseleave = () => {
      tooltip.classList.add("hidden");
      hoverGroup?.classList.add("hidden");
    };
  }

  function renderMultiCurrencyChart(seriesList) {
    if (!el.analyticsCurrencyChart) {
      return;
    }
    const visibleSeries = Array.isArray(seriesList) ? seriesList.filter((item) => Array.isArray(item.points) && item.points.length >= 2) : [];
    if (!visibleSeries.length) {
      renderEmptyChart("Недостаточно истории курса по отслеживаемым валютам");
      return;
    }
    const width = 980;
    const height = 280;
    const padX = 56;
    const padY = 36;
    const orderedDates = Array.from(new Set(
      visibleSeries.flatMap((series) => series.points.map((point) => point.rate_date)),
    )).sort();
    if (orderedDates.length < 2) {
      renderEmptyChart("Недостаточно истории курса по отслеживаемым валютам");
      return;
    }
    const allRates = visibleSeries.flatMap((series) => series.points.map((point) => Number(point.rate || 0))).filter((value) => Number.isFinite(value));
    const minRate = Math.min(...allRates);
    const maxRate = Math.max(...allRates);
    const yRange = maxRate - minRate || 1;
    const xStep = (width - padX * 2) / Math.max(1, orderedDates.length - 1);
    const toX = (index) => padX + index * xStep;
    const toY = (value) => height - padY - ((value - minRate) / yRange) * (height - padY * 2);
    const bucketWidth = orderedDates.length > 1 ? xStep : width - padX * 2;
    const legend = visibleSeries.map((series, index) => `
      <g transform="translate(${padX + index * 128}, 18)">
        <line x1="0" y1="0" x2="18" y2="0" stroke="${series.color}" stroke-width="4" stroke-linecap="round"></line>
        <text x="24" y="4" class="currency-chart-legend-label">${escapeHtml(core.formatCurrencyLabel(series.currency))}</text>
      </g>
    `).join("");
    const seriesMarkup = visibleSeries.map((series) => {
      const polyline = orderedDates
        .filter((rateDate) => series.pointsByDate.has(rateDate))
        .map((rateDate) => {
          const index = orderedDates.indexOf(rateDate);
          const point = series.pointsByDate.get(rateDate);
          return `${toX(index)},${toY(Number(point.rate || 0))}`;
        })
        .join(" ");
      const dots = series.points.map((point) => {
        const index = orderedDates.indexOf(point.rate_date);
        return `<circle cx="${toX(index)}" cy="${toY(Number(point.rate || 0))}" r="3.2" fill="${series.color}" stroke="rgba(255,255,255,0.88)" stroke-width="1.6"></circle>`;
      }).join("");
      return `
        <g class="currency-chart-series">
          <polyline fill="none" stroke="${series.color}" stroke-width="3.25" stroke-linejoin="round" stroke-linecap="round" points="${polyline}"></polyline>
          ${dots}
        </g>
      `;
    }).join("");
    const xTickIndexes = [0, Math.floor(orderedDates.length / 2), orderedDates.length - 1]
      .filter((value, idx, arr) => arr.indexOf(value) === idx);
    const xTicks = xTickIndexes.map((index) => `
      <line x1="${toX(index)}" y1="${height - padY}" x2="${toX(index)}" y2="${height - padY + 6}" stroke="rgba(207, 219, 245, 0.28)" stroke-width="1"></line>
      <text x="${toX(index)}" y="${height - 8}" text-anchor="${index === 0 ? "start" : index === orderedDates.length - 1 ? "end" : "middle"}" class="analytics-chart-empty">${core.formatDateRu(orderedDates[index])}</text>
    `).join("");
    const midRate = minRate + yRange / 2;
    const yMarks = [minRate, midRate, maxRate].map((value) => `
      <line x1="${width - padX - 8}" y1="${toY(value)}" x2="${width - padX}" y2="${toY(value)}" stroke="rgba(207, 219, 245, 0.28)" stroke-width="1"></line>
      <text x="${width - padX}" y="${Math.max(padY + 10, toY(value) - 8)}" text-anchor="end" class="analytics-chart-empty">${Number(value).toFixed(4)}</text>
    `).join("");
    const hitboxes = orderedDates.map((rateDate, index) => `
      <g class="trend-bucket" data-analytics-bucket-index="${index}" data-analytics-rate-date="${rateDate}">
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
      ${legend}
      ${seriesMarkup}
      ${xTicks}
      ${yMarks}
      ${hitboxes}
      <g class="currency-chart-hover hidden">
        <line class="currency-chart-hover-y" x1="0" y1="0" x2="0" y2="0" stroke="rgba(255,255,255,0.28)" stroke-dasharray="4 4" stroke-width="1"></line>
        <g class="currency-chart-hover-dots"></g>
        <text class="analytics-chart-empty currency-chart-hover-x-label" x="0" y="0" text-anchor="middle"></text>
      </g>
    `;
    bindMultiCurrencyChartTooltip(el.analyticsCurrencyChart, visibleSeries, orderedDates, { toX, toY, height, padY });
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
    const pointDots = points.map((item, index) => `
      <circle cx="${toX(index)}" cy="${toY(Number(item.rate || 0))}" r="2.8" fill="rgba(255,255,255,0.82)"></circle>
    `).join("");
    const xTicks = [0, Math.floor(points.length / 2), points.length - 1]
      .filter((value, idx, arr) => arr.indexOf(value) === idx)
      .map((index) => `
        <line x1="${toX(index)}" y1="${height - padY}" x2="${toX(index)}" y2="${height - padY + 6}" stroke="rgba(207, 219, 245, 0.28)" stroke-width="1"></line>
      `).join("");
    const yTicks = [minRate, midRate, maxRate].map((value) => `
      <line x1="${width - padX - 8}" y1="${toY(value)}" x2="${width - padX}" y2="${toY(value)}" stroke="rgba(207, 219, 245, 0.28)" stroke-width="1"></line>
    `).join("");
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
      ${pointDots}
      <circle cx="${toX(points.length - 1)}" cy="${toY(Number(last.rate || 0))}" r="5" fill="var(--accent, #6ea8ff)"></circle>
      ${xTicks}
      ${yTicks}
      ${hitboxes}
      <g class="currency-chart-hover hidden">
        <line class="currency-chart-hover-x" x1="0" y1="0" x2="0" y2="0" stroke="rgba(255,255,255,0.28)" stroke-dasharray="4 4" stroke-width="1"></line>
        <line class="currency-chart-hover-y" x1="0" y1="0" x2="0" y2="0" stroke="rgba(255,255,255,0.28)" stroke-dasharray="4 4" stroke-width="1"></line>
        <circle class="currency-chart-hover-dot" cx="0" cy="0" r="5.5" fill="var(--accent, #6ea8ff)" stroke="#fff" stroke-width="2"></circle>
        <text class="analytics-chart-empty currency-chart-hover-x-label" x="0" y="0" text-anchor="middle">${core.formatDateRu(last.rate_date)}</text>
        <text class="analytics-chart-empty currency-chart-hover-y-label" x="0" y="0" text-anchor="end">${Number(last.rate || 0).toFixed(4)}</text>
      </g>
      <text x="${padX}" y="${height - 8}" class="analytics-chart-empty">${core.formatDateRu(first.rate_date)}</text>
      <text x="${toX(Math.floor(points.length / 2))}" y="${height - 8}" text-anchor="middle" class="analytics-chart-empty">${core.formatDateRu(middle.rate_date)}</text>
      <text x="${width - padX}" y="${height - 8}" text-anchor="end" class="analytics-chart-empty">${core.formatDateRu(last.rate_date)}</text>
      <text x="${width - padX}" y="${padY + 4}" text-anchor="end" class="analytics-chart-empty">${Number(maxRate).toFixed(4)}</text>
      <text x="${width - padX}" y="${((padY + height - padY) / 2).toFixed(2)}" text-anchor="end" class="analytics-chart-empty">${Number(midRate).toFixed(4)}</text>
      <text x="${width - padX}" y="${height - padY - 8}" text-anchor="end" class="analytics-chart-empty">${Number(minRate).toFixed(4)}</text>
    `;
    bindCurrencyChartTooltip(el.analyticsCurrencyChart, points, { toX, toY, width, height, padX, padY });
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
