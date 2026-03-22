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

    function getActions() {
      return window.App.actions || {};
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

    function getReceiptTemplateMatch(token, shopName = "") {
      const normalizedToken = normalizeReceiptName(token).toLowerCase();
      if (!normalizedToken) {
        return null;
      }
      const shopCi = normalizeReceiptName(shopName).toLowerCase();
      return (state.receiptTemplateHints || []).find((item) => (
        item.name_ci === normalizedToken
        && (!shopCi || (item.shop_name_ci || "") === shopCi)
      )) || null;
    }

    function getReceiptTemplateSuggestions(query, shopName = "", limit = 6) {
      const normalized = normalizeReceiptName(query).toLowerCase();
      const shopCi = normalizeReceiptName(shopName).toLowerCase();
      const templates = Array.isArray(state.receiptTemplateHints) ? state.receiptTemplateHints : [];
      const scopedTemplates = shopCi
        ? templates.filter((item) => (item.shop_name_ci || "") === shopCi)
        : templates;
      if (!normalized) {
        return scopedTemplates.slice(0, limit);
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
        if (starts.length + contains.length >= limit) {
          break;
        }
      }
      return [...starts, ...contains].slice(0, limit);
    }

    function getReceiptShopSuggestions(query = "", limit = 24) {
      const normalized = normalizeReceiptName(query).toLowerCase();
      const byShop = new Map();
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

    function upsertLocalReceiptTemplate(name, latestUnitPrice = 0, shopName = "") {
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
        return existing;
      }
      receiptUiState.localTemplateSeq += 1;
      const created = {
        id: -receiptUiState.localTemplateSeq,
        shop_name: normalizedShop || null,
        shop_name_ci: shopNameCi || "",
        name: normalizedName,
        name_ci: nameCi,
        last_category_id: null,
        latest_unit_price: Number(latestUnitPrice || 0) || 0,
      };
      state.receiptTemplateHints = [created, ...(state.receiptTemplateHints || [])];
      return created;
    }

    function hideAllReceiptPickers() {
      for (const listNode of [el.receiptItemsList, el.editReceiptItemsList]) {
        if (!listNode) {
          continue;
        }
        listNode.querySelectorAll(".receipt-item-row").forEach((node) => node.classList.remove("has-open-popover"));
        listNode.querySelectorAll(".receipt-shop-cell, .receipt-name-cell, .receipt-category-cell").forEach((node) => node.classList.remove("has-open-popover"));
        listNode.querySelectorAll(".receipt-shop-picker, .receipt-name-picker, .receipt-category-picker").forEach((node) => {
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
        <button type="button" class="chip-btn" data-receipt-shop-name="${escHtml(shopName)}" data-receipt-item-id="${rowItem.draft_id}">
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
      const exact = getReceiptTemplateMatch(normalizedQuery, rowItem.shop_name || "");
      const suggestions = getReceiptTemplateSuggestions(normalizedQuery, rowItem.shop_name || "");
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
        <button type="button" class="chip-btn" data-receipt-template-id="${item.id}" data-receipt-item-id="${rowItem.draft_id}">
          ${core.renderCategoryChip({ name: item.name, icon: "🧾", accent_color: null }, normalizedQuery)}
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
      if (getActions().openCreateCategoryModal) {
        getActions().openCreateCategoryModal({
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

    async function loadReceiptTemplates(query = "") {
      const normalized = String(query || "").trim().toLowerCase();
      const cacheKey = `op:receipt:templates:q=${normalized}`;
      const cached = core.getUiRequestCache ? core.getUiRequestCache(cacheKey, RECEIPT_TEMPLATES_CACHE_TTL_MS) : null;
      if (cached) {
        return cached.items || [];
      }
      const params = new URLSearchParams({
        page: "1",
        page_size: "20",
      });
      if (normalized) {
        params.set("q", normalized);
      }
      const payload = await core.requestJson(`/api/v1/operations/item-templates?${params.toString()}`, {
        headers: core.authHeaders(),
      });
      if (core.setUiRequestCache) {
        core.setUiRequestCache(cacheKey, payload);
      }
      return payload.items || [];
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
        try {
          templates = await loadReceiptTemplates("");
        } catch {
          templates = [];
        }
        const serverTemplates = templates.map((item) => ({
          id: Number(item.id || 0),
          shop_name: normalizeReceiptName(item.shop_name || "") || null,
          shop_name_ci: normalizeReceiptName(item.shop_name || "").toLowerCase(),
          name: normalizeReceiptName(item.name || ""),
          name_ci: normalizeReceiptName(item.name || "").toLowerCase(),
          last_category_id: item.last_category_id ? Number(item.last_category_id) : null,
          latest_unit_price: Number(item.latest_unit_price || 0) || 0,
        }));
        const merged = [...serverTemplates];
        for (const localItem of state.receiptTemplateHints || []) {
          if (!localItem?.name_ci) {
            continue;
          }
          if (!merged.some((serverItem) => serverItem.name_ci === localItem.name_ci && (serverItem.shop_name_ci || "") === (localItem.shop_name_ci || ""))) {
            merged.push(localItem);
          }
        }
        state.receiptTemplateHints = merged;
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
      getReceiptShopSuggestions,
      upsertLocalReceiptTemplate,
      hideAllReceiptPickers,
      renderReceiptShopPickerForRow,
      renderReceiptNamePickerForRow,
      openCreateCategoryFromReceipt,
      renderReceiptCategoryPickerForRow,
      loadReceiptTemplateHints,
    };
  }

  window.App = window.App || {};
  window.App.registerRuntimeModule?.("operation-modal-receipt-picker-factory", createOperationModalReceiptPickerFeature);
})();
