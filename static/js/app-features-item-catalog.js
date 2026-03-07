(() => {
  const { state, el, core } = window.App;
  const sessionFeatures = window.App.featureSession;
  const savePreferences = sessionFeatures.savePreferences;
  const savePreferencesDebounced = sessionFeatures.savePreferencesDebounced;
  const cancelDebouncedPreferencesSave = sessionFeatures.cancelDebouncedPreferencesSave;

  let itemCatalogRequestController = null;
  let itemCatalogRequestSeq = 0;
  let itemCatalogBaseItems = [];
  let itemCatalogBaseTotal = 0;
  const ITEM_CATALOG_CACHE_TTL_MS = 20000;
  const ITEM_CATALOG_NO_SHOP_KEY = "__no_shop__";

  function normalizeItemCatalogShopName(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
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
    const grouped = new Map();
    for (const sourceName of readItemCatalogSourceGroups()) {
      const sourceKey = getItemCatalogShopKey(sourceName);
      if (!grouped.has(sourceKey)) {
        grouped.set(sourceKey, {
          shopKey: sourceKey,
          shopName: sourceName || "Без источника",
          items: [],
        });
      }
    }
    for (const item of rows) {
      const shopNameRaw = normalizeItemCatalogShopName(item.shop_name || "");
      const shopKey = getItemCatalogShopKey(shopNameRaw);
      if (!grouped.has(shopKey)) {
        grouped.set(shopKey, {
          shopKey,
          shopName: shopNameRaw || "Без источника",
          items: [],
        });
      }
      grouped.get(shopKey).items.push(item);
    }
    const preset = state.itemCatalogSortPreset || "usage";
    const groups = Array.from(grouped.values()).map((group) => {
      const sortedItems = group.items.slice().sort((a, b) => compareItemCatalogItems(a, b, preset));
      const useCountTotal = sortedItems.reduce((acc, item) => acc + Number(item.use_count || 0), 0);
      const prices = sortedItems
        .map((item) => Number(item.latest_unit_price || 0))
        .filter((value) => Number.isFinite(value) && value > 0);
      const avgPrice = prices.length ? prices.reduce((acc, value) => acc + value, 0) / prices.length : null;
      const lastUsedMs = sortedItems.reduce((max, item) => {
        const ts = itemCatalogLastUsedMs(item);
        return ts > max ? ts : max;
      }, 0);
      return {
        ...group,
        items: sortedItems,
        useCountTotal,
        avgPrice,
        lastUsedMs,
        lastUsedLabel: lastUsedMs ? new Date(lastUsedMs).toLocaleDateString("ru-RU") : "—",
      };
    });

    groups.sort((a, b) => {
      const aNoShop = a.shopKey === ITEM_CATALOG_NO_SHOP_KEY ? 1 : 0;
      const bNoShop = b.shopKey === ITEM_CATALOG_NO_SHOP_KEY ? 1 : 0;
      if (aNoShop !== bNoShop) {
        return aNoShop - bNoShop;
      }
      if (preset === "name") {
        return a.shopName.localeCompare(b.shopName, "ru");
      }
      if (preset === "recent") {
        const tsDiff = b.lastUsedMs - a.lastUsedMs;
        if (tsDiff !== 0) {
          return tsDiff;
        }
        const usageDiff = b.useCountTotal - a.useCountTotal;
        if (usageDiff !== 0) {
          return usageDiff;
        }
        return a.shopName.localeCompare(b.shopName, "ru");
      }
      const usageDiff = b.useCountTotal - a.useCountTotal;
      if (usageDiff !== 0) {
        return usageDiff;
      }
      const tsDiff = b.lastUsedMs - a.lastUsedMs;
      if (tsDiff !== 0) {
        return tsDiff;
      }
      return a.shopName.localeCompare(b.shopName, "ru");
    });

    return groups;
  }

  function toggleItemCatalogGroup(shopKey) {
    if (!shopKey) {
      return;
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
  }

  function setItemCatalogSortPreset(value) {
    const next = ["usage", "recent", "name"].includes(value) ? value : "usage";
    state.itemCatalogSortPreset = next;
    core.syncSegmentedActive(el.itemCatalogSortTabs, "item-sort", next);
    renderItemCatalog(state.itemCatalogItems);
    savePreferencesDebounced(450);
  }

  function collapseAllItemCatalogGroups() {
    const groups = buildItemCatalogGroups(state.itemCatalogItems || []);
    writeItemCatalogCollapsedShops(new Set(groups.map((group) => group.shopKey)));
    renderItemCatalog(state.itemCatalogItems);
    savePreferencesDebounced(450);
  }

  function expandAllItemCatalogGroups() {
    writeItemCatalogCollapsedShops(new Set());
    renderItemCatalog(state.itemCatalogItems);
    savePreferencesDebounced(450);
  }

  function syncItemCatalogControls(queryActive, hasRows) {
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

  function handleItemCatalogBodyClick(event) {
    const btn = event.target.closest("button[data-item-catalog-shop-key]");
    if (!btn) {
      return;
    }
    const query = String(el.itemCatalogSearchQ?.value || "").trim();
    if (query) {
      return;
    }
    const encodedKey = btn.dataset.itemCatalogShopKey || "";
    let shopKey = "";
    try {
      shopKey = encodedKey ? decodeURIComponent(encodedKey) : "";
    } catch {
      shopKey = "";
    }
    toggleItemCatalogGroup(shopKey);
  }

  function renderItemCatalog(items) {
    if (!el.itemCatalogBody) {
      return;
    }
    const rows = Array.isArray(items) ? items : [];
    const query = String(el.itemCatalogSearchQ?.value || "").trim();
    const queryActive = Boolean(query);
    core.syncSegmentedActive(el.itemCatalogSortTabs, "item-sort", state.itemCatalogSortPreset || "usage");
    const groupsAll = buildItemCatalogGroups(rows);
    const groups = queryActive
      ? groupsAll.filter((group) => {
        const sourceMatch = group.shopName.toLowerCase().includes(query.toLowerCase());
        return group.items.length > 0 || sourceMatch;
      })
      : groupsAll;
    if (!groups.length) {
      syncItemCatalogControls(queryActive, false);
      el.itemCatalogBody.innerHTML = '<tr><td colspan="4">Нет позиций</td></tr>';
      return;
    }
    syncItemCatalogControls(queryActive, true);
    const collapsedShops = readItemCatalogCollapsedShops();

    el.itemCatalogBody.innerHTML = groups.map((group) => {
      const isCollapsed = !queryActive && collapsedShops.has(group.shopKey);
      const chevron = isCollapsed ? "▸" : "▾";
      const childRows = group.items.map((item) => `
        <tr class="item-catalog-item-row ${isCollapsed ? "hidden" : ""}" data-item-template-row="1">
          <td></td>
          <td>${core.highlightText(item.name || "—", query)}</td>
          <td>${core.formatMoney(item.latest_unit_price || 0)}</td>
          <td>
            <div class="actions row-actions">
              <button class="btn btn-secondary btn-xs" data-item-template-history-id="${item.id}" type="button">История</button>
              <button class="btn btn-secondary btn-xs" data-edit-item-template-id="${item.id}" type="button">Редактировать</button>
              <button class="btn btn-danger btn-xs" data-delete-item-template-id="${item.id}" type="button">Удалить</button>
            </div>
          </td>
        </tr>
      `).join("");
      const emptyRow = !group.items.length && !isCollapsed
        ? '<tr class="item-catalog-item-row"><td></td><td colspan="3" class="muted-small">Позиции в источнике пока не добавлены</td></tr>'
        : "";
      return `
        <tr class="item-catalog-group-row">
          <td colspan="4" class="item-catalog-group-cell">
            <button type="button" class="item-catalog-group-btn" data-item-catalog-shop-key="${encodeURIComponent(group.shopKey)}" ${queryActive ? "disabled" : ""}>
              <span class="item-catalog-group-chevron">${chevron}</span>
              <span class="item-catalog-group-name">${core.highlightText(group.shopName, query)}</span>
              <span class="item-catalog-group-metas">
                <span class="item-catalog-group-meta">${group.items.length} поз.</span>
                <span class="item-catalog-group-meta">исп: ${group.useCountTotal}</span>
                <span class="item-catalog-group-meta">ср: ${group.avgPrice !== null ? core.formatMoney(group.avgPrice, { withCurrency: false }) : "—"}</span>
                <span class="item-catalog-group-meta">посл: ${group.lastUsedLabel}</span>
              </span>
            </button>
          </td>
        </tr>
        ${childRows}
        ${emptyRow}
      `;
    }).join("");
    const rowNodes = el.itemCatalogBody.querySelectorAll('tr.item-catalog-item-row[data-item-template-row="1"]');
    let index = 0;
    for (const group of groups) {
      for (const item of group.items) {
        const row = rowNodes[index];
        if (row) {
          row.dataset.itemTemplate = JSON.stringify(item);
        }
        index += 1;
      }
    }
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

  function openItemTemplateModal(item = null) {
    if (!el.itemTemplateModal || !el.itemTemplateForm) {
      return;
    }
    const isEdit = Boolean(item?.id);
    state.editItemTemplateId = isEdit ? Number(item.id) : null;
    if (el.itemTemplateModalTitle) {
      el.itemTemplateModalTitle.textContent = isEdit ? "Редактировать позицию" : "Новая позиция";
    }
    if (el.itemTemplateSource) {
      el.itemTemplateSource.value = normalizeItemCatalogShopName(item?.shop_name || "");
    }
    if (el.itemTemplateSourceSearch) {
      el.itemTemplateSourceSearch.value = normalizeItemCatalogShopName(item?.shop_name || "");
    }
    if (el.itemTemplateSourcePickerBlock) {
      el.itemTemplateSourcePickerBlock.classList.add("hidden");
    }
    if (el.itemTemplateName) {
      el.itemTemplateName.value = item?.name || "";
    }
    if (el.itemTemplatePrice) {
      el.itemTemplatePrice.value = item?.latest_unit_price || "";
    }
    if (el.itemTemplatePreviewBody) {
      updateItemTemplatePreview();
    }
    el.itemTemplateModal.classList.remove("hidden");
    setTimeout(() => {
      if (!isEdit && el.itemTemplateSourceSearch) {
        el.itemTemplateSourceSearch.focus();
        return;
      }
      if (el.itemTemplateName) {
        el.itemTemplateName.focus();
        el.itemTemplateName.select();
      }
    }, 0);
  }

  function closeItemTemplateModal() {
    state.editItemTemplateId = null;
    if (el.itemTemplateForm) {
      el.itemTemplateForm.reset();
    }
    if (el.itemTemplateModal) {
      el.itemTemplateModal.classList.add("hidden");
    }
    if (el.itemTemplatePreviewBody) {
      el.itemTemplatePreviewBody.innerHTML = "";
    }
    if (el.itemTemplateSourcePickerBlock) {
      el.itemTemplateSourcePickerBlock.classList.add("hidden");
    }
  }

  function closeItemTemplateSourcePicker() {
    if (el.itemTemplateSourcePickerBlock) {
      el.itemTemplateSourcePickerBlock.classList.add("hidden");
    }
  }

  function updateItemTemplatePreview() {
    if (!el.itemTemplatePreviewBody) {
      return;
    }
    const source = normalizeItemCatalogShopName(el.itemTemplateSource?.value || el.itemTemplateSourceSearch?.value || "") || "Без источника";
    const name = String(el.itemTemplateName?.value || "").trim() || "—";
    const price = Number(el.itemTemplatePrice?.value || 0);
    const validPrice = Number.isFinite(price) && price > 0 ? price : 0;
    el.itemTemplatePreviewBody.innerHTML = `
      <tr class="preview-row">
        <td>${escapeHtml(source)}</td>
        <td>${escapeHtml(name)}</td>
        <td>${core.formatMoney(validPrice)}</td>
      </tr>
    `;
  }

  async function submitItemTemplateForm(event) {
    event.preventDefault();
    const sourceName = normalizeItemCatalogShopName(el.itemTemplateSource?.value || el.itemTemplateSourceSearch?.value || "");
    const payload = {
      shop_name: sourceName || null,
      name: String(el.itemTemplateName?.value || "").trim(),
    };
    const priceRaw = String(el.itemTemplatePrice?.value || "").trim();
    if (priceRaw) {
      payload.latest_unit_price = priceRaw;
    }
    if (!payload.name) {
      core.setStatus("Введите название позиции");
      return;
    }
    const templateId = Number(state.editItemTemplateId || 0);
    const isEdit = templateId > 0;
    const url = isEdit ? `/api/v1/operations/item-templates/${templateId}` : "/api/v1/operations/item-templates";
    const method = isEdit ? "PATCH" : "POST";
    await core.requestJson(url, {
      method,
      headers: core.authHeaders(),
      body: JSON.stringify(payload),
    });
    if (sourceName) {
      const groups = readItemCatalogSourceGroups();
      if (!groups.some((name) => getItemCatalogShopKey(name) === getItemCatalogShopKey(sourceName))) {
        writeItemCatalogSourceGroups([...groups, sourceName]);
        savePreferencesDebounced(450);
      }
    }
    core.invalidateUiRequestCache("item-catalog");
    closeItemTemplateModal();
    await loadItemCatalog({ force: true });
  }

  function renderItemTemplateSourcePicker(query = "") {
    if (!el.itemTemplateSourcePickerBlock || !el.itemTemplateSourceAll) {
      return;
    }
    const normalizedQuery = normalizeItemCatalogShopName(query);
    const normalizedQueryCi = normalizedQuery.toLowerCase();
    const sources = listItemCatalogSourceNames(80);
    const matched = normalizedQuery
      ? sources.filter((name) => name.toLowerCase().includes(normalizedQueryCi))
      : sources.slice(0, 24);
    const exact = Boolean(normalizedQuery) && sources.some((name) => getItemCatalogShopKey(name) === getItemCatalogShopKey(normalizedQuery));
    const chips = matched.map((sourceName) => {
      const chip = core.renderCategoryChip({ name: sourceName, icon: null, accent_color: null }, normalizedQuery);
      return `<button type="button" class="chip-btn" data-item-template-source-name="${escapeHtml(sourceName)}">${chip}</button>`;
    }).join("");
    const createChip = normalizedQuery && !exact
      ? `<button type="button" class="chip-btn chip-btn-create" data-item-template-source-create="${escapeHtml(normalizedQuery)}">+ Создать источник «${escapeHtml(normalizedQuery)}»</button>`
      : "";
    el.itemTemplateSourceAll.innerHTML = chips + createChip || "<span class='muted-small'>Нет источников</span>";
    el.itemTemplateSourcePickerBlock.classList.remove("hidden");
  }

  function selectItemTemplateSource(name, { keepPickerOpen = false } = {}) {
    const normalized = normalizeItemCatalogShopName(name);
    if (el.itemTemplateSource) {
      el.itemTemplateSource.value = normalized;
    }
    if (el.itemTemplateSourceSearch) {
      el.itemTemplateSourceSearch.value = normalized;
    }
    updateItemTemplatePreview();
    if (!keepPickerOpen) {
      closeItemTemplateSourcePicker();
    }
  }

  function handleItemTemplateSourceSearchFocus() {
    renderItemTemplateSourcePicker(el.itemTemplateSourceSearch?.value || "");
  }

  function handleItemTemplateSourceSearchInput() {
    selectItemTemplateSource(el.itemTemplateSourceSearch?.value || "", { keepPickerOpen: true });
    renderItemTemplateSourcePicker(el.itemTemplateSourceSearch?.value || "");
  }

  function handleItemTemplateSourceSearchKeydown(event) {
    if (event.key === "Escape") {
      closeItemTemplateSourcePicker();
      return;
    }
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    const query = normalizeItemCatalogShopName(el.itemTemplateSourceSearch?.value || "");
    if (!query) {
      return;
    }
    const firstMatch = listItemCatalogSourceNames(80).find((name) => name.toLowerCase().includes(query.toLowerCase()));
    selectItemTemplateSource(firstMatch || query);
  }

  function handleItemTemplateSourcePickerClick(event) {
    const selectBtn = event.target.closest("[data-item-template-source-name]");
    if (selectBtn) {
      selectItemTemplateSource(selectBtn.dataset.itemTemplateSourceName || "");
      return;
    }
    const createBtn = event.target.closest("[data-item-template-source-create]");
    if (createBtn) {
      const createdName = createBtn.dataset.itemTemplateSourceCreate || "";
      selectItemTemplateSource(createdName);
      const normalized = normalizeItemCatalogShopName(createdName);
      if (normalized) {
        const groups = readItemCatalogSourceGroups();
        if (!groups.some((name) => getItemCatalogShopKey(name) === getItemCatalogShopKey(normalized))) {
          writeItemCatalogSourceGroups([...groups, normalized]);
          savePreferencesDebounced(450);
        }
      }
    }
  }

  function handleItemTemplateSourceOutsidePointer(event) {
    if (!el.itemTemplateSourcePickerBlock || el.itemTemplateSourcePickerBlock.classList.contains("hidden")) {
      return;
    }
    const path = typeof event.composedPath === "function" ? event.composedPath() : [];
    if (path.some((node) => node?.id === "itemTemplateSourceField")) {
      return;
    }
    closeItemTemplateSourcePicker();
  }

  function handleItemTemplateSourceSearchFocusOut(event) {
    const next = event.relatedTarget;
    if (next && next.closest && next.closest("#itemTemplateSourceField")) {
      return;
    }
    setTimeout(() => {
      const active = document.activeElement;
      if (active && active.closest && active.closest("#itemTemplateSourceField")) {
        return;
      }
      closeItemTemplateSourcePicker();
    }, 0);
  }

  async function deleteItemTemplateFlow(item) {
    core.runDestructiveAction({
      confirmMessage: `Удалить позицию «${item.name || "без названия"}»?`,
      doDelete: async () => {
        await core.requestJson(`/api/v1/operations/item-templates/${item.id}`, {
          method: "DELETE",
          headers: core.authHeaders(),
        });
        core.invalidateUiRequestCache("item-catalog");
      },
      onAfterDelete: async () => {
        await loadItemCatalog({ force: true });
      },
      toastMessage: "Позиция удалена",
      onDeleteError: "Не удалось удалить позицию",
    });
  }

  async function deleteAllItemTemplatesFlow() {
    core.runDestructiveAction({
      confirmMessage: "Удалить все позиции из каталога?",
      doDelete: async () => {
        await core.requestJson("/api/v1/operations/item-templates", {
          method: "DELETE",
          headers: core.authHeaders(),
        });
        core.invalidateUiRequestCache("item-catalog");
      },
      onAfterDelete: async () => {
        await loadItemCatalog({ force: true });
      },
      toastMessage: "Каталог позиций очищен",
      onDeleteError: "Не удалось удалить позиции",
    });
  }

  function openSourceGroupModal() {
    if (!el.sourceGroupModal || !el.sourceGroupForm) {
      return;
    }
    el.sourceGroupForm.reset();
    updateSourceGroupPreview();
    el.sourceGroupModal.classList.remove("hidden");
    setTimeout(() => {
      if (el.sourceGroupName) {
        el.sourceGroupName.focus();
      }
    }, 0);
  }

  function closeSourceGroupModal() {
    if (el.sourceGroupModal) {
      el.sourceGroupModal.classList.add("hidden");
    }
  }

  function updateSourceGroupPreview() {
    if (!el.sourceGroupPreviewBody) {
      return;
    }
    const sourceName = normalizeItemCatalogShopName(el.sourceGroupName?.value || "") || "—";
    if (sourceName === "—") {
      el.sourceGroupPreviewBody.innerHTML = "";
      return;
    }
    const sourceKey = getItemCatalogShopKey(sourceName);
    const existingGroup = buildItemCatalogGroups(state.itemCatalogItems || []).find((group) => group.shopKey === sourceKey);
    const positions = existingGroup?.items?.length || 0;
    const usage = existingGroup?.useCountTotal || 0;
    const avg = existingGroup?.avgPrice !== null && existingGroup?.avgPrice !== undefined
      ? core.formatMoney(existingGroup.avgPrice, { withCurrency: false })
      : "—";
    el.sourceGroupPreviewBody.innerHTML = `
      <tr class="preview-row">
        <td>${escapeHtml(sourceName)}</td>
        <td>${positions}</td>
        <td>${usage}</td>
        <td>${avg}</td>
      </tr>
    `;
  }

  async function submitSourceGroupForm(event) {
    event.preventDefault();
    const sourceName = normalizeItemCatalogShopName(el.sourceGroupName?.value || "");
    if (!sourceName) {
      core.setStatus("Введите название источника");
      return;
    }
    const groups = readItemCatalogSourceGroups();
    const exists = groups.some((name) => getItemCatalogShopKey(name) === getItemCatalogShopKey(sourceName));
    if (exists) {
      closeSourceGroupModal();
      renderItemCatalog(state.itemCatalogItems);
      return;
    }
    writeItemCatalogSourceGroups([...groups, sourceName]);
    closeSourceGroupModal();
    renderItemCatalog(state.itemCatalogItems);
    savePreferencesDebounced(450);
  }

  async function openItemTemplateHistoryModal(item) {
    if (!item?.id || !el.itemTemplateHistoryModal || !el.itemTemplateHistoryBody) {
      return;
    }
    if (el.itemTemplateHistoryTitle) {
      el.itemTemplateHistoryTitle.textContent = `История цен: ${item.name || "Позиция"}`;
    }
    if (el.itemTemplateHistoryMeta) {
      const source = normalizeItemCatalogShopName(item.shop_name || "") || "Без источника";
      el.itemTemplateHistoryMeta.innerHTML = `
        <div class="muted-small">Источник</div>
        <div class="operation-receipt-shop">${core.renderCategoryChip({ name: source, icon: null, accent_color: null }, "")}</div>
      `;
    }
    el.itemTemplateHistoryBody.innerHTML = '<tr><td colspan="2">Загрузка...</td></tr>';
    el.itemTemplateHistoryModal.classList.remove("hidden");
    const rows = await core.requestJson(`/api/v1/operations/item-templates/${item.id}/prices?limit=200`, {
      headers: core.authHeaders(),
    });
    const list = Array.isArray(rows) ? rows : [];
    if (!list.length) {
      el.itemTemplateHistoryBody.innerHTML = '<tr><td colspan="2">История цен пока пустая</td></tr>';
      return;
    }
    el.itemTemplateHistoryBody.innerHTML = list.map((row) => `
      <tr>
        <td>${core.formatDateRu(row.recorded_at)}</td>
        <td>${core.formatMoney(row.unit_price || 0)}</td>
      </tr>
    `).join("");
  }

  function closeItemTemplateHistoryModal() {
    if (el.itemTemplateHistoryModal) {
      el.itemTemplateHistoryModal.classList.add("hidden");
    }
  }

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

  window.App.featureItemCatalog = {
    loadItemCatalog,
    setItemCatalogSortPreset,
    collapseAllItemCatalogGroups,
    expandAllItemCatalogGroups,
    handleItemCatalogBodyClick,
    openItemTemplateModal,
    closeItemTemplateModal,
    submitItemTemplateForm,
    deleteItemTemplateFlow,
    deleteAllItemTemplatesFlow,
    openSourceGroupModal,
    closeSourceGroupModal,
    submitSourceGroupForm,
    updateSourceGroupPreview,
    updateItemTemplatePreview,
    handleItemTemplateSourceSearchFocus,
    handleItemTemplateSourceSearchInput,
    handleItemTemplateSourceSearchKeydown,
    handleItemTemplateSourcePickerClick,
    handleItemTemplateSourceOutsidePointer,
    handleItemTemplateSourceSearchFocusOut,
    openItemTemplateHistoryModal,
    closeItemTemplateHistoryModal,
    cleanupItemCatalogRuntime,
  };
})();
