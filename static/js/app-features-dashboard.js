(() => {
  const { state, el, core } = window.App;
  const debtUi = core.debtUi;
  let dashboardLoadSeq = 0;
  let dashboardLoadController = null;
  let dashboardOptionalLoadSeq = 0;
  let dashboardOptionalLoadController = null;
  let dashboardOptionalLoadPromise = null;
  let dashboardPlansLoadPromise = null;
  let dashboardRatesController = null;

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

  const percentFormat = new Intl.NumberFormat("ru-RU", {
    style: "percent", signDisplay: "exceptZero", minimumFractionDigits: 2, maximumFractionDigits: 2,
  });

  function renderDashboardCurrencyRates(rates) {
    const commonDate = rates[0]?.rate_date;
    const sameDate = commonDate && rates.every((row) => row.rate_date === commonDate);
    el.dashboardCurrencyDate.textContent = sameDate ? core.formatDateRu(commonDate) : "";
    if (!rates.length) {
      el.dashboardCurrencyRates.innerHTML = '<span class="muted-small">Выберите валюты в настройках.</span>';
      return;
    }
    el.dashboardCurrencyRates.innerHTML = rates.map((row) => {
      const code = core.escapeHtml(row.currency);
      const label = row.display_scale > 1 ? `${row.display_scale} ${code}` : code;
      const date = !sameDate && row.rate_date ? core.formatDateRu(row.rate_date) : "";
      const value = row.display_rate == null
        ? '<span class="muted-small">Нет курса</span>'
        : `<strong>${core.formatRateDisplay(row.display_rate).replace(".", ",")} <small>BYN</small></strong>`;
      const change = row.change_pct;
      const tone = change > 0 ? "positive" : change < 0 ? "negative" : "neutral";
      return `<button type="button" class="dashboard-rate-row" data-dashboard-quote="${code}"
          title="Сравнить курсы банков для ${code}">
        <span class="dashboard-rate-code">${label}${date ? `<small>${date}</small>` : ""}</span>
        ${value}
        <span class="dashboard-rate-change ${tone}" title="К предыдущему опубликованному курсу">${change == null ? "" : percentFormat.format(change / 100)}</span>
        ${window.App.icons.svg("forward")}
      </button>`;
    }).join("");
  }

  async function loadDashboardCurrencyRates() {
    if (dashboardRatesController || state.activeSection !== "dashboard"
        || state.preferences?.data?.currency?.show_dashboard_kpi === false) return;
    const controller = new AbortController();
    dashboardRatesController = controller;
    try {
      const rates = await core.requestJson("/api/v1/dashboard/currency-rates", {
        headers: core.authHeaders(), signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      renderDashboardCurrencyRates(rates);
      state.dashboardCurrencyHydrated = true;
      setDashboardPanelState(el.dashboardCurrencyPanel, "ready");
    } catch (error) {
      if (controller.signal.aborted || core.isAbortError(error)) return;
      reportOptionalDashboardPanelFailure("currency", error);
      if (state.dashboardCurrencyHydrated) {
        setDashboardPanelState(el.dashboardCurrencyPanel, "stale");
      } else {
        el.dashboardCurrencyDate.textContent = "";
        el.dashboardCurrencyRates.innerHTML = dashboardPanelError("Не удалось загрузить курсы НБРБ");
      }
    } finally {
      if (dashboardRatesController === controller) dashboardRatesController = null;
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

  function dashboardPanelError(message) {
    return `<div class="panel-load-state panel-load-state-error" role="alert">
      <span>${core.escapeHtml?.(message) || message}</span>
      <button class="btn btn-secondary btn-xs btn-icon" type="button" data-dashboard-retry aria-label="Повторить загрузку" title="Повторить загрузку">${window.App.icons.svg("refresh")}</button>
    </div>`;
  }

  function renderDashboardLoadFailure({ preserveExisting = false } = {}) {
    if (preserveExisting) {
      setDashboardPanelState(el.dashboardCurrencyPanel, "stale");
      setDashboardPanelState(el.dashboardDebtsPanel, "stale");
      getLoadingSkeletons().clearDashboardAnalyticsSkeletonState?.();
      return;
    }
    if (el.dashboardCurrencyRates) {
      el.dashboardCurrencyDate.textContent = "";
      el.dashboardCurrencyRates.innerHTML = dashboardPanelError("Не удалось загрузить курсы НБРБ");
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
    if (el.dashboardDebtKpiGrid) {
      el.dashboardDebtKpiGrid.innerHTML = dashboardPanelError("Не удалось загрузить итоги долгов");
    }
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
    const showCurrency = state.preferences?.data?.currency?.show_dashboard_kpi !== false;
    el.dashboardCurrencyPanel?.classList.toggle("hidden", !showCurrency);
    if (startedOnDashboard && showCurrency && !state.dashboardCurrencyHydrated) {
      skeletons.renderDashboardCurrencySkeleton?.();
    }
    const dashboardData = getDashboardData();
    const shouldRefreshCurrency = startedOnDashboard && showCurrency && state.dashboardCurrencyHydrated;
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
        ? dashboardData.loadAllTimeSummary({ signal: requestSignal, debtTotalsOnly: true })
        : core.requestJson("/api/v1/dashboard/summary?period=all_time&view=debt_totals", { headers: core.authHeaders(), signal: requestSignal }));
      if (!isCurrentDashboardLoad()) {
        return;
      }
      if (el.dashboardDebtKpiGrid) {
        el.dashboardDebtKpiGrid.classList.remove("hidden");
        el.dashboardDebtKpiGrid.innerHTML = data.debt_summary_available === false
          ? dashboardPanelError("Не удалось загрузить итоги долгов")
          : core.renderDebtSummaryKpi({ lendTotal: data.debt_lend_outstanding, borrowTotal: data.debt_borrow_outstanding }, { dashboard: true });
      }
      state.dashboardSummaryHydrated = true;
      setDashboardPanelState(el.dashboardDebtsPanel, "ready");
      if (data.debt_summary_available === false) {
        state.dashboardDebtSummaryLoaded = false;
      }
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
      const currencyRatesTask = showCurrency ? loadDashboardCurrencyRates() : Promise.resolve();
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
      dashboardOptionalLoadPromise = Promise.allSettled([currencyRatesTask, plansTask, debtCardsTask]).finally(() => {
        if (dashboardOptionalLoadController?.signal === optionalRequestSignal) {
          dashboardOptionalLoadController = null;
          dashboardOptionalLoadPromise = null;
        }
      });

      currencyRatesTask.finally(() => {
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
        renderDashboardLoadFailure({ preserveExisting: state.dashboardSummaryHydrated });
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
    dashboardRatesController?.abort();
    dashboardRatesController = null;
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

  function bindDashboardRetryActions() {
    [el.dashboardCurrencyPanel, el.dashboardPlansPanel, el.dashboardDebtsPanel].filter(Boolean).forEach((panel) => {
      panel.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-dashboard-retry]");
        if (!button) return;
        if (panel === el.dashboardCurrencyPanel) {
          core.runAction({
            button,
            pendingText: "Загрузка…",
            errorPrefix: "Не удалось загрузить курсы НБРБ",
            action: loadDashboardCurrencyRates,
          });
          return;
        }
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

  bindDashboardRetryActions();

  const api = {
    loadDashboard,
    abortDashboardLoad,
    loadDashboardOperations: loadDashboardPlans,
    loadDashboardPlans,
  };

  window.App.registerRuntimeModule?.("dashboard", api);
})();
