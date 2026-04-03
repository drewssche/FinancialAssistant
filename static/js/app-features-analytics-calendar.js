(() => {
  const { state, el, core } = window.App;
  const shared = window.App.analyticsShared || {};
  const CALENDAR_CACHE_TTL_MS = 20000;
  const escapeHtml = shared.escapeHtml || ((value) => String(value ?? ""));
  const describeResult = shared.describeResult || ((balanceRaw) => {
    const balance = Number(balanceRaw || 0);
    if (balance > 0) {
      return { label: "Профицит", tone: "positive", cardClass: "positive", amount: balance };
    }
    if (balance < 0) {
      return { label: "Дефицит", tone: "negative", cardClass: "negative", amount: Math.abs(balance) };
    }
    return { label: "Ноль", tone: "neutral", cardClass: "neutral", amount: 0 };
  });
  let calendarScrollUiBound = false;

  function syncCalendarScrollFade() {
    if (!el.analyticsCalendarScrollWrap) {
      return;
    }
    const node = el.analyticsCalendarScrollWrap;
    if ((state.analyticsCalendarView || "month") !== "month") {
      node.classList.remove("has-left-fade", "has-right-fade");
      return;
    }
    const maxScrollLeft = Math.max(0, node.scrollWidth - node.clientWidth);
    if (maxScrollLeft <= 4) {
      node.classList.remove("has-left-fade", "has-right-fade");
      return;
    }
    const scrollLeft = Math.max(0, node.scrollLeft || 0);
    const edgeTolerance = 2;
    node.classList.toggle("has-left-fade", scrollLeft > edgeTolerance);
    node.classList.toggle("has-right-fade", scrollLeft < maxScrollLeft - edgeTolerance);
  }

  function bindCalendarScrollUi() {
    if (calendarScrollUiBound || !el.analyticsCalendarScrollWrap) {
      return;
    }
    calendarScrollUiBound = true;
    el.analyticsCalendarScrollWrap.addEventListener("scroll", syncCalendarScrollFade, { passive: true });
    window.addEventListener("resize", syncCalendarScrollFade);
  }

  function parseMonthAnchor(rawValue) {
    const raw = String(rawValue || "").trim();
    const match = /^(\d{4})-(\d{2})$/.exec(raw);
    if (!match) {
      return null;
    }
    const year = Number(match[1]);
    const month = Number(match[2]);
    if (!Number.isFinite(year) || !Number.isFinite(month) || month < 1 || month > 12) {
      return null;
    }
    return new Date(Date.UTC(year, month - 1, 1));
  }

  function currentAnchorDate() {
    const parsed = parseMonthAnchor(state.analyticsMonthAnchor);
    if (parsed) {
      return parsed;
    }
    const now = new Date();
    return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  }

  function serializeMonthAnchor(anchorDate) {
    const year = anchorDate.getUTCFullYear();
    const month = String(anchorDate.getUTCMonth() + 1).padStart(2, "0");
    return `${year}-${month}`;
  }

  function getAnalyticsFeature() {
    return window.App.getRuntimeModule?.("analytics") || {};
  }

  function getLoadingSkeletons() {
    return window.App.getRuntimeModule?.("loading-skeletons") || {};
  }

  function getInlineRefreshState() {
    return window.App.getRuntimeModule?.("inline-refresh-state") || {};
  }

  function syncMonthLabelByView(dateObj, view) {
    if (!el.analyticsMonthLabel) {
      return;
    }
    if (view === "year") {
      el.analyticsMonthLabel.textContent = String(dateObj.getUTCFullYear());
      return;
    }
    const value = dateObj.toLocaleDateString("ru-RU", { month: "long", year: "numeric", timeZone: "UTC" });
    el.analyticsMonthLabel.textContent = value.charAt(0).toUpperCase() + value.slice(1);
  }

  function applyCalendarViewUi() {
    const view = state.analyticsCalendarView || "month";
    core.syncSegmentedActive(el.analyticsCalendarViewTabs, "analytics-calendar-view", view);
    if (el.analyticsPrevGridBtn) {
      el.analyticsPrevGridBtn.textContent = view === "year" ? "← Год" : "← Месяц";
    }
    if (el.analyticsNextGridBtn) {
      el.analyticsNextGridBtn.textContent = view === "year" ? "Год →" : "Месяц →";
    }
    if (el.analyticsTodayGridBtn) {
      el.analyticsTodayGridBtn.textContent = view === "year" ? "Текущий год" : "Текущий месяц";
    }
    if (el.analyticsMonthGridWrap) {
      el.analyticsMonthGridWrap.classList.toggle("hidden", view !== "month");
    }
    if (el.analyticsYearGridWrap) {
      el.analyticsYearGridWrap.classList.toggle("hidden", view !== "year");
    }
    if (el.analyticsGridMonthPickerWrap) {
      el.analyticsGridMonthPickerWrap.classList.toggle("hidden", view !== "month");
    } else if (el.analyticsGridMonthPicker) {
      el.analyticsGridMonthPicker.classList.toggle("hidden", view !== "month");
    }
    if (el.analyticsGridYearPicker) {
      el.analyticsGridYearPicker.classList.toggle("hidden", view !== "year");
    }
    syncGridPickers();
  }

  function syncGridPickers() {
    const anchor = currentAnchorDate();
    if (el.analyticsGridMonthPicker) {
      el.analyticsGridMonthPicker.value = serializeMonthAnchor(anchor);
    }
    if (el.analyticsGridYearPicker) {
      el.analyticsGridYearPicker.value = String(anchor.getUTCFullYear());
    }
  }

  function resolveCashflowTotals(item) {
    const operationIncome = Number(item?.income_total || 0);
    const operationExpense = Number(item?.expense_total || 0);
    const debtCashflow = Number(item?.debt_cashflow_total || 0);
    const fxCashflow = Number(item?.fx_cashflow_total || 0);
    return {
      incomeTotal: operationIncome + Math.max(0, debtCashflow) + Math.max(0, fxCashflow),
      expenseTotal: operationExpense + Math.abs(Math.min(0, debtCashflow)) + Math.abs(Math.min(0, fxCashflow)),
      resultTotal: Number(item?.cashflow_total ?? (operationIncome - operationExpense + debtCashflow + fxCashflow)),
      operationsCount: Number(item?.operations_count || 0),
      eventsCount: Number(item?.cashflow_events_count || item?.operations_count || 0),
      debtCashflow,
      debtEventsCount: Number(item?.debt_events_count || 0),
      fxCashflow,
      fxEventsCount: Number(item?.fx_events_count || 0),
    };
  }

  function renderCalendarTotals(data, view, currencyOverview = null) {
    if (!el.analyticsCalendarTotals || !el.analyticsCalendarTotalsSecondary) {
      return;
    }
    const isYear = view === "year";
    if (el.analyticsCalendarTotalsTitle) {
      el.analyticsCalendarTotalsTitle.textContent = isYear ? "Итоги года" : "Итоги месяца";
    }
    const rangeStart = isYear ? data.year_start : data.month_start;
    const rangeEnd = isYear ? data.year_end : data.month_end;
    if (el.analyticsCalendarTotalsRangeLabel && rangeStart && rangeEnd) {
      el.analyticsCalendarTotalsRangeLabel.textContent = `${core.formatDateRu(rangeStart)} - ${core.formatDateRu(rangeEnd)}`;
    }

    const cashflow = resolveCashflowTotals(data);
    const operatingResultValue = Number(data?.balance ?? 0);
    const result = describeResult(cashflow.resultTotal);
    const resultTone = result.cardClass || result.tone || "neutral";
    const operatingTone = operatingResultValue > 0 ? "income" : operatingResultValue < 0 ? "expense" : "neutral";
    const primary = [
      { label: "Приток", value: core.formatMoney(cashflow.incomeTotal), tone: "income" },
      { label: "Отток", value: core.formatMoney(cashflow.expenseTotal), tone: "expense" },
      { label: "Операционный результат", value: core.formatMoney(operatingResultValue), tone: operatingTone },
      { label: "Денежный поток", value: core.formatMoney(cashflow.resultTotal), tone: resultTone },
      { label: "События", value: String(cashflow.eventsCount || 0), tone: "neutral" },
    ];
    el.analyticsCalendarTotals.innerHTML = primary
      .map(
        (item) => `
      <article class="analytics-kpi-card analytics-kpi-${item.tone}">
        <div class="muted-small">${escapeHtml(item.label)}</div>
        <strong>${escapeHtml(item.value)}</strong>
      </article>
    `,
      )
      .join("");

    const chips = [
      `<span class="analytics-kpi-chip analytics-kpi-chip-${result.tone}">Денежный поток: ${escapeHtml(core.formatMoney(cashflow.resultTotal))}</span>`,
    ];
    if (cashflow.debtEventsCount > 0) {
      const debtResult = describeResult(cashflow.debtCashflow);
      chips.push(
        `<span class="analytics-kpi-chip analytics-kpi-chip-${debtResult.tone}">Долги в потоке: ${escapeHtml(core.formatMoney(cashflow.debtCashflow))} · ${escapeHtml(String(cashflow.debtEventsCount))} событ.</span>`,
      );
    }
    if (cashflow.fxEventsCount > 0) {
      const fxResult = describeResult(cashflow.fxCashflow);
      chips.push(
        `<span class="analytics-kpi-chip analytics-kpi-chip-${fxResult.tone}">Валюта в потоке: ${escapeHtml(core.formatMoney(cashflow.fxCashflow))} · ${escapeHtml(String(cashflow.fxEventsCount))} событ.</span>`,
      );
    }
    el.analyticsCalendarTotalsSecondary.innerHTML = chips.join("");
  }

  function renderAnalyticsCalendarMonth(data) {
    if (!el.analyticsCalendarBody) {
      return;
    }
    const anchor = parseMonthAnchor(data.month) || currentAnchorDate();
    syncMonthLabelByView(anchor, "month");
    el.analyticsCalendarBody.innerHTML = "";
    for (const week of data.weeks || []) {
      const tr = document.createElement("tr");
      const weekCashflow = resolveCashflowTotals(week);
      const weekResult = describeResult(weekCashflow.resultTotal);
      for (const day of week.days || []) {
        const cell = document.createElement("td");
        cell.className = `analytics-day-cell ${day.in_month ? "" : "analytics-day-cell-out"}`.trim();
        if (!day.in_month) {
          cell.innerHTML = "<span class='muted-small'>·</span>";
        } else {
          const cashflow = resolveCashflowTotals(day);
          const markerBits = [];
          if (cashflow.debtEventsCount > 0) {
            markerBits.push(`Долг ${core.formatMoney(cashflow.debtCashflow)}`);
          }
          if (cashflow.fxEventsCount > 0) {
            markerBits.push(`FX ${core.formatMoney(cashflow.fxCashflow)}`);
          }
          const result = describeResult(cashflow.resultTotal);
          const operationalExpense = Number(day?.expense_total || 0);
          const titleBits = [
            core.formatDateRu(day.date),
            `Приток ${core.formatMoney(cashflow.incomeTotal)}`,
            `Отток ${core.formatMoney(cashflow.expenseTotal)}`,
            `Операционные траты ${core.formatMoney(operationalExpense)}`,
            `Денежный поток ${core.formatMoney(cashflow.resultTotal)}`,
            `${cashflow.eventsCount} событ.`,
          ];
          if (markerBits.length) {
            titleBits.push(markerBits.join(" · "));
          }
          const dayTitle = titleBits.join(" | ");
          cell.innerHTML = `
            <button
              type="button"
              class="analytics-day-btn"
              data-analytics-date="${day.date}"
              title="${escapeHtml(dayTitle)}"
              aria-label="${escapeHtml(dayTitle)}"
            >
              <div class="analytics-day-date">${new Date(`${day.date}T00:00:00`).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" })}</div>
              <div class="analytics-day-money analytics-income">+${core.formatMoney(cashflow.incomeTotal)}</div>
              <div class="analytics-day-money analytics-expense">-${core.formatMoney(cashflow.expenseTotal)}</div>
              <div class="muted-small analytics-day-meta">Опер. траты: ${core.formatMoney(operationalExpense)}</div>
              <div class="muted-small">${cashflow.eventsCount} событ.</div>
            </button>
          `;
        }
        tr.appendChild(cell);
      }
      tr.innerHTML += `
        <td class="analytics-week-total analytics-income">${core.formatMoney(weekCashflow.incomeTotal)}</td>
        <td class="analytics-week-total analytics-expense">${core.formatMoney(weekCashflow.expenseTotal)}</td>
        <td class="analytics-week-total">${weekCashflow.eventsCount}</td>
        <td class="analytics-week-total analytics-expense">${core.formatMoney(Number(week?.expense_total || 0))}</td>
        <td class="analytics-week-total">
          <span class="analytics-kpi-chip analytics-kpi-chip-${weekResult.tone}">
            Денежный поток: ${core.formatMoney(weekCashflow.resultTotal)}
          </span>
        </td>
      `;
      el.analyticsCalendarBody.appendChild(tr);
    }
    window.requestAnimationFrame(syncCalendarScrollFade);
  }

  function renderAnalyticsCalendarYear(data) {
    if (!el.analyticsYearGrid) {
      return;
    }
    syncMonthLabelByView(new Date(Date.UTC(Number(data.year || 0), 0, 1)), "year");
    const months = Array.isArray(data.months) ? data.months : [];
    el.analyticsYearGrid.innerHTML = months
      .map((item) => {
        const cashflow = resolveCashflowTotals(item);
        const result = describeResult(cashflow.resultTotal);
        const resultTone = result.cardClass || result.tone || "neutral";
        const monthDate = parseMonthAnchor(item.month);
        const label = monthDate
          ? monthDate.toLocaleDateString("ru-RU", { month: "short", year: "numeric", timeZone: "UTC" })
          : item.month;
        return `
          <article class="analytics-year-card" data-analytics-month-anchor="${item.month}">
            <div class="analytics-insight-head">
              <strong>${label}</strong>
              <span class="muted-small analytics-ops">${cashflow.eventsCount} событ.</span>
            </div>
            <div class="muted-small analytics-income">Приток: ${core.formatMoney(cashflow.incomeTotal)}</div>
            <div class="muted-small analytics-expense">Отток: ${core.formatMoney(cashflow.expenseTotal)}</div>
            <div class="muted-small analytics-${resultTone}">Денежный поток: ${core.formatMoney(cashflow.resultTotal)}</div>
          </article>
        `;
      })
      .join("");
    window.requestAnimationFrame(syncCalendarScrollFade);
  }

  async function loadAnalyticsCalendar(options = {}) {
    bindCalendarScrollUi();
    const force = options.force === true;
    if (!state.analyticsMonthAnchor) {
      const now = new Date();
      state.analyticsMonthAnchor = serializeMonthAnchor(new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1)));
    }
    const anchor = currentAnchorDate();
    const month = state.analyticsMonthAnchor;
    const view = state.analyticsCalendarView || "month";
    applyCalendarViewUi();
    if (!state.analyticsCalendarHydrated && state.activeSection === "analytics" && (state.analyticsTab || "calendar") === "calendar") {
      getLoadingSkeletons().renderAnalyticsCalendarSkeleton?.();
    }
    const refreshState = getInlineRefreshState();
    const shouldRefreshInline = state.analyticsCalendarHydrated;
    if (shouldRefreshInline) {
      refreshState.begin?.(el.analyticsCalendarPanel, "Обновляется");
    }

    try {
      if (view === "year") {
        const year = anchor.getUTCFullYear();
        const cacheKey = `analytics:calendar-year:${year}`;
        const currencyCacheKey = "analytics:calendar:currency-summary";
        if (!force) {
          const cached = core.getUiRequestCache(cacheKey, CALENDAR_CACHE_TTL_MS);
          const cachedCurrency = core.getUiRequestCache(currencyCacheKey, CALENDAR_CACHE_TTL_MS);
          if (cached) {
            renderAnalyticsCalendarYear(cached);
            renderCalendarTotals(cached, "year", cachedCurrency || null);
            state.analyticsCalendarHydrated = true;
            window.requestAnimationFrame(syncCalendarScrollFade);
            return cached;
          }
        }
        const [data, currencyOverview] = await Promise.all([
          core.requestJson(`/api/v1/dashboard/analytics/calendar/year?year=${year}`, {
            headers: core.authHeaders(),
          }),
          core.requestJson("/api/v1/currency/overview?trades_limit=10", {
            headers: core.authHeaders(),
          }).catch(() => null),
        ]);
        core.setUiRequestCache(cacheKey, data);
        core.setUiRequestCache(currencyCacheKey, currencyOverview);
        renderAnalyticsCalendarYear(data);
        renderCalendarTotals(data, "year", currencyOverview);
        state.analyticsCalendarHydrated = true;
        window.requestAnimationFrame(syncCalendarScrollFade);
        return data;
      }

      const cacheKey = `analytics:calendar:month=${month}`;
      const currencyCacheKey = "analytics:calendar:currency-summary";
      if (!force) {
        const cached = core.getUiRequestCache(cacheKey, CALENDAR_CACHE_TTL_MS);
        const cachedCurrency = core.getUiRequestCache(currencyCacheKey, CALENDAR_CACHE_TTL_MS);
        if (cached) {
          renderAnalyticsCalendarMonth(cached);
          renderCalendarTotals(cached, "month", cachedCurrency || null);
          state.analyticsCalendarHydrated = true;
          window.requestAnimationFrame(syncCalendarScrollFade);
          return cached;
        }
      }
      const [data, currencyOverview] = await Promise.all([
        core.requestJson(`/api/v1/dashboard/analytics/calendar?month=${encodeURIComponent(month)}`, {
          headers: core.authHeaders(),
        }),
        core.requestJson("/api/v1/currency/overview?trades_limit=10", {
          headers: core.authHeaders(),
        }).catch(() => null),
      ]);
      core.setUiRequestCache(cacheKey, data);
      core.setUiRequestCache(currencyCacheKey, currencyOverview);
      renderAnalyticsCalendarMonth(data);
      renderCalendarTotals(data, "month", currencyOverview);
      state.analyticsCalendarHydrated = true;
      window.requestAnimationFrame(syncCalendarScrollFade);
      return data;
    } finally {
      if (shouldRefreshInline) {
        refreshState.end?.(el.analyticsCalendarPanel);
      }
    }
  }

  async function shiftAnalyticsMonth(step) {
    const current = currentAnchorDate();
    if ((state.analyticsCalendarView || "month") === "year") {
      current.setUTCFullYear(current.getUTCFullYear() + step, 0, 1);
    } else {
      current.setUTCMonth(current.getUTCMonth() + step, 1);
    }
    state.analyticsMonthAnchor = serializeMonthAnchor(current);
    const analyticsFeature = getAnalyticsFeature();
    if (analyticsFeature.loadAnalyticsSection) {
      await analyticsFeature.loadAnalyticsSection({ force: true });
    }
  }

  async function resetAnalyticsMonth() {
    const now = new Date();
    state.analyticsMonthAnchor = serializeMonthAnchor(new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1)));
    const analyticsFeature = getAnalyticsFeature();
    if (analyticsFeature.loadAnalyticsSection) {
      await analyticsFeature.loadAnalyticsSection({ force: true });
    }
  }

  async function openAnalyticsMonth(anchorMonth) {
    const parsed = parseMonthAnchor(anchorMonth);
    if (!parsed) {
      return;
    }
    state.analyticsMonthAnchor = serializeMonthAnchor(parsed);
    state.analyticsCalendarView = "month";
    const analyticsFeature = getAnalyticsFeature();
    if (analyticsFeature.loadAnalyticsSection) {
      await analyticsFeature.loadAnalyticsSection({ force: true });
    }
  }

  async function setAnalyticsCalendarView(view) {
    const allowed = new Set(["month", "year"]);
    state.analyticsCalendarView = allowed.has(view) ? view : "month";
    applyCalendarViewUi();
    await loadAnalyticsCalendar({ force: true });
  }

  async function setAnalyticsGridMonthAnchor(monthValue) {
    const parsed = parseMonthAnchor(monthValue);
    if (!parsed) {
      return;
    }
    state.analyticsMonthAnchor = serializeMonthAnchor(parsed);
    syncGridPickers();
    syncMonthLabelByView(parsed, "month");
    await loadAnalyticsCalendar({ force: true });
  }

  async function setAnalyticsGridYearAnchor(yearValue) {
    const year = Number(yearValue || 0);
    if (!Number.isFinite(year) || year < 1970 || year > 2100) {
      return;
    }
    state.analyticsMonthAnchor = `${year}-01`;
    if (state.analyticsCalendarView !== "year") {
      state.analyticsCalendarView = "year";
      applyCalendarViewUi();
    }
    syncGridPickers();
    syncMonthLabelByView(new Date(Date.UTC(year, 0, 1)), "year");
    await loadAnalyticsCalendar({ force: true });
  }

  const api = {
    parseMonthAnchor,
    currentAnchorDate,
    serializeMonthAnchor,
    applyCalendarViewUi,
    loadAnalyticsCalendar,
    shiftAnalyticsMonth,
    resetAnalyticsMonth,
    openAnalyticsMonth,
    setAnalyticsCalendarView,
    setAnalyticsGridMonthAnchor,
    setAnalyticsGridYearAnchor,
    syncCalendarScrollFade,
  };

  window.App.registerRuntimeModule?.("analytics-calendar-module", api);
})();
