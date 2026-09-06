(() => {
  const { state, el, core } = window.App;
  const media = () => window.App.getRuntimeModule?.("catalog-media") || {};
  const catalog = () => window.App.getRuntimeModule?.("item-catalog") || {};
  const operations = () => window.App.getRuntimeModule?.("operations") || {};
  const CACHE_TTL_MS = 20000;
  let requestController = null;
  let searchTimer = null;
  let bound = false;
  let editorProduct = null;

  function esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function asId(value) {
    const id = Number(value || 0);
    return Number.isInteger(id) && id > 0 ? id : null;
  }

  function normalizeOffer(raw = {}, product = {}) {
    const sourceName = String(raw.source_name || raw.shop_name || "").trim();
    return {
      ...raw,
      id: asId(raw.id || raw.template_id),
      template_id: asId(raw.template_id || raw.id),
      product_id: asId(raw.product_id || product.id),
      name: String(raw.name || raw.offer_name || product.name || "").trim(),
      source_id: asId(raw.source_id),
      source_name: sourceName,
      shop_name: sourceName,
      source_image_id: asId(raw.source_image_id),
      image_id: asId(raw.image_id || raw.item_image_id || product.image_id),
      latest_unit_price: raw.latest_unit_price == null ? null : Number(raw.latest_unit_price),
      latest_price_date: raw.latest_price_date || null,
      use_count: Number(raw.use_count || 0),
      last_used_at: raw.last_used_at || null,
      last_category_id: asId(raw.last_category_id || raw.category_id || product.category_id),
      brand_id: asId(raw.brand_id || product.brand_id),
      brand_name: raw.brand_name || product.brand_name || null,
      brand_accent_color: raw.brand_accent_color || product.brand_accent_color || null,
      brand_image_id: asId(raw.brand_image_id || product.brand_image_id),
    };
  }

  function normalizeProduct(raw = {}) {
    const offers = (Array.isArray(raw.offers) ? raw.offers : (raw.item_templates || []))
      .map((offer) => normalizeOffer(offer, raw))
      .filter((offer) => offer.id);
    const prices = offers.map((offer) => Number(offer.latest_unit_price)).filter((value) => value > 0);
    const latestOffer = offers.slice().sort((left, right) => (
      String(right.last_used_at || right.latest_price_date || "").localeCompare(String(left.last_used_at || left.latest_price_date || ""))
    ))[0] || null;
    return {
      ...raw,
      id: asId(raw.id || raw.product_id),
      name: String(raw.name || raw.product_name || "").trim(),
      image_id: asId(raw.image_id || raw.product_image_id),
      brand_id: asId(raw.brand_id),
      brand_name: raw.brand_name || null,
      brand_accent_color: raw.brand_accent_color || raw.accent_color || null,
      brand_image_id: asId(raw.brand_image_id),
      category_id: asId(raw.category_id || raw.last_category_id),
      category_name: raw.category_name || raw.last_category_name || null,
      category_icon: raw.category_icon || null,
      category_accent_color: raw.category_accent_color || raw.group_accent_color || null,
      offers,
      offers_count: Number(raw.offers_count ?? raw.offer_count ?? offers.length),
      sources_count: Number(raw.sources_count ?? new Set(offers.map((offer) => offer.source_id || offer.source_name.toLowerCase())).size),
      use_count: Number(raw.use_count || offers.reduce((sum, offer) => sum + Number(offer.use_count || 0), 0)),
      last_used_at: raw.last_used_at || latestOffer?.last_used_at || null,
      min_unit_price: raw.min_unit_price == null ? (prices.length ? Math.min(...prices) : null) : Number(raw.min_unit_price),
      max_unit_price: raw.max_unit_price == null ? (prices.length ? Math.max(...prices) : null) : Number(raw.max_unit_price),
      latest_price_date: raw.latest_price_date || latestOffer?.latest_price_date || null,
    };
  }

  function categoryMeta(product) {
    return (state.categories || []).find((item) => Number(item.id) === Number(product.category_id)) || {
      name: product.category_name || "Без категории",
      icon: product.category_icon || null,
      group_accent_color: product.category_accent_color || null,
    };
  }

  function brandMeta(product) {
    return (state.itemBrands || []).find((item) => Number(item.id) === Number(product.brand_id)) || {
      name: product.brand_name || "",
      accent_color: product.brand_accent_color || null,
      image_id: product.brand_image_id || null,
    };
  }

  function renderBrand(product) {
    const brand = brandMeta(product);
    if (!brand?.name) return "<span class='muted-small'>Без бренда</span>";
    const renderer = window.App.getRuntimeModule?.("item-brands")?.renderBrandChip;
    return typeof renderer === "function" ? renderer(brand) : esc(brand.name);
  }

  function renderCategory(product) {
    const category = categoryMeta(product);
    if (!product.category_id && !product.category_name) return "<span class='muted-small'>Без категории</span>";
    return core.renderCategoryChip?.({
      name: category.name || product.category_name || "Категория",
      icon: category.icon || category.group_icon || product.category_icon || null,
      accent_color: category.group_accent_color || category.accent_color || product.category_accent_color || null,
    }, "") || esc(category.name || product.category_name || "Категория");
  }

  function formatPriceRange(product) {
    const min = Number(product.min_unit_price || 0);
    const max = Number(product.max_unit_price || 0);
    if (!(min > 0) && !(max > 0)) return "—";
    if (!(max > 0) || Math.abs(min - max) < 0.000001) return core.formatMoney(min || max);
    return `${core.formatMoney(min)} – ${core.formatMoney(max)}`;
  }

  function productOfferSummary(product) {
    const labels = (product?.offers || []).map((offer) => {
      const source = String(offer.source_name || offer.shop_name || "").trim() || "Без источника";
      const price = Number(offer.latest_unit_price || 0);
      return price > 0 ? `${source} · ${core.formatMoney(price)}` : source;
    });
    return Array.from(new Set(labels)).join("; ") || "Без источника";
  }

  function renderOffer(product, offer) {
    const templateId = Number(offer.template_id || offer.id || 0);
    const source = offer.source_name || "Без источника";
    const image = media().renderThumb?.(offer.source_image_id, {
      kind: "source", size: "chip", alt: source, fallback: source.slice(0, 1),
    }) || "";
    return `
      <tr class="catalog-product-offer-row" data-catalog-product-offer-id="${templateId}" data-catalog-product-parent-id="${product.id}">
        <td></td>
        <td data-label="Предложение"><span class="catalog-product-tree-guide" aria-hidden="true">↳</span><span title="${esc(offer.name)}">${esc(offer.name)}</span></td>
        <td data-label="Источник"><span class="catalog-product-source-cell">${image}<span>${esc(source)}</span></span></td>
        <td data-label="Цена"><strong>${Number(offer.latest_unit_price || 0) > 0 ? core.formatMoney(offer.latest_unit_price) : "—"}</strong></td>
        <td data-label="Дата">${offer.latest_price_date ? esc(core.formatDateRu(offer.latest_price_date)) : "—"}</td>
        <td data-label="Покупок">${Number(offer.use_count || 0)}</td>
        <td colspan="2" class="catalog-product-offer-actions">
          <button class="btn btn-secondary btn-xs" type="button" data-product-offer-action="history" data-template-id="${templateId}">История цен</button>
          <button class="btn btn-secondary btn-xs" type="button" data-product-offer-action="operations" data-template-id="${templateId}">Операции</button>
          <button class="btn btn-secondary btn-xs" type="button" data-product-offer-action="edit" data-template-id="${templateId}">Изменить</button>
          <button class="btn btn-danger btn-xs" type="button" data-product-offer-action="detach" data-template-id="${templateId}" data-product-id="${product.id}">Отделить</button>
        </td>
      </tr>`;
  }

  function renderProduct(product) {
    const expanded = state.catalogProductExpandedIds.has(Number(product.id));
    const selected = state.selectedCatalogProductIds.has(Number(product.id));
    const thumb = media().renderThumb?.(product.image_id, {
      kind: "item", size: "row", alt: product.name, fallback: product.name.slice(0, 1),
    }) || "";
    const offerRows = expanded ? product.offers.map((offer) => renderOffer(product, offer)).join("") : "";
    return `
      <tr class="catalog-product-row ${expanded ? "is-expanded" : ""}" data-catalog-product-id="${product.id}">
        <td><input type="checkbox" data-select-catalog-product-id="${product.id}" ${selected ? "checked" : ""} aria-label="Выбрать ${esc(product.name)}" /></td>
        <td data-label="Товар">
          <button class="catalog-product-expand-btn" type="button" data-toggle-catalog-product="${product.id}" aria-expanded="${expanded}" aria-label="${expanded ? "Свернуть" : "Развернуть"} предложения">⌄</button>
          <button class="catalog-product-name-btn" type="button" data-open-catalog-product="${product.id}" title="Открыть карточку ${esc(product.name)}">${thumb}<span>${esc(product.name)}</span></button>
        </td>
        <td data-label="Бренд">${renderBrand(product)}</td>
        <td data-label="Категория">${renderCategory(product)}</td>
        <td data-label="Источники"><strong>${product.sources_count}</strong><span class="muted-small"> · ${product.offers_count} предл.</span></td>
        <td data-label="Цена"><strong>${formatPriceRange(product)}</strong></td>
        <td data-label="Последняя покупка">${product.last_used_at ? esc(core.formatDateRu(product.last_used_at)) : "—"}</td>
        <td class="catalog-product-row-actions"><button class="btn btn-secondary btn-xs" type="button" data-open-catalog-product-operations="${product.id}">Операции</button><button class="btn btn-secondary btn-xs" type="button" data-open-catalog-product="${product.id}">Изменить</button></td>
      </tr>${offerRows}`;
  }

  function renderKpis() {
    if (!el.catalogProductsKpiGrid) return;
    const products = state.catalogProducts || [];
    const offers = products.reduce((sum, product) => sum + Number(product.offers_count || 0), 0);
    const sources = new Set(products.flatMap((product) => product.offers.map((offer) => offer.source_id || offer.source_name.toLowerCase())).filter(Boolean));
    el.catalogProductsKpiGrid.innerHTML = `
      <article class="analytics-kpi-card analytics-kpi-neutral"><div class="muted-small">Товаров</div><strong>${Number(state.catalogProductsTotal || products.length)}</strong></article>
      <article class="analytics-kpi-card analytics-kpi-positive"><div class="muted-small">Предложений</div><strong>${offers}</strong></article>
      <article class="analytics-kpi-card analytics-kpi-neutral"><div class="muted-small">Источников</div><strong>${sources.size}</strong></article>
      <article class="analytics-kpi-card ${state.catalogProductMergeCandidatesTotal ? "analytics-kpi-neutral" : "analytics-kpi-positive"}"><div class="muted-small">Возможных дублей</div><strong>${state.catalogProductMergeCandidatesTotal}</strong></article>`;
  }

  function syncSelection() {
    const visibleIds = new Set((state.catalogProducts || []).map((product) => Number(product.id)));
    for (const id of Array.from(state.selectedCatalogProductIds)) {
      if (!visibleIds.has(Number(id))) state.selectedCatalogProductIds.delete(id);
    }
    const count = state.selectedCatalogProductIds.size;
    el.catalogProductsBulkBar?.classList.toggle("hidden", count < 2);
    if (el.catalogProductsSelectedCount) el.catalogProductsSelectedCount.textContent = `Выбрано: ${count}`;
    if (el.mergeCatalogProductsBtn) el.mergeCatalogProductsBtn.disabled = count < 2;
    if (el.catalogProductsSelectAll) {
      el.catalogProductsSelectAll.checked = Boolean(visibleIds.size) && count === visibleIds.size;
      el.catalogProductsSelectAll.indeterminate = count > 0 && count < visibleIds.size;
    }
  }

  function render() {
    if (!el.catalogProductsBody) return;
    const products = state.catalogProducts || [];
    el.catalogProductsBody.innerHTML = products.length
      ? products.map(renderProduct).join("")
      : `<tr><td colspan="8"><div class="empty">${state.catalogProductsLoading ? "Загрузка товаров…" : "Товары не найдены"}</div></td></tr>`;
    renderKpis();
    syncSelection();
    media().hydrate?.(el.catalogProductsBody);
  }

  function candidateIds(candidate) {
    const raw = candidate?.product_ids || candidate?.products || candidate?.items || [candidate?.target_product, candidate?.source_product, candidate?.left_product_id, candidate?.right_product_id, candidate?.source_product_id, candidate?.target_product_id];
    return Array.from(new Set((Array.isArray(raw) ? raw : []).map((item) => asId(item?.id || item)).filter(Boolean)));
  }

  function renderCandidates() {
    const candidates = state.catalogProductMergeCandidates || [];
    el.catalogProductsCandidatesBtn?.classList.toggle("hidden", !candidates.length);
    if (el.catalogProductsCandidatesCount) el.catalogProductsCandidatesCount.textContent = candidates.length ? `(${state.catalogProductMergeCandidatesTotal || candidates.length})` : "";
    if (!el.catalogProductsCandidatesPanel) return;
    el.catalogProductsCandidatesPanel.innerHTML = candidates.map((candidate, index) => {
      const ids = candidateIds(candidate);
      const embedded = (candidate?.products || [candidate?.target_product, candidate?.source_product]).filter(Boolean).map(normalizeProduct);
      const products = ids.map((id) => (state.catalogProducts || []).find((item) => Number(item.id) === id) || embedded.find((item) => Number(item.id) === id)).filter(Boolean);
      const label = String(candidate?.name || candidate?.normalized_name || products[0]?.name || "Похожие товары");
      const summaries = products.map((product) => `
        <span class="catalog-product-candidate-product">
          <b>${esc(product.name)}</b>
          <small>${esc(productOfferSummary(product))}</small>
        </span>`).join("");
      return `<article class="catalog-product-candidate"><div><strong>${esc(label)}</strong><div class="catalog-product-candidate-products">${summaries}</div><span class="muted-small">Совпадение по названию — проверьте перед объединением</span></div><button class="btn btn-secondary btn-xs" type="button" data-merge-candidate-index="${index}" ${ids.length < 2 ? "disabled" : ""}>Проверить и объединить</button></article>`;
    }).join("") || "<div class='empty'>Возможных совпадений нет</div>";
  }

  async function fetchAllProducts(query, signal) {
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (query) params.set("q", query);
    const first = await core.requestJson(`/api/v1/operations/catalog-products?${params}`, { headers: core.authHeaders(), signal });
    const items = (Array.isArray(first) ? first : (first.items || [])).slice();
    const total = Number(first?.total || items.length);
    const pageSize = Number(first?.page_size || 100) || 100;
    for (let page = 2; page <= Math.ceil(total / pageSize); page += 1) {
      const next = new URLSearchParams(params);
      next.set("page", String(page));
      const payload = await core.requestJson(`/api/v1/operations/catalog-products?${next}`, { headers: core.authHeaders(), signal });
      items.push(...(Array.isArray(payload) ? payload : (payload.items || [])));
    }
    return { items, total };
  }

  async function loadMergeCandidates(options = {}) {
    try {
      const payload = await core.requestJson("/api/v1/operations/catalog-products/merge-candidates?limit=500", { headers: core.authHeaders() });
      state.catalogProductMergeCandidates = Array.isArray(payload) ? payload : (payload?.items || payload?.candidates || []);
      state.catalogProductMergeCandidatesTotal = Number(payload?.total || state.catalogProductMergeCandidates.length);
    } catch (err) {
      if (options.silent !== true) throw err;
      state.catalogProductMergeCandidates = [];
      state.catalogProductMergeCandidatesTotal = 0;
    }
    renderCandidates();
    renderKpis();
  }

  async function load(options = {}) {
    const force = options.force === true;
    const query = String(el.catalogProductsSearchQ?.value || "").trim();
    const cacheKey = `catalog-products:q=${query.toLowerCase()}`;
    const cached = !force ? core.getUiRequestCache?.(cacheKey, CACHE_TTL_MS) : null;
    if (cached?.items) {
      state.catalogProducts = cached.items.map(normalizeProduct);
      state.catalogProductsTotal = Number(cached.total || state.catalogProducts.length);
      state.catalogProductsLoaded = true;
      render();
      return state.catalogProducts;
    }
    requestController?.abort();
    requestController = new AbortController();
    state.catalogProductsLoading = true;
    render();
    try {
      await Promise.all([
        window.App.getRuntimeModule?.("item-brands")?.ensureItemBrandsLoaded?.().catch(() => []),
        (state.categories || []).length ? Promise.resolve() : window.App.getRuntimeModule?.("category-actions")?.loadCategories?.().catch(() => []),
      ]);
      const payload = await fetchAllProducts(query, requestController.signal);
      state.catalogProducts = payload.items.map(normalizeProduct).filter((item) => item.id);
      state.catalogProductsTotal = payload.total;
      state.catalogProductsLoaded = true;
      core.setUiRequestCache?.(cacheKey, payload);
      render();
      if (!query) await loadMergeCandidates({ silent: true });
      return state.catalogProducts;
    } catch (err) {
      if (core.isAbortError?.(err)) return state.catalogProducts;
      throw err;
    } finally {
      state.catalogProductsLoading = false;
      requestController = null;
      render();
    }
  }

  function productById(productId) {
    return (state.catalogProducts || []).find((item) => Number(item.id) === Number(productId)) || null;
  }

  function offerById(templateId) {
    for (const product of state.catalogProducts || []) {
      const offer = product.offers.find((item) => Number(item.template_id || item.id) === Number(templateId));
      if (offer) return { product, offer };
    }
    return null;
  }

  function fillSelects(product = {}) {
    if (el.catalogProductBrand) {
      const brands = (state.itemBrands || []).filter((item) => !item.is_archived);
      el.catalogProductBrand.innerHTML = `<option value="">Без бренда</option>${brands.map((item) => `<option value="${item.id}">${esc(item.name)}</option>`).join("")}`;
      el.catalogProductBrand.value = product.brand_id ? String(product.brand_id) : "";
    }
    if (el.catalogProductCategory) {
      const categories = (state.categories || []).filter((item) => item.kind === "expense");
      el.catalogProductCategory.innerHTML = `<option value="">Без категории</option>${categories.map((item) => `<option value="${item.id}">${esc(item.name)}</option>`).join("")}`;
      el.catalogProductCategory.value = product.category_id ? String(product.category_id) : "";
    }
  }

  function renderModalOffers(product) {
    if (!el.catalogProductOffersList || !el.catalogProductOffersSection) return;
    el.catalogProductOffersSection.classList.toggle("hidden", !product?.id);
    el.catalogProductOffersList.innerHTML = (product?.offers || []).map((offer) => `
      <article class="catalog-product-modal-offer">
        <div class="catalog-product-source-cell">${media().renderThumb?.(offer.source_image_id, { kind: "source", size: "chip", alt: offer.source_name, fallback: offer.source_name?.slice(0, 1) }) || ""}<div><strong>${esc(offer.source_name || "Без источника")}</strong><span class="muted-small">${esc(offer.name)}</span></div></div>
        <div><strong>${Number(offer.latest_unit_price || 0) > 0 ? core.formatMoney(offer.latest_unit_price) : "—"}</strong><span class="muted-small">${offer.latest_price_date ? esc(core.formatDateRu(offer.latest_price_date)) : "Нет цены"}</span></div>
        <button class="btn btn-secondary btn-xs" type="button" data-product-modal-offer-edit="${offer.template_id}">Изменить</button>
      </article>`).join("") || "<div class='empty'>Предложений пока нет. Нажмите «Добавить источник» или выберите этот товар в чеке магазина.</div>";
    media().hydrate?.(el.catalogProductOffersList);
  }

  async function openEditor(productOrId = null) {
    const id = asId(productOrId?.id || productOrId);
    let product = id ? productById(id) : null;
    if (id && !product) {
      product = normalizeProduct(await core.requestJson(`/api/v1/operations/catalog-products/${id}`, { headers: core.authHeaders() }));
    }
    state.editCatalogProductId = product?.id || null;
    editorProduct = product;
    window.App.getRuntimeModule?.("activity")?.configureActivityButton?.(el.catalogProductActivityBtn, product ? "catalog_product" : null, product?.id);
    if (el.catalogProductModalTitle) el.catalogProductModalTitle.textContent = product ? "Редактировать товар" : "Новый товар";
    if (el.catalogProductName) el.catalogProductName.value = product?.name || "";
    fillSelects(product || {});
    renderModalOffers(product);
    el.deleteCatalogProductBtn?.classList.toggle("hidden", !product);
    if (el.submitCatalogProductBtn) el.submitCatalogProductBtn.textContent = product ? "Сохранить" : "Создать товар";
    media().resetPicker?.("catalog-product", { imageId: product?.image_id, kind: "item", label: product?.name || "Товар" });
    el.catalogProductModal?.classList.remove("hidden");
    core.bringModalToFront?.(el.catalogProductModal);
    setTimeout(() => el.catalogProductName?.focus(), 0);
  }

  function closeEditor() {
    state.editCatalogProductId = null;
    editorProduct = null;
    window.App.getRuntimeModule?.("activity")?.configureActivityButton?.(el.catalogProductActivityBtn, null, null);
    el.catalogProductModal?.classList.add("hidden");
    core.markModalClosed?.(el.catalogProductModal);
    el.catalogProductForm?.reset();
  }

  async function refreshOpenOffers(productId) {
    if (Number(state.editCatalogProductId) !== Number(productId) || el.catalogProductModal?.classList.contains("hidden")) return;
    const product = normalizeProduct(await core.requestJson(`/api/v1/operations/catalog-products/${productId}`, { headers: core.authHeaders() }));
    if (Number(state.editCatalogProductId) !== Number(productId)) return;
    editorProduct = product;
    state.catalogProducts = (state.catalogProducts || []).map((item) => Number(item.id) === Number(productId) ? product : item);
    // Refresh just the offers, preserving unsaved name/brand/photo edits above.
    renderModalOffers(product);
    render();
  }

  async function addSource() {
    const product = editorProduct;
    if (!product) return;
    await catalog().loadItemSources?.();
    if (editorProduct !== product) return;
    catalog().openItemTemplateModal?.({
      name: product.name, last_category_id: product.category_id,
      brand_id: product.brand_id, brand_name: product.brand_name,
      brand_accent_color: product.brand_accent_color, brand_image_id: product.brand_image_id,
      image_id: product.image_id,
    }, { product });
  }

  function invalidate() {
    core.invalidateUiRequestCache?.("catalog-products");
    core.invalidateUiRequestCache?.("op:receipt:products");
    core.invalidateUiRequestCache?.("op:receipt:templates");
    core.invalidateUiRequestCache?.("item-catalog");
    state.catalogProductsLoaded = false;
    state.receiptProductHints = [];
    state.receiptTemplateHints = [];
  }

  async function save(event) {
    event?.preventDefault?.();
    const id = asId(state.editCatalogProductId);
    const name = String(el.catalogProductName?.value || "").replace(/\s+/g, " ").trim();
    if (!name) return;
    const payload = {
      name,
      brand_id: asId(el.catalogProductBrand?.value),
      category_id: asId(el.catalogProductCategory?.value),
    };
    const saved = await core.requestJson(id ? `/api/v1/operations/catalog-products/${id}` : "/api/v1/operations/catalog-products", {
      method: id ? "PATCH" : "POST",
      headers: core.authHeaders(),
      body: JSON.stringify(payload),
    });
    const savedId = asId(saved?.id || id);
    if (savedId) await media().commitPicker?.("catalog-product", "product", savedId);
    invalidate();
    closeEditor();
    await Promise.all([load({ force: true }), catalog().loadItemCatalog?.({ force: true }).catch(() => {})]);
    core.showToast?.(id ? "Товар обновлён" : "Товар создан", { type: "success" });
  }

  function removeCurrent() {
    const product = productById(state.editCatalogProductId);
    if (!product) return;
    core.showConfirm?.(`Удалить товар «${product.name}»? Его предложения будут скрыты из каталога, а история покупок и цен сохранится.`, async () => {
      await core.requestJson(`/api/v1/operations/catalog-products/${product.id}`, { method: "DELETE", headers: core.authHeaders() });
      closeEditor();
      invalidate();
      await load({ force: true });
      core.showToast?.("Товар удалён", { type: "success" });
    });
  }

  function openMerge(idsInput) {
    const requested = idsInput || Array.from(state.selectedCatalogProductIds);
    const embedded = requested.filter((item) => item && typeof item === "object").map(normalizeProduct);
    const ids = Array.from(new Set(requested.map((item) => asId(item?.id || item)).filter(Boolean)));
    const products = ids.map((id) => productById(id) || embedded.find((item) => Number(item.id) === id)).filter(Boolean);
    if (products.length < 2) {
      core.showToast?.("Выберите минимум два товара", { type: "error" });
      return;
    }
    if (el.catalogProductMergeOptions) {
      el.catalogProductMergeOptions.innerHTML = products.map((product, index) => `
        <label class="catalog-product-merge-option">
          <input type="radio" name="catalogProductMergeTarget" value="${product.id}" ${index === 0 ? "checked" : ""} />
          ${media().renderThumb?.(product.image_id, { kind: "item", size: "picker", alt: product.name, fallback: product.name.slice(0, 1) }) || ""}
          <span><strong>${esc(product.name)}</strong><small class="catalog-product-merge-sources">${esc(productOfferSummary(product))}</small><small>${product.offers_count} предл. · ${product.sources_count} источн.</small></span>
        </label>`).join("");
    }
    if (el.catalogProductMergeWarning) {
      const sourceCounts = new Map();
      for (const product of products) {
        const seenInProduct = new Set();
        for (const offer of product.offers || []) {
          const key = offer.source_id ? `id:${offer.source_id}` : `name:${String(offer.source_name || "").toLowerCase()}`;
          if (key !== "name:") seenInProduct.add(key);
        }
        for (const key of seenInProduct) sourceCounts.set(key, Number(sourceCounts.get(key) || 0) + 1);
      }
      const conflicts = Array.from(sourceCounts.values()).filter((count) => count > 1).length;
      el.catalogProductMergeWarning.classList.toggle("hidden", !conflicts);
      el.catalogProductMergeWarning.textContent = conflicts
        ? `Обратите внимание: у выбранных карточек совпадают ${conflicts} источн. После объединения предложения каждого магазина останутся отдельными — цены и история не потеряются.`
        : "";
    }
    el.catalogProductMergeModal.dataset.productIds = ids.join(",");
    el.catalogProductMergeModal?.classList.remove("hidden");
    core.bringModalToFront?.(el.catalogProductMergeModal);
    media().hydrate?.(el.catalogProductMergeOptions);
  }

  function closeMerge() {
    el.catalogProductMergeModal?.classList.add("hidden");
    core.markModalClosed?.(el.catalogProductMergeModal);
    if (el.catalogProductMergeModal) el.catalogProductMergeModal.dataset.productIds = "";
  }

  async function merge(event) {
    event?.preventDefault?.();
    const targetId = asId(el.catalogProductMergeOptions?.querySelector('input[name="catalogProductMergeTarget"]:checked')?.value);
    const allIds = String(el.catalogProductMergeModal?.dataset.productIds || "").split(",").map(asId).filter(Boolean);
    const sourceIds = allIds.filter((id) => id !== targetId);
    if (!targetId || !sourceIds.length) return;
    const result = await core.requestJson(`/api/v1/operations/catalog-products/${targetId}/merge`, {
      method: "POST", headers: core.authHeaders(), body: JSON.stringify({ source_product_ids: sourceIds }),
    });
    closeMerge();
    state.selectedCatalogProductIds.clear();
    invalidate();
    await Promise.all([load({ force: true }), catalog().loadItemCatalog?.({ force: true }).catch(() => {})]);
    const conflictCount = Array.isArray(result?.source_conflicts) ? result.source_conflicts.length : 0;
    core.showToast?.(conflictCount ? `Товары объединены; в ${conflictCount} источн. сохранено несколько предложений` : "Товары объединены", { type: "success" });
  }

  async function detach(productId, templateId) {
    await core.requestJson(`/api/v1/operations/catalog-products/${productId}/offers/${templateId}/detach`, {
      method: "POST", headers: core.authHeaders(), body: JSON.stringify({}),
    });
    invalidate();
    await Promise.all([load({ force: true }), catalog().loadItemCatalog?.({ force: true }).catch(() => {})]);
    core.showToast?.("Предложение отделено в самостоятельный товар", { type: "success" });
  }

  function editOffer(templateId) {
    const found = offerById(templateId);
    if (!found) return;
    const category = categoryMeta(found.product);
    catalog().openItemTemplateModal?.({
      ...found.offer,
      id: found.offer.template_id,
      product_id: found.product.id,
      product_name: found.product.name,
      product_image_id: found.product.image_id,
      brand_id: found.product.brand_id,
      brand_name: found.product.brand_name,
      brand_accent_color: found.product.brand_accent_color,
      brand_image_id: found.product.brand_image_id,
      last_category_id: found.offer.last_category_id || found.product.category_id || category?.id || null,
    });
    core.bringModalToFront?.(el.itemTemplateModal);
  }

  function handleBodyClick(event) {
    const toggle = event.target.closest("[data-toggle-catalog-product]");
    if (toggle) {
      const id = Number(toggle.dataset.toggleCatalogProduct);
      state.catalogProductExpandedIds.has(id) ? state.catalogProductExpandedIds.delete(id) : state.catalogProductExpandedIds.add(id);
      render();
      return;
    }
    const open = event.target.closest("[data-open-catalog-product]");
    if (open) {
      core.runAction({ errorPrefix: "Не удалось открыть товар", action: () => openEditor(open.dataset.openCatalogProduct) });
      return;
    }
    const productOperations = event.target.closest("[data-open-catalog-product-operations]");
    if (productOperations) {
      const product = productById(productOperations.dataset.openCatalogProductOperations);
      if (product) operations().openOperationsForProduct?.(product.id, product.name);
      return;
    }
    const offerAction = event.target.closest("[data-product-offer-action]");
    if (!offerAction) return;
    const templateId = asId(offerAction.dataset.templateId);
    const productId = asId(offerAction.dataset.productId || offerAction.closest("[data-catalog-product-parent-id]")?.dataset.catalogProductParentId);
    const found = offerById(templateId);
    if (offerAction.dataset.productOfferAction === "edit") editOffer(templateId);
    if (offerAction.dataset.productOfferAction === "history" && found) catalog().openItemTemplateHistoryModal?.({ ...found.offer, id: templateId });
    if (offerAction.dataset.productOfferAction === "operations" && found) operations().openOperationsForItemTemplate?.(templateId, found.offer.name);
    if (offerAction.dataset.productOfferAction === "detach" && productId && templateId) {
      core.showConfirm?.(`Отделить предложение «${found?.offer?.name || "позиция"}» от товара?`, () => detach(productId, templateId), {
        title: "Отделить предложение", confirmLabel: "Отделить", confirmTone: "primary",
      });
    }
  }

  function bind() {
    if (bound) return;
    bound = true;
    el.catalogProductsBody?.addEventListener("click", handleBodyClick);
    el.catalogProductsBody?.addEventListener("change", (event) => {
      const input = event.target.closest("[data-select-catalog-product-id]");
      if (!input) return;
      const id = Number(input.dataset.selectCatalogProductId);
      input.checked ? state.selectedCatalogProductIds.add(id) : state.selectedCatalogProductIds.delete(id);
      syncSelection();
    });
    el.catalogProductsSelectAll?.addEventListener("change", () => {
      state.selectedCatalogProductIds.clear();
      if (el.catalogProductsSelectAll.checked) (state.catalogProducts || []).forEach((product) => state.selectedCatalogProductIds.add(Number(product.id)));
      render();
    });
    el.clearSelectedCatalogProductsBtn?.addEventListener("click", () => { state.selectedCatalogProductIds.clear(); render(); });
    el.mergeCatalogProductsBtn?.addEventListener("click", () => openMerge());
    el.refreshCatalogProductsBtn?.addEventListener("click", () => core.runAction({ errorPrefix: "Не удалось обновить товары", action: () => load({ force: true }) }));
    el.catalogProductsCollapseAllBtn?.addEventListener("click", () => { state.catalogProductExpandedIds.clear(); render(); });
    el.catalogProductsExpandAllBtn?.addEventListener("click", () => { (state.catalogProducts || []).forEach((item) => state.catalogProductExpandedIds.add(Number(item.id))); render(); });
    el.catalogProductsCandidatesBtn?.addEventListener("click", () => el.catalogProductsCandidatesPanel?.classList.toggle("hidden"));
    el.catalogProductsCandidatesPanel?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-merge-candidate-index]");
      if (button) {
        const candidate = state.catalogProductMergeCandidates[Number(button.dataset.mergeCandidateIndex)];
        openMerge(candidate?.products || [candidate?.target_product, candidate?.source_product].filter(Boolean));
      }
    });
    el.catalogProductsSearchQ?.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => core.runAction({ errorPrefix: "Не удалось найти товары", action: () => load({ force: true }) }), 220);
    });
    el.closeCatalogProductModalBtn?.addEventListener("click", closeEditor);
    el.addCatalogProductSourceBtn?.addEventListener("click", () => core.runAction({ errorPrefix: "Не удалось открыть добавление источника", action: addSource }));
    el.catalogProductForm?.addEventListener("submit", (event) => core.runAction({ errorPrefix: "Не удалось сохранить товар", action: () => save(event) }));
    el.deleteCatalogProductBtn?.addEventListener("click", removeCurrent);
    el.catalogProductOffersList?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-product-modal-offer-edit]");
      if (button) editOffer(button.dataset.productModalOfferEdit);
    });
    el.openCatalogProductOperationsBtn?.addEventListener("click", () => {
      const product = productById(state.editCatalogProductId);
      if (product) operations().openOperationsForProduct?.(product.id, product.name);
    });
    el.closeCatalogProductMergeModalBtn?.addEventListener("click", closeMerge);
    el.catalogProductMergeForm?.addEventListener("submit", (event) => core.runAction({ errorPrefix: "Не удалось объединить товары", action: () => merge(event) }));
    for (const modal of [el.catalogProductModal, el.catalogProductMergeModal]) {
      modal?.addEventListener("click", (event) => { if (event.target === modal) (modal === el.catalogProductModal ? closeEditor : closeMerge)(); });
    }
  }

  function cleanupRuntime() {
    requestController?.abort();
    requestController = null;
    clearTimeout(searchTimer);
    state.catalogProducts = [];
    state.catalogProductsTotal = 0;
    state.catalogProductsLoaded = false;
    state.catalogProductMergeCandidates = [];
    state.catalogProductMergeCandidatesTotal = 0;
    state.catalogProductExpandedIds = new Set();
    state.selectedCatalogProductIds = new Set();
    state.editCatalogProductId = null;
    editorProduct = null;
  }

  window.App.registerRuntimeModule?.("catalog-products", {
    bind, load, render, invalidate, openEditor, closeEditor, openMerge, closeMerge, cleanupRuntime, refreshOpenOffers,
    normalizeProduct, normalizeOffer, productById,
  });
})();
