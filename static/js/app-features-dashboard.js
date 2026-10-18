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
    el.dashboardCurrencyPanel?.classList.toggle("hidden", currencyPrefs.show_dashboard_kpi === false);
    for (const node of [el.dashboardCurrencyKpiGrid, el.dashboardCurrencyBalances, el.dashboardCurrencyPositions]) {
      if (node) { node.replaceChildren(); node.classList.add("hidden"); }
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

  function renderDashboardCurrencyRates(currentRates = [], trackedCurrencies = [], bankRates = []) {
    if (!el.dashboardCurrencyRates) {
      return;
    }
    const tracked = Array.isArray(trackedCurrencies) ? trackedCurrencies : [];
    const normalizedTracked = tracked
      .map((item) => core.normalizeCurrencyCode?.(item, "") || "")
      .filter(Boolean);
    const rows = Array.isArray(currentRates) ? currentRates : [];
    const bankRows = Array.isArray(bankRates) ? bankRates : [];
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
              <button class="btn btn-secondary btn-xs btn-icon" type="button" data-dashboard-refresh-currency="${currency}" aria-label="Обновить курс" title="Обновить курс">${window.App.icons.svg("refresh")}</button>
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
      const displayScale = itemCurrency === "RUB" ? 100 : 1;
      const currencyLabel = `${displayScale > 1 ? `${displayScale} ` : ""}${core.formatCurrencyLabel(itemCurrency)}`;
      const baseCurrencySymbol = core.formatCurrencySymbol?.(core.getCurrencyConfig?.().code || "BYN") || "BYN";
      const currencyBankRows = bankRows.filter((row) => (core.normalizeCurrencyCode?.(row.currency, "") || "") === itemCurrency);
      const bankRatesHtml = currencyBankRows.length ? `
        <div class="dashboard-bank-rates" aria-label="Курсы банков для ${itemCurrency}">
          <div class="dashboard-bank-rate-row dashboard-bank-rate-head">
            <span>Банк</span><span>Покупка</span><span>Продажа</span>
          </div>
          ${currencyBankRows.map((row) => {
            const bankName = String(row.bank_name || row.bank_code || "Банк");
            const channelLabel = String(row.channel_label || row.channel || "");
            const staleClass = row.stale ? " dashboard-bank-rate-stale" : "";
            return `
              <div class="dashboard-bank-rate-row${staleClass}" title="${core.escapeHtml ? core.escapeHtml(`${bankName}${channelLabel ? ` · ${channelLabel}` : ""}${row.stale ? " · данные устарели" : ""}`) : bankName}">
                <span class="dashboard-bank-rate-name">${core.escapeHtml ? core.escapeHtml(bankName) : bankName}</span>
                <strong>${core.formatRateDisplay?.(row.buy_rate || 0, 4, 6)}</strong>
                <strong>${core.formatRateDisplay?.(row.sell_rate || 0, 4, 6)}</strong>
              </div>
            `;
          }).join("")}
        </div>
      ` : '<div class="dashboard-bank-rates-empty muted-small">Банковские курсы ещё загружаются</div>';
      return `
        <article class="dashboard-currency-rate-card">
          <div class="dashboard-currency-rate-head">
            <strong>${core.escapeHtml ? core.escapeHtml(currencyLabel) : currencyLabel}</strong>

          </div>
          <div class="dashboard-currency-rate-value-row">
            <div class="dashboard-currency-rate-value">${core.formatRateDisplay?.(Number(item.rate || 0) * displayScale, 4, 6)}</div>
            <div class="dashboard-currency-rate-delta dashboard-currency-rate-delta-${deltaTone}">
              ${hasDelta ? `${formatSignedRate(Number(item.change_value || 0) * displayScale)} · ${formatSignedPercent(item.change_pct || 0)}` : "—"}
            </div>
          </div>
          <div class="dashboard-currency-rate-meta muted-small">${isStale ? `Последний доступный курс к ${baseCurrencySymbol}` : `Официальный курс к ${baseCurrencySymbol}`} · ${rateDate}</div>
          <div class="dashboard-currency-rate-delta-caption muted-small">${hasDelta ? (isStale ? "К предыдущему курсу" : "За день") : "Нет предыдущего курса для сравнения"}</div>
          <div class="dashboard-currency-rate-source muted-small">Источник: ${core.escapeHtml ? core.escapeHtml(source) : source}</div>
          ${bankRatesHtml}
          <div class="dashboard-currency-rate-actions">
            <button class="btn btn-secondary btn-xs btn-icon" type="button" data-dashboard-refresh-currency="${item.currency}" aria-label="Обновить курс" title="Обновить курс">${window.App.icons.svg("refresh")}</button>
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
      <button class="btn btn-secondary btn-xs btn-icon" type="button" data-dashboard-retry aria-label="Повторить загрузку" title="Повторить загрузку">${window.App.icons.svg("refresh")}</button>
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
    window.App.getRuntimeModule("catalog-watch")?.loadDashboard();
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
      optionalPanelTasksStarted = true;
      dashboardOptionalLoadPromise = Promise.allSettled([currencyOverviewTask, plansTask, debtCardsTask]).finally(() => {
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
          renderDashboardCurrencyRates([], [], []);
        } else {
          if (!isCurrentOptionalDashboardLoad()) {
            return;
          }
          const currencyOverview = currencyOverviewResult.value || {};
          renderDashboardCurrencyRates(
            currencyOverview.current_rates,
            currencyOverview.tracked_currencies,
            currencyOverview.bank_rates,
          );
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
                const compact = document.createElement('article');
                compact.className = 'panel debt-card';
                compact.dataset.dashboardDebtCard = '';
                compact.renderDebtRows = () => {
                  compact.innerHTML = `<div class="debt-mobile-card-head"><div class="debt-mobile-card-title-block"><h3>${core.highlightText(card.counterparty || '', '')}</h3></div></div>${window.App.debtCardsRenderer.renderDebtRows(visibleDebts, {dashboard:true, now})}`;
                };
                compact.renderDebtRows();
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
    [el.dashboardCurrencyPanel, el.dashboardPlansPanel, el.dashboardDebtsPanel].filter(Boolean).forEach((panel) => {
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

  bindCurrencyActions();
  bindDashboardRetryActions();

  const api = {
    loadDashboard,
    abortDashboardLoad,
    refreshDashboardCurrencyRates,
    loadDashboardOperations: loadDashboardPlans,
    loadDashboardPlans,
  };

  window.App.registerRuntimeModule?.("dashboard", api);
})();
