(() => {
  function createCurrencyTradesFeature(deps) {
    const {
      state,
      el,
      core,
      pickerUtils,
      formatTradeQuoteTotal,
      formatRateWithQuote,
      openCurrencyTradeEdit,
      deleteCurrencyTrade,
      openLinkedOperation,
      deleteLinkedOperation,
    } = deps;
    const tradeItemsById = new Map();
    let tradesObserver = null;

    function toggleTableMenu(trigger) {
      const menuId = String(trigger?.dataset.tableMenuTrigger || "");
      const menu = menuId
        ? document.querySelector(`.table-kebab-popover[data-table-menu="${CSS.escape(menuId)}"]`)
        : null;
      const ownerRow = trigger?.closest("tr");
      const ownerCell = trigger?.closest("td");
      if (!menu || !pickerUtils?.setPopoverOpen) {
        return false;
      }
      const clearOpenState = () => {
        ownerCell?.classList.remove("table-menu-open-cell");
        ownerRow?.classList.remove("table-menu-open-row");
      };
      const shouldOpen = menu.classList.contains("hidden");
      document.querySelectorAll(".table-kebab-popover:not(.hidden)").forEach((node) => {
        if (node === menu) {
          return;
        }
        pickerUtils.setPopoverOpen(node, false, {
          owners: Array.isArray(node.__appPopoverOwners) ? node.__appPopoverOwners : [],
        });
        (Array.isArray(node.__appPopoverOwners) ? node.__appPopoverOwners : []).forEach((owner) => owner?.blur?.());
        node.closest(".table-menu-open-cell")?.classList.remove("table-menu-open-cell");
        node.closest(".table-menu-open-row")?.classList.remove("table-menu-open-row");
      });
      pickerUtils.setPopoverOpen(menu, shouldOpen, {
        owners: [trigger, trigger?.parentElement].filter(Boolean),
        onClose: clearOpenState,
      });
      ownerCell?.classList.toggle("table-menu-open-cell", shouldOpen);
      ownerRow?.classList.toggle("table-menu-open-row", shouldOpen);
      if (!shouldOpen) {
        clearOpenState();
        trigger?.blur?.();
      }
      return true;
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
        el.currencyTradesBody.innerHTML = `<tr><td colspan="7" class="muted-small">${emptyLabel}</td></tr>`;
        el.currencyTradesInfiniteSentinel?.classList.add("hidden");
        return;
      }
      el.currencyTradesBody.innerHTML = trades.map((item) => {
        const isLinkedSettlement = item.trade_kind === "card_payment" && Number(item.linked_operation_id || 0) > 0;
        const sideClass = isLinkedSettlement || item.side === "sell" ? "expense" : "income";
        const sideLabel = isLinkedSettlement ? "Оплата картой" : item.side === "sell" ? "Продажа" : "Покупка";
        const linkedMeta = isLinkedSettlement
          ? `<div class="currency-trade-meta"><span class="meta-chip meta-chip-info">Связано с операцией</span><button class="meta-chip-btn meta-chip-btn-neutral" type="button" data-open-linked-operation-id="${Number(item.linked_operation_id)}">Открыть</button></div>`
          : "";
        const menuItems = isLinkedSettlement
          ? [
            `<button class="btn btn-secondary" type="button" data-open-linked-operation-id="${Number(item.linked_operation_id)}">Открыть операцию</button>`,
            `<button class="btn btn-secondary" type="button" data-activity-entity-type="currency_trade" data-activity-entity-id="${Number(item.id)}">Журнал</button>`,
            `<button class="btn btn-danger" type="button" data-delete-linked-operation-id="${Number(item.linked_operation_id)}">Удалить операцию</button>`,
          ].join("")
          : [
            `<button class="btn btn-secondary" type="button" data-activity-entity-type="currency_trade" data-activity-entity-id="${Number(item.id)}">Журнал</button>`,
            `<button class="btn btn-secondary" type="button" data-edit-currency-trade-id="${Number(item.id)}">Редактировать</button>`,
            `<button class="btn btn-danger" type="button" data-delete-currency-trade-id="${Number(item.id)}">Удалить</button>`,
          ].join("");
        return `
          <tr class="table-record-open-row" data-currency-trade-row-id="${Number(item.id)}">
            <td data-label="Дата">${core.formatDateRu(item.trade_date)}</td>
            <td data-label="Действие"><span class="kind-pill kind-pill-${sideClass}">${sideLabel}</span></td>
            <td data-label="Валюта">${core.escapeHtml?.(core.formatCurrencyLabel(item.asset_currency)) || core.formatCurrencyLabel(item.asset_currency)}</td>
            <td data-label="Количество">${core.formatAmount(item.quantity || 0)} ${core.escapeHtml?.(item.asset_currency || "") || (item.asset_currency || "")}<div class="muted-small">≈ ${formatTradeQuoteTotal(item)}</div></td>
            <td data-label="Курс">${formatRateWithQuote(item.unit_price || 0, item.quote_currency || "BYN")}</td>
            <td class="mobile-note-cell" data-label="Комментарий"><div class="currency-trade-note">${linkedMeta}${core.escapeHtml?.(item.note || "") || (item.note || "")}</div></td>
            <td class="mobile-actions-cell table-kebab-cell" data-label="Действия">
              ${core.renderInlineKebabMenu?.(`currency-trade-${Number(item.id)}`, menuItems, "Действия валютной сделки", "operation-row-kebab") || '<span class="muted-small">Через операцию</span>'}
            </td>
          </tr>
        `;
      }).join("");
      el.currencyTradesInfiniteSentinel?.classList.toggle("hidden", !state.currencyTradesHasMore);
    }

    function appendUniqueTrades(items) {
      const existing = new Set(
        (state.currencyTradesItems || []).map((item) => Number(item?.id || 0)).filter((id) => id > 0),
      );
      const nextItems = Array.isArray(state.currencyTradesItems) ? [...state.currencyTradesItems] : [];
      for (const item of Array.isArray(items) ? items : []) {
        const tradeId = Number(item?.id || 0);
        if (tradeId > 0 && existing.has(tradeId)) {
          continue;
        }
        if (tradeId > 0) {
          existing.add(tradeId);
        }
        nextItems.push(item);
      }
      state.currencyTradesItems = nextItems;
    }

    async function loadTradesPage(page, options = {}) {
      const reset = options.reset === true;
      if (state.currencyTradesLoading && !reset) {
        return;
      }
      state.currencyTradesLoading = true;
      try {
        const params = new URLSearchParams({
          page: String(page),
          page_size: String(state.currencyTradesPageSize || 20),
        });
        if (state.currencyFilter && state.currencyFilter !== "all") {
          params.set("currency", state.currencyFilter);
        }
        const data = await core.requestJson(`/api/v1/currency/trades?${params.toString()}`, {
          headers: core.authHeaders(),
        });
        if (reset) {
          state.currencyTradesItems = Array.isArray(data.items) ? data.items : [];
        } else {
          appendUniqueTrades(data.items);
        }
        state.currencyTradesPage = Number(data.page || page);
        state.currencyTradesTotal = Number(data.total || 0);
        state.currencyTradesHasMore = state.currencyTradesItems.length < state.currencyTradesTotal;
        renderTrades({ recent_trades: state.currencyTradesItems });
      } finally {
        state.currencyTradesLoading = false;
      }
    }

    async function loadMoreTrades() {
      if (!state.currencyTradesHasMore || state.currencyTradesLoading) {
        return;
      }
      await loadTradesPage(Number(state.currencyTradesPage || 1) + 1);
    }

    function bindInfiniteScroll() {
      if (!el.currencyTradesInfiniteSentinel || !("IntersectionObserver" in window)) {
        return;
      }
      tradesObserver?.disconnect();
      tradesObserver = new IntersectionObserver((entries) => {
        if (!entries[0]?.isIntersecting || state.activeSection !== "currency") {
          return;
        }
        if (!state.currencyTradesHasMore || state.currencyTradesLoading) {
          return;
        }
        loadMoreTrades().catch((err) => core.setStatus(String(err)));
      }, { root: null, rootMargin: "240px 0px", threshold: 0 });
      tradesObserver.observe(el.currencyTradesInfiniteSentinel);
    }

    function handleActionClick(event) {
      const actionMap = [
        ["[data-edit-currency-trade-id]", "editCurrencyTradeId", openCurrencyTradeEdit, "Ошибка открытия валютной сделки"],
        ["[data-delete-currency-trade-id]", "deleteCurrencyTradeId", deleteCurrencyTrade, ""],
        ["[data-open-linked-operation-id]", "openLinkedOperationId", openLinkedOperation, "Ошибка открытия связанной операции"],
        ["[data-delete-linked-operation-id]", "deleteLinkedOperationId", deleteLinkedOperation, "Ошибка удаления связанной операции"],
      ];
      for (const [selector, dataKey, action, errorPrefix] of actionMap) {
        const button = event.target.closest(selector);
        if (!button) {
          continue;
        }
        const id = Number(button.dataset[dataKey] || 0);
        if (errorPrefix) {
          core.runAction({ errorPrefix, action: () => action(id) });
        } else {
          action(id);
        }
        return true;
      }
      return false;
    }

    function bind() {
      el.currencyTradesBody?.addEventListener("click", (event) => {
        const trigger = event.target.closest("[data-table-menu-trigger]");
        if (trigger) {
          event.preventDefault();
          event.stopPropagation();
          toggleTableMenu(trigger);
          return;
        }
        if (handleActionClick(event)) {
          return;
        }
        const row = event.target.closest("tr[data-currency-trade-row-id]");
        if (!row || event.target.closest("button, a, input, select, textarea, label, .app-popover")) {
          return;
        }
        const trade = tradeItemsById.get(Number(row.dataset.currencyTradeRowId || 0));
        if (trade?.trade_kind === "card_payment" && Number(trade.linked_operation_id || 0) > 0) {
          core.runAction({
            errorPrefix: "Ошибка открытия связанной операции",
            action: () => openLinkedOperation(Number(trade.linked_operation_id)),
          });
          return;
        }
        if (trade?.id) {
          core.runAction({
            errorPrefix: "Ошибка открытия валютной сделки",
            action: () => openCurrencyTradeEdit(Number(trade.id)),
          });
        }
      });
      document.addEventListener("click", (event) => {
        if (event.target.closest(".table-kebab-popover[data-table-menu^=\"currency-trade-\"]")) {
          handleActionClick(event);
        }
      });
    }

    bind();
    return {
      loadTradesPage,
      loadMoreTrades,
      bindInfiniteScroll,
      getTradeById: (tradeId) => tradeItemsById.get(Number(tradeId)) || null,
    };
  }

  window.App.registerRuntimeModule?.("currency-trades-factory", createCurrencyTradesFeature);
})();
