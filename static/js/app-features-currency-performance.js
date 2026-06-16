(() => {
  function createCurrencyPerformanceFeature(deps) {
    const { state, el, core, pickerUtils, escapeHtml, reload } = deps;

    function getRange() {
      const today = core.getTodayIso();
      if (state.currencyPerformancePeriod === "all_time") {
        return { dateFrom: "", dateTo: today };
      }
      const days = { "30d": 30, "90d": 90, "365d": 365 }[state.currencyPerformancePeriod] || 90;
      const end = new Date(`${today}T00:00:00`);
      const start = new Date(end);
      if (state.currencyPerformancePeriodAnchor === "previous") {
        end.setDate(end.getDate() - days);
      }
      start.setDate(start.getDate() - (days - 1));
      return {
        dateFrom: start.toISOString().slice(0, 10),
        dateTo: end.toISOString().slice(0, 10),
      };
    }

    function closePopover() {
      pickerUtils?.setPopoverOpen?.(el.currencyPerformancePeriodPopover, false, {
        owners: [el.currencyPerformancePeriodTabs].filter(Boolean),
      });
    }

    function syncPeriodTabs() {
      if (el.currencyPerformancePeriodTabs) {
        core.syncSegmentedActive(
          el.currencyPerformancePeriodTabs,
          "currency-performance-period",
          state.currencyPerformancePeriod || "90d",
        );
      }
    }

    function renderPeriodOptions(period = state.currencyPerformancePeriod || "90d") {
      if (!el.currencyPerformancePeriodOptions) {
        return;
      }
      const labels = {
        "30d": { current: "Текущие 30 дней", previous: "Предыдущие 30 дней" },
        "90d": { current: "Текущие 3 месяца", previous: "Предыдущие 3 месяца" },
        "365d": { current: "Текущие 12 месяцев", previous: "Предыдущие 12 месяцев" },
      };
      const copy = labels[period] || { current: "Текущий период", previous: "Предыдущий период" };
      const previousAnchor = state.currencyPerformancePeriodAnchor;
      state.currencyPerformancePeriodAnchor = "current";
      const currentRange = getRange();
      state.currencyPerformancePeriodAnchor = "previous";
      const previousRange = getRange();
      state.currencyPerformancePeriodAnchor = previousAnchor;
      const activeAnchor = previousAnchor === "previous" ? "previous" : "current";
      el.currencyPerformancePeriodOptions.innerHTML = `
        <button class="btn btn-secondary settings-picker-option ${activeAnchor === "current" ? "active" : ""}" type="button" data-currency-performance-quick-period="${period}" data-currency-performance-quick-anchor="current">
          ${copy.current}<span class="muted-small">${core.formatPeriodLabel(currentRange.dateFrom, currentRange.dateTo)}</span>
        </button>
        <button class="btn btn-secondary settings-picker-option ${activeAnchor === "previous" ? "active" : ""}" type="button" data-currency-performance-quick-period="${period}" data-currency-performance-quick-anchor="previous">
          ${copy.previous}<span class="muted-small">${core.formatPeriodLabel(previousRange.dateFrom, previousRange.dateTo)}</span>
        </button>
        <button class="btn btn-secondary settings-picker-option" type="button" data-currency-performance-quick-period="all_time" data-currency-performance-quick-anchor="current">
          Все время<span class="muted-small">Полная история результата</span>
        </button>
      `;
    }

    function openPopover(period, trigger) {
      if (!pickerUtils?.setPopoverOpen || !["30d", "90d", "365d"].includes(period)) {
        return;
      }
      renderPeriodOptions(period);
      pickerUtils.setPopoverOpen(el.currencyPerformancePeriodPopover, true, {
        owners: [trigger || el.currencyPerformancePeriodTabs].filter(Boolean),
        onClose: closePopover,
      });
    }

    function applyPeriod(period, anchor = "current") {
      state.currencyPerformancePeriod = period === "all_time"
        ? "all_time"
        : (["30d", "90d", "365d"].includes(period) ? period : "90d");
      state.currencyPerformancePeriodAnchor = state.currencyPerformancePeriod === "all_time"
        ? "current"
        : (anchor === "previous" ? "previous" : "current");
      syncPeriodTabs();
      closePopover();
      reload().catch((err) => core.setStatus(String(err)));
    }

    async function fetchHistory() {
      const range = getRange();
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

    function renderEmpty(message) {
      if (el.currencyPerformanceChart) {
        el.currencyPerformanceChart.innerHTML = `
          <text x="490" y="140" text-anchor="middle" class="analytics-chart-empty">${escapeHtml(message)}</text>
        `;
      }
    }

    function renderChart(history) {
      const chart = el.currencyPerformanceChart;
      if (!chart) {
        return;
      }
      const points = Array.isArray(history?.points) ? history.points : [];
      if (el.currencyPerformanceRangeLabel) {
        const scope = history?.currency ? core.formatCurrencyLabel(history.currency) : "Все валюты";
        const from = history?.date_from ? core.formatDateRu(history.date_from) : "—";
        const to = history?.date_to ? core.formatDateRu(history.date_to) : "—";
        const windowLabel = state.currencyPerformancePeriodAnchor === "previous" ? "Предыдущее окно" : "Текущее окно";
        el.currencyPerformanceRangeLabel.textContent = `${scope} · ${windowLabel}: ${from} - ${to}`;
      }
      const values = points.map((item) => Number(item.total_result_value || 0)).filter(Number.isFinite);
      if (points.length < 2 || values.length < 2) {
        renderEmpty("Недостаточно истории результата по валютным сделкам");
        return;
      }
      const width = 980;
      const height = 280;
      const padX = 56;
      const padY = 28;
      const minValue = Math.min(...values);
      const maxValue = Math.max(...values);
      const yRange = maxValue - minValue || 1;
      const xStep = (width - padX * 2) / Math.max(1, points.length - 1);
      const toX = (index) => padX + index * xStep;
      const toY = (value) => height - padY - ((value - minValue) / yRange) * (height - padY * 2);
      const last = points[points.length - 1];
      const middle = points[Math.floor(points.length / 2)];
      const lineColor = Number(last.total_result_value || 0) >= 0 ? "#62d39a" : "#ff7c98";
      const polyline = points.map((item, index) => `${toX(index)},${toY(Number(item.total_result_value || 0))}`).join(" ");
      const dots = points.map((item, index) => `<circle cx="${toX(index)}" cy="${toY(Number(item.total_result_value || 0))}" r="2.8" fill="rgba(255,255,255,0.82)"></circle>`).join("");
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
      chart.innerHTML = `
        <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" class="analytics-axis-line"></line>
        <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height - padY}" class="analytics-axis-line"></line>
        <polyline fill="none" stroke="${lineColor}" stroke-width="4" points="${polyline}"></polyline>
        ${dots}<circle cx="${toX(points.length - 1)}" cy="${toY(Number(last.total_result_value || 0))}" r="5" fill="${lineColor}"></circle>
        ${yMarks}${hitboxes}
        <text x="${padX}" y="${height - 8}" class="analytics-chart-empty">${escapeHtml(core.formatDateRu(points[0].point_date))}</text>
        <text x="${toX(Math.floor(points.length / 2))}" y="${height - 8}" text-anchor="middle" class="analytics-chart-empty">${escapeHtml(core.formatDateRu(middle.point_date))}</text>
        <text x="${width - padX}" y="${height - 8}" text-anchor="end" class="analytics-chart-empty">${escapeHtml(core.formatDateRu(last.point_date))}</text>
      `;
      const wrapper = chart.parentElement;
      let tooltip = wrapper?.querySelector(".analytics-chart-tooltip");
      if (wrapper && !tooltip) {
        tooltip = document.createElement("div");
        tooltip.className = "analytics-chart-tooltip hidden";
        wrapper.appendChild(tooltip);
      }
      chart.onmousemove = (event) => {
        const index = Number(event.target.closest(".trend-bucket")?.dataset.currencyPerformanceIndex ?? -1);
        const point = points[index];
        if (!point || !tooltip) {
          tooltip?.classList.add("hidden");
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
        const rect = chart.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        tooltip.style.left = `${Math.max(8, Math.min(rect.width - tooltipRect.width - 8, event.clientX - rect.left + 12))}px`;
        tooltip.style.top = `${Math.max(8, Math.min(rect.height - tooltipRect.height - 8, event.clientY - rect.top - tooltipRect.height - 10))}px`;
      };
      chart.onmouseleave = () => tooltip?.classList.add("hidden");
    }

    function bind() {
      el.currencyPerformancePeriodTabs?.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-currency-performance-period]");
        if (!button) {
          return;
        }
        const period = String(button.dataset.currencyPerformancePeriod || "90d");
        if (period === state.currencyPerformancePeriod && ["30d", "90d", "365d"].includes(period)) {
          openPopover(period, button);
          return;
        }
        applyPeriod(period, "current");
      });
      el.currencyPerformancePeriodOptions?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-currency-performance-quick-period][data-currency-performance-quick-anchor]");
        if (button) {
          applyPeriod(
            String(button.dataset.currencyPerformanceQuickPeriod || "90d"),
            String(button.dataset.currencyPerformanceQuickAnchor || "current"),
          );
        }
      });
    }

    bind();
    return { syncPeriodTabs, fetchHistory, renderChart };
  }

  window.App.registerRuntimeModule?.("currency-performance-factory", createCurrencyPerformanceFeature);
})();
