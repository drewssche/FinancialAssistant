(() => {
  function createOperationModalReceiptInteractionsFeature(deps) {
    const {
      state,
      el,
      core,
      receiptUiState,
      normalizeReceiptName,
      getReceiptModeFromNode,
      getReceiptItemByDraftId,
      getReceiptContext,
      updateReceiptItemField,
      ensureTrailingReceiptRow,
      renderReceiptItems,
      renderReceiptSummary,
      receiptLineTotal,
      removeReceiptItem,
      updateCreatePreview,
      updateEditPreview,
      RECEIPT_TEMPLATES_CACHE_TTL_MS,
    } = deps;
    const CATEGORY_USAGE_KEY = "fa_category_usage_v1";
    function escHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }
    function readCategoryUsage() {
      try {
        const raw = localStorage.getItem(CATEGORY_USAGE_KEY);
        const parsed = raw ? JSON.parse(raw) : {};
        return parsed && typeof parsed === "object" ? parsed : {};
      } catch {
        return {};
      }
    }
    function getReceiptCategoriesSorted(kind, query = "") {
      const usage = readCategoryUsage();
      const normalizedQuery = String(query || "").trim().toLowerCase();
      return (state.categories || [])
        .filter((item) => item.kind === kind)
        .filter((item) => {
          if (!normalizedQuery) {
            return true;
          }
          return item.name.toLowerCase().includes(normalizedQuery) || (item.group_name || "").toLowerCase().includes(normalizedQuery);
        })
        .map((item) => ({ ...item, usage: Number(usage[String(item.id)] || 0) }))
        .sort((a, b) => {
          if (b.usage !== a.usage) {
            return b.usage - a.usage;
          }
          const colorA = (a.group_accent_color || "~").toLowerCase();
          const colorB = (b.group_accent_color || "~").toLowerCase();
          if (colorA !== colorB) {
            return colorA.localeCompare(colorB, "ru");
          }
          const groupA = (a.group_name || "~").toLowerCase();
          const groupB = (b.group_name || "~").toLowerCase();
          if (groupA !== groupB) {
            return groupA.localeCompare(groupB, "ru");
          }
          return a.name.localeCompare(b.name, "ru");
        });
    }
    function createReceiptCategoryChipButton(category, selected, searchQuery = "") {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chip-btn";
      if (selected) {
        btn.classList.add("active");
      }
      btn.dataset.receiptCategoryId = String(category.id);
      btn.innerHTML = core.renderCategoryChip(
        {
          name: category.name,
          icon: category.icon || category.group_icon || null,
          accent_color: category.group_accent_color || null,
        },
        searchQuery,
      );
      return btn;
    }

    function createReceiptNoCategoryChipButton(selected) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chip-btn chip-btn-meta";
      if (selected) {
        btn.classList.add("active");
      }
      btn.dataset.receiptCategoryId = "";
      btn.innerHTML = core.renderMetaChip("Без категории");
      return btn;
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
    function getReceiptShopSuggestions(query = "", limit = 8) {
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
        if (byShop.size >= limit) {
          break;
        }
      }
      return Array.from(byShop.values()).slice(0, limit);
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
        listNode.querySelectorAll(".receipt-shop-picker").forEach((node) => node.classList.add("hidden"));
        listNode.querySelectorAll(".receipt-name-picker").forEach((node) => node.classList.add("hidden"));
        listNode.querySelectorAll(".receipt-category-picker").forEach((node) => node.classList.add("hidden"));
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
      picker.classList.remove("hidden");
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
      picker.classList.remove("hidden");
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
      if (window.App.actions?.openCreateCategoryModal) {
        window.App.actions.openCreateCategoryModal({
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
        const createChip = document.createElement("button");
        createChip.type = "button";
        createChip.className = "chip-btn chip-btn-create";
        createChip.dataset.receiptCreateCategory = normalizedQuery;
        createChip.dataset.receiptItemId = String(rowItem.draft_id);
        createChip.textContent = `+ Создать категорию «${normalizedQuery}»`;
        picker.appendChild(createChip);
      }
      if (!categories.length && !normalizedQuery) {
        const empty = document.createElement("span");
        empty.className = "muted-small";
        empty.textContent = "Без категорий для выбранного типа";
        picker.appendChild(empty);
      }
      picker.classList.remove("hidden");
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
    function commitReceiptRowMutation(mode) {
      ensureTrailingReceiptRow(mode);
      renderReceiptItems(mode);
      renderReceiptSummary(mode);
      if (mode === "create") {
        updateCreatePreview();
      } else {
        updateEditPreview();
      }
    }
    function handleReceiptItemsListInput(event) {
      const row = event.target.closest("[data-receipt-item-id]");
      if (!row) {
        return;
      }
      const draftId = Number(row.dataset.receiptItemId || 0);
      const field = event.target.dataset.receiptField;
      if (!field) {
        return;
      }
      const mode = getReceiptModeFromNode(row);
      const cursorPos = typeof event.target.selectionStart === "number" ? event.target.selectionStart : null;
      const updated = updateReceiptItemField(draftId, field, event.target.value, mode);
      if (!updated?.item) {
        return;
      }
      if (field === "name") {
        const token = normalizeReceiptName(event.target.value).toLowerCase();
        const matched = getReceiptTemplateMatch(token, updated.item.shop_name || "");
        if (matched) {
          updated.item.template_id = matched.id;
          updated.item.shop_name = normalizeReceiptName(matched.shop_name || updated.item.shop_name || "");
          if (!updated.item.category_id && matched.last_category_id) {
            updated.item.category_id = Number(matched.last_category_id);
          }
          if (!updated.item.unit_price || Number(updated.item.unit_price) <= 0) {
            updated.item.unit_price = matched.latest_unit_price || 0;
            const rowPriceInput = row.querySelector('[data-receipt-field="unit_price"]');
            if (rowPriceInput) {
              rowPriceInput.value = core.formatAmount(updated.item.unit_price);
            }
          }
          upsertLocalReceiptTemplate(updated.item.name, updated.item.unit_price, updated.item.shop_name || "");
        } else {
          updated.item.template_id = null;
        }
      }
      let structureChanged = false;
      if (field === "name" && updated.hadName !== updated.hasName) {
        commitReceiptRowMutation(mode);
        structureChanged = true;
      } else {
        const totalCell = row.querySelector(".receipt-line-total");
        if (totalCell) {
          totalCell.innerHTML = `<span>Итого</span><strong>${core.formatMoney(receiptLineTotal(updated.item), { withCurrency: false })}</strong>`;
        }
      }
      if (field === "category_search") {
        updated.item.category_id = null;
      }
      if (field === "shop_name") {
        renderReceiptShopPickerForRow(row, updated.item, event.target.value);
      }
      if (field === "name") {
        renderReceiptNamePickerForRow(row, updated.item, event.target.value);
      }
      if (field === "category_search") {
        renderReceiptCategoryPickerForRow(row, updated.item, event.target.value);
      }
      if (!structureChanged) {
        renderReceiptSummary(mode);
        if (mode === "create") {
          updateCreatePreview();
        } else {
          updateEditPreview();
        }
      }
      if (structureChanged) {
        const listNode = getReceiptContext(mode).listNode;
        const restoredInput = listNode?.querySelector(
          `[data-receipt-item-id="${draftId}"] [data-receipt-field="${field}"]`,
        );
        if (restoredInput) {
          restoredInput.focus();
          if ((field === "name" || field === "shop_name") && cursorPos !== null && typeof restoredInput.setSelectionRange === "function") {
            restoredInput.setSelectionRange(cursorPos, cursorPos);
          }
          if (field === "shop_name") {
            const restoredRow = restoredInput.closest("[data-receipt-item-id]");
            const restoredItem = getReceiptItemByDraftId(draftId, mode);
            if (restoredRow && restoredItem) {
              renderReceiptShopPickerForRow(restoredRow, restoredItem, restoredInput.value);
            }
          }
          if (field === "name") {
            const restoredRow = restoredInput.closest("[data-receipt-item-id]");
            const restoredItem = getReceiptItemByDraftId(draftId, mode);
            if (restoredRow && restoredItem) {
              renderReceiptNamePickerForRow(restoredRow, restoredItem, restoredInput.value);
            }
          }
          if (field === "category_search") {
            const restoredRow = restoredInput.closest("[data-receipt-item-id]");
            const restoredItem = getReceiptItemByDraftId(draftId, mode);
            if (restoredRow && restoredItem) {
              renderReceiptCategoryPickerForRow(restoredRow, restoredItem, restoredInput.value);
            }
          }
        }
      }
    }
    function handleReceiptItemsListFocusIn(event) {
      const input = event.target.closest('[data-receipt-field="name"], [data-receipt-field="shop_name"], [data-receipt-field="category_search"]');
      if (!input) return;
      const row = input.closest("[data-receipt-item-id]");
      if (!row) return;
      const draftId = Number(row.dataset.receiptItemId || 0);
      const mode = getReceiptModeFromNode(row);
      const rowItem = getReceiptItemByDraftId(draftId, mode);
      if (!rowItem) return;
      const field = input.dataset.receiptField;
      if (field === "shop_name") {
        renderReceiptShopPickerForRow(row, rowItem, input.value);
        return;
      }
      if (field === "category_search") {
        renderReceiptCategoryPickerForRow(row, rowItem, input.value);
        return;
      }
      renderReceiptNamePickerForRow(row, rowItem, input.value);
    }
    function handleReceiptItemsListKeydown(event) {
      const input = event.target.closest('[data-receipt-field="name"], [data-receipt-field="shop_name"], [data-receipt-field="category_search"]');
      if (!input) return;
      const row = input.closest("[data-receipt-item-id]");
      if (!row) return;
      const draftId = Number(row.dataset.receiptItemId || 0);
      const mode = getReceiptModeFromNode(row);
      const rowItem = getReceiptItemByDraftId(draftId, mode);
      if (!rowItem) return;
      if (event.key === "Escape") {
        const picker = input.dataset.receiptField === "shop_name"
          ? row.querySelector(".receipt-shop-picker")
          : input.dataset.receiptField === "category_search"
            ? row.querySelector(".receipt-category-picker")
            : row.querySelector(".receipt-name-picker");
        picker?.classList.add("hidden");
        receiptUiState.activePicker = null;
        return;
      }
      if (event.key !== "Enter") return;
      event.preventDefault();
      const query = normalizeReceiptName(input.value);
      if (!query) return;
      const field = input.dataset.receiptField;
      if (field === "shop_name") {
        const shops = getReceiptShopSuggestions(query, 1);
        const firstShop = shops[0] || query;
        rowItem.shop_name = normalizeReceiptName(firstShop);
        rowItem.template_id = null;
        commitReceiptRowMutation(mode);
        return;
      }
      if (field === "category_search") {
        const categories = getReceiptCategoriesSorted(
          mode === "edit" ? (el.editKind?.value || "expense") : (el.opKind?.value || "expense"),
          query,
        );
        if (categories.length) {
          rowItem.category_id = Number(categories[0].id);
        } else {
          openCreateCategoryFromReceipt(row, rowItem, query);
          return;
        }
        commitReceiptRowMutation(mode);
        return;
      }
      const exact = getReceiptTemplateMatch(query, rowItem.shop_name || "");
      const first = exact || getReceiptTemplateSuggestions(query, rowItem.shop_name || "", 1)[0] || null;
      if (first) {
        rowItem.name = first.name;
        rowItem.template_id = first.id;
        rowItem.shop_name = normalizeReceiptName(first.shop_name || rowItem.shop_name || "");
        if (!rowItem.category_id && first.last_category_id) {
          rowItem.category_id = Number(first.last_category_id);
        }
        if (!rowItem.unit_price || Number(rowItem.unit_price) <= 0) {
          rowItem.unit_price = first.latest_unit_price || 0;
        }
      } else {
        rowItem.name = query;
        rowItem.template_id = null;
      }
      commitReceiptRowMutation(mode);
      const nextInput = getReceiptContext(mode).listNode?.querySelector(
        `[data-receipt-item-id="${rowItem.draft_id}"] [data-receipt-field="name"]`,
      );
      nextInput?.blur();
    }
    function handleReceiptItemsListClick(event) {
      const shopBtn = event.target.closest("button[data-receipt-shop-name], button[data-receipt-create-shop]");
      if (shopBtn) {
        const draftId = Number(shopBtn.dataset.receiptItemId || 0);
        const row = shopBtn.closest("[data-receipt-item-id]");
        const mode = getReceiptModeFromNode(row);
        const rowItem = getReceiptItemByDraftId(draftId, mode);
        if (rowItem) {
          rowItem.shop_name = normalizeReceiptName(
            shopBtn.dataset.receiptShopName || shopBtn.dataset.receiptCreateShop || "",
          );
          rowItem.template_id = null;
          receiptUiState.activePicker = null;
          commitReceiptRowMutation(mode);
        }
        return;
      }
      const templateBtn = event.target.closest("button[data-receipt-template-id]");
      if (templateBtn) {
        const draftId = Number(templateBtn.dataset.receiptItemId || 0);
        const templateId = Number(templateBtn.dataset.receiptTemplateId || 0);
        const row = templateBtn.closest("[data-receipt-item-id]");
        const mode = getReceiptModeFromNode(row);
        const rowItem = getReceiptItemByDraftId(draftId, mode);
        const template = (state.receiptTemplateHints || []).find((item) => Number(item.id) === templateId);
        if (rowItem && template) {
          rowItem.shop_name = normalizeReceiptName(template.shop_name || rowItem.shop_name || "");
          rowItem.name = template.name;
          rowItem.template_id = template.id;
          if (!rowItem.category_id && template.last_category_id) {
            rowItem.category_id = Number(template.last_category_id);
          }
          if (!rowItem.unit_price || Number(rowItem.unit_price) <= 0) {
            rowItem.unit_price = template.latest_unit_price || 0;
          }
          if (!rowItem.quantity || Number(rowItem.quantity) <= 0) {
            rowItem.quantity = 1;
          }
          upsertLocalReceiptTemplate(rowItem.name, rowItem.unit_price, rowItem.shop_name || "");
          receiptUiState.activePicker = null;
          commitReceiptRowMutation(mode);
        }
        return;
      }
      const createBtn = event.target.closest("button[data-receipt-create-name]");
      if (createBtn) {
        const draftId = Number(createBtn.dataset.receiptItemId || 0);
        const row = createBtn.closest("[data-receipt-item-id]");
        const mode = getReceiptModeFromNode(row);
        const rowItem = getReceiptItemByDraftId(draftId, mode);
        if (rowItem) {
          rowItem.name = normalizeReceiptName(createBtn.dataset.receiptCreateName || "");
          const createdTemplate = upsertLocalReceiptTemplate(rowItem.name, rowItem.unit_price, rowItem.shop_name || "");
          rowItem.template_id = createdTemplate?.id || null;
          if (!rowItem.quantity || Number(rowItem.quantity) <= 0) {
            rowItem.quantity = 1;
          }
          receiptUiState.activePicker = null;
          commitReceiptRowMutation(mode);
        }
        return;
      }
      const categoryBtn = event.target.closest("button[data-receipt-category-id], button[data-receipt-create-category]");
      if (categoryBtn) {
        const draftId = Number(categoryBtn.dataset.receiptItemId || 0) || Number(categoryBtn.closest("[data-receipt-item-id]")?.dataset.receiptItemId || 0);
        const row = categoryBtn.closest("[data-receipt-item-id]");
        const mode = getReceiptModeFromNode(row);
        const rowItem = getReceiptItemByDraftId(draftId, mode);
        if (!rowItem || !row) {
          return;
        }
        if (categoryBtn.dataset.receiptCreateCategory) {
          openCreateCategoryFromReceipt(row, rowItem, categoryBtn.dataset.receiptCreateCategory || "");
          return;
        }
        rowItem.category_id = categoryBtn.dataset.receiptCategoryId ? Number(categoryBtn.dataset.receiptCategoryId) : null;
        receiptUiState.activePicker = null;
        commitReceiptRowMutation(mode);
        return;
      }
      const removeBtn = event.target.closest("button[data-receipt-remove-id]");
      if (!removeBtn) return;
      const row = removeBtn.closest("[data-receipt-item-id]");
      const mode = getReceiptModeFromNode(row);
      removeReceiptItem(Number(removeBtn.dataset.receiptRemoveId || 0), mode);
    }
    function handleReceiptOutsidePointer(event) {
      const insideShopCell = event.target.closest(".receipt-shop-cell");
      const insideShopPicker = event.target.closest(".receipt-shop-picker");
      const insideActiveNameCell = event.target.closest(".receipt-name-cell");
      const insidePicker = event.target.closest(".receipt-name-picker");
      const insideCategoryCell = event.target.closest(".receipt-category-cell");
      const insideCategoryPicker = event.target.closest(".receipt-category-picker");
      if (insideShopCell || insideShopPicker || insideActiveNameCell || insidePicker || insideCategoryCell || insideCategoryPicker) {
        return;
      }
      hideAllReceiptPickers();
    }
    return {
      loadReceiptTemplateHints,
      hideAllReceiptPickers,
      handleReceiptItemsListInput,
      handleReceiptItemsListFocusIn,
      handleReceiptItemsListKeydown,
      handleReceiptItemsListClick,
      handleReceiptOutsidePointer,
    };
  }
  window.App = window.App || {};
  window.App.createOperationModalReceiptInteractionsFeature = createOperationModalReceiptInteractionsFeature;
})();
