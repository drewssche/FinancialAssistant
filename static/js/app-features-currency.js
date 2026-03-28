(() => {
  const { state, el, core } = window.App;
  const tradeItemsById = new Map();
  const pickerUtils = window.App.getRuntimeModule?.("picker-utils");

  function getDashboardFeature() {
    return window.App.getRuntimeModule?.("dashboard") || {};
  }

  function getAnalyticsCurrencyFeature() {
    return window.App.getRuntimeModule?.("analytics-currency-module") || {};
  }

  function getOperationModal() {
    return window.App.getRuntimeModule?.("operation-modal") || {};
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

  function toggleTableMenu(trigger) {
    const menuId = String(trigger?.dataset.tableMenuTrigger || "");
    const menu = menuId ? document.querySelector(`.table-kebab-popover[data-table-menu="${CSS.escape(menuId)}"]`) : null;
    const ownerRow = trigger.closest("tr");
    const ownerCell = trigger.closest("td");
    if (!menu || !pickerUtils?.setPopoverOpen) {
      return false;
    }
    const owners = [trigger, trigger.parentElement].filter(Boolean);
    const clearOpenState = () => {
      ownerCell?.classList.remove("table-menu-open-cell");
      ownerRow?.classList.remove("table-menu-open-row");
    };
    const shouldOpen = menu.classList.contains("hidden");
    document.querySelectorAll(".table-kebab-popover:not(.hidden)").forEach((node) => {
      if (node !== menu) {
        pickerUtils.setPopoverOpen(node, false, {
          owners: Array.isArray(node.__appPopoverOwners) ? node.__appPopoverOwners : [],
        });
        (Array.isArray(node.__appPopoverOwners) ? node.__appPopoverOwners : []).forEach((owner) => owner?.blur?.());
        node.closest(".table-menu-open-cell")?.classList.remove("table-menu-open-cell");
        node.closest(".table-menu-open-row")?.classList.remove("table-menu-open-row");
      }
    });
    pickerUtils.setPopoverOpen(menu, shouldOpen, { owners, onClose: clearOpenState });
    ownerCell?.classList.toggle("table-menu-open-cell", shouldOpen);
    ownerRow?.classList.toggle("table-menu-open-row", shouldOpen);
    if (!shouldOpen) {
      clearOpenState();
      trigger?.blur?.();
    }
    return true;
  }

  async function refreshAfterTradeMutation() {
    await loadCurrencySection({ force: true });
    core.invalidateUiRequestCache?.("dashboard:summary");
    getDashboardFeature().loadDashboard?.().catch(() => {});
    getAnalyticsCurrencyFeature().loadAnalyticsCurrency?.({ force: true }).catch(() => {});
  }

  function getTrackedCurrencies() {
    const raw = state.preferences?.data?.currency?.tracked_currencies;
    if (!Array.isArray(raw) || !raw.length) {
      return ["USD", "EUR"];
    }
    return raw.map((item) => String(item || "").toUpperCase()).filter(Boolean);
  }

  function syncRateAssetOptions(preserveValue = "") {
    if (!el.currencyRateAsset) {
      return;
    }
    const tracked = core.getSelectableCurrencies?.({ includeBase: false }) || getTrackedCurrencies();
    const normalized = Array.from(new Set(
      tracked
        .map((item) => String(item || "").trim().toUpperCase())
        .filter(Boolean),
    ));
    const nextValue = String(preserveValue || el.currencyRateAsset.value || normalized[0] || "").toUpperCase();
    el.currencyRateAsset.innerHTML = normalized.map((currency) => {
      const selected = currency === nextValue ? " selected" : "";
      return `<option value="${currency}"${selected}>${core.formatCurrencyLabel(currency)}</option>`;
    }).join("");
    if (nextValue) {
      el.currencyRateAsset.value = nextValue;
    }
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
      const label = item === "all" ? "Все" : core.formatCurrencyLabel(item);
      return `<button class="segmented-btn ${isActive ? "active" : ""}" data-currency-filter="${item}" type="button">${label}</button>`;
    }).join("");
  }

  async function openTradePanel() {
    const operationModal = getOperationModal();
    if (operationModal?.openCreateModalForCurrency) {
      await operationModal.openCreateModalForCurrency();
      return;
    }
    if (!operationModal?.openCreateModal || !operationModal?.setCreateEntryMode) {
      return;
    }
    await operationModal.openCreateModal();
    operationModal.setCreateEntryMode("currency");
  }

  function openRatePanel() {
    syncRateAssetOptions();
    el.currencyRatePanel?.classList.remove("hidden");
    el.currencyTradePanel?.classList.add("hidden");
    primeDefaultDates();
    el.currencyRateAsset?.focus();
  }

  function closeRatePanel() {
    el.currencyRatePanel?.classList.add("hidden");
  }

  function renderSummary(data) {
    const resultTone = getResultPresentation(data.total_result_value || 0);
    if (el.currencySummaryCurrentValue) {
      el.currencySummaryCurrentValue.textContent = core.formatMoney(data.total_current_value || 0);
    }
    if (el.currencySummaryBookValue) {
      el.currencySummaryBookValue.textContent = core.formatMoney(data.total_book_value || 0);
    }
    if (el.currencySummaryResultValue) {
      el.currencySummaryResultValue.textContent = core.formatMoney(data.total_result_value || 0);
    }
    if (el.currencySummaryResultCard) {
      el.currencySummaryResultCard.classList.remove("analytics-kpi-income", "analytics-kpi-expense", "analytics-kpi-neutral");
      el.currencySummaryResultCard.classList.add(resultTone.cardClass);
    }
    if (el.currencySummaryResultLabel) {
      el.currencySummaryResultLabel.textContent = resultTone.label;
    }
    if (el.currencySummaryActiveCount) {
      el.currencySummaryActiveCount.textContent = String(data.active_positions || 0);
    }
    if (el.currencySummaryBuyVolume) {
      el.currencySummaryBuyVolume.textContent = core.formatMoney(data.buy_volume_base || 0);
    }
    if (el.currencySummaryBuyCount) {
      el.currencySummaryBuyCount.textContent = `${String(data.buy_trades_count || 0)} сделок · ср. курс ${Number(data.buy_average_rate || 0).toFixed(4)}`;
    }
    if (el.currencySummarySellVolume) {
      el.currencySummarySellVolume.textContent = core.formatMoney(data.sell_volume_base || 0);
    }
    if (el.currencySummarySellCount) {
      el.currencySummarySellCount.textContent = `${String(data.sell_trades_count || 0)} сделок · ср. курс ${Number(data.sell_average_rate || 0).toFixed(4)}`;
    }
  }

  function renderPositions(data) {
    const positions = Array.isArray(data.positions) ? data.positions : [];
    const positionsByCurrency = new Map(positions.map((item) => [String(item.currency || "").toUpperCase(), item]));
    const currentRates = Array.isArray(data.current_rates) ? data.current_rates : [];
    const currentRatesByCurrency = new Map(currentRates.map((item) => [String(item.currency || "").toUpperCase(), item]));
    const trackedCurrencies = Array.isArray(data.tracked_currencies) && data.tracked_currencies.length
      ? data.tracked_currencies.map((item) => String(item || "").toUpperCase()).filter(Boolean)
      : getTrackedCurrencies();
    const baseCurrency = String(data.base_currency || (core.getCurrencyConfig?.().code || "BYN")).toUpperCase();
    if (el.currencyBalancesRow) {
      const bynCard = `
        <article class="currency-balance-card">
          <div class="muted-small">${core.formatCurrencyLabel(baseCurrency)}</div>
          <strong>${core.formatMoney(data.total_current_value || 0, { currency: baseCurrency })}</strong>
          <div class="currency-balance-secondary">Текущая оценка всех открытых валютных позиций</div>
        </article>
      `;
      const positionCards = trackedCurrencies.map((currency) => {
        const item = positionsByCurrency.get(currency) || null;
        const currentRate = currentRatesByCurrency.get(currency) || null;
        const currencyLabel = core.formatCurrencyLabel(currency);
        return `
          <article class="currency-balance-card">
            <div class="muted-small">${core.escapeHtml ? core.escapeHtml(currencyLabel) : currencyLabel}</div>
            <strong>${core.formatAmount(item?.quantity || 0)}</strong>
            <div class="currency-balance-secondary">${core.formatMoney(item?.current_value || 0, { currency: baseCurrency })} по текущему курсу${currentRate?.rate ? ` · ${Number(currentRate.rate || 0).toFixed(4)}` : ""}</div>
          </article>
        `;
      });
      el.currencyBalancesRow.innerHTML = [bynCard, ...positionCards].join("");
    }
    if (!el.currencyPositionsList) {
      return;
    }
    if (!positions.length) {
      const trackedSummary = trackedCurrencies.length
        ? `Отслеживаются: ${trackedCurrencies.map((currency) => core.formatCurrencyLabel(currency)).join(", ")}.`
        : "Отслеживаемые валюты остаются в карточках выше.";
      el.currencyPositionsList.innerHTML = `
        <div class="muted-small">
          Открытых валютных позиций пока нет. ${trackedSummary}
        </div>
      `;
      return;
    }
    el.currencyPositionsList.innerHTML = positions.map((item) => {
      const resultTone = getResultPresentation(item.result_value || 0);
      const currencyLabel = core.formatCurrencyLabel(item.currency);
      return `
        <article class="panel">
          <div class="panel-head row between">
            <div>
              <h3>${core.escapeHtml ? core.escapeHtml(currencyLabel) : currencyLabel}</h3>
              <p class="subtitle">
                <span class="currency-position-primary">${core.formatAmount(item.quantity || 0)}</span>
                <span class="currency-position-secondary">${core.formatMoney(item.current_value || 0)} по текущему курсу</span>
              </p>
            </div>
            <span class="analytics-kpi-chip ${resultTone.chipClass}">${resultTone.label}: ${core.formatMoney(item.result_value || 0)}</span>
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
    tradeItemsById.clear();
    trades.forEach((item) => {
      if (item?.id) {
        tradeItemsById.set(Number(item.id), item);
      }
    });
    if (!trades.length) {
      const emptyLabel = state.currencyFilter && state.currencyFilter !== "all"
        ? `Сделок по ${core.formatCurrencyLabel(state.currencyFilter)} пока нет`
        : "Сделок по отслеживаемым валютам пока нет";
      el.currencyTradesBody.innerHTML = `<tr><td colspan="8" class="muted-small">${emptyLabel}</td></tr>`;
      return;
    }
    el.currencyTradesBody.innerHTML = trades.map((item) => {
      const menuItems = [
        `<button class="table-kebab-item" type="button" data-edit-currency-trade-id="${Number(item.id)}">Редактировать</button>`,
        `<button class="table-kebab-item danger" type="button" data-delete-currency-trade-id="${Number(item.id)}">Удалить</button>`,
      ].join("");
      return `
      <tr>
        <td>${core.formatDateRu(item.trade_date)}</td>
        <td>${item.side === "sell" ? "Продажа" : "Покупка"}</td>
        <td>${core.escapeHtml ? core.escapeHtml(core.formatCurrencyLabel(item.asset_currency)) : core.formatCurrencyLabel(item.asset_currency)}</td>
        <td>${core.formatAmount(item.quantity || 0)}</td>
        <td>${formatRateWithQuote(item.unit_price || 0, item.quote_currency || "BYN")}</td>
        <td>${core.formatMoney(item.fee || 0, { withCurrency: true, currency: item.quote_currency || "BYN" })}</td>
        <td>${core.escapeHtml ? core.escapeHtml(item.note || "") : (item.note || "")}</td>
        <td>
          ${core.renderInlineKebabMenu?.(`currency-trade-${Number(item.id)}`, menuItems, "Действия валютной сделки")}
        </td>
      </tr>
    `;
    }).join("");
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
    syncRateAssetOptions();
    return data;
  }

  async function submitCurrencyRate(event) {
    event.preventDefault();
    const refreshState = window.App.getRuntimeModule?.("inline-refresh-state") || {};
    await refreshState.withRefresh?.(el.currencyRatePanel || el.currencySection, async () => {
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
    }, "Обновляется курс");
    if (el.currencyRateValue) {
      el.currencyRateValue.value = "";
    }
    closeRatePanel();
    await loadCurrencySection({ force: true });
    core.setStatus("Текущий курс обновлен");
    core.invalidateUiRequestCache?.("dashboard:summary");
    getDashboardFeature().loadDashboard?.().catch(() => {});
    getAnalyticsCurrencyFeature().loadAnalyticsCurrency?.({ force: true }).catch(() => {});
  }

  async function openCurrencyTradeEdit(tradeId) {
    const trade = tradeItemsById.get(Number(tradeId));
    if (!trade) {
      core.setStatus("Сделка не найдена");
      return;
    }
    await getOperationModal().openCreateModalForCurrencyEdit?.(trade);
  }

  function deleteCurrencyTrade(tradeId) {
    const trade = tradeItemsById.get(Number(tradeId));
    if (!trade) {
      core.setStatus("Сделка не найдена");
      return;
    }
    const actionLabel = trade.side === "sell" ? "Продажа" : "Покупка";
    core.runDestructiveAction({
      confirmMessage: `Удалить валютную сделку «${actionLabel} ${core.formatCurrencyLabel(trade.asset_currency)}»?`,
      doDelete: async () => {
        await core.requestJson(`/api/v1/currency/trades/${Number(trade.id)}`, {
          method: "DELETE",
          headers: core.authHeaders(),
        });
        core.invalidateUiRequestCache?.("currency");
      },
      onAfterDelete: async () => {
        await refreshAfterTradeMutation();
      },
      toastMessage: "Валютная сделка удалена",
      onDeleteError: "Не удалось удалить валютную сделку",
    });
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
    if (el.openCurrencyRatePanelBtn) {
      el.openCurrencyRatePanelBtn.addEventListener("click", openRatePanel);
    }
    if (el.closeCurrencyRatePanelBtn) {
      el.closeCurrencyRatePanelBtn.addEventListener("click", closeRatePanel);
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
    if (el.currencyTradesBody) {
      el.currencyTradesBody.addEventListener("click", (event) => {
        const trigger = event.target.closest("[data-table-menu-trigger]");
        if (trigger) {
          event.preventDefault();
          event.stopPropagation();
          toggleTableMenu(trigger);
          return;
        }
        const editBtn = event.target.closest("[data-edit-currency-trade-id]");
        if (editBtn) {
          const tradeId = Number(editBtn.dataset.editCurrencyTradeId || 0);
          core.runAction({
            errorPrefix: "Ошибка открытия валютной сделки",
            action: () => openCurrencyTradeEdit(tradeId),
          });
          return;
        }
        const deleteBtn = event.target.closest("[data-delete-currency-trade-id]");
        if (deleteBtn) {
          const tradeId = Number(deleteBtn.dataset.deleteCurrencyTradeId || 0);
          deleteCurrencyTrade(tradeId);
        }
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
