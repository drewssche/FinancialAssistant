(() => {
  const { state, el, core } = window.App;

  function getDashboardFeature() {
    return window.App.getRuntimeModule?.("dashboard") || {};
  }

  function getTrackedCurrencies() {
    const raw = state.preferences?.data?.currency?.tracked_currencies;
    if (!Array.isArray(raw) || !raw.length) {
      return ["USD", "EUR"];
    }
    return raw.map((item) => String(item || "").toUpperCase()).filter(Boolean);
  }

  function syncFilterTabs() {
    if (!el.currencyFilterTabs) {
      return;
    }
    const tracked = getTrackedCurrencies();
    const tabs = ["all", ...tracked];
    if (!tabs.includes(state.currencyFilter)) {
      state.currencyFilter = "all";
    }
    el.currencyFilterTabs.innerHTML = tabs.map((item) => {
      const isActive = state.currencyFilter === item;
      const label = item === "all" ? "Все" : item;
      return `<button class="segmented-btn ${isActive ? "active" : ""}" data-currency-filter="${item}" type="button">${label}</button>`;
    }).join("");
  }

  function openTradePanel() {
    el.currencyTradePanel?.classList.remove("hidden");
    el.currencyRatePanel?.classList.add("hidden");
    primeDefaultDates();
    el.currencyTradeAsset?.focus();
  }

  function closeTradePanel() {
    el.currencyTradePanel?.classList.add("hidden");
  }

  function openRatePanel() {
    el.currencyRatePanel?.classList.remove("hidden");
    el.currencyTradePanel?.classList.add("hidden");
    primeDefaultDates();
    el.currencyRateAsset?.focus();
  }

  function closeRatePanel() {
    el.currencyRatePanel?.classList.add("hidden");
  }

  function renderSummary(data) {
    if (el.currencySummaryCurrentValue) {
      el.currencySummaryCurrentValue.textContent = core.formatMoney(data.total_current_value || 0);
    }
    if (el.currencySummaryBookValue) {
      el.currencySummaryBookValue.textContent = core.formatMoney(data.total_book_value || 0);
    }
    if (el.currencySummaryResultValue) {
      el.currencySummaryResultValue.textContent = core.formatMoney(data.total_result_value || 0);
    }
    if (el.currencySummaryActiveCount) {
      el.currencySummaryActiveCount.textContent = String(data.active_positions || 0);
    }
  }

  function renderPositions(data) {
    if (!el.currencyPositionsList) {
      return;
    }
    const positions = Array.isArray(data.positions) ? data.positions : [];
    if (!positions.length) {
      el.currencyPositionsList.innerHTML = `<div class="muted-small">Пока нет открытых валютных позиций</div>`;
      return;
    }
    el.currencyPositionsList.innerHTML = positions.map((item) => {
      const resultClass = Number(item.result_value || 0) >= 0 ? "analytics-kpi-chip-positive" : "analytics-kpi-chip-negative";
      return `
        <article class="panel">
          <div class="panel-head row between">
            <div>
              <h3>${core.escapeHtml ? core.escapeHtml(item.currency) : item.currency}</h3>
              <p class="subtitle">Остаток ${core.formatAmount(item.quantity || 0)}</p>
            </div>
            <span class="analytics-kpi-chip ${resultClass}">Прибыль / убыток: ${core.formatMoney(item.result_value || 0)}</span>
          </div>
          <div class="analytics-kpi-grid">
            <article class="analytics-kpi-card analytics-kpi-neutral">
              <div class="muted-small">Средняя цена покупки</div>
              <strong>${Number(item.average_buy_rate || 0).toFixed(4)}</strong>
            </article>
            <article class="analytics-kpi-card analytics-kpi-balance">
              <div class="muted-small">Вложено</div>
              <strong>${core.formatMoney(item.book_value || 0)}</strong>
            </article>
            <article class="analytics-kpi-card analytics-kpi-income">
              <div class="muted-small">Текущая оценка</div>
              <strong>${core.formatMoney(item.current_value || 0)}</strong>
            </article>
            <article class="analytics-kpi-card analytics-kpi-neutral">
              <div class="muted-small">Текущий курс</div>
              <strong>${Number(item.current_rate || 0).toFixed(4)}</strong>
              <span class="analytics-kpi-delta">${item.current_rate_date ? core.formatDateRu(item.current_rate_date) : "Курс не задан"}</span>
            </article>
          </div>
        </article>
      `;
    }).join("");
  }

  function renderTrades(data) {
    if (!el.currencyTradesBody) {
      return;
    }
    const trades = Array.isArray(data.recent_trades) ? data.recent_trades : [];
    if (!trades.length) {
      el.currencyTradesBody.innerHTML = `<tr><td colspan="7" class="muted-small">Сделок пока нет</td></tr>`;
      return;
    }
    el.currencyTradesBody.innerHTML = trades.map((item) => `
      <tr>
        <td>${core.formatDateRu(item.trade_date)}</td>
        <td>${item.side === "sell" ? "Продажа" : "Покупка"}</td>
        <td>${core.escapeHtml ? core.escapeHtml(item.asset_currency) : item.asset_currency}</td>
        <td>${core.formatAmount(item.quantity || 0)}</td>
        <td>${Number(item.unit_price || 0).toFixed(4)}</td>
        <td>${core.formatMoney(item.fee || 0, { withCurrency: true, currency: item.quote_currency || "BYN" })}</td>
        <td>${core.escapeHtml ? core.escapeHtml(item.note || "") : (item.note || "")}</td>
      </tr>
    `).join("");
  }

  function primeDefaultDates() {
    const today = core.getTodayIso();
    if (el.currencyTradeDate && !el.currencyTradeDate.value) {
      core.syncDateFieldValue(el.currencyTradeDate, today);
    }
    if (el.currencyRateDate && !el.currencyRateDate.value) {
      core.syncDateFieldValue(el.currencyRateDate, today);
    }
  }

  async function loadCurrencySection(options = {}) {
    syncFilterTabs();
    primeDefaultDates();
    const params = new URLSearchParams({ trades_limit: "100" });
    if (state.currencyFilter && state.currencyFilter !== "all") {
      params.set("currency", state.currencyFilter);
    }
    const data = await core.requestJson(`/api/v1/currency/overview?${params.toString()}`, {
      headers: core.authHeaders(),
    });
    renderSummary(data);
    renderPositions(data);
    renderTrades(data);
    state.currencySectionHydrated = true;
    if (options.force !== false) {
      syncFilterTabs();
    }
    return data;
  }

  async function submitCurrencyTrade(event) {
    event.preventDefault();
    await core.requestJson("/api/v1/currency/trades", {
      method: "POST",
      headers: core.authHeaders(),
      body: JSON.stringify({
        side: el.currencyTradeSide?.value || "buy",
        asset_currency: el.currencyTradeAsset?.value || "USD",
        quote_currency: String(el.currencyTradeQuote?.value || "BYN").toUpperCase(),
        quantity: el.currencyTradeQuantity?.value || "0",
        unit_price: el.currencyTradeUnitPrice?.value || "0",
        fee: el.currencyTradeFee?.value || "0",
        trade_date: el.currencyTradeDate?.value || core.getTodayIso(),
        note: el.currencyTradeNote?.value || "",
      }),
    });
    if (el.currencyTradeQuantity) {
      el.currencyTradeQuantity.value = "";
    }
    if (el.currencyTradeUnitPrice) {
      el.currencyTradeUnitPrice.value = "";
    }
    if (el.currencyTradeFee) {
      el.currencyTradeFee.value = "0";
    }
    if (el.currencyTradeNote) {
      el.currencyTradeNote.value = "";
    }
    closeTradePanel();
    await loadCurrencySection({ force: true });
    core.setStatus("Сделка по валюте сохранена");
    core.invalidateUiRequestCache?.("dashboard:summary");
    getDashboardFeature().loadDashboard?.().catch(() => {});
  }

  async function submitCurrencyRate(event) {
    event.preventDefault();
    await core.requestJson("/api/v1/currency/rates/current", {
      method: "PUT",
      headers: core.authHeaders(),
      body: JSON.stringify({
        currency: el.currencyRateAsset?.value || "USD",
        rate: el.currencyRateValue?.value || "0",
        rate_date: el.currencyRateDate?.value || core.getTodayIso(),
        source: el.currencyRateSource?.value || "manual",
      }),
    });
    if (el.currencyRateValue) {
      el.currencyRateValue.value = "";
    }
    closeRatePanel();
    await loadCurrencySection({ force: true });
    core.setStatus("Текущий курс обновлен");
    core.invalidateUiRequestCache?.("dashboard:summary");
    getDashboardFeature().loadDashboard?.().catch(() => {});
  }

  function bind() {
    if (el.currencyFilterTabs) {
      el.currencyFilterTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-currency-filter]");
        if (!btn) {
          return;
        }
        state.currencyFilter = btn.dataset.currencyFilter || "all";
        loadCurrencySection({ force: true }).catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.currencyTradeSideTabs) {
      el.currencyTradeSideTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-currency-side]");
        if (!btn) {
          return;
        }
        const next = btn.dataset.currencySide === "sell" ? "sell" : "buy";
        if (el.currencyTradeSide) {
          el.currencyTradeSide.value = next;
        }
        core.syncSegmentedActive(el.currencyTradeSideTabs, "currency-side", next);
      });
    }
    if (el.openCurrencyTradePanelBtn) {
      el.openCurrencyTradePanelBtn.addEventListener("click", openTradePanel);
    }
    if (el.closeCurrencyTradePanelBtn) {
      el.closeCurrencyTradePanelBtn.addEventListener("click", closeTradePanel);
    }
    if (el.openCurrencyRatePanelBtn) {
      el.openCurrencyRatePanelBtn.addEventListener("click", openRatePanel);
    }
    if (el.closeCurrencyRatePanelBtn) {
      el.closeCurrencyRatePanelBtn.addEventListener("click", closeRatePanel);
    }
    if (el.currencyTradeForm) {
      el.currencyTradeForm.addEventListener("submit", (event) => {
        core.runAction({
          button: el.submitCurrencyTradeBtn,
          pendingText: "Сохранение...",
          errorPrefix: "Ошибка сохранения валютной сделки",
          action: () => submitCurrencyTrade(event),
        });
      });
    }
    if (el.currencyRateForm) {
      el.currencyRateForm.addEventListener("submit", (event) => {
        core.runAction({
          button: el.submitCurrencyRateBtn,
          pendingText: "Обновление...",
          errorPrefix: "Ошибка обновления курса",
          action: () => submitCurrencyRate(event),
        });
      });
    }
  }

  bind();

  window.App.registerRuntimeModule?.("currency", {
    loadCurrencySection,
    syncFilterTabs,
    openTradePanel,
    openRatePanel,
  });
})();
