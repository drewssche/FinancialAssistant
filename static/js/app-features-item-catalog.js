(() => {
  const { state, el, core } = window.App;
  const sessionFeatures = window.App.getRuntimeModule?.("session");
  const itemCatalogSectionCoordinator = window.App.getRuntimeModule?.("item-catalog-section-coordinator");
  const itemCatalogRenderCoordinator = window.App.getRuntimeModule?.("item-catalog-render-coordinator");
  const savePreferencesDebounced = sessionFeatures.savePreferencesDebounced;
  const cancelDebouncedPreferencesSave = sessionFeatures.cancelDebouncedPreferencesSave;
  const escapeHtml = core.escapeHtml || ((value) => String(value ?? ""));

  let itemCatalogRequestController = null;
  let itemCatalogRequestSeq = 0;
  let itemCatalogBaseItems = [];
  let itemCatalogBaseTotal = 0;
  const ITEM_CATALOG_CACHE_TTL_MS = 20000;
  const ITEM_CATALOG_NO_SHOP_KEY = "__no_shop__";

  function normalizeItemCatalogShopName(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function getItemCatalogShopKey(value) {
    const normalized = normalizeItemCatalogShopName(value).toLowerCase();
    return normalized || ITEM_CATALOG_NO_SHOP_KEY;
  }

  function readItemCatalogCollapsedShops() {
    const list = state.preferences?.data?.ui?.item_catalog_collapsed_sources
      || state.preferences?.data?.ui?.item_catalog_collapsed_shops;
    if (!Array.isArray(list)) {
      return new Set();
    }
    return new Set(list.map((item) => String(item)));
  }

  function writeItemCatalogCollapsedShops(nextSet) {
    if (!state.preferences) {
      return;
    }
    state.preferences.data = state.preferences.data || {};
    state.preferences.data.ui = state.preferences.data.ui || {};
    state.preferences.data.ui.item_catalog_collapsed_sources = Array.from(nextSet);
    state.preferences.data.ui.item_catalog_collapsed_shops = Array.from(nextSet);
  }

  function readItemCatalogSourceGroups() {
    const list = state.preferences?.data?.ui?.item_catalog_sources;
    if (!Array.isArray(list)) {
      return [];
    }
    return list
      .map((item) => normalizeItemCatalogShopName(item))
      .filter((item, idx, arr) => item && arr.indexOf(item) === idx);
  }

  function listItemCatalogSourceNames(limit = 24) {
    const byKey = new Map();
    for (const sourceName of readItemCatalogSourceGroups()) {
      const normalized = normalizeItemCatalogShopName(sourceName);
      if (!normalized) {
        continue;
      }
      byKey.set(getItemCatalogShopKey(normalized), normalized);
    }
    for (const item of state.itemCatalogItems || []) {
      const normalized = normalizeItemCatalogShopName(item?.shop_name || "");
      if (!normalized) {
        continue;
      }
      const key = getItemCatalogShopKey(normalized);
      if (!byKey.has(key)) {
        byKey.set(key, normalized);
      }
    }
    return Array.from(byKey.values())
      .sort((a, b) => a.localeCompare(b, "ru"))
      .slice(0, limit);
  }

  function writeItemCatalogSourceGroups(items) {
    if (!state.preferences) {
      return;
    }
    state.preferences.data = state.preferences.data || {};
    state.preferences.data.ui = state.preferences.data.ui || {};
    state.preferences.data.ui.item_catalog_sources = items;
  }

  function itemCatalogLastUsedMs(item) {
    const ms = Date.parse(String(item?.last_used_at || ""));
    return Number.isFinite(ms) ? ms : 0;
  }

  function compareItemCatalogItems(a, b, preset) {
    if (preset === "name") {
      return String(a?.name || "").localeCompare(String(b?.name || ""), "ru");
    }
    if (preset === "recent") {
      const tsDiff = itemCatalogLastUsedMs(b) - itemCatalogLastUsedMs(a);
      if (tsDiff !== 0) {
        return tsDiff;
      }
      const usageDiff = Number(b?.use_count || 0) - Number(a?.use_count || 0);
      if (usageDiff !== 0) {
        return usageDiff;
      }
      return String(a?.name || "").localeCompare(String(b?.name || ""), "ru");
    }
    const usageDiff = Number(b?.use_count || 0) - Number(a?.use_count || 0);
    if (usageDiff !== 0) {
      return usageDiff;
    }
    const tsDiff = itemCatalogLastUsedMs(b) - itemCatalogLastUsedMs(a);
    if (tsDiff !== 0) {
      return tsDiff;
    }
    return String(a?.name || "").localeCompare(String(b?.name || ""), "ru");
  }

  function buildItemCatalogGroups(rows) {
    return itemCatalogRenderCoordinator?.buildItemCatalogGroups?.({
      rows,
      state,
      readItemCatalogSourceGroups,
      normalizeItemCatalogShopName,
      getItemCatalogShopKey,
      compareItemCatalogItems,
      itemCatalogLastUsedMs,
      itemCatalogNoShopKey: ITEM_CATALOG_NO_SHOP_KEY,
    }) || [];
  }

  function setItemCatalogSortPreset(value) {
    itemCatalogSectionCoordinator?.setItemCatalogSortPreset?.({
      value,
      state,
      el,
      core,
      renderItemCatalog,
      savePreferencesDebounced,
    });
  }

  function collapseAllItemCatalogGroups() {
    itemCatalogSectionCoordinator?.collapseAllItemCatalogGroups?.({
      state,
      buildItemCatalogGroups,
      writeItemCatalogCollapsedShops,
      renderItemCatalog,
      savePreferencesDebounced,
    });
  }

  function expandAllItemCatalogGroups() {
    itemCatalogSectionCoordinator?.expandAllItemCatalogGroups?.({
      state,
      writeItemCatalogCollapsedShops,
      renderItemCatalog,
      savePreferencesDebounced,
    });
  }

  function handleItemCatalogBodyClick(event) {
    itemCatalogSectionCoordinator?.handleItemCatalogGroupToggle?.({
      event,
      el,
      state,
      renderItemCatalog,
      readItemCatalogCollapsedShops,
      writeItemCatalogCollapsedShops,
      savePreferencesDebounced,
    });
  }

  function renderItemCatalog(items) {
    itemCatalogRenderCoordinator?.renderItemCatalog?.({
      items,
      el,
      state,
      core,
      escapeHtml,
      readItemCatalogCollapsedShops,
      buildItemCatalogGroups,
      syncItemCatalogControls: itemCatalogSectionCoordinator?.syncItemCatalogControls,
    });
  }

  function filterItemCatalogLocally(items, queryRaw) {
    const query = String(queryRaw || "").trim().toLowerCase();
    if (!query) {
      return Array.isArray(items) ? items.slice() : [];
    }
    return (Array.isArray(items) ? items : []).filter((item) => {
      const name = String(item?.name || "").toLowerCase();
      const source = String(item?.shop_name || "").toLowerCase();
      const category = (state.categories || []).find(
        (row) => Number(row?.id || 0) === Number(item?.last_category_id || 0),
      );
      const categoryName = String(category?.name || "").toLowerCase();
      const brand = (state.itemBrands || []).find(
        (row) => Number(row?.id || 0) === Number(item?.brand_id || 0),
      );
      const brandName = String(item?.brand_name || brand?.name || "").toLowerCase();
      return name.includes(query) || source.includes(query) || categoryName.includes(query) || brandName.includes(query);
    });
  }

  function applySavedItemCatalogItem(item) {
    const templateId = Number(item?.id || 0);
    if (!templateId) {
      return;
    }
    const upsert = (items) => {
      const rows = Array.isArray(items) ? items.slice() : [];
      const index = rows.findIndex((entry) => Number(entry?.id || 0) === templateId);
      if (index >= 0) {
        rows[index] = { ...rows[index], ...item };
      } else {
        rows.unshift(item);
      }
      return rows;
    };
    const query = String(el.itemCatalogSearchQ?.value || "").trim();
    const hadBaseItem = itemCatalogBaseItems.some((entry) => Number(entry?.id || 0) === templateId);
    if (itemCatalogBaseItems.length || !query) {
      itemCatalogBaseItems = upsert(itemCatalogBaseItems);
      state.itemCatalogAllItems = itemCatalogBaseItems.slice();
      if (!hadBaseItem) {
        itemCatalogBaseTotal = Math.max(itemCatalogBaseTotal + 1, itemCatalogBaseItems.length);
      }
      state.itemCatalogItems = query
        ? filterItemCatalogLocally(itemCatalogBaseItems, query)
        : itemCatalogBaseItems.slice();
    } else {
      state.itemCatalogItems = filterItemCatalogLocally(upsert(state.itemCatalogItems), query);
    }
    renderItemCatalog(state.itemCatalogItems);
  }

  function applySavedReceiptTemplateHint(item) {
    const templateId = Number(item?.id || 0);
    if (!templateId) {
      return;
    }
    const normalizedShop = normalizeItemCatalogShopName(item?.shop_name || "");
    const normalizedName = String(item?.name || "").trim();
    const normalized = {
      ...item,
      id: templateId,
      shop_name: normalizedShop || null,
      shop_name_ci: normalizedShop.toLowerCase(),
      name: normalizedName,
      name_ci: normalizedName.toLowerCase(),
      last_category_id: Number(item?.last_category_id || 0) || null,
      latest_unit_price: item?.latest_unit_price === null || item?.latest_unit_price === undefined
        ? null
        : Number(item.latest_unit_price),
    };
    const hints = Array.isArray(state.receiptTemplateHints) ? state.receiptTemplateHints.slice() : [];
    const index = hints.findIndex((entry) => Number(entry?.id || 0) === templateId);
    if (index >= 0) {
      hints[index] = normalized;
    } else {
      hints.unshift(normalized);
    }
    state.receiptTemplateHints = hints;
    core.invalidateUiRequestCache("op:receipt:templates");
  }

  function invalidateItemCatalogDependentCaches() {
    for (const prefix of [
      "item-catalog",
      "item-brands",
      "op:receipt:templates",
      "operations",
      "plans",
      "analytics",
      "dashboard:highlights",
    ]) {
      core.invalidateUiRequestCache?.(prefix);
    }
    state.receiptTemplateHints = [];
    state.itemBrandsLoaded = false;
  }

  async function fetchItemCatalogPages(params, requestController) {
    const firstPayload = await core.requestJson(`/api/v1/operations/item-templates?${params.toString()}`, {
      headers: core.authHeaders(),
      signal: requestController.signal,
    });
    const items = Array.isArray(firstPayload.items) ? firstPayload.items.slice() : [];
    const total = Number(firstPayload.total || items.length || 0);
    const pageSize = Number(firstPayload.page_size || params.get("page_size") || 100) || 100;
    if (total > items.length) {
      const pageCount = Math.ceil(total / pageSize);
      for (let page = 2; page <= pageCount; page += 1) {
        const pageParams = new URLSearchParams(params);
        pageParams.set("page", String(page));
        const pagePayload = await core.requestJson(`/api/v1/operations/item-templates?${pageParams.toString()}`, {
          headers: core.authHeaders(),
          signal: requestController.signal,
        });
        items.push(...(Array.isArray(pagePayload.items) ? pagePayload.items : []));
      }
    }
    return { ...firstPayload, items };
  }

  async function loadItemCatalog(options = {}) {
    if (!state.itemBrandsLoaded) {
      await window.App.getRuntimeModule?.("item-brands")?.ensureItemBrandsLoaded?.().catch(() => []);
    }
    if (!(state.categories || []).length) {
      await window.App.getRuntimeModule?.("category-actions")?.loadCategories?.();
    }
    const force = options.force === true;
    const query = String(el.itemCatalogSearchQ?.value || "").trim();
    if (query && !force && itemCatalogBaseTotal > 0 && itemCatalogBaseItems.length >= itemCatalogBaseTotal) {
      state.itemCatalogItems = filterItemCatalogLocally(itemCatalogBaseItems, query);
      renderItemCatalog(state.itemCatalogItems);
      return;
    }
    const params = new URLSearchParams({
      page: "1",
      page_size: "100",
    });
    if (query) {
      params.set("q", query);
    }
    const cacheKey = `item-catalog:${params.toString()}`;
    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, ITEM_CATALOG_CACHE_TTL_MS);
      if (cached?.items) {
        state.itemCatalogItems = cached.items.slice();
        if (!query) {
          itemCatalogBaseItems = state.itemCatalogItems.slice();
          state.itemCatalogAllItems = itemCatalogBaseItems.slice();
          itemCatalogBaseTotal = Number(cached.total || state.itemCatalogItems.length || 0);
        }
        renderItemCatalog(state.itemCatalogItems);
        return;
      }
    }
    if (itemCatalogRequestController) {
      itemCatalogRequestController.abort();
    }
    const requestController = new AbortController();
    itemCatalogRequestController = requestController;
    const requestSeq = ++itemCatalogRequestSeq;
    try {
      const payload = await fetchItemCatalogPages(params, requestController);
      if (requestSeq !== itemCatalogRequestSeq) {
        return;
      }
      state.itemCatalogItems = Array.isArray(payload.items) ? payload.items.slice() : [];
      if (!query) {
        itemCatalogBaseItems = state.itemCatalogItems.slice();
        state.itemCatalogAllItems = itemCatalogBaseItems.slice();
        itemCatalogBaseTotal = Number(payload.total || state.itemCatalogItems.length || 0);
      }
      core.setUiRequestCache(cacheKey, payload);
      renderItemCatalog(state.itemCatalogItems);
    } catch (err) {
      if (core.isAbortError && core.isAbortError(err)) {
        return;
      }
      throw err;
    } finally {
      if (itemCatalogRequestController === requestController) {
        itemCatalogRequestController = null;
      }
    }
  }

  const createItemCatalogModalFeature = window.App.getRuntimeModule?.("item-catalog-modal-factory");
  const itemCatalogModal = createItemCatalogModalFeature
    ? createItemCatalogModalFeature({
      state,
      el,
      core,
      normalizeItemCatalogShopName,
      escapeHtml,
      getItemCatalogShopKey,
      readItemCatalogSourceGroups,
      writeItemCatalogSourceGroups,
      listItemCatalogSourceNames,
      buildItemCatalogGroups,
      renderItemCatalog,
      loadItemCatalog,
      applySavedItemCatalogItem,
      applySavedReceiptTemplateHint,
      invalidateItemCatalogDependentCaches,
      savePreferencesDebounced,
    })
    : {};

  function cleanupItemCatalogRuntime() {
    cancelDebouncedPreferencesSave();
    window.App.getRuntimeModule?.("item-brands")?.cleanupRuntime?.();
    if (itemCatalogRequestController) {
      itemCatalogRequestController.abort();
      itemCatalogRequestController = null;
    }
    itemCatalogRequestSeq = 0;
    itemCatalogBaseItems = [];
    itemCatalogBaseTotal = 0;
    state.itemCatalogItems = [];
    state.itemCatalogAllItems = [];
    state.receiptTemplateHints = [];
    state.itemBrands = [];
    state.itemBrandsLoaded = false;
    state.selectedItemCatalogIds = new Set();
    state.itemCatalogView = "positions";
    state.itemCatalogBrandFilter = "all";
    state.editItemBrandId = null;
  }

  function refreshItemCatalogView() {
    renderItemCatalog(state.itemCatalogItems);
    window.App.getRuntimeModule?.("item-brands")?.renderCatalogBulkState?.();
  }

  const api = {
    loadItemCatalog,
    refreshItemCatalogView,
    setItemCatalogSortPreset,
    collapseAllItemCatalogGroups,
    expandAllItemCatalogGroups,
    handleItemCatalogBodyClick,
    openItemTemplateModal: itemCatalogModal.openItemTemplateModal,
    closeItemTemplateModal: itemCatalogModal.closeItemTemplateModal,
    submitItemTemplateForm: itemCatalogModal.submitItemTemplateForm,
    deleteItemTemplateFlow: itemCatalogModal.deleteItemTemplateFlow,
    deleteAllItemTemplatesFlow: itemCatalogModal.deleteAllItemTemplatesFlow,
    openSourceGroupModal: itemCatalogModal.openSourceGroupModal,
    openEditSourceGroupModal: itemCatalogModal.openEditSourceGroupModal,
    closeSourceGroupModal: itemCatalogModal.closeSourceGroupModal,
    submitSourceGroupForm: itemCatalogModal.submitSourceGroupForm,
    deleteItemSourceFlow: itemCatalogModal.deleteItemSourceFlow,
    updateSourceGroupPreview: itemCatalogModal.updateSourceGroupPreview,
    updateItemTemplatePreview: itemCatalogModal.updateItemTemplatePreview,
    handleItemTemplateSourceSearchFocus: itemCatalogModal.handleItemTemplateSourceSearchFocus,
    handleItemTemplateSourceSearchInput: itemCatalogModal.handleItemTemplateSourceSearchInput,
    handleItemTemplateSourceSearchKeydown: itemCatalogModal.handleItemTemplateSourceSearchKeydown,
    handleItemTemplateSourcePickerClick: itemCatalogModal.handleItemTemplateSourcePickerClick,
    handleItemTemplateSourceOutsidePointer: itemCatalogModal.handleItemTemplateSourceOutsidePointer,
    handleItemTemplateSourceSearchFocusOut: itemCatalogModal.handleItemTemplateSourceSearchFocusOut,
    handleItemTemplateCategorySearchFocus: itemCatalogModal.handleItemTemplateCategorySearchFocus,
    handleItemTemplateCategorySearchInput: itemCatalogModal.handleItemTemplateCategorySearchInput,
    handleItemTemplateCategorySearchKeydown: itemCatalogModal.handleItemTemplateCategorySearchKeydown,
    handleItemTemplateCategoryPickerClick: itemCatalogModal.handleItemTemplateCategoryPickerClick,
    handleItemTemplateCategorySearchFocusOut: itemCatalogModal.handleItemTemplateCategorySearchFocusOut,
    handleItemTemplateBrandSearchFocus: itemCatalogModal.handleItemTemplateBrandSearchFocus,
    handleItemTemplateBrandSearchInput: itemCatalogModal.handleItemTemplateBrandSearchInput,
    handleItemTemplateBrandSearchKeydown: itemCatalogModal.handleItemTemplateBrandSearchKeydown,
    handleItemTemplateBrandPickerClick: itemCatalogModal.handleItemTemplateBrandPickerClick,
    handleItemTemplateBrandSearchFocusOut: itemCatalogModal.handleItemTemplateBrandSearchFocusOut,
    openItemTemplateHistoryModal: itemCatalogModal.openItemTemplateHistoryModal,
    closeItemTemplateHistoryModal: itemCatalogModal.closeItemTemplateHistoryModal,
    deleteItemTemplatePriceFlow: itemCatalogModal.deleteItemTemplatePriceFlow,
    cleanupItemCatalogRuntime,
    applySavedItemCatalogItem,
    applySavedReceiptTemplateHint,
    invalidateItemCatalogDependentCaches,
  };

  window.App.registerRuntimeModule?.("item-catalog", api);
})();
