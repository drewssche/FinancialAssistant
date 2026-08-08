(() => {
  const { state, el, core } = window.App;
  const operationModal = window.App.getRuntimeModule?.("operation-modal");
  const debtUi = core.debtUi;
  const getCategoryMetaById = operationModal.getCategoryMetaById;
  let dashboardLoadSeq = 0;
  let dashboardLoadController = null;
  let dashboardOptionalLoadSeq = 0;
  let dashboardOptionalLoadController = null;
  let dashboardOptionalLoadPromise = null;
  let dashboardPlansLoadPromise = null;

  function getPlansFeature() {
    return window.App.getRuntimeModule?.("plans");
  }

  function getDashboardData() {
    return window.App.getRuntimeModule?.("dashboard-data");
  }

  function getLoadingSkeletons() {
    return window.App.getRuntimeModule?.("loading-skeletons") || {};
  }

  function renderDashboardRecommendations(items) {
    if (!el.dashboardRecommendationsList) {
      return;
    }
    const list = Array.isArray(items) ? items : [];
    state.dashboardRecommendations = list;
    if (!list.length) {
      el.dashboardRecommendationsList.innerHTML = `
        <div class="muted-small">Рекомендаций пока нет. Включи их в карточке нужной позиции каталога.</div>
      `;
      return;
    }
    el.dashboardRecommendationsList.innerHTML = list.map((item) => {
      const daysUntil = Number(item.days_until || 0);
      const dueLabel = item.status === "overdue"
        ? `Просрочено на ${Math.abs(daysUntil)} дн.`
        : item.status === "due"
          ? "Пора купить сегодня"
          : `Через ${daysUntil} дн.`;
      const source = item.shop_name || "Без источника";
      const price = Number(item.latest_unit_price || 0) > 0
        ? core.formatMoney(item.latest_unit_price)
        : "Цена не указана";
      return `
        <article class="recommendation-card" data-recommendation-template-id="${Number(item.template_id)}">
          <div class="recommendation-card-head">
            <div class="recommendation-card-copy">
              <strong>${core.escapeHtml(item.name || "Позиция")}</strong>
              <span class="muted-small">${core.escapeHtml(source)} · ${price}</span>
            </div>
            <strong class="recommendation-due-${item.status}">${dueLabel}</strong>
          </div>
          <div class="muted-small">${core.escapeHtml(item.explanation || "")}</div>
          <div class="recommendation-card-actions">
            <button class="btn btn-primary btn-xs" type="button" data-recommendation-action="receipt">В чек</button>
            <button class="btn btn-secondary btn-xs" type="button" data-recommendation-action="plan">В план</button>
            <button class="btn btn-secondary btn-xs" type="button" data-recommendation-action="snooze">+7 дней</button>
            <button class="btn btn-secondary btn-xs" type="button" data-recommendation-action="settings">Настроить</button>
            <button class="btn btn-secondary btn-xs" type="button" data-recommendation-action="disable">Отключить</button>
          </div>
        </article>
      `;
    }).join("");
  }

  async function loadDashboardRecommendations({ signal } = {}) {
    const items = await core.requestJson("/api/v1/operations/item-recommendations?limit=12", {
      headers: core.authHeaders(),
      signal,
    });
    renderDashboardRecommendations(items);
    return items;
  }

  function getInlineRefreshState() {
    return window.App.getRuntimeModule?.("inline-refresh-state") || {};
  }

  function getTrackedCurrencies() {
    const raw = state.preferences?.data?.currency?.tracked_currencies;
    if (!Array.isArray(raw) || !raw.length) {
      return ["USD", "EUR"];
    }
    return raw.map((item) => String(item || "").toUpperCase()).filter(Boolean);
  }

  function getResultPresentation(rawValue) {
    const value = Number(rawValue || 0);
    if (value > 0) {
      return { cardClass: "analytics-kpi-income", label: "Прибыль" };
    }
    if (value < 0) {
      return { cardClass: "analytics-kpi-expense", label: "Убыток" };
    }
    return { cardClass: "analytics-kpi-neutral", label: "Результат" };
  }

  function dueBadgeLabel(stateValue, dueDate) {
    if (stateValue === "overdue") {
      return "Просрочено";
    }
    if (stateValue === "soon") {
      return core.formatDateRu(dueDate);
    }
    if (stateValue === "future" && dueDate) {
      return core.formatDateRu(dueDate);
    }
    return "Без срока";
  }

  function duePriorityRank(stateValue) {
    if (stateValue === "overdue") {
      return 0;
    }
    if (stateValue === "soon") {
      return 1;
    }
    if (stateValue === "future") {
      return 2;
    }
    if (stateValue === "none") {
      return 3;
    }
    return 4;
  }

  function renderDashboardCurrencySummary(summary) {
    const currencyPrefs = state.preferences?.data?.currency || {};
    const unrealizedTone = getResultPresentation(summary.currency_unrealized_result_value || summary.currency_result_value || 0);
    const realizedTone = getResultPresentation(summary.currency_realized_result_value || 0);
    const totalTone = getResultPresentation(summary.currency_total_result_value || summary.currency_result_value || 0);
    if (el.dashboardCurrencyPanel) {
      el.dashboardCurrencyPanel.classList.toggle("hidden", currencyPrefs.show_dashboard_kpi === false);
    }
    if (el.dashboardCurrencyKpiGrid) {
      el.dashboardCurrencyKpiGrid.innerHTML = "";
      el.dashboardCurrencyKpiGrid.classList.add("hidden");
    }
    if (el.dashboardCurrencyBalances) {
      const positions = Array.isArray(summary.tracked_currency_positions) ? summary.tracked_currency_positions : [];
      const positionsByCurrency = new Map(positions.map((item) => [core.normalizeCurrencyCode?.(item.currency, "") || "", item]));
      const trackedCurrencies = getTrackedCurrencies();
      const baseCurrency = core.getCurrencyConfig?.().code || "BYN";
      const baseCurrencySymbol = core.formatCurrencySymbol?.(baseCurrency) || baseCurrency;
      const portfolioCurrentValue = Number(summary.currency_current_value || 0);
      const portfolioBookValue = Number(summary.currency_book_value || 0);
      const portfolioTotalResultValue = Number(summary.currency_total_result_value || summary.currency_result_value || 0);
      const hasPortfolioActivity = (
        Math.abs(portfolioCurrentValue) > 0.000001
        || Math.abs(portfolioBookValue) > 0.000001
        || Math.abs(portfolioTotalResultValue) > 0.000001
        || Number(summary.active_currency_positions || 0) > 0
        || positions.some((item) => Math.abs(Number(item?.quantity || 0)) > 0.000001 || Math.abs(Number(item?.current_value || 0)) > 0.000001)
      );
      el.dashboardCurrencyBalances.classList.toggle("hidden", !hasPortfolioActivity);
      if (!hasPortfolioActivity) {
        el.dashboardCurrencyBalances.innerHTML = "";
      } else {
        const portfolioCard = `
          <article class="currency-balance-card">
            <div class="muted-small">Оценка валютного портфеля</div>
            <strong>${core.formatMoney(portfolioCurrentValue, { currency: baseCurrency })}</strong>
            <div class="currency-balance-secondary">Вложено ${core.formatMoney(portfolioBookValue, { currency: baseCurrency })} · итоговый результат ${core.formatMoney(portfolioTotalResultValue, { currency: baseCurrency })}</div>
          </article>
        `;
        const positionCards = trackedCurrencies.map((currency) => {
          const item = positionsByCurrency.get(currency) || null;
          const currencyLabel = core.formatCurrencyLabel(currency);
          const quantity = Number(item?.quantity || 0);
          const currentRate = Number(item?.current_rate || 0);
          const currentValue = Number(item?.current_value || 0);
          if (Math.abs(quantity) <= 0.000001 && Math.abs(currentValue) <= 0.000001) {
            return "";
          }
          const currentRateDate = item?.current_rate_date ? core.formatDateRu(item.current_rate_date) : "";
          const currentRateLabel = currentRate > 0
            ? `${core.formatRateDisplay?.(currentRate, 4, 6)} ${baseCurrencySymbol}${currentRateDate ? ` · ${currentRateDate}` : ""}`
            : "Курс не задан";
          const currentValueLabel = currentValue > 0
            ? `≈ ${core.formatMoney(currentValue, { currency: baseCurrency })}`
            : `≈ ${core.formatMoney(0, { currency: baseCurrency })}`;
          return `
            <article class="currency-balance-card">
              <div class="muted-small">${core.escapeHtml ? core.escapeHtml(currencyLabel) : currencyLabel}</div>
              <strong>${core.formatAmount(quantity)} ${core.escapeHtml ? core.escapeHtml(currency) : currency}</strong>
              <div class="currency-balance-secondary">Курс: ${currentRateLabel}</div>
              <div class="currency-balance-secondary">${currentValueLabel} по текущему курсу</div>
            </article>
          `;
        }).filter(Boolean);
        el.dashboardCurrencyBalances.innerHTML = [portfolioCard, ...positionCards].join("");
      }
    }
    if (el.dashboardCurrencyPositions) {
      const positions = Array.isArray(summary.tracked_currency_positions) ? summary.tracked_currency_positions : [];
      const hasPortfolioActivity = (
        Math.abs(Number(summary.currency_current_value || 0)) > 0.000001
        || Math.abs(Number(summary.currency_book_value || 0)) > 0.000001
        || Math.abs(Number(summary.currency_total_result_value || summary.currency_result_value || 0)) > 0.000001
        || Number(summary.active_currency_positions || 0) > 0
        || positions.some((item) => Math.abs(Number(item?.quantity || 0)) > 0.000001 || Math.abs(Number(item?.current_value || 0)) > 0.000001)
      );
      el.dashboardCurrencyPositions.classList.toggle("hidden", !hasPortfolioActivity);
      if (!hasPortfolioActivity) {
        el.dashboardCurrencyPositions.innerHTML = "";
        return;
      }
      const summaryChips = [
        `<span class="analytics-kpi-chip analytics-kpi-chip-neutral">Вложено: ${core.formatMoney(summary.currency_book_value || 0)}</span>`,
        `<span class="analytics-kpi-chip analytics-kpi-chip-${unrealizedTone.chipClass}">Нереализованный: ${core.formatMoney(summary.currency_unrealized_result_value || summary.currency_result_value || 0)}</span>`,
        `<span class="analytics-kpi-chip analytics-kpi-chip-${realizedTone.chipClass}">Реализованный: ${core.formatMoney(summary.currency_realized_result_value || 0)}</span>`,
        `<span class="analytics-kpi-chip analytics-kpi-chip-${totalTone.chipClass}">Итог: ${core.formatMoney(summary.currency_total_result_value || summary.currency_result_value || 0)}</span>`,
        `<span class="analytics-kpi-chip analytics-kpi-chip-neutral">Открытых позиций: ${String(summary.active_currency_positions || 0)}</span>`,
      ];
      el.dashboardCurrencyPositions.innerHTML = summaryChips.join("");
    }
  }

  function formatSignedRate(value, digits = 4) {
    const numeric = Number(value || 0);
    const prefix = numeric > 0 ? "+" : numeric < 0 ? "-" : "";
    return `${prefix}${Math.abs(numeric).toFixed(digits)}`;
  }

  function formatSignedPercent(value) {
    const numeric = Number(value || 0);
    const prefix = numeric > 0 ? "+" : numeric < 0 ? "-" : "";
    return `${prefix}${Math.abs(numeric).toFixed(2)}%`;
  }

  function renderDashboardCurrencyRates(currentRates = [], trackedCurrencies = []) {
    if (!el.dashboardCurrencyRates) {
      return;
    }
    const tracked = Array.isArray(trackedCurrencies) ? trackedCurrencies : [];
    const normalizedTracked = tracked
      .map((item) => core.normalizeCurrencyCode?.(item, "") || "")
      .filter(Boolean);
    const rows = Array.isArray(currentRates) ? currentRates : [];
    const rowsByCurrency = new Map(rows.map((item) => [core.normalizeCurrencyCode?.(item.currency, "") || "", item]));
    const visibleCurrencies = normalizedTracked.length
      ? normalizedTracked
      : Array.from(rowsByCurrency.keys());
    if (!visibleCurrencies.length) {
      el.dashboardCurrencyRates.innerHTML = `
        <article class="dashboard-currency-rate-card dashboard-currency-rate-card-empty">
          <strong>Курсы пока не заданы</strong>
          <span class="muted-small">Добавь отслеживаемую валюту и хотя бы один snapshot курса</span>
        </article>
      `;
      return;
    }
    el.dashboardCurrencyRates.innerHTML = visibleCurrencies.map((currency) => {
      const item = rowsByCurrency.get(currency);
      if (!item) {
        const currencyLabel = core.formatCurrencyLabel(currency);
        return `
          <article class="dashboard-currency-rate-card dashboard-currency-rate-card-empty">
            <div class="dashboard-currency-rate-head">
              <strong>${core.escapeHtml ? core.escapeHtml(currencyLabel) : currencyLabel}</strong>
              <span class="dashboard-currency-rate-badge dashboard-currency-rate-badge-empty">Нет курса</span>
            </div>
            <div class="dashboard-currency-rate-value">—</div>
            <div class="dashboard-currency-rate-meta muted-small">Сохрани текущий курс в разделе Валюта</div>
            <div class="dashboard-currency-rate-actions">
              <button class="btn btn-secondary btn-xs" type="button" data-dashboard-refresh-currency="${currency}">Обновить</button>
            </div>
          </article>
        `;
      }
      const deltaValue = Number(item.change_value || 0);
      const hasDelta = item.change_value !== null && item.change_value !== undefined;
      const rateDateIso = item.rate_date ? String(item.rate_date) : "";
      const isStale = Boolean(rateDateIso) && rateDateIso < core.getTodayIso();
      const deltaTone = deltaValue > 0 ? "positive" : deltaValue < 0 ? "negative" : "neutral";
      const rateDate = item.rate_date ? core.formatDateRu(item.rate_date) : "без даты";
      const source = item.source ? String(item.source).trim() : "manual";
      const itemCurrency = core.normalizeCurrencyCode?.(item.currency, "") || "";
      const currencyLabel = core.formatCurrencyLabel(itemCurrency);
      const baseCurrencySymbol = core.formatCurrencySymbol?.(core.getCurrencyConfig?.().code || "BYN") || "BYN";
      return `
        <article class="dashboard-currency-rate-card">
          <div class="dashboard-currency-rate-head">
            <strong>${core.escapeHtml ? core.escapeHtml(currencyLabel) : currencyLabel}</strong>
            <span class="dashboard-currency-rate-badge dashboard-currency-rate-badge-${deltaTone}">
              ${isStale ? "последний" : (hasDelta ? formatSignedRate(item.change_value) : "новый")}
            </span>
          </div>
          <div class="dashboard-currency-rate-value-row">
            <div class="dashboard-currency-rate-value">${core.formatRateDisplay?.(item.rate || 0, 4, 6)}</div>
            <div class="dashboard-currency-rate-delta dashboard-currency-rate-delta-${deltaTone}">
              ${hasDelta ? `${formatSignedRate(item.change_value)} · ${formatSignedPercent(item.change_pct || 0)}` : "—"}
            </div>
          </div>
          <div class="dashboard-currency-rate-meta muted-small">${isStale ? `Последний доступный курс к ${baseCurrencySymbol}` : `Официальный курс к ${baseCurrencySymbol}`} · ${rateDate}</div>
          <div class="dashboard-currency-rate-delta-caption muted-small">${hasDelta ? (isStale ? "К предыдущему курсу" : "За день") : "Нет предыдущего курса для сравнения"}</div>
          <div class="dashboard-currency-rate-source muted-small">Источник: ${core.escapeHtml ? core.escapeHtml(source) : source}</div>
          <div class="dashboard-currency-rate-actions">
            <button class="btn btn-secondary btn-xs" type="button" data-dashboard-refresh-currency="${item.currency}">Обновить</button>
          </div>
        </article>
      `;
    }).join("");
  }

  async function refreshDashboardCurrencyRates(currency = "") {
    const refreshState = getInlineRefreshState();
    const query = currency ? `?currency=${encodeURIComponent(currency)}` : "";
    await refreshState.withRefresh?.(el.dashboardCurrencyPanel, async () => {
      await core.requestJson(`/api/v1/currency/rates/refresh${query}`, {
        method: "POST",
        headers: core.authHeaders(),
      });
      core.invalidateUiRequestCache?.("dashboard:summary");
      await loadDashboard();
      if (state.activeSection === "currency") {
        window.App.getRuntimeModule?.("currency")?.loadCurrencySection?.({ force: true }).catch(() => {});
      }
      if (state.activeSection === "analytics" && state.analyticsTab === "currency") {
        window.App.getRuntimeModule?.("analytics-currency-module")?.loadAnalyticsCurrency?.({ force: true }).catch(() => {});
      }
    }, currency ? `Обновляется ${currency}` : "Обновляются курсы");
  }

  function formatDateTimeRu(value) {
    if (!value) {
      return "";
    }
    try {
      const date = value instanceof Date ? value : new Date(value);
      if (Number.isNaN(date.getTime())) {
        return "";
      }
      return new Intl.DateTimeFormat("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      }).format(date);
    } catch {
      return "";
    }
  }

  function reportOptionalDashboardPanelFailure(panelName, err) {
    console.warn("Optional dashboard panel failed", {
      panel: panelName,
      reason: err,
    });
  }

  function setDashboardPanelState(panel, loadState = "ready") {
    if (!panel) return;
    panel.dataset.loadState = loadState;
    panel.classList.toggle("is-stale", loadState === "stale");
    panel.querySelector(":scope > .panel-stale-indicator")?.remove();
    if (loadState === "stale") {
      const indicator = document.createElement("div");
      indicator.className = "panel-stale-indicator";
      indicator.setAttribute("role", "status");
      indicator.textContent = "Показаны последние данные · обновление не удалось";
      panel.appendChild(indicator);
    }
  }

  function endDashboardOptionalRefreshes({ currency = false, debts = false, plans = false } = {}) {
    const refreshState = getInlineRefreshState();
    if (currency && el.dashboardCurrencyPanel) {
      refreshState.end?.(el.dashboardCurrencyPanel);
    }
    if (debts && el.dashboardDebtsPanel) {
      refreshState.end?.(el.dashboardDebtsPanel);
    }
    if (plans && el.dashboardPlansPanel) {
      refreshState.end?.(el.dashboardPlansPanel);
    }
  }

  function setDebtKpiTone(node, tone = "neutral") {
    if (!node) return;
    node.classList.toggle("is-positive", tone === "positive");
    node.classList.toggle("is-negative", tone === "negative");
  }

  function renderDebtKpiTones({ lend = 0, borrow = 0, net = 0 } = {}) {
    const epsilon = 0.000001;
    setDebtKpiTone(el.dashboardDebtLendKpi, Number(lend) > epsilon ? "positive" : "neutral");
    setDebtKpiTone(el.dashboardDebtBorrowKpi, Number(borrow) > epsilon ? "negative" : "neutral");
    setDebtKpiTone(el.dashboardDebtNetKpi, Number(net) > epsilon ? "positive" : Number(net) < -epsilon ? "negative" : "neutral");
  }

  function dashboardPanelError(message) {
    return `<div class="panel-load-state panel-load-state-error" role="alert">
      <span>${core.escapeHtml?.(message) || message}</span>
      <button class="btn btn-secondary btn-xs" type="button" data-dashboard-retry>Повторить</button>
    </div>`;
  }

  function renderDashboardLoadFailure(err, { preserveExisting = false } = {}) {
    const message = core.errorMessage ? core.errorMessage(err) : String(err || "Ошибка загрузки");
    if (preserveExisting) {
      setDashboardPanelState(el.dashboardCurrencyPanel, "stale");
      setDashboardPanelState(el.dashboardDebtsPanel, "stale");
      getLoadingSkeletons().clearDashboardAnalyticsSkeletonState?.();
      return;
    }
    if (el.dashboardCurrencyBalances) {
      el.dashboardCurrencyBalances.innerHTML = `<div class="muted-small">Не удалось загрузить валютный портфель: ${core.escapeHtml ? core.escapeHtml(message) : message}</div>`;
    }
    if (el.dashboardCurrencyRates) {
      el.dashboardCurrencyRates.innerHTML = "";
    }
    if (el.dashboardCurrencyPositions) {
      el.dashboardCurrencyPositions.innerHTML = "";
    }
    if (el.dashboardPlansList) {
      el.dashboardPlansList.innerHTML = dashboardPanelError("Не удалось загрузить ближайшие планы");
    }
    if (el.dashboardPlansKpi) {
      el.dashboardPlansKpi.innerHTML = "";
    }
    if (el.dashboardDebtsList) {
      el.dashboardDebtsList.innerHTML = dashboardPanelError("Не удалось загрузить активные долги");
    }
    if (el.debtLendTotal) {
      el.debtLendTotal.textContent = core.formatMoney(0);
    }
    if (el.debtBorrowTotal) {
      el.debtBorrowTotal.textContent = core.formatMoney(0);
    }
    if (el.debtNetTotal) {
      el.debtNetTotal.textContent = core.formatMoney(0);
    }
    renderDebtKpiTones();
    getLoadingSkeletons().clearDashboardAnalyticsSkeletonState?.();
  }


  async function loadDashboard() {
    if (dashboardLoadController) {
      dashboardLoadController.abort();
    }
    dashboardLoadController = new AbortController();
    const requestSignal = dashboardLoadController.signal;
    const loadSeq = ++dashboardLoadSeq;
    const isCurrentDashboardLoad = () => !requestSignal.aborted && loadSeq === dashboardLoadSeq && state.activeSection === "dashboard";
    const startedOnDashboard = state.activeSection === "dashboard";
    const skeletons = getLoadingSkeletons();
    const refreshState = getInlineRefreshState();
    const ui = core.getUiSettings ? core.getUiSettings() : null;
    if (el.dashboardAnalyticsPanel && ui) {
      el.dashboardAnalyticsPanel.classList.toggle("hidden", ui.showDashboardAnalytics === false);
    }
    if (el.dashboardStructurePanel && ui) {
      el.dashboardStructurePanel.classList.toggle("hidden", ui.showDashboardAnalytics === false);
    }
    if (el.dashboardPlansPanel && ui) {
      el.dashboardPlansPanel.classList.toggle("hidden", ui.showDashboardOperations === false);
    }
    if (el.dashboardDebtsPanel && ui) {
      el.dashboardDebtsPanel.classList.toggle("hidden", ui.showDashboardDebts === false);
    }
    if (startedOnDashboard && !state.dashboardDebtSummaryLoaded) {
      skeletons.renderDashboardDebtsSkeleton?.();
    }
    if (startedOnDashboard && !state.dashboardPlansHydrated) {
      skeletons.renderDashboardPlansSkeleton?.();
    }
    if (startedOnDashboard && !state.dashboardCurrencyHydrated) {
      skeletons.renderDashboardCurrencySkeleton?.();
    }
    const dashboardData = getDashboardData();
    const shouldRefreshCurrency = startedOnDashboard && state.dashboardCurrencyHydrated;
    const shouldRefreshDebts = startedOnDashboard && (state.dashboardDebtSummaryLoaded || state.dashboardDebtsHydrated);
    const shouldRefreshPlans = startedOnDashboard && state.dashboardPlansHydrated;
    if (shouldRefreshCurrency && el.dashboardCurrencyPanel) {
      refreshState.begin?.(el.dashboardCurrencyPanel, "Обновляется");
    }
    if (shouldRefreshDebts && el.dashboardDebtsPanel && core.isDashboardDebtsVisible()) {
      refreshState.begin?.(el.dashboardDebtsPanel, "Обновляется");
    }
    if (shouldRefreshPlans && el.dashboardPlansPanel && ui?.showDashboardOperations !== false) {
      refreshState.begin?.(el.dashboardPlansPanel, "Обновляется");
    }
    let optionalPanelTasksStarted = false;
    try {
      const data = await (dashboardData.loadAllTimeSummary
        ? dashboardData.loadAllTimeSummary({ signal: requestSignal })
        : core.requestJson("/api/v1/dashboard/summary?period=all_time", { headers: core.authHeaders(), signal: requestSignal }));
      if (!isCurrentDashboardLoad()) {
        return;
      }
      if (el.debtLendTotal) {
        el.debtLendTotal.textContent = core.formatMoney(data.debt_lend_outstanding);
      }
      if (el.debtBorrowTotal) {
        el.debtBorrowTotal.textContent = core.formatMoney(data.debt_borrow_outstanding);
      }
      if (el.debtNetTotal) {
        el.debtNetTotal.textContent = core.formatMoney(data.debt_net_position);
      }
      renderDebtKpiTones({
        lend: data.debt_lend_outstanding,
        borrow: data.debt_borrow_outstanding,
        net: data.debt_net_position,
      });
      state.dashboardSummaryHydrated = true;
      setDashboardPanelState(el.dashboardDebtsPanel, "ready");
      setDashboardPanelState(el.dashboardCurrencyPanel, "ready");
      if (el.dashboardDebtKpiGrid) {
        const lendTotal = Number(data.debt_lend_outstanding || 0);
        const borrowTotal = Number(data.debt_borrow_outstanding || 0);
        const netTotal = Number(data.debt_net_position || 0);
        const hasDebtKpi = Math.abs(lendTotal) > 0.000001 || Math.abs(borrowTotal) > 0.000001 || Math.abs(netTotal) > 0.000001;
        el.dashboardDebtKpiGrid.classList.toggle("hidden", !hasDebtKpi);
      }
      if (data.debt_summary_available === false) {
        state.dashboardDebtSummaryLoaded = false;
      }
      renderDashboardCurrencySummary(data);
      if (data.debt_summary_available !== false) {
        state.dashboardDebtSummaryLoaded = true;
      }

      if (dashboardOptionalLoadPromise) {
        optionalPanelTasksStarted = true;
        dashboardOptionalLoadPromise.finally(() => {
          endDashboardOptionalRefreshes({
            currency: shouldRefreshCurrency,
            debts: shouldRefreshDebts,
            plans: shouldRefreshPlans,
          });
        });
        return;
      }

      dashboardOptionalLoadController = new AbortController();
      const optionalRequestSignal = dashboardOptionalLoadController.signal;
      const optionalLoadSeq = ++dashboardOptionalLoadSeq;
      const isCurrentOptionalDashboardLoad = () => (
        !optionalRequestSignal.aborted
        && optionalLoadSeq === dashboardOptionalLoadSeq
        && state.activeSection === "dashboard"
      );
      const currencyOverviewTask = core.requestJson("/api/v1/currency/overview?trades_limit=10", {
        headers: core.authHeaders(),
        signal: optionalRequestSignal,
      })
        .then((value) => ({ value, error: null }))
        .catch((error) => ({ value: null, error }));
      const plansTask = el.dashboardPlansPanel && ui?.showDashboardOperations !== false
        ? Promise.resolve(getPlansFeature().loadPlans?.({ signal: optionalRequestSignal }))
          .then((value) => ({ value, error: null }))
          .catch((error) => ({ value: null, error }))
        : Promise.resolve({ value: null, error: null });
      const debtCardsTask = core.isDashboardDebtsVisible() && el.dashboardDebtsList
        ? (dashboardData.loadDebtPreview
          ? dashboardData.loadDebtPreview({ limit: 6, signal: optionalRequestSignal })
          : core.requestJson("/api/v1/dashboard/debts/preview?limit=6", {
            headers: core.authHeaders(),
            signal: optionalRequestSignal,
          }))
          .then((value) => ({ value, error: null }))
          .catch((error) => ({ value: null, error }))
        : Promise.resolve({ value: null, error: null });
      const recommendationsTask = el.dashboardRecommendationsList
        ? core.requestJson("/api/v1/operations/item-recommendations?limit=12", {
          headers: core.authHeaders(),
          signal: optionalRequestSignal,
        })
          .then((value) => ({ value, error: null }))
          .catch((error) => ({ value: null, error }))
        : Promise.resolve({ value: [], error: null });
      optionalPanelTasksStarted = true;
      dashboardOptionalLoadPromise = Promise.allSettled([currencyOverviewTask, plansTask, debtCardsTask, recommendationsTask]).finally(() => {
        if (dashboardOptionalLoadController?.signal === optionalRequestSignal) {
          dashboardOptionalLoadController = null;
        }
        if (dashboardOptionalLoadPromise) {
          dashboardOptionalLoadPromise = null;
        }
      });

      currencyOverviewTask.then((currencyOverviewResult) => {
        if (currencyOverviewResult.error) {
          if (core.isAbortError?.(currencyOverviewResult.error)) {
            return;
          }
          if (!isCurrentOptionalDashboardLoad()) {
            return;
          }
          reportOptionalDashboardPanelFailure("currency", currencyOverviewResult.error);
          if (state.dashboardCurrencyHydrated) {
            setDashboardPanelState(el.dashboardCurrencyPanel, "stale");
            return;
          }
          renderDashboardCurrencyRates([], []);
        } else {
          if (!isCurrentOptionalDashboardLoad()) {
            return;
          }
          const currencyOverview = currencyOverviewResult.value || {};
          renderDashboardCurrencyRates(currencyOverview.current_rates, currencyOverview.tracked_currencies);
          state.dashboardCurrencyHydrated = true;
          setDashboardPanelState(el.dashboardCurrencyPanel, "ready");
        }
      }).catch((err) => {
        if (!core.isAbortError?.(err)) {
          reportOptionalDashboardPanelFailure("currency", err);
        }
      }).finally(() => {
        if (shouldRefreshCurrency && el.dashboardCurrencyPanel) {
          refreshState.end?.(el.dashboardCurrencyPanel);
        }
      });

      recommendationsTask.then((recommendationsResult) => {
        if (!isCurrentOptionalDashboardLoad()) {
          return;
        }
        if (recommendationsResult.error) {
          if (!core.isAbortError?.(recommendationsResult.error)) {
            el.dashboardRecommendationsList.innerHTML = dashboardPanelError("Не удалось загрузить рекомендации");
          }
          return;
        }
        renderDashboardRecommendations(recommendationsResult.value);
      }).catch((err) => {
        if (!core.isAbortError?.(err)) {
          reportOptionalDashboardPanelFailure("recommendations", err);
        }
      });

      if (el.dashboardPlansPanel && ui?.showDashboardOperations !== false) {
        plansTask.then((plansResult) => {
          if (plansResult.error) {
            if (core.isAbortError?.(plansResult.error)) {
              return;
            }
            reportOptionalDashboardPanelFailure("plans", plansResult.error);
            if (isCurrentOptionalDashboardLoad()) {
              if (state.dashboardPlansHydrated) {
                setDashboardPanelState(el.dashboardPlansPanel, "stale");
              } else {
                el.dashboardPlansList.innerHTML = dashboardPanelError("Не удалось загрузить ближайшие планы");
              }
            }
          } else if (!isCurrentOptionalDashboardLoad()) {
            return;
          } else {
            setDashboardPanelState(el.dashboardPlansPanel, "ready");
          }
        }).catch((err) => {
          if (!core.isAbortError?.(err)) {
            reportOptionalDashboardPanelFailure("plans", err);
          }
        }).finally(() => {
          if (shouldRefreshPlans && el.dashboardPlansPanel) {
            refreshState.end?.(el.dashboardPlansPanel);
          }
        });
      } else {
        if (isCurrentOptionalDashboardLoad()) {
          getPlansFeature().renderDashboardPlans?.();
        }
        if (shouldRefreshPlans && el.dashboardPlansPanel) {
          refreshState.end?.(el.dashboardPlansPanel);
        }
      }

      if (!core.isDashboardDebtsVisible()) {
        if (shouldRefreshDebts && el.dashboardDebtsPanel) {
          refreshState.end?.(el.dashboardDebtsPanel);
        }
        return;
      }

      if (el.dashboardDebtsList) {
        debtCardsTask.then((debtCardsResult) => {
          if (debtCardsResult.error) {
            if (core.isAbortError?.(debtCardsResult.error)) {
              return;
            }
            reportOptionalDashboardPanelFailure("debts-preview", debtCardsResult.error);
            if (state.dashboardDebtsHydrated) {
              setDashboardPanelState(el.dashboardDebtsPanel, "stale");
            } else {
              el.dashboardDebtsList.innerHTML = dashboardPanelError("Не удалось загрузить активные долги");
            }
            return;
          }
          const cards = Array.isArray(debtCardsResult.value) ? debtCardsResult.value : [];
          if (isCurrentOptionalDashboardLoad()) {
            el.dashboardDebtsList.innerHTML = "";
            if (!cards.length) {
              const empty = document.createElement("div");
              empty.className = "muted-small";
              empty.textContent = "Нет активных долгов";
              el.dashboardDebtsList.appendChild(empty);
            } else {
              for (const card of cards) {
                const now = new Date();
                const activeDebts = (card.debts || []).filter((debt) => Number(debt.outstanding_total || 0) > 0);
                activeDebts.sort((a, b) => {
                  const aState = debtUi.debtDueState(a, now);
                  const bState = debtUi.debtDueState(b, now);
                  const rankDiff = duePriorityRank(aState) - duePriorityRank(bState);
                  if (rankDiff !== 0) {
                    return rankDiff;
                  }
                  const aDue = debtUi.parseIsoDateEnd(a.due_date);
                  const bDue = debtUi.parseIsoDateEnd(b.due_date);
                  if (aDue && bDue) {
                    return aDue.getTime() - bDue.getTime();
                  }
                  if (aDue) {
                    return -1;
                  }
                  if (bDue) {
                    return 1;
                  }
                  return Number(b.id || 0) - Number(a.id || 0);
                });
                const visibleDebts = activeDebts.slice(0, 2);
                const rowsHtml = visibleDebts
                  .map((debt) => {
                    const principal = debtUi.parseAmount(debt.principal || 0);
                    const outstanding = debtUi.parseAmount(debt.outstanding_total || 0);
                    const repaid = debtUi.parseAmount(debt.repaid_total || 0);
                    const forgiven = debtUi.parseAmount(debt.forgiven_total || 0);
                    const settled = repaid + forgiven;
                    const repayPercent = principal > 0 ? Math.max(0, Math.min(100, Math.round((settled / principal) * 100))) : 0;
                    const direction = debt.direction === "borrow" ? "borrow" : "lend";
                    const directionLabel = debtUi.debtDirectionBalanceLabel(direction);
                    const repayTone = direction === "borrow" ? (repayPercent >= 100 ? "borrow-ok" : repayPercent >= 40 ? "borrow-warn" : "borrow-danger") : (repayPercent >= 100 ? "lend-ok" : "lend-warn");
                    const dueState = debtUi.debtDueState(debt, now);
                    const dueProgress = debtUi.debtDueProgress(debt, dueState, now);
                    const dueDays = debtUi.debtDueDaysBadge(debt, dueState, now);
                    const settlementChips = [
                      repaid > 0 ? `<span class="meta-chip debt-meta-chip debt-meta-chip-repaid">Погашено ${core.formatMoney(repaid, { currency: debt.currency || "BYN" })}</span>` : "",
                      forgiven > 0 ? `<span class="meta-chip debt-meta-chip debt-meta-chip-forgiven">Прощено ${core.formatMoney(forgiven, { currency: debt.currency || "BYN" })}</span>` : "",
                    ].filter(Boolean).join("");
                    return `
                    <div class="dashboard-debt-row">
                      <div class="dashboard-debt-row-col">
                        <div class="muted-small">${directionLabel}</div>
                        <div class="debt-amount-principal ${direction === "borrow" ? "debt-amount-principal-borrow" : "debt-amount-principal-lend"}">${core.formatMoney(outstanding, { currency: debt.currency || "BYN" })}</div>
                        ${(core.normalizeCurrencyCode?.(debt.currency || "BYN", "BYN") || "BYN") !== (core.normalizeCurrencyCode?.(debt.base_currency || "BYN", "BYN") || "BYN") ? `<div class="muted-small">≈ ${core.formatMoney(debt.current_base_outstanding_total || 0, { currency: debt.base_currency || "BYN" })}</div>` : ""}
                      </div>
                      <div class="dashboard-debt-row-col">
                        <div class="muted-small">Погашение</div>
                        <div class="debt-repay-progress">
                          <div class="debt-repay-progress-track">
                            <span class="debt-repay-progress-bar debt-repay-progress-bar-${repayTone}" style="width:${repayPercent}%"></span>
                          </div>
                          <span class="muted-small">${repayPercent}% (${core.formatMoney(settled, { currency: debt.currency || "BYN" })} из ${core.formatMoney(principal, { currency: debt.currency || "BYN" })})</span>
                        </div>
                        ${settlementChips ? `<div class="debt-meta-chips dashboard-debt-meta-chips">${settlementChips}</div>` : ""}
                      </div>
                      <div class="dashboard-debt-row-col">
                        <div class="row debt-due-head">
                          <span class="dashboard-debt-due-label dashboard-debt-due-label-${dueState}">${dueBadgeLabel(dueState, debt.due_date || "")}</span>
                          ${dueDays ? `<span class="debt-due-days-badge debt-due-days-badge-${dueState}">${dueDays}</span>` : ""}
                        </div>
                        ${
                          dueProgress
                            ? `<div class="debt-due-progress"><div class="debt-due-progress-track"><span class="debt-due-progress-bar debt-due-progress-bar-${dueProgress.tone}" style="width:${dueProgress.percent}%"></span></div><span class="muted-small">Срок: ${dueProgress.percent}%</span></div>`
                            : `<span class="muted-small">Срок не задан</span>`
                        }
                        <div class="dashboard-debt-actions">
                          <button class="btn btn-repay btn-xs" type="button" data-dashboard-repay-debt-id="${debt.id}" ${outstanding <= 0 ? "disabled" : ""}>Погашение</button>
                          <button class="btn btn-secondary btn-xs" type="button" data-dashboard-history-debt-id="${debt.id}">Движения</button>
                        </div>
                      </div>
                    </div>
                  `;
                  })
                  .join("");
                const createdAt = visibleDebts[0]?.created_at ? formatDateTimeRu(visibleDebts[0].created_at) : "";
                const compact = document.createElement("article");
                compact.className = "panel debt-card debt-card-compact";
                compact.innerHTML = `
                <div class="debt-card-compact-grid">
                  <div class="debt-card-compact-col debt-card-compact-main">
                    <div class="debt-card-compact-head">
                      <div class="debt-card-compact-title-block">
                        <h3>${core.highlightText(card.counterparty || "", "")}</h3>
                        <span class="debt-status debt-status-${card.status}">${card.status === "active" ? "Активный" : "Закрыт"}</span>
                        ${createdAt ? `<span class="muted-small">Создано: ${createdAt}</span>` : ""}
                      </div>
                    </div>
                  </div>
                  <div class="debt-card-compact-col debt-card-compact-rows debt-child-zone">${rowsHtml}</div>
                </div>
              `;
                el.dashboardDebtsList.appendChild(compact);
              }
            }
            state.dashboardDebtsHydrated = true;
            setDashboardPanelState(el.dashboardDebtsPanel, "ready");
          }
        }).catch((err) => {
          if (!core.isAbortError?.(err)) {
            reportOptionalDashboardPanelFailure("debts-preview", err);
          }
        }).finally(() => {
          if (shouldRefreshDebts && el.dashboardDebtsPanel) {
            refreshState.end?.(el.dashboardDebtsPanel);
          }
        });
      } else if (shouldRefreshDebts && el.dashboardDebtsPanel) {
        refreshState.end?.(el.dashboardDebtsPanel);
      }
    } catch (err) {
      if (core.isAbortError?.(err)) {
        return;
      }
      if (isCurrentDashboardLoad()) {
        renderDashboardLoadFailure(err, { preserveExisting: state.dashboardSummaryHydrated });
        throw err;
      }
    } finally {
      if (dashboardLoadController?.signal === requestSignal) {
        dashboardLoadController = null;
      }
      if (!optionalPanelTasksStarted) {
        endDashboardOptionalRefreshes({
          currency: shouldRefreshCurrency,
          debts: shouldRefreshDebts,
          plans: shouldRefreshPlans,
        });
      }
    }
  }

  async function loadDashboardPlans() {
    const ui = core.getUiSettings ? core.getUiSettings() : null;
    if (ui && ui.showDashboardOperations === false) {
      return;
    }
    if (dashboardOptionalLoadPromise) {
      await dashboardOptionalLoadPromise;
      return;
    }
    if (!dashboardPlansLoadPromise) {
      dashboardPlansLoadPromise = Promise.resolve(getPlansFeature().loadPlans?.()).finally(() => {
        dashboardPlansLoadPromise = null;
      });
    }
    await dashboardPlansLoadPromise;
  }

  function abortDashboardLoad() {
    if (dashboardLoadController) {
      dashboardLoadController.abort();
      dashboardLoadController = null;
    }
    if (dashboardOptionalLoadController) {
      dashboardOptionalLoadController.abort();
      dashboardOptionalLoadController = null;
    }
    dashboardOptionalLoadPromise = null;
    dashboardPlansLoadPromise = null;
    dashboardLoadSeq += 1;
    dashboardOptionalLoadSeq += 1;
  }

  function bindCurrencyActions() {
    if (el.dashboardRefreshAllCurrencyRatesBtn) {
      el.dashboardRefreshAllCurrencyRatesBtn.addEventListener("click", () => {
        core.runAction({
          button: el.dashboardRefreshAllCurrencyRatesBtn,
          pendingText: "Обновление...",
          errorPrefix: "Ошибка обновления курсов",
          action: async () => {
            await refreshDashboardCurrencyRates("");
            core.setStatus("Курсы валют обновлены");
          },
        });
      });
    }
    if (el.dashboardCurrencyRates) {
      el.dashboardCurrencyRates.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-dashboard-refresh-currency]");
        if (!btn) {
          return;
        }
        const currency = String(btn.dataset.dashboardRefreshCurrency || "").trim().toUpperCase();
        core.runAction({
          button: btn,
          pendingText: "Обновление...",
          errorPrefix: "Ошибка обновления курса",
          action: async () => {
            await refreshDashboardCurrencyRates(currency);
            core.setStatus(`Курс ${core.formatCurrencyLabel(currency)} обновлен`);
          },
        });
      });
    }
  }

  function bindDashboardRetryActions() {
    [el.dashboardCurrencyPanel, el.dashboardPlansPanel, el.dashboardDebtsPanel, el.dashboardRecommendationsPanel].filter(Boolean).forEach((panel) => {
      panel.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-dashboard-retry]");
        if (!button) return;
        state.dashboardDebtSummaryLoaded = false;
        state.dashboardSummaryHydrated = false;
        state.dashboardDebtsHydrated = false;
        state.dashboardPlansHydrated = false;
        state.dashboardCurrencyHydrated = false;
        getDashboardData().invalidateReadCaches?.();
        core.runAction({
          button,
          pendingText: "Загрузка…",
          errorPrefix: "Не удалось обновить дашборд",
          action: () => loadDashboard(),
        });
      });
    });
  }

  function bindRecommendationActions() {
    el.openRecommendationCatalogBtn?.addEventListener("click", () => {
      window.App.getRuntimeModule?.("item-recommendation-manager")?.setPreferredView?.("recommendations");
      window.App.getRuntimeModule?.("navigation")?.switchSection?.("item_catalog", { scrollToTop: true });
    });
    el.dashboardRecommendationsList?.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-recommendation-action]");
      const card = button?.closest("[data-recommendation-template-id]");
      if (!button || !card) {
        return;
      }
      const templateId = Number(card.dataset.recommendationTemplateId || 0);
      const item = (state.dashboardRecommendations || []).find((entry) => Number(entry.template_id) === templateId);
      if (!item) {
        return;
      }
      const action = button.dataset.recommendationAction;
      if (action === "receipt") {
        operationModal.openCreateReceiptWithItem?.(item);
        return;
      }
      if (action === "plan") {
        getPlansFeature()?.openCreatePlanWithReceiptItem?.(item);
        return;
      }
      if (action === "settings") {
        window.App.getRuntimeModule?.("item-catalog")?.openItemTemplateModal?.({
          id: item.template_id,
          shop_name: item.shop_name,
          name: item.name,
          last_category_id: item.category_id,
          latest_unit_price: item.latest_unit_price,
          recommendation_enabled: true,
          recommendation_mode: "manual",
          recommendation_interval_days: item.interval_days,
          recommendation_base_quantity: item.base_quantity,
          recommendation_next_date: item.next_date,
          recommendation_snoozed_until: item.effective_date !== item.next_date ? item.effective_date : null,
        });
        return;
      }
      core.runAction({
        button,
        pendingText: action === "snooze" ? "Откладываем…" : "Отключаем…",
        errorPrefix: "Не удалось обновить рекомендацию",
        action: async () => {
          if (action === "snooze") {
            await core.requestJson(`/api/v1/operations/item-recommendations/${templateId}/snooze`, {
              method: "POST",
              headers: core.authHeaders(),
              body: JSON.stringify({ days: 7 }),
            });
          } else if (action === "disable") {
            await core.requestJson(`/api/v1/operations/item-templates/${templateId}`, {
              method: "PATCH",
              headers: core.authHeaders(),
              body: JSON.stringify({ recommendation_enabled: false }),
            });
          }
          await loadDashboardRecommendations();
        },
      });
    });
  }

  bindCurrencyActions();
  bindDashboardRetryActions();
  bindRecommendationActions();

  const api = {
    loadDashboard,
    abortDashboardLoad,
    refreshDashboardCurrencyRates,
    loadDashboardOperations: loadDashboardPlans,
    loadDashboardPlans,
    loadDashboardRecommendations,
  };

  window.App.registerRuntimeModule?.("dashboard", api);
})();
