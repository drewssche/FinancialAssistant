(() => {
  function createOperationModalReceiptPickerFeature(deps) {
    const {
      state,
      el,
      core,
      receiptUiState,
      normalizeReceiptName,
      getReceiptModeFromNode,
      RECEIPT_TEMPLATES_CACHE_TTL_MS,
    } = deps;

    function getPickerUtils() {
      return window.App.getRuntimeModule?.("picker-utils");
    }

    function getCategoryActions() {
      return window.App.getRuntimeModule?.("category-actions") || {};
    }

    const pickerUtils = getPickerUtils();
    const CATEGORY_USAGE_KEY = pickerUtils.DEFAULT_CATEGORY_USAGE_KEY;

    function escHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function renderReceiptBrandChip(brand) {
      const renderer = window.App.getRuntimeModule?.("item-brands")?.renderBrandChip;
      const normalizedBrand = {
        name: brand?.brand_name || brand?.name || "",
        accent_color: brand?.brand_accent_color || brand?.accent_color || null,
        image_id: brand?.brand_image_id || brand?.image_id || null,
      };
      return typeof renderer === "function"
        ? renderer(normalizedBrand)
        : core.renderCategoryChip({ ...normalizedBrand, icon: null }, "");
    }

    function getReceiptCategoriesSorted(kind, query = "") {
      return pickerUtils.sortCategoriesByUsage(
        (state.categories || []).filter((item) => item.kind === kind),
        query,
        CATEGORY_USAGE_KEY,
      );
    }

    function createReceiptCategoryChipButton(category, selected, searchQuery = "") {
      return pickerUtils.createChipButton({
        datasetName: "receiptCategoryId",
        datasetValue: category.id,
        selected,
        html: core.renderCategoryChip(
          {
            name: category.name,
            icon: category.icon || category.group_icon || null,
            accent_color: category.group_accent_color || null,
          },
          searchQuery,
        ),
      });
    }

    function createReceiptNoCategoryChipButton(selected) {
      return pickerUtils.createMetaChipButton({
        datasetName: "receiptCategoryId",
        datasetValue: "",
        selected,
        label: "Без категории",
        core,
      });
    }

    function getReceiptTemplateMatch(token, shopName = "", brandId = null) {
      const normalizedToken = normalizeReceiptName(token).toLowerCase();
      if (!normalizedToken) {
        return null;
      }
      const shopCi = normalizeReceiptName(shopName).toLowerCase();
      const selectedBrandId = brandId ? Number(brandId) : null;
      return (state.receiptTemplateHints || []).find((item) => (
        item.name_ci === normalizedToken
        && (!shopCi || (item.shop_name_ci || "") === shopCi)
        && (!selectedBrandId || Number(item.brand_id || 0) === selectedBrandId)
      )) || null;
    }

    function getReceiptTemplateSuggestions(query, shopName = "", limit = 50, brandId = null) {
      const normalized = normalizeReceiptName(query).toLowerCase();
      const shopCi = normalizeReceiptName(shopName).toLowerCase();
      const selectedBrandId = brandId ? Number(brandId) : null;
      const templates = Array.isArray(state.receiptTemplateHints) ? state.receiptTemplateHints : [];
      const scopedTemplates = templates.filter((item) => (
        (!shopCi || (item.shop_name_ci || "") === shopCi)
        && (!selectedBrandId || Number(item.brand_id || 0) === selectedBrandId)
      ));
      if (!normalized) {
        return limit > 0 ? scopedTemplates.slice(0, limit) : scopedTemplates;
      }
      const starts = [];
      const contains = [];
      for (const item of scopedTemplates) {
        if (!item.name_ci) {
          continue;
        }
        if (item.name_ci.startsWith(normalized)) {
          starts.push(item);
        } else if (item.name_ci.includes(normalized)) {
          contains.push(item);
        }
      }
      const matches = [...starts, ...contains];
      return limit > 0 ? matches.slice(0, limit) : matches;
    }

    function getReceiptBrandSuggestions(query = "") {
      const normalized = normalizeReceiptName(query).toLowerCase();
      return (state.itemBrands || [])
        .filter((item) => !item.is_archived)
        .filter((item) => !normalized || normalizeReceiptName(item.name).toLowerCase().includes(normalized))
        .sort((left, right) => normalizeReceiptName(left.name).localeCompare(normalizeReceiptName(right.name), "ru"));
    }

    function getReceiptSourceMeta(shopName) {
      const normalized = normalizeReceiptName(shopName).toLowerCase();
      if (!normalized) return null;
      const source = (state.itemSources || []).find(
        (item) => normalizeReceiptName(item?.name || "").toLowerCase() === normalized,
      );
      if (source) return source;
      const template = (state.receiptTemplateHints || []).find(
        (item) => normalizeReceiptName(item?.source_name || item?.shop_name || "").toLowerCase() === normalized,
      );
      return template ? {
        id: template.source_id || null,
        name: template.source_name || template.shop_name || shopName,
        image_id: template.source_image_id || null,
      } : null;
    }

    function getReceiptShopSuggestions(query = "", limit = 100) {
      const normalized = normalizeReceiptName(query).toLowerCase();
      const byShop = new Map();
      const preferenceSources = state.preferences?.data?.ui?.item_catalog_sources;
      if (!state.itemSourcesLoaded && Array.isArray(preferenceSources)) {
        for (const sourceName of preferenceSources) {
          const shopName = normalizeReceiptName(sourceName || "");
          if (!shopName) {
            continue;
          }
          const shopNameCi = shopName.toLowerCase();
          if (normalized && !shopNameCi.includes(normalized)) {
            continue;
          }
          if (!byShop.has(shopNameCi)) {
            byShop.set(shopNameCi, shopName);
          }
        }
      }
      for (const source of state.itemSources || []) {
        if (source?.is_archived) continue;
        const shopName = normalizeReceiptName(source?.name || "");
        const shopNameCi = shopName.toLowerCase();
        if (!shopName || (normalized && !shopNameCi.includes(normalized))) continue;
        if (!byShop.has(shopNameCi)) byShop.set(shopNameCi, shopName);
      }
      for (const item of state.receiptTemplateHints || []) {
        const shopName = normalizeReceiptName(item.shop_name || "");
        if (!shopName) {
          continue;
        }
        const shopNameCi = shopName.toLowerCase();
        if (normalized && !shopNameCi.includes(normalized)) {
          continue;
        }
        if (!byShop.has(shopNameCi)) {
          byShop.set(shopNameCi, shopName);
        }
        if (limit > 0 && byShop.size >= limit) {
          break;
        }
      }
      return limit > 0 ? Array.from(byShop.values()).slice(0, limit) : Array.from(byShop.values());
    }

    function upsertLocalReceiptTemplate(name, latestUnitPrice = 0, shopName = "", brand = {}) {
      const normalizedName = normalizeReceiptName(name);
      if (!normalizedName) {
        return null;
      }
      const normalizedShop = normalizeReceiptName(shopName);
      const shopNameCi = normalizedShop.toLowerCase();
      const nameCi = normalizedName.toLowerCase();
      const existing = (state.receiptTemplateHints || []).find((item) => (
        item.name_ci === nameCi && (item.shop_name_ci || "") === shopNameCi
      ));
      if (existing) {
        if (Number(latestUnitPrice || 0) > 0) {
          existing.latest_unit_price = Number(latestUnitPrice || 0);
        }
        if (Object.prototype.hasOwnProperty.call(brand, "brand_id")) {
          existing.brand_id = brand.brand_id ? Number(brand.brand_id) : null;
          existing.brand_name = normalizeReceiptName(brand.brand_name || "") || null;
          existing.brand_accent_color = brand.brand_accent_color || null;
          existing.brand_image_id = brand.brand_image_id || null;
          existing.brand_is_archived = Boolean(brand.brand_is_archived);
        }
        return existing;
      }
      receiptUiState.localTemplateSeq += 1;
      const created = {
        id: -receiptUiState.localTemplateSeq,
        shop_name: normalizedShop || null,
        shop_name_ci: shopNameCi || "",
        name: normalizedName,
        name_ci: nameCi,
        brand_id: brand.brand_id ? Number(brand.brand_id) : null,
        brand_name: normalizeReceiptName(brand.brand_name || "") || null,
        brand_accent_color: brand.brand_accent_color || null,
        brand_image_id: brand.brand_image_id || null,
        brand_is_archived: Boolean(brand.brand_is_archived),
        image_id: null,
        source_id: null,
        source_image_id: null,
        last_category_id: null,
        latest_unit_price: Number(latestUnitPrice || 0) || 0,
      };
      state.receiptTemplateHints = [created, ...(state.receiptTemplateHints || [])];
      return created;
    }

    function normalizeServerReceiptTemplate(item) {
      return {
        id: Number(item.id || 0),
        shop_name: normalizeReceiptName(item.shop_name || "") || null,
        shop_name_ci: normalizeReceiptName(item.shop_name || "").toLowerCase(),
        name: normalizeReceiptName(item.name || ""),
        name_ci: normalizeReceiptName(item.name || "").toLowerCase(),
        brand_id: item.brand_id ? Number(item.brand_id) : null,
        brand_name: normalizeReceiptName(item.brand_name || "") || null,
        brand_accent_color: item.brand_accent_color || null,
        brand_image_id: item.brand_image_id || null,
        brand_is_archived: Boolean(item.brand_is_archived),
        image_id: item.image_id || null,
        source_id: item.source_id || null,
        source_image_id: item.source_image_id || null,
        last_category_id: item.last_category_id ? Number(item.last_category_id) : null,
        latest_unit_price: Number(item.latest_unit_price || 0) || 0,
      };
    }

    function mergeReceiptTemplateHints(items = []) {
      const byKey = new Map();
      for (const item of state.receiptTemplateHints || []) {
        if (item?.name_ci) {
          byKey.set(`${item.name_ci}::${item.shop_name_ci || ""}`, item);
        }
      }
      for (const raw of items) {
        const item = raw?.name_ci ? raw : normalizeServerReceiptTemplate(raw);
        if (item?.name_ci) {
          byKey.set(`${item.name_ci}::${item.shop_name_ci || ""}`, item);
        }
      }
      state.receiptTemplateHints = Array.from(byKey.values());
      return state.receiptTemplateHints;
    }

    function hideAllReceiptPickers() {
      for (const listNode of [el.receiptItemsList, el.editReceiptItemsList]) {
        if (!listNode) {
          continue;
        }
        listNode.querySelectorAll(".receipt-item-row").forEach((node) => node.classList.remove("has-open-popover"));
        listNode.querySelectorAll(".receipt-shop-cell, .receipt-brand-cell, .receipt-name-cell, .receipt-category-cell").forEach((node) => node.classList.remove("has-open-popover"));
        listNode.querySelectorAll(".receipt-shop-picker, .receipt-brand-picker, .receipt-name-picker, .receipt-category-picker").forEach((node) => {
          pickerUtils.setPopoverOpen(node, false);
        });
      }
      receiptUiState.activePicker = null;
    }

    function renderReceiptShopPickerForRow(rowNode, rowItem, query) {
      if (!rowNode || !rowItem) {
        return;
      }
      const picker = rowNode.querySelector(".receipt-shop-picker");
      if (!picker) {
        return;
      }
      hideAllReceiptPickers();
      const normalizedQuery = normalizeReceiptName(query);
      const shopSuggestions = getReceiptShopSuggestions(normalizedQuery);
      const exact = shopSuggestions.some((shop) => shop.toLowerCase() === normalizedQuery.toLowerCase());
      if (!normalizedQuery && !shopSuggestions.length) {
        picker.classList.add("hidden");
        picker.innerHTML = "";
        return;
      }
      const suggestionsHtml = shopSuggestions.map((shopName) => `
        <button type="button" class="chip-btn" data-receipt-shop-name="${escHtml(shopName)}" data-receipt-item-id="${rowItem.draft_id}" title="${escHtml(shopName)}">
          ${window.App.getRuntimeModule?.("catalog-media")?.renderThumb?.(getReceiptSourceMeta(shopName)?.image_id, { kind: "source", size: "chip", alt: shopName, fallback: shopName.slice(0, 1) }) || ""}
          ${core.renderCategoryChip({ name: shopName, icon: null, accent_color: null }, normalizedQuery)}
        </button>
      `).join("");
      const createHtml = !normalizedQuery || exact ? "" : `
        <button type="button" class="chip-btn chip-btn-create" data-receipt-create-shop="${escHtml(normalizedQuery)}" data-receipt-item-id="${rowItem.draft_id}">
          + Создать источник «${escHtml(normalizedQuery)}»
        </button>
      `;
      picker.innerHTML = `${suggestionsHtml}${createHtml}` || "<span class='muted-small'>Нет источников</span>";
      pickerUtils.setPopoverOpen(picker, true, {
        owners: [rowNode, rowNode.querySelector(".receipt-shop-cell")],
        onClose: hideAllReceiptPickers,
      });
      receiptUiState.activePicker = { draft_id: Number(rowItem.draft_id), field: "shop_name", mode: getReceiptModeFromNode(rowNode) };
    }

    function renderReceiptBrandPickerForRow(rowNode, rowItem, query = "") {
      if (!rowNode || !rowItem) {
        return;
      }
      const picker = rowNode.querySelector(".receipt-brand-picker");
      if (!picker) {
        return;
      }
      hideAllReceiptPickers();
      const rawQuery = normalizeReceiptName(query);
      const normalizedQuery = rawQuery.toLowerCase() === normalizeReceiptName(rowItem.brand_name || "").toLowerCase()
        ? ""
        : rawQuery;
      const suggestions = getReceiptBrandSuggestions(normalizedQuery);
      const clearHtml = `
        <button type="button" class="chip-btn ${rowItem.brand_id ? "" : "active"}" data-receipt-brand-clear="true" data-receipt-item-id="${rowItem.draft_id}" title="Не привязывать бренд">
          ${core.renderCategoryChip({ name: "Без бренда", icon: null, accent_color: null }, normalizedQuery)}
        </button>
      `;
      const suggestionsHtml = suggestions.map((brand) => `
        <button type="button" class="chip-btn ${Number(rowItem.brand_id || 0) === Number(brand.id) ? "active" : ""}" data-receipt-brand-id="${Number(brand.id)}" data-receipt-item-id="${rowItem.draft_id}" title="${escHtml(brand.name)}">
          ${renderReceiptBrandChip(brand)}
        </button>
      `).join("");
      const emptyHtml = suggestions.length
        ? ""
        : "<span class='muted-small receipt-picker-empty'>Бренд не найден · создать можно в Каталоге → Бренды</span>";
      picker.innerHTML = `${clearHtml}${suggestionsHtml}${emptyHtml}`;
      pickerUtils.setPopoverOpen(picker, true, {
        owners: [rowNode, rowNode.querySelector(".receipt-brand-cell")],
        onClose: hideAllReceiptPickers,
      });
      receiptUiState.activePicker = { draft_id: Number(rowItem.draft_id), field: "brand_id", mode: getReceiptModeFromNode(rowNode) };
      if (!(state.itemBrands || []).length) {
        loadReceiptBrands()
          .then(() => {
            const active = receiptUiState.activePicker;
            if (
              active?.field === "brand_id"
              && Number(active.draft_id) === Number(rowItem.draft_id)
              && !picker.classList.contains("hidden")
            ) {
              renderReceiptBrandPickerForRow(rowNode, rowItem, query);
            }
          })
          .catch(() => {});
      }
    }

    function renderReceiptNamePickerForRow(rowNode, rowItem, query) {
      if (!rowNode || !rowItem) {
        return;
      }
      const picker = rowNode.querySelector(".receipt-name-picker");
      const badge = rowNode.querySelector(".receipt-new-badge");
      if (!picker) {
        return;
      }
      hideAllReceiptPickers();
      const normalizedQuery = normalizeReceiptName(query);
      const exact = getReceiptTemplateMatch(normalizedQuery, rowItem.shop_name || "", rowItem.brand_id);
      const suggestions = getReceiptTemplateSuggestions(normalizedQuery, rowItem.shop_name || "", 50, rowItem.brand_id);
      if (!normalizedQuery) {
        if (badge) {
          badge.classList.add("hidden");
        }
        if (!suggestions.length) {
          picker.classList.add("hidden");
          picker.innerHTML = "";
          return;
        }
      }
      if (badge) {
        badge.classList.toggle("hidden", Boolean(exact));
      }
      const suggestionsHtml = suggestions.map((item) => `
        <button type="button" class="chip-btn receipt-template-suggestion" data-receipt-template-id="${item.id}" data-receipt-item-id="${rowItem.draft_id}" title="${escHtml(item.name)}">
          ${window.App.getRuntimeModule?.("catalog-media")?.renderThumb?.(item.image_id, { kind: "item", size: "picker", alt: item.name, fallback: String(item.name || "П").slice(0, 1) }) || ""}
          <span class="receipt-template-suggestion-main">
            <span class="receipt-template-suggestion-name">${core.highlightText?.(item.name, normalizedQuery) || escHtml(item.name)}</span>
            <span class="receipt-template-suggestion-meta">
              ${item.brand_name ? `<span class="receipt-template-suggestion-brand">${renderReceiptBrandChip(item)}</span>` : ""}
              ${Number(item.latest_unit_price || 0) > 0 ? `<span>${core.formatMoney(item.latest_unit_price)}</span>` : ""}
            </span>
          </span>
        </button>
      `).join("");
      const createHtml = !normalizedQuery || exact ? "" : `
        <button type="button" class="chip-btn chip-btn-create" data-receipt-create-name="${escHtml(normalizedQuery)}" data-receipt-item-id="${rowItem.draft_id}">
          + Создать позицию «${escHtml(normalizedQuery)}»
        </button>
      `;
      picker.innerHTML = `${suggestionsHtml}${createHtml}` || "<span class='muted-small'>Нет совпадений</span>";
      pickerUtils.setPopoverOpen(picker, true, {
        owners: [rowNode, rowNode.querySelector(".receipt-name-cell")],
        onClose: hideAllReceiptPickers,
      });
      receiptUiState.activePicker = { draft_id: Number(rowItem.draft_id), field: "name", mode: getReceiptModeFromNode(rowNode) };
      if (normalizedQuery && !exact && suggestions.length < 50) {
        loadReceiptTemplates(normalizedQuery)
          .then((items) => {
            const prevCount = Array.isArray(state.receiptTemplateHints) ? state.receiptTemplateHints.length : 0;
            mergeReceiptTemplateHints(items);
            const active = receiptUiState.activePicker;
            if (
              active?.field === "name"
              && Number(active.draft_id) === Number(rowItem.draft_id)
              && !picker.classList.contains("hidden")
              && state.receiptTemplateHints.length !== prevCount
            ) {
              renderReceiptNamePickerForRow(rowNode, rowItem, query);
            }
          })
          .catch(() => {});
      }
    }

    function openCreateCategoryFromReceipt(rowNode, rowItem, query) {
      const trimmed = String(query || "").trim();
      if (!trimmed) {
        return;
      }
      const mode = getReceiptModeFromNode(rowNode);
      const kind = mode === "edit" ? (el.editKind?.value || "expense") : (el.opKind?.value || "expense");
      state.pendingCreateCategoryFromReceipt = {
        draft_id: Number(rowItem.draft_id),
        mode,
        kind,
        query: trimmed,
      };
      hideAllReceiptPickers();
      if (getCategoryActions().openCreateCategoryModal) {
        getCategoryActions().openCreateCategoryModal({
          kind,
          prefillName: trimmed,
          reset: true,
        });
      }
    }

    function renderReceiptCategoryPickerForRow(rowNode, rowItem, query) {
      if (!rowNode || !rowItem) {
        return;
      }
      const picker = rowNode.querySelector(".receipt-category-picker");
      const input = rowNode.querySelector('[data-receipt-field="category_search"]');
      if (!picker || !input) {
        return;
      }
      hideAllReceiptPickers();
      const mode = getReceiptModeFromNode(rowNode);
      const kind = mode === "edit" ? (el.editKind?.value || "expense") : (el.opKind?.value || "expense");
      const selectedId = rowItem.category_id ? Number(rowItem.category_id) : null;
      const effectiveCategoryId = Number(input.dataset.receiptEffectiveCategoryId || 0) || null;
      const displayedCategory = (state.categories || []).find((item) => (
        Number(item.id) === Number(selectedId || effectiveCategoryId || 0) && item.kind === kind
      ));
      const rawQuery = String(query ?? input.value ?? "").trim();
      const normalizedQuery = displayedCategory && rawQuery.toLowerCase() === displayedCategory.name.toLowerCase() ? "" : rawQuery;
      const categories = getReceiptCategoriesSorted(kind, normalizedQuery);
      picker.innerHTML = "";
      picker.appendChild(createReceiptNoCategoryChipButton(!selectedId && !effectiveCategoryId));
      for (const item of categories) {
        const isActive = selectedId
          ? selectedId === Number(item.id)
          : effectiveCategoryId === Number(item.id);
        picker.appendChild(createReceiptCategoryChipButton(item, isActive, normalizedQuery));
      }
      if (!categories.length && normalizedQuery) {
        const createChip = pickerUtils.createActionChipButton({
          datasetName: "receiptCreateCategory",
          datasetValue: normalizedQuery,
          label: `+ Создать категорию «${normalizedQuery}»`,
        });
        createChip.dataset.receiptItemId = String(rowItem.draft_id);
        picker.appendChild(createChip);
      }
      if (!categories.length && !normalizedQuery) {
        const empty = document.createElement("span");
        empty.className = "muted-small";
        empty.textContent = "Без категорий для выбранного типа";
        picker.appendChild(empty);
      }
      pickerUtils.setPopoverOpen(picker, true, {
        owners: [rowNode, rowNode.querySelector(".receipt-category-cell")],
        onClose: hideAllReceiptPickers,
      });
      receiptUiState.activePicker = { draft_id: Number(rowItem.draft_id), field: "category_id", mode };
    }

    async function loadReceiptTemplates(query = "", options = {}) {
      const normalized = String(query || "").trim().toLowerCase();
      const allPages = options.allPages === true && !normalized;
      const cacheKey = `op:receipt:templates:q=${normalized}:all=${allPages ? "1" : "0"}`;
      const cached = core.getUiRequestCache ? core.getUiRequestCache(cacheKey, RECEIPT_TEMPLATES_CACHE_TTL_MS) : null;
      if (cached) {
        return cached.items || [];
      }
      const params = new URLSearchParams({
        page: "1",
        page_size: "100",
      });
      if (normalized) {
        params.set("q", normalized);
      }
      const payload = await core.requestJson(`/api/v1/operations/item-templates?${params.toString()}`, {
        headers: core.authHeaders(),
      });
      const items = Array.isArray(payload.items) ? payload.items.slice() : [];
      const total = Number(payload.total || items.length || 0);
      if (allPages && total > items.length) {
        const pageSize = Number(payload.page_size || 100) || 100;
        const pageCount = Math.ceil(total / pageSize);
        for (let page = 2; page <= pageCount; page += 1) {
          const pageParams = new URLSearchParams(params);
          pageParams.set("page", String(page));
          const pagePayload = await core.requestJson(`/api/v1/operations/item-templates?${pageParams.toString()}`, {
            headers: core.authHeaders(),
          });
          items.push(...(Array.isArray(pagePayload.items) ? pagePayload.items : []));
        }
      }
      const result = { ...payload, items };
      if (core.setUiRequestCache) {
        core.setUiRequestCache(cacheKey, result);
      }
      return items;
    }

    async function loadReceiptBrands(options = {}) {
      const force = options.force === true;
      const now = Date.now();
      const brandsFresh = now - Number(receiptUiState.brandsLoadedAt || 0) < RECEIPT_TEMPLATES_CACHE_TTL_MS;
      if (!force && brandsFresh && state.itemBrandsLoaded && Array.isArray(state.itemBrands)) {
        return state.itemBrands;
      }
      if (receiptUiState.brandsPromise) {
        return receiptUiState.brandsPromise;
      }
      receiptUiState.brandsPromise = (async () => {
        const itemBrands = window.App.getRuntimeModule?.("item-brands");
        const itemCatalog = window.App.getRuntimeModule?.("item-catalog");
        const runtimeLoader = itemBrands?.ensureItemBrandsLoaded
          || itemBrands?.ensureItemBrands
          || itemBrands?.loadItemBrands
          || itemCatalog?.loadItemBrands;
        if (typeof runtimeLoader === "function") {
          try {
            await runtimeLoader({ force });
          } catch {
            // Fall through to the lightweight receipt loader.
          }
        }
        if ((!Array.isArray(state.itemBrands) || (!state.itemBrands.length && !state.itemBrandsLoaded)) || force) {
          const params = new URLSearchParams({ page: "1", page_size: "100", include_archived: "false" });
          const firstPayload = await core.requestJson(`/api/v1/operations/item-brands?${params.toString()}`, {
            headers: core.authHeaders(),
          });
          const brands = (Array.isArray(firstPayload) ? firstPayload : (firstPayload.items || [])).slice();
          const total = Number(firstPayload?.total || brands.length || 0);
          const pageSize = Number(firstPayload?.page_size || 100) || 100;
          const pageCount = Math.ceil(total / pageSize);
          for (let page = 2; page <= pageCount; page += 1) {
            const pageParams = new URLSearchParams(params);
            pageParams.set("page", String(page));
            const payload = await core.requestJson(`/api/v1/operations/item-brands?${pageParams.toString()}`, {
              headers: core.authHeaders(),
            });
            brands.push(...(Array.isArray(payload) ? payload : (payload.items || [])));
          }
          state.itemBrands = brands.filter((item) => !item.is_archived);
          state.itemBrandsLoaded = true;
        }
        receiptUiState.brandsLoadedAt = Date.now();
        return state.itemBrands || [];
      })();
      try {
        return await receiptUiState.brandsPromise;
      } finally {
        receiptUiState.brandsPromise = null;
      }
    }

    async function loadReceiptTemplateHints() {
      const now = Date.now();
      const hintsFresh = now - Number(receiptUiState.hintsLoadedAt || 0) < RECEIPT_TEMPLATES_CACHE_TTL_MS;
      if (hintsFresh && Array.isArray(state.receiptTemplateHints) && state.receiptTemplateHints.length > 0) {
        return;
      }
      if (receiptUiState.hintsPromise) {
        await receiptUiState.hintsPromise;
        return;
      }
      receiptUiState.hintsPromise = (async () => {
        let templates = [];
        await Promise.all([
          loadReceiptTemplates("", { allPages: true }).then((items) => { templates = items; }).catch(() => {}),
          loadReceiptBrands().catch(() => {}),
          Promise.resolve(window.App.getRuntimeModule?.("item-catalog")?.loadItemSources?.()).catch(() => {}),
        ]);
        mergeReceiptTemplateHints(templates);
        receiptUiState.hintsLoadedAt = Date.now();
      })();
      try {
        await receiptUiState.hintsPromise;
      } finally {
        receiptUiState.hintsPromise = null;
      }
    }

    return {
      getReceiptCategoriesSorted,
      getReceiptTemplateMatch,
      getReceiptTemplateSuggestions,
      getReceiptBrandSuggestions,
      getReceiptShopSuggestions,
      upsertLocalReceiptTemplate,
      mergeReceiptTemplateHints,
      hideAllReceiptPickers,
      renderReceiptShopPickerForRow,
      renderReceiptBrandPickerForRow,
      renderReceiptNamePickerForRow,
      openCreateCategoryFromReceipt,
      renderReceiptCategoryPickerForRow,
      loadReceiptTemplateHints,
      loadReceiptBrands,
    };
  }

  window.App = window.App || {};
  window.App.registerRuntimeModule?.("operation-modal-receipt-picker-factory", createOperationModalReceiptPickerFeature);
})();
