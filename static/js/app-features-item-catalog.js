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
      return name.includes(query) || source.includes(query);
    });
  }

  async function loadItemCatalog(options = {}) {
    const force = options.force === true;
    const query = String(el.itemCatalogSearchQ?.value || "").trim();
    if (query && !force && itemCatalogBaseTotal > 0 && itemCatalogBaseItems.length >= itemCatalogBaseTotal) {
      state.itemCatalogItems = filterItemCatalogLocally(itemCatalogBaseItems, query);
      renderItemCatalog(state.itemCatalogItems);
      return;
    }
    const params = new URLSearchParams({
      page: "1",
      page_size: "50",
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
      const payload = await core.requestJson(`/api/v1/operations/item-templates?${params.toString()}`, {
        headers: core.authHeaders(),
        signal: requestController.signal,
      });
      if (requestSeq !== itemCatalogRequestSeq) {
        return;
      }
      state.itemCatalogItems = Array.isArray(payload.items) ? payload.items.slice() : [];
      if (!query) {
        itemCatalogBaseItems = state.itemCatalogItems.slice();
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
      savePreferencesDebounced,
    })
    : {};

  function cleanupItemCatalogRuntime() {
    cancelDebouncedPreferencesSave();
    if (itemCatalogRequestController) {
      itemCatalogRequestController.abort();
      itemCatalogRequestController = null;
    }
    itemCatalogRequestSeq = 0;
    itemCatalogBaseItems = [];
    itemCatalogBaseTotal = 0;
  }

  function refreshItemCatalogView() {
    renderItemCatalog(state.itemCatalogItems);
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
    openItemTemplateHistoryModal: itemCatalogModal.openItemTemplateHistoryModal,
    closeItemTemplateHistoryModal: itemCatalogModal.closeItemTemplateHistoryModal,
    cleanupItemCatalogRuntime,
  };

  window.App.registerRuntimeModule?.("item-catalog", api);
})();
