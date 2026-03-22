(() => {
  function syncItemCatalogControls({ el, queryActive, hasRows }) {
    if (el.itemCatalogCollapseAllBtn) {
      el.itemCatalogCollapseAllBtn.disabled = queryActive || !hasRows;
    }
    if (el.itemCatalogExpandAllBtn) {
      el.itemCatalogExpandAllBtn.disabled = queryActive || !hasRows;
    }
    if (el.deleteAllItemTemplatesBtn) {
      el.deleteAllItemTemplatesBtn.disabled = !hasRows;
    }
  }

  function handleItemCatalogGroupToggle({
    event,
    el,
    state,
    renderItemCatalog,
    readItemCatalogCollapsedShops,
    writeItemCatalogCollapsedShops,
    savePreferencesDebounced,
  }) {
    const btn = event.target.closest("button[data-item-catalog-shop-key]");
    if (!btn) {
      return false;
    }
    const query = String(el.itemCatalogSearchQ?.value || "").trim();
    if (query) {
      return true;
    }
    const encodedKey = btn.dataset.itemCatalogShopKey || "";
    let shopKey = "";
    try {
      shopKey = encodedKey ? decodeURIComponent(encodedKey) : "";
    } catch {
      shopKey = "";
    }
    if (!shopKey) {
      return true;
    }
    const collapsed = readItemCatalogCollapsedShops();
    if (collapsed.has(shopKey)) {
      collapsed.delete(shopKey);
    } else {
      collapsed.add(shopKey);
    }
    writeItemCatalogCollapsedShops(collapsed);
    renderItemCatalog(state.itemCatalogItems);
    savePreferencesDebounced(450);
    return true;
  }

  function setItemCatalogSortPreset({ value, state, el, core, renderItemCatalog, savePreferencesDebounced }) {
    const next = ["usage", "recent", "name"].includes(value) ? value : "usage";
    state.itemCatalogSortPreset = next;
    core.syncSegmentedActive(el.itemCatalogSortTabs, "item-sort", next);
    renderItemCatalog(state.itemCatalogItems);
    savePreferencesDebounced(450);
  }

  function collapseAllItemCatalogGroups({
    state,
    buildItemCatalogGroups,
    writeItemCatalogCollapsedShops,
    renderItemCatalog,
    savePreferencesDebounced,
  }) {
    const groups = buildItemCatalogGroups(state.itemCatalogItems || []);
    writeItemCatalogCollapsedShops(new Set(groups.map((group) => group.shopKey)));
    renderItemCatalog(state.itemCatalogItems);
    savePreferencesDebounced(450);
  }

  function expandAllItemCatalogGroups({ state, writeItemCatalogCollapsedShops, renderItemCatalog, savePreferencesDebounced }) {
    writeItemCatalogCollapsedShops(new Set());
    renderItemCatalog(state.itemCatalogItems);
    savePreferencesDebounced(450);
  }

  function bindItemCatalogSearch({ el, core, loadItemCatalog }) {
    if (!el.itemCatalogSearchQ || !loadItemCatalog) {
      return;
    }
    let itemCatalogSearchDebounceId = null;
    el.itemCatalogSearchQ.addEventListener("input", () => {
      if (itemCatalogSearchDebounceId) {
        clearTimeout(itemCatalogSearchDebounceId);
      }
      itemCatalogSearchDebounceId = setTimeout(() => {
        core.runAction({
          errorPrefix: "Ошибка поиска по каталогу позиций",
          action: () => loadItemCatalog(),
        });
      }, 250);
    });
  }

  function bindItemCatalogSortTabs({ el, state, setItemCatalogSortPresetAction }) {
    if (!el.itemCatalogSortTabs || !setItemCatalogSortPresetAction) {
      return;
    }
    el.itemCatalogSortTabs.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-item-sort]");
      if (!btn) {
        return;
      }
      if (btn.dataset.itemSort === state.itemCatalogSortPreset) {
        return;
      }
      setItemCatalogSortPresetAction(btn.dataset.itemSort);
    });
  }

  function bindItemCatalogCollapseExpand({ el, collapseAllItemCatalogGroupsAction, expandAllItemCatalogGroupsAction }) {
    if (el.itemCatalogCollapseAllBtn && collapseAllItemCatalogGroupsAction) {
      el.itemCatalogCollapseAllBtn.addEventListener("click", () => {
        collapseAllItemCatalogGroupsAction();
      });
    }
    if (el.itemCatalogExpandAllBtn && expandAllItemCatalogGroupsAction) {
      el.itemCatalogExpandAllBtn.addEventListener("click", () => {
        expandAllItemCatalogGroupsAction();
      });
    }
  }

  const api = {
    syncItemCatalogControls,
    handleItemCatalogGroupToggle,
    setItemCatalogSortPreset,
    collapseAllItemCatalogGroups,
    expandAllItemCatalogGroups,
    bindItemCatalogSearch,
    bindItemCatalogSortTabs,
    bindItemCatalogCollapseExpand,
  };

  window.App.registerRuntimeModule?.("item-catalog-section-coordinator", api);
})();
