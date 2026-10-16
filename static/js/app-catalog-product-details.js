(() => {
  const {core, el} = window.App;
  const node = (id) => document.getElementById(id);
  const esc = (value) => core.escapeHtml(String(value ?? ""));
  const catalog = () => window.App.getRuntimeModule("catalog-products");
  let product = null, tab = "product", controller = null, generation = 0, page = 0, bound = false;
  let purchaseRows = [], purchaseTotal = 0, nestedOperation = false, returnTarget = null, purchasesDirty = false;
  let offerReturnId = null, workspaceGeneration = 0;
  let preferredPriceSeries = null;
  const visible = () => product && !el.catalogProductModal.classList.contains("hidden");

  function cancel() { generation += 1; controller?.abort(); controller = null; }
  function resetOptions() {
    const options = (product?.offers || []).map((offer) => `<option value="${Number(offer.template_id)}">${esc(offer.source_name || "Без источника")} · ${esc(offer.name)}</option>`).join("");
    for (const id of ["catalogProductPriceOffer", "catalogProductPurchaseOffer"]) {
      const select = node(id), previous = select.value;
      select.innerHTML = (id.includes("Purchase") ? '<option value="">Все предложения товара</option>' : "") + options;
      if ([...select.options].some((o) => o.value === previous)) select.value = previous;
    }
  }
  function errorHtml(error) {
    return `<div class="form-error">Не удалось загрузить данные: ${esc(error?.message || error)}</div><button class="btn btn-secondary" type="button" data-product-detail-retry>Повторить</button>`;
  }
  async function loadPrices({preserve = false} = {}) {
    cancel();
    const token = generation, target = node("catalogProductPricesList");
    const offerId = Number(node("catalogProductPriceOffer").value);
    if (!offerId) { target.innerHTML = '<div class="empty">Добавьте предложение во вкладке «Предложения».</div>'; return; }
    const purchases = node("catalogProductPriceMode").value === "purchases";
    node("catalogProductHistoryControls").classList.toggle("hidden", !purchases);
    node("catalogProductLegacyPriceNote").classList.toggle("hidden", purchases);
    const params = new URLSearchParams({template_id: offerId, basis: node("catalogProductPriceBasis").value, price_kind: node("catalogProductPriceKind").value});
    if (node("catalogProductPriceFrom").value) params.set("date_from", node("catalogProductPriceFrom").value);
    if (node("catalogProductPriceTo").value) params.set("date_to", node("catalogProductPriceTo").value);
    controller = new AbortController();
    target.innerHTML = '<div class="muted-small">Загрузка цен…</div>';
    try {
      const url = purchases ? `/api/v1/operations/catalog-products/${product.id}/price-observations?${params}` : `/api/v1/operations/item-templates/${offerId}/prices?limit=200`;
      const rows = await core.requestJson(url, {headers: core.authHeaders(), signal: controller.signal});
      if (token !== generation || !visible()) return;
      if (purchases) { window.App.getRuntimeModule("catalog-price-history").render(rows, preserve, preferredPriceSeries); preferredPriceSeries = null; return; }
      target.innerHTML = (rows || []).map((row) => `<article class="catalog-product-price-row"><span>${esc(core.formatDateRu(row.recorded_at))}</span><strong>${core.formatMoney(row.unit_price)}</strong><button class="btn btn-danger btn-icon" title="Удалить цену" aria-label="Удалить цену" type="button" data-product-price-delete="${Number(row.id)}" data-offer-id="${offerId}">${window.App.icons.svg("trash")}</button></article>`).join("") || '<div class="empty">История цен пока пустая</div>';
      if (rows?.length === 200) target.insertAdjacentHTML("beforeend", '<p class="muted-small">Показаны последние 200 записей.</p>');
    } catch (error) { if (token === generation && error.name !== "AbortError") target.innerHTML = errorHtml(error); }
  }
  function renderPurchases() {
    node("catalogProductPurchasesList").innerHTML = purchaseRows.map((item) => {
      const id = Number(item.source_id), matching = (item.receipt_items || []).filter((row) => Number(row.product_id) === Number(product.id));
      const shops = [...new Set(matching.map((row) => row.shop_name).filter(Boolean))].join(" · ");
      return `<button type="button" class="catalog-product-purchase-row" data-product-purchase-id="${id}"><span><strong>${esc(core.formatDateRu(item.event_date))}</strong><small>${esc(shops || item.title || "Операция")}</small></span><span><strong>${core.formatMoney(item.amount || 0, {currency: item.base_currency || item.currency})}</strong><small>Операция целиком</small></span></button>`;
    }).join("") || '<div class="empty">Операций с этим товаром пока нет</div>';
    node("catalogProductMorePurchases").classList.toggle("hidden", purchaseRows.length >= purchaseTotal);
  }
  async function loadPurchases(more = false) {
    cancel();
    const token = generation, target = node("catalogProductPurchasesList"), button = node("catalogProductMorePurchases");
    const nextPage = more ? page + 1 : 1;
    if (!more) { purchaseRows = []; page = 0; target.innerHTML = '<div class="muted-small">Загрузка покупок…</div>'; button.classList.add("hidden"); }
    button.disabled = true;
    controller = new AbortController();
    const params = new URLSearchParams({source: "operation", product_id: product.id, page: nextPage, page_size: "50", sort_by: "operation_date", sort_dir: "desc"});
    if (node("catalogProductPurchaseOffer").value) params.set("item_template_id", node("catalogProductPurchaseOffer").value);
    try {
      const payload = await core.requestJson(`/api/v1/operations/money-flow?${params}`, {headers: core.authHeaders(), signal: controller.signal});
      if (token !== generation || !visible()) return;
      purchaseRows.push(...(payload.items || []));
      purchaseTotal = Number(payload.total || 0); page = nextPage;
      renderPurchases();
    } catch (error) {
      if (token === generation && error.name !== "AbortError") {
        if (more) core.showToast?.("Не удалось загрузить следующую страницу. Попробуйте ещё раз.", {type: "error"});
        else target.innerHTML = errorHtml(error);
      }
    } finally { if (token === generation) button.disabled = false; }
  }
  function select(next, offerId) {
    cancel();
    tab = product && ["product", "offers", "prices", "purchases"].includes(next) ? next : "product";
    for (const panel of el.catalogProductModal.querySelectorAll("[data-product-panel]")) panel.classList.toggle("hidden", panel.dataset.productPanel !== tab);
    for (const button of node("catalogProductTabs").querySelectorAll("button")) {
      button.classList.toggle("active", button.dataset.productTab === tab);
      button.setAttribute("aria-pressed", String(button.dataset.productTab === tab));
    }
    if (offerId) {
      for (const id of ["catalogProductPriceOffer", "catalogProductPurchaseOffer"]) node(id).value = String(offerId);
    }
    if (tab === "prices") loadPrices();
    if (tab === "purchases") loadPurchases();
    if (tab === "offers" && offerId) {
      const offer = el.catalogProductOffersList.querySelector(`[data-modal-offer-id="${Number(offerId)}"]`);
      offer?.scrollIntoView({block: "nearest"});
      offer?.querySelector("button")?.focus({preventScroll: true});
    }
  }
  async function removePrice(button) {
    const productId = product.id, offerId = Number(button.dataset.offerId), priceId = Number(button.dataset.productPriceDelete);
    core.runDestructiveAction({
      confirmTitle: "Удалить цену из истории?", confirmMessage: "Цена в уже сохранённой операции не изменится.", confirmLabel: "Удалить цену",
      doDelete: () => core.requestJson(`/api/v1/operations/item-templates/${offerId}/prices/${priceId}`, {method: "DELETE", headers: core.authHeaders()}),
      onAfterDelete: async () => {
        catalog().invalidate();
        await catalog().refreshOpenOffers(productId);
        await Promise.all([catalog().load({force: true}), window.App.getRuntimeModule("item-catalog").loadItemCatalog({force: true})]);
      }, onDeleteError: "Не удалось удалить цену",
    });
  }
  async function openPurchase(button) {
    // Opening another operation must never overwrite an existing receipt edit draft.
    if (!el.editModal.classList.contains("hidden")) {
      core.showToast?.("Сначала завершите редактирование открытой операции.", {type: "error"}); return;
    }
    returnTarget = button; purchasesDirty = false;
    await window.App.getRuntimeModule("operations").openMoneyFlowSource({sourceKind: "operation", sourceId: Number(button.dataset.productPurchaseId), mode: "edit"});
    nestedOperation = true;
    core.bringModalToFront?.(el.editModal);
  }
  function bind() {
    if (bound) return; bound = true;
    const conditions = window.App.taskDialogs.attach(node('catalogProductHistoryControls').querySelector('.product-price-controls'), 'Сравнение и период', node('catalogProductHistoryControls'));
    conditions.id = 'catalogProductConditionsDialog'; conditions.trigger.id = 'catalogProductConditionsButton';
    el.catalogProductModal.addEventListener("change", event => { if (event.target.closest('[data-product-panel="prices"]')) node("catalogProductComparisonSummary").classList.add("hidden"); });
    document.addEventListener("app:activity-changed", (event) => {
      const {method, path} = event.detail || {};
      if (["POST", "PUT", "PATCH", "DELETE"].includes(method) && String(path).startsWith("/api/v1/operations")) node("catalogProductComparisonSummary").classList.add("hidden");
      if (nestedOperation && ["PATCH", "DELETE"].includes(method) && /^\/api\/v1\/operations\/\d+$/.test(path || "")) purchasesDirty = true;
    });
    new MutationObserver(() => {
      if (!visible() || !el.itemTemplateModal.classList.contains("hidden")) return;
      const target = offerReturnId
        ? el.catalogProductOffersList.querySelector(`[data-product-offer-action="edit"][data-template-id="${offerReturnId}"]`)
        : el.addCatalogProductSourceBtn;
      if (tab === "offers") target?.focus({preventScroll: true});
    }).observe(el.itemTemplateModal, {attributes: true, attributeFilter: ["class"]});
    node("catalogProductTabs").addEventListener("click", (event) => {
      const button = event.target.closest("[data-product-tab]");
      if (button) select(button.dataset.productTab);
    });
    for (const id of ["catalogProductPriceOffer", "catalogProductPriceMode", "catalogProductPriceKind", "catalogProductPriceBasis", "catalogProductPriceFrom", "catalogProductPriceTo"]) node(id).addEventListener("change", loadPrices);
    node("catalogProductPurchaseOffer").addEventListener("change", () => loadPurchases());
    node("catalogProductMorePurchases").addEventListener("click", () => loadPurchases(true));
    el.catalogProductModal.addEventListener("click", (event) => {
      const offerButton = event.target.closest('[data-product-offer-action="edit"]');
      if (offerButton) offerReturnId = Number(offerButton.dataset.templateId);
      if (event.target.closest("#addCatalogProductSourceBtn")) offerReturnId = null;
      if (event.target.closest("[data-product-detail-retry]")) select(tab);
      const price = event.target.closest("[data-product-price-delete]");
      if (price) core.runAction({errorPrefix: "Не удалось удалить цену", action: () => removePrice(price)});
      const purchase = event.target.closest("[data-product-purchase-id]");
      if (purchase) core.runAction({errorPrefix: "Не удалось открыть покупку", action: () => openPurchase(purchase)});
    });
    new MutationObserver(() => {
      if (!nestedOperation || !el.editModal.classList.contains("hidden")) return;
      nestedOperation = false;
      if (!visible()) return;
      core.bringModalToFront?.(el.catalogProductModal);
      returnTarget?.focus({preventScroll: true});
      if (tab === "prices" && purchasesDirty) {
        const id = returnTarget?.dataset.productPurchaseId, workspace = workspaceGeneration;
        const card = el.catalogProductModal.querySelector(".modal-card"), scrollTop = card.scrollTop;
        loadPrices({preserve: true}).then(() => {
          if (workspace === workspaceGeneration && visible() && tab === "prices") {
            node("catalogProductPricesList").querySelector(`[data-product-purchase-id="${Number(id)}"]`)?.focus({preventScroll: true});
            card.scrollTop = scrollTop;
          }
        });
      }
      // Keep the product draft and reload current receipt results after an edit/delete.
      if (tab === "purchases" && purchasesDirty) {
        const pages = page, id = returnTarget?.dataset.productPurchaseId;
        const card = el.catalogProductModal.querySelector(".modal-card"), scrollTop = card.scrollTop;
        const owner = product.id, workspace = workspaceGeneration;
        core.runAction({errorPrefix: "Не удалось обновить покупки", action: async () => {
          await loadPurchases();
          while (workspace === workspaceGeneration && visible() && product.id === owner && tab === "purchases" && page > 0 && page < pages && purchaseRows.length < purchaseTotal) { const previous = page; await loadPurchases(true); if (page === previous) break; }
          if (workspace !== workspaceGeneration || !visible() || product.id !== owner || tab !== "purchases") return;
          node("catalogProductPurchasesList").querySelector(`[data-product-purchase-id="${Number(id)}"]`)?.focus({preventScroll: true});
          card.scrollTop = scrollTop;
        }});
      }
    }).observe(el.editModal, {attributes: true, attributeFilter: ["class"]});
  }
  function open(value, options = {}) {
    workspaceGeneration += 1;
    bind(); product = value; nestedOperation = false; preferredPriceSeries = options.priceSeries || null;
    window.App.getRuntimeModule("catalog-product-codes").open(value);
    node("catalogProductTabs").classList.toggle("hidden", !product);
    node("catalogProductPriceOffer").innerHTML = ""; node("catalogProductPurchaseOffer").innerHTML = "";
    node("catalogProductPriceMode").value = "purchases";
    node("catalogProductPriceKind").value = "paid"; node("catalogProductPriceBasis").value = "unit";
    node("catalogProductPriceFrom").value = ""; node("catalogProductPriceTo").value = "";
    if (options.priceFilters) {
      node("catalogProductPriceKind").value = options.priceFilters.price_kind || "paid";
      node("catalogProductPriceBasis").value = options.priceFilters.basis || "unit";
      node("catalogProductPriceFrom").value = options.priceFilters.date_from || "";
      node("catalogProductPriceTo").value = options.priceFilters.date_to || "";
    }
    const summary = node("catalogProductComparisonSummary");
    summary.innerHTML = options.comparisonHtml || "";
    summary.classList.toggle("hidden", !options.comparisonHtml);
    resetOptions(); select(options.tab || "product", options.offerId);
  }
  function close() { window.App.getRuntimeModule("catalog-product-codes").close(); window.App.getRuntimeModule("catalog-price-history").cleanup(); workspaceGeneration += 1; cancel(); product = null; nestedOperation = false; returnTarget = null; }
  function refresh(value) { window.App.getRuntimeModule("catalog-product-codes").refresh(value); product = value; resetOptions(); select(tab); }
  window.App.registerRuntimeModule("catalog-product-details", {open, close, refresh, select, cleanup: close});
})();
