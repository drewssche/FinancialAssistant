(() => {
  function createAnalyticsCurrencyTradesFeature(deps) {
    const {
      state,
      el,
      core,
      escapeHtml,
      formatRateWithQuote,
    } = deps;
    let tradesObserver = null;

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
        el.analyticsCurrencyTradesInfiniteSentinel?.classList.add("hidden");
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
      el.analyticsCurrencyTradesInfiniteSentinel?.classList.toggle("hidden", !state.analyticsCurrencyTradesHasMore);
    }

    function appendUniqueTrades(items) {
      const existing = new Set(
        (state.analyticsCurrencyTradesItems || [])
          .map((item) => Number(item?.id || 0))
          .filter((id) => id > 0),
      );
      const nextItems = Array.isArray(state.analyticsCurrencyTradesItems)
        ? [...state.analyticsCurrencyTradesItems]
        : [];
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
      state.analyticsCurrencyTradesItems = nextItems;
    }

    async function loadTradesPage(page, options = {}) {
      const reset = options.reset === true;
      if (state.analyticsCurrencyTradesLoading && !reset) {
        return;
      }
      state.analyticsCurrencyTradesLoading = true;
      try {
        const params = new URLSearchParams({
          page: String(page),
          page_size: String(state.analyticsCurrencyTradesPageSize || 20),
        });
        if (state.analyticsCurrencyFilter && state.analyticsCurrencyFilter !== "all") {
          params.set("currency", state.analyticsCurrencyFilter);
        }
        const data = await core.requestJson(`/api/v1/currency/trades?${params.toString()}`, {
          headers: core.authHeaders(),
        });
        if (reset) {
          state.analyticsCurrencyTradesItems = Array.isArray(data.items) ? data.items : [];
        } else {
          appendUniqueTrades(data.items);
        }
        state.analyticsCurrencyTradesPage = Number(data.page || page);
        state.analyticsCurrencyTradesTotal = Number(data.total || 0);
        state.analyticsCurrencyTradesHasMore = (
          state.analyticsCurrencyTradesItems.length < state.analyticsCurrencyTradesTotal
        );
        renderTrades({ recent_trades: state.analyticsCurrencyTradesItems });
      } finally {
        state.analyticsCurrencyTradesLoading = false;
      }
    }

    async function loadMoreTrades() {
      if (!state.analyticsCurrencyTradesHasMore || state.analyticsCurrencyTradesLoading) {
        return;
      }
      await loadTradesPage(Number(state.analyticsCurrencyTradesPage || 1) + 1);
    }

    function bindInfiniteScroll() {
      if (!el.analyticsCurrencyTradesInfiniteSentinel || !("IntersectionObserver" in window)) {
        return;
      }
      tradesObserver?.disconnect();
      tradesObserver = new IntersectionObserver(
        (entries) => {
          const entry = entries[0];
          if (!entry?.isIntersecting) {
            return;
          }
          if (state.activeSection !== "analytics" || state.analyticsTab !== "currency") {
            return;
          }
          if (!state.analyticsCurrencyTradesHasMore || state.analyticsCurrencyTradesLoading) {
            return;
          }
          loadMoreTrades().catch((err) => core.setStatus(String(err)));
        },
        { root: null, rootMargin: "240px 0px", threshold: 0 },
      );
      tradesObserver.observe(el.analyticsCurrencyTradesInfiniteSentinel);
    }

    return {
      renderTrades,
      loadTradesPage,
      loadMoreTrades,
      bindInfiniteScroll,
    };
  }

  window.App.registerRuntimeModule?.(
    "analytics-currency-trades-factory",
    createAnalyticsCurrencyTradesFeature,
  );
})();
