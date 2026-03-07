(() => {
  const { state, el, core } = window.App;
  const categoryActions = window.App.actions;
  const CATEGORY_USAGE_KEY = "fa_category_usage_v1";
  const RECEIPT_TEMPLATES_CACHE_TTL_MS = 20000;
  let activeReceiptPicker = null;
  let receiptLocalTemplateSeq = 0;

  function readCategoryUsage() {
    try {
      const raw = localStorage.getItem(CATEGORY_USAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  }

  function writeCategoryUsage(usage) {
    localStorage.setItem(CATEGORY_USAGE_KEY, JSON.stringify(usage));
  }

  function trackCategoryUsage(categoryId) {
    if (!categoryId) {
      return;
    }
    const usage = readCategoryUsage();
    const key = String(categoryId);
    usage[key] = Number(usage[key] || 0) + 1;
    writeCategoryUsage(usage);
  }

  function getSelectedCreateCategoryId() {
    return el.opCategory.value ? Number(el.opCategory.value) : null;
  }

  function getCategoryMetaById(categoryId) {
    if (!categoryId) {
      return null;
    }
    const category = state.categories.find((item) => item.id === categoryId);
    if (!category) {
      return null;
    }
    return {
      id: category.id,
      name: category.name,
      icon: category.icon || category.group_icon || null,
      accent_color: category.group_accent_color || null,
      kind: category.kind,
      group_name: category.group_name || "",
    };
  }

  function getCreateFormCategoryMeta() {
    return getCategoryMetaById(getSelectedCreateCategoryId());
  }

  const previewModule = window.App.operationModalPreview;
  const preview = previewModule?.build({
    state,
    el,
    core,
    getSelectedCreateCategoryId,
    getCategoryMetaById,
  });
  const updateDebtDueHint = preview?.updateDebtDueHint || (() => {});
  const getCreateFormPreviewItem = preview?.getCreateFormPreviewItem || (() => ({}));
  const getEditFormPreviewItem = preview?.getEditFormPreviewItem || (() => ({}));
  const updateCreatePreview = preview?.updateCreatePreview || (() => {});
  const updateEditPreview = preview?.updateEditPreview || (() => {});
  const handleCreatePreviewClick = preview?.handleCreatePreviewClick || (() => {});

  function openCreateCategoryPopover() {
    if (el.opEntryMode.value === "debt") {
      return;
    }
    el.createCategoryPickerBlock.classList.remove("hidden");
  }

  function closeCreateCategoryPopover() {
    el.createCategoryPickerBlock.classList.add("hidden");
  }

  function getCreateCategoriesSorted(kind, query = "") {
    const usage = readCategoryUsage();
    const normalizedQuery = query.trim().toLowerCase();
    return state.categories
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

  function createCategoryChipButton(category, selected, searchQuery = "") {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip-btn";
    if (selected) {
      btn.classList.add("active");
    }
    btn.dataset.categoryId = String(category.id);
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

  function renderCreateCategoryPicker() {
    const kind = el.opKind.value || "expense";
    const selectedId = getSelectedCreateCategoryId();
    const selectedCategory = state.categories.find((item) => item.id === selectedId && item.kind === kind);
    const rawQuery = el.opCategorySearch.value.trim();
    const query = selectedCategory && rawQuery.toLowerCase() === selectedCategory.name.toLowerCase() ? "" : rawQuery;
    const allCategories = getCreateCategoriesSorted(kind, query);

    el.opCategoryAll.innerHTML = "";
    for (const item of allCategories) {
      const chip = createCategoryChipButton(item, selectedId === item.id, query);
      el.opCategoryAll.appendChild(chip);
    }
    if (!allCategories.length && query) {
      const createChip = document.createElement("button");
      createChip.type = "button";
      createChip.className = "chip-btn chip-btn-create";
      createChip.dataset.createCategory = query;
      createChip.textContent = `+ Создать категорию «${query}»`;
      el.opCategoryAll.appendChild(createChip);
    }
    if (!allCategories.length && !query) {
      el.opCategoryAll.innerHTML = "<span class='muted-small'>Без категорий для выбранного типа</span>";
    }
  }

  function setDebtDirection(direction) {
    const nextDirection = direction === "borrow" ? "borrow" : "lend";
    el.debtDirection.value = nextDirection;
    core.syncSegmentedActive(el.createDebtDirectionSwitch, "debt-direction", nextDirection);
    updateCreatePreview();
  }

  function applyDebtCurrencyUi() {
    core.applyMoneyInputs();
  }

  function selectCreateCategory(categoryId, options = {}) {
    const value = categoryId ? String(categoryId) : "";
    el.opCategory.value = value;
    const categoryMeta = getCreateFormCategoryMeta();
    if (!options.keepSearch) {
      el.opCategorySearch.value = categoryMeta?.name || "";
    }
    renderCreateCategoryPicker();
    updateCreatePreview();
    closeCreateCategoryPopover();
  }

  function handleCreateCategorySearchFocus() {
    openCreateCategoryPopover();
    renderCreateCategoryPicker();
  }

  function handleCreateCategorySearchInput() {
    if (el.opCategory.value) {
      el.opCategory.value = "";
    }
    openCreateCategoryPopover();
    renderCreateCategoryPicker();
    updateCreatePreview();
  }

  function handleCreateCategorySearchKeydown(event) {
    if (event.key === "Escape") {
      closeCreateCategoryPopover();
      return;
    }
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    const query = el.opCategorySearch.value.trim();
    const matches = getCreateCategoriesSorted(el.opKind.value || "expense", query);
    if (matches.length) {
      selectCreateCategory(matches[0].id);
      return;
    }
    if (query) {
      openCreateCategoryFromOperation(query);
    }
  }

  function handleCreateCategoryOutsidePointer(event) {
    if (el.createCategoryPickerBlock.classList.contains("hidden")) {
      return;
    }
    if (event.target.closest("#createCategoryField")) {
      return;
    }
    closeCreateCategoryPopover();
  }

  function openCreateCategoryFromOperation(searchText) {
    const trimmed = searchText.trim();
    state.pendingCreateCategoryFromOperation = trimmed;
    closeCreateCategoryPopover();
    if (categoryActions.openCreateCategoryModal) {
      categoryActions.openCreateCategoryModal({
        kind: el.opKind.value || "expense",
        prefillName: trimmed,
        reset: true,
      });
    }
  }

  function handleCreateCategoryPickerClick(event) {
    const createBtn = event.target.closest("button[data-create-category]");
    if (createBtn) {
      openCreateCategoryFromOperation(createBtn.dataset.createCategory || "");
      return;
    }
    const chipBtn = event.target.closest("button[data-category-id]");
    if (!chipBtn) {
      return;
    }
    selectCreateCategory(Number(chipBtn.dataset.categoryId || 0));
  }

  function onCategoryCreated(createdCategory) {
    if (!createdCategory) {
      return;
    }
    const pending = (state.pendingCreateCategoryFromOperation || "").trim().toLowerCase();
    const createdName = String(createdCategory.name || "").trim().toLowerCase();
    const kindMatches = createdCategory.kind === (el.opKind.value || "expense");
    if (!pending || pending !== createdName || !kindMatches) {
      state.pendingCreateCategoryFromOperation = "";
      return;
    }
    state.pendingCreateCategoryFromOperation = "";
    selectCreateCategory(createdCategory.id);
  }

  function normalizeReceiptName(value) {
    return String(value || "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function asMoney(value) {
    const num = Number(value || 0);
    if (!Number.isFinite(num)) {
      return 0;
    }
    return Math.round(num * 100) / 100;
  }

  function asQty(value) {
    const num = Number(value || 0);
    if (!Number.isFinite(num)) {
      return 0;
    }
    return Math.round(num * 1000) / 1000;
  }

  function receiptLineTotal(item) {
    return asMoney(asQty(item.quantity) * asMoney(item.unit_price));
  }

  function getReceiptContext(mode = "create") {
    const isEdit = mode === "edit";
    return {
      mode,
      itemsKey: isEdit ? "editReceiptItems" : "createReceiptItems",
      seqKey: isEdit ? "editReceiptSeq" : "createReceiptSeq",
      enabledNode: isEdit ? el.editReceiptEnabled : el.opReceiptEnabled,
      fieldsNode: isEdit ? el.editReceiptFields : el.opReceiptFields,
      listNode: isEdit ? el.editReceiptItemsList : el.receiptItemsList,
      totalNode: isEdit ? el.editReceiptTotalValue : el.receiptTotalValue,
      diffNode: isEdit ? el.editReceiptDiffValue : el.receiptDiffValue,
      amountNode: document.getElementById(isEdit ? "editAmount" : "opAmount"),
    };
  }

  function getReceiptModeFromNode(node) {
    const mode = node?.closest?.("[data-receipt-mode]")?.dataset?.receiptMode || "create";
    return mode === "edit" ? "edit" : "create";
  }

  function getReceiptItems(mode = "create") {
    const ctx = getReceiptContext(mode);
    if (!Array.isArray(state[ctx.itemsKey])) {
      state[ctx.itemsKey] = [];
    }
    return state[ctx.itemsKey];
  }

  function createReceiptDraft(seed = {}, mode = "create") {
    const ctx = getReceiptContext(mode);
    const hasQuantity = seed.quantity !== undefined && seed.quantity !== null && String(seed.quantity).trim() !== "";
    const hasUnitPrice = seed.unit_price !== undefined && seed.unit_price !== null && String(seed.unit_price).trim() !== "";
    state[ctx.seqKey] = Number(state[ctx.seqKey] || 0) + 1;
    return {
      draft_id: state[ctx.seqKey],
      template_id: seed.template_id || null,
      shop_name: normalizeReceiptName(seed.shop_name || ""),
      name: normalizeReceiptName(seed.name || ""),
      quantity: hasQuantity ? asQty(seed.quantity) : 0,
      unit_price: hasUnitPrice ? asMoney(seed.unit_price) : 0,
      note: seed.note || "",
    };
  }

  function getReceiptItemByDraftId(draftId, mode = "create") {
    return getReceiptItems(mode).find((entry) => Number(entry.draft_id) === Number(draftId)) || null;
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
    receiptLocalTemplateSeq += 1;
    const created = {
      id: -receiptLocalTemplateSeq,
      shop_name: normalizedShop || null,
      shop_name_ci: shopNameCi || "",
      name: normalizedName,
      name_ci: nameCi,
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
    }
    activeReceiptPicker = null;
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
    const esc = (value) => String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
    const suggestionsHtml = shopSuggestions.map((shopName) => `
      <button type="button" class="chip-btn" data-receipt-shop-name="${esc(shopName)}" data-receipt-item-id="${rowItem.draft_id}">
        ${core.renderCategoryChip({ name: shopName, icon: null, accent_color: null }, normalizedQuery)}
      </button>
    `).join("");
    const createHtml = !normalizedQuery || exact ? "" : `
      <button type="button" class="chip-btn chip-btn-create" data-receipt-create-shop="${esc(normalizedQuery)}" data-receipt-item-id="${rowItem.draft_id}">
        + Создать источник «${esc(normalizedQuery)}»
      </button>
    `;
    picker.innerHTML = `${suggestionsHtml}${createHtml}` || "<span class='muted-small'>Нет источников</span>";
    picker.classList.remove("hidden");
    activeReceiptPicker = { draft_id: Number(rowItem.draft_id), field: "shop_name", mode: getReceiptModeFromNode(rowNode) };
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
    const esc = (value) => String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
    const suggestionsHtml = suggestions.map((item) => `
      <button type="button" class="chip-btn" data-receipt-template-id="${item.id}" data-receipt-item-id="${rowItem.draft_id}">
        ${core.renderCategoryChip({ name: item.name, icon: "🧾", accent_color: null }, normalizedQuery)}
      </button>
    `).join("");
    const createHtml = !normalizedQuery || exact ? "" : `
      <button type="button" class="chip-btn chip-btn-create" data-receipt-create-name="${esc(normalizedQuery)}" data-receipt-item-id="${rowItem.draft_id}">
        + Создать позицию «${esc(normalizedQuery)}»
      </button>
    `;
    picker.innerHTML = `${suggestionsHtml}${createHtml}` || "<span class='muted-small'>Нет совпадений</span>";
    picker.classList.remove("hidden");
    activeReceiptPicker = { draft_id: Number(rowItem.draft_id), field: "name", mode: getReceiptModeFromNode(rowNode) };
  }

  function setReceiptEnabled(enabled, mode = "create") {
    const ctx = getReceiptContext(mode);
    const isEnabled = enabled === true;
    if (ctx.enabledNode) {
      ctx.enabledNode.checked = isEnabled;
    }
    if (ctx.fieldsNode) {
      ctx.fieldsNode.classList.toggle("hidden", !isEnabled);
    }
    if (ctx.amountNode) {
      ctx.amountNode.required = !isEnabled;
    }
    if (isEnabled) {
      ensureTrailingReceiptRow(mode);
      loadReceiptTemplateHints().catch(() => {});
    } else {
      activeReceiptPicker = null;
    }
    renderReceiptItems(mode);
    renderReceiptSummary(mode);
    if (mode === "create") {
      updateCreatePreview();
    } else {
      updateEditPreview();
    }
  }

  function clearReceiptItems(mode = "create") {
    const ctx = getReceiptContext(mode);
    state[ctx.itemsKey] = [];
    state[ctx.seqKey] = 0;
    activeReceiptPicker = null;
    renderReceiptItems(mode);
    renderReceiptSummary(mode);
  }

  function updateReceiptItemField(draftId, key, value, mode = "create") {
    const items = getReceiptItems(mode);
    const item = items.find((entry) => Number(entry.draft_id) === Number(draftId));
    if (!item) {
      return null;
    }
    const hadName = hasReceiptRowName(item);
    if (key === "quantity") {
      item.quantity = asQty(value);
    } else if (key === "unit_price") {
      item.unit_price = asMoney(value);
    } else if (key === "shop_name") {
      item.shop_name = normalizeReceiptName(value);
      item.template_id = null;
    } else if (key === "name") {
      item.name = normalizeReceiptName(value);
      item.template_id = null;
    } else if (key === "note") {
      item.note = value || "";
    }
    return {
      item,
      hadName,
      hasName: hasReceiptRowName(item),
    };
  }

  function removeReceiptItem(draftId, mode = "create") {
    const ctx = getReceiptContext(mode);
    state[ctx.itemsKey] = getReceiptItems(mode).filter((entry) => Number(entry.draft_id) !== Number(draftId));
    if (Number(activeReceiptPicker?.draft_id || 0) === Number(draftId) && (activeReceiptPicker?.mode || "create") === mode) {
      activeReceiptPicker = null;
    }
    ensureTrailingReceiptRow(mode);
    renderReceiptItems(mode);
    renderReceiptSummary(mode);
    if (mode === "create") {
      updateCreatePreview();
    } else {
      updateEditPreview();
    }
  }

  function isReceiptRowEmpty(item) {
    const shopName = normalizeReceiptName(item?.shop_name || "");
    const name = normalizeReceiptName(item?.name || "");
    const qty = asQty(item?.quantity || 0);
    const price = asMoney(item?.unit_price || 0);
    return !shopName && !name && qty <= 0 && price <= 0;
  }

  function hasReceiptRowName(item) {
    return normalizeReceiptName(item?.name || "") !== "";
  }

  function hasReceiptRowContent(item) {
    return !isReceiptRowEmpty(item);
  }

  function ensureTrailingReceiptRow(mode = "create") {
    const ctx = getReceiptContext(mode);
    const rows = getReceiptItems(mode);
    if (!rows.length) {
      state[ctx.itemsKey] = [createReceiptDraft({}, mode)];
      return;
    }
    const normalizedRows = rows.filter((item) => hasReceiptRowContent(item));
    if (!normalizedRows.length) {
      state[ctx.itemsKey] = [createReceiptDraft({}, mode)];
      return;
    }
    const last = normalizedRows[normalizedRows.length - 1];
    if (hasReceiptRowName(last)) {
      state[ctx.itemsKey] = [...normalizedRows, createReceiptDraft({}, mode)];
      return;
    }
    state[ctx.itemsKey] = normalizedRows;
  }

  function renderReceiptItems(mode = "create") {
    const ctx = getReceiptContext(mode);
    if (!ctx.listNode) {
      return;
    }
    const rows = getReceiptItems(mode);
    const esc = (value) => String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
    ctx.listNode.innerHTML = rows.map((item, idx) => {
      const total = receiptLineTotal(item);
      const isLast = idx === rows.length - 1;
      const removeHidden = isLast && isReceiptRowEmpty(item);
      return `
        <div class="receipt-item-row" data-receipt-mode="${mode}" data-receipt-item-id="${item.draft_id}">
          <div class="receipt-shop-cell">
            <input type="text" data-receipt-field="shop_name" value="${esc(item.shop_name || "")}" placeholder="Источник" />
            <div class="receipt-shop-picker ${Number(activeReceiptPicker?.draft_id || 0) === Number(item.draft_id) && activeReceiptPicker?.field === "shop_name" && (activeReceiptPicker?.mode || "create") === mode ? "" : "hidden"}"></div>
          </div>
          <div class="receipt-name-cell">
            <input type="text" data-receipt-field="name" value="${esc(item.name)}" placeholder="Позиция" />
            <span class="receipt-new-badge ${item.name && !item.template_id ? "" : "hidden"}">Новая позиция</span>
            <div class="receipt-name-picker ${Number(activeReceiptPicker?.draft_id || 0) === Number(item.draft_id) && activeReceiptPicker?.field === "name" && (activeReceiptPicker?.mode || "create") === mode ? "" : "hidden"}"></div>
          </div>
          <input type="number" step="0.01" min="0" data-receipt-field="unit_price" value="${item.unit_price || ""}" placeholder="Цена" />
          <input type="number" step="0.001" min="0" data-receipt-field="quantity" value="${item.quantity || ""}" placeholder="Кол-во" />
          <div class="receipt-line-total"><span>Итого</span><strong>${core.formatMoney(total, { withCurrency: false })}</strong></div>
          <button class="btn btn-danger receipt-remove-btn ${removeHidden ? "hidden" : ""}" type="button" data-receipt-remove-id="${item.draft_id}" title="Удалить">×</button>
        </div>
      `;
    }).join("");
  }

  function getReceiptTotal(mode = "create") {
    return getReceiptItems(mode).reduce((acc, item) => acc + receiptLineTotal(item), 0);
  }

  function renderReceiptSummary(mode = "create") {
    const ctx = getReceiptContext(mode);
    if (!ctx.totalNode || !ctx.diffNode) {
      return;
    }
    const total = getReceiptTotal(mode);
    ctx.totalNode.textContent = core.formatMoney(total);
    const amount = asMoney(ctx.amountNode?.value || 0);
    const hasAmount = String(ctx.amountNode?.value || "").trim() !== "";
    const diff = hasAmount ? asMoney(amount - total) : 0;
    ctx.diffNode.textContent = core.formatMoney(diff, { withCurrency: false });
    ctx.diffNode.classList.toggle("receipt-diff-warn", Math.abs(diff) >= 0.01);
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
      ensureTrailingReceiptRow(mode);
      renderReceiptItems(mode);
      structureChanged = true;
    } else {
      const totalCell = row.querySelector(".receipt-line-total");
      if (totalCell) {
        totalCell.innerHTML = `<span>Итого</span><strong>${core.formatMoney(receiptLineTotal(updated.item), { withCurrency: false })}</strong>`;
      }
    }
    if (field === "shop_name") {
      renderReceiptShopPickerForRow(row, updated.item, event.target.value);
    }
    if (field === "name") {
      renderReceiptNamePickerForRow(row, updated.item, event.target.value);
    }
    renderReceiptSummary(mode);
    if (mode === "create") {
      updateCreatePreview();
    } else {
      updateEditPreview();
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
      }
    }
  }

  function handleReceiptItemsListFocusIn(event) {
    const input = event.target.closest('[data-receipt-field="name"], [data-receipt-field="shop_name"]');
    if (!input) {
      return;
    }
    const row = input.closest("[data-receipt-item-id]");
    if (!row) {
      return;
    }
    const draftId = Number(row.dataset.receiptItemId || 0);
    const mode = getReceiptModeFromNode(row);
    const rowItem = getReceiptItemByDraftId(draftId, mode);
    if (!rowItem) {
      return;
    }
    const field = input.dataset.receiptField;
    if (field === "shop_name") {
      renderReceiptShopPickerForRow(row, rowItem, input.value);
      return;
    }
    renderReceiptNamePickerForRow(row, rowItem, input.value);
  }

  function handleReceiptItemsListKeydown(event) {
    const input = event.target.closest('[data-receipt-field="name"], [data-receipt-field="shop_name"]');
    if (!input) {
      return;
    }
    const row = input.closest("[data-receipt-item-id]");
    if (!row) {
      return;
    }
    const draftId = Number(row.dataset.receiptItemId || 0);
    const mode = getReceiptModeFromNode(row);
    const rowItem = getReceiptItemByDraftId(draftId, mode);
    if (!rowItem) {
      return;
    }
    if (event.key === "Escape") {
      const picker = input.dataset.receiptField === "shop_name"
        ? row.querySelector(".receipt-shop-picker")
        : row.querySelector(".receipt-name-picker");
      picker?.classList.add("hidden");
      activeReceiptPicker = null;
      return;
    }
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    const query = normalizeReceiptName(input.value);
    if (!query) {
      return;
    }
    const field = input.dataset.receiptField;
    if (field === "shop_name") {
      const shops = getReceiptShopSuggestions(query, 1);
      const firstShop = shops[0] || query;
      rowItem.shop_name = normalizeReceiptName(firstShop);
      rowItem.template_id = null;
      ensureTrailingReceiptRow(mode);
      renderReceiptItems(mode);
      renderReceiptSummary(mode);
      if (mode === "create") {
        updateCreatePreview();
      } else {
        updateEditPreview();
      }
      return;
    }
    const exact = getReceiptTemplateMatch(query, rowItem.shop_name || "");
    const first = exact || getReceiptTemplateSuggestions(query, rowItem.shop_name || "", 1)[0] || null;
    if (first) {
      rowItem.name = first.name;
      rowItem.template_id = first.id;
      rowItem.shop_name = normalizeReceiptName(first.shop_name || rowItem.shop_name || "");
      if (!rowItem.unit_price || Number(rowItem.unit_price) <= 0) {
        rowItem.unit_price = first.latest_unit_price || 0;
      }
    } else {
      rowItem.name = query;
      rowItem.template_id = null;
    }
    ensureTrailingReceiptRow(mode);
    renderReceiptItems(mode);
    renderReceiptSummary(mode);
    if (mode === "create") {
      updateCreatePreview();
    } else {
      updateEditPreview();
    }
    const nextInput = getReceiptContext(mode).listNode?.querySelector(
      `[data-receipt-item-id="${rowItem.draft_id}"] [data-receipt-field="name"]`,
    );
    nextInput?.blur();
  }

  function handleReceiptItemsListClick(event) {
    const shopBtn = event.target.closest("button[data-receipt-shop-name]");
    if (shopBtn) {
      const draftId = Number(shopBtn.dataset.receiptItemId || 0);
      const row = shopBtn.closest("[data-receipt-item-id]");
      const mode = getReceiptModeFromNode(row);
      const rowItem = getReceiptItemByDraftId(draftId, mode);
      if (rowItem) {
        rowItem.shop_name = normalizeReceiptName(shopBtn.dataset.receiptShopName || "");
        rowItem.template_id = null;
        activeReceiptPicker = null;
        ensureTrailingReceiptRow(mode);
        renderReceiptItems(mode);
        renderReceiptSummary(mode);
        if (mode === "create") {
          updateCreatePreview();
        } else {
          updateEditPreview();
        }
      }
      return;
    }
    const createShopBtn = event.target.closest("button[data-receipt-create-shop]");
    if (createShopBtn) {
      const draftId = Number(createShopBtn.dataset.receiptItemId || 0);
      const row = createShopBtn.closest("[data-receipt-item-id]");
      const mode = getReceiptModeFromNode(row);
      const rowItem = getReceiptItemByDraftId(draftId, mode);
      if (rowItem) {
        rowItem.shop_name = normalizeReceiptName(createShopBtn.dataset.receiptCreateShop || "");
        rowItem.template_id = null;
        activeReceiptPicker = null;
        ensureTrailingReceiptRow(mode);
        renderReceiptItems(mode);
        renderReceiptSummary(mode);
        if (mode === "create") {
          updateCreatePreview();
        } else {
          updateEditPreview();
        }
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
        if (!rowItem.unit_price || Number(rowItem.unit_price) <= 0) {
          rowItem.unit_price = template.latest_unit_price || 0;
        }
        if (!rowItem.quantity || Number(rowItem.quantity) <= 0) {
          rowItem.quantity = 1;
        }
        upsertLocalReceiptTemplate(rowItem.name, rowItem.unit_price, rowItem.shop_name || "");
        activeReceiptPicker = null;
        ensureTrailingReceiptRow(mode);
        renderReceiptItems(mode);
        renderReceiptSummary(mode);
        if (mode === "create") {
          updateCreatePreview();
        } else {
          updateEditPreview();
        }
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
        activeReceiptPicker = null;
        ensureTrailingReceiptRow(mode);
        renderReceiptItems(mode);
        renderReceiptSummary(mode);
        if (mode === "create") {
          updateCreatePreview();
        } else {
          updateEditPreview();
        }
      }
      return;
    }
    const removeBtn = event.target.closest("button[data-receipt-remove-id]");
    if (!removeBtn) {
      return;
    }
    const row = removeBtn.closest("[data-receipt-item-id]");
    const mode = getReceiptModeFromNode(row);
    removeReceiptItem(Number(removeBtn.dataset.receiptRemoveId || 0), mode);
  }

  function handlePullReceiptTotal(modeOrEvent = "create") {
    const mode = typeof modeOrEvent === "string"
      ? modeOrEvent
      : (modeOrEvent?.target?.dataset?.receiptMode || "create");
    const ctx = getReceiptContext(mode);
    const total = getReceiptTotal(mode);
    if (!ctx.amountNode) {
      return;
    }
    ctx.amountNode.value = core.formatAmount(total);
    renderReceiptSummary(mode);
    if (mode === "create") {
      updateCreatePreview();
    } else {
      updateEditPreview();
    }
  }

  function handleReceiptOutsidePointer(event) {
    const insideShopCell = event.target.closest(".receipt-shop-cell");
    const insideShopPicker = event.target.closest(".receipt-shop-picker");
    const insideActiveNameCell = event.target.closest(".receipt-name-cell");
    const insidePicker = event.target.closest(".receipt-name-picker");
    if (insideShopCell || insideShopPicker || insideActiveNameCell || insidePicker) {
      return;
    }
    hideAllReceiptPickers();
  }

  function getCreateReceiptPayload() {
    if (!el.opReceiptEnabled?.checked) {
      return [];
    }
    return getReceiptItems("create")
      .map((item) => ({
        shop_name: normalizeReceiptName(item.shop_name || "") || null,
        name: normalizeReceiptName(item.name),
        quantity: String(asQty(item.quantity || 0)),
        unit_price: core.formatAmount(item.unit_price || 0),
      }))
      .filter((item) => item.name && Number(item.quantity) > 0 && Number(item.unit_price) > 0);
  }

  function getEditReceiptPayload() {
    if (!el.editReceiptEnabled?.checked) {
      return [];
    }
    return getReceiptItems("edit")
      .map((item) => ({
        shop_name: normalizeReceiptName(item.shop_name || "") || null,
        name: normalizeReceiptName(item.name),
        quantity: String(asQty(item.quantity || 0)),
        unit_price: core.formatAmount(item.unit_price || 0),
      }))
      .filter((item) => item.name && Number(item.quantity) > 0 && Number(item.unit_price) > 0);
  }

  function setCreateEntryMode(mode) {
    const nextMode = mode === "debt" ? "debt" : "operation";
    el.opEntryMode.value = nextMode;
    core.syncSegmentedActive(el.createEntryModeSwitch, "entry-mode", nextMode);
    const isDebt = nextMode === "debt";
    el.createKindSwitch.classList.toggle("hidden", isDebt);
    el.createCategoryField.classList.toggle("hidden", isDebt);
    el.opReceiptBlock?.classList.toggle("hidden", isDebt);
    const opAmountField = document.getElementById("opAmountField");
    const opAmount = document.getElementById("opAmount");
    const opDate = document.getElementById("opDate");
    const opNote = document.getElementById("opNote");
    if (opAmountField) {
      opAmountField.classList.toggle("hidden", isDebt);
    }
    if (opAmount) {
      opAmount.required = !isDebt;
      if (!isDebt && el.opReceiptEnabled?.checked) {
        opAmount.required = false;
      }
    }
    if (opDate) {
      opDate.classList.toggle("hidden", isDebt);
      opDate.required = !isDebt;
    }
    if (opNote) {
      opNote.classList.toggle("hidden", isDebt);
      opNote.placeholder = isDebt ? "Комментарий (долг)" : "Комментарий";
    }
    el.createDebtFields.classList.toggle("hidden", !isDebt);
    if (el.createPreviewHeadOperation && el.createPreviewHeadDebt) {
      el.createPreviewHeadOperation.classList.toggle("hidden", isDebt);
      el.createPreviewHeadDebt.classList.toggle("hidden", !isDebt);
    }
    if (isDebt) {
      closeCreateCategoryPopover();
    }
    el.debtCounterparty.required = isDebt;
    el.debtPrincipal.required = isDebt;
    el.debtStartDate.required = isDebt;
    const submit = document.getElementById("submitCreateOperationBtn");
    if (isDebt) {
      if (!el.debtStartDate.value) {
        el.debtStartDate.value = new Date().toISOString().slice(0, 10);
      }
      if (submit) {
        submit.textContent = state.editDebtCreateId ? "Сохранить долг" : "Создать долг";
      }
    } else {
      if (submit) {
        submit.textContent = "Добавить";
      }
    }
    updateCreatePreview();
  }

  function setOperationKind(mode, kind) {
    if (mode === "create") {
      el.opKind.value = kind;
      core.syncSegmentedActive(el.createKindSwitch, "kind", kind);
      categoryActions.populateCategorySelect(el.opCategory, el.opCategory.value, kind);
      if (el.opCategory.value && !state.categories.some((item) => String(item.id) === el.opCategory.value && item.kind === kind)) {
        el.opCategory.value = "";
        el.opCategorySearch.value = "";
      }
      renderCreateCategoryPicker();
      updateCreatePreview();
      return;
    }

    if (mode === "edit") {
      el.editKind.value = kind;
      core.syncSegmentedActive(el.editKindSwitch, "kind", kind);
      categoryActions.populateCategorySelect(el.editCategory, el.editCategory.value, kind);
      updateEditPreview();
    }
  }

  function openCreateModal() {
    state.editDebtCreateId = null;
    const createTitle = document.getElementById("createTitle");
    if (createTitle) {
      createTitle.textContent = "Новая операция";
    }
    if (el.createEntryModeSwitch) {
      el.createEntryModeSwitch.classList.remove("hidden");
    }
    const dateInput = document.getElementById("opDate");
    if (!dateInput.value) {
      dateInput.value = new Date().toISOString().slice(0, 10);
    }
    setOperationKind("create", el.opKind.value || "expense");
    el.opCategory.value = "";
    el.opCategorySearch.value = "";
    if (el.opReceiptEnabled) {
      el.opReceiptEnabled.checked = false;
    }
    clearReceiptItems("create");
    setReceiptEnabled(false, "create");
    closeCreateCategoryPopover();
    el.debtCounterparty.value = "";
    el.debtPrincipal.value = "";
    el.debtStartDate.value = "";
    el.debtDueDate.value = "";
    el.debtNote.value = "";
    setDebtDirection("lend");
    applyDebtCurrencyUi();
    updateDebtDueHint();
    setCreateEntryMode("operation");
    renderCreateCategoryPicker();
    loadReceiptTemplateHints().catch(() => {});
    renderReceiptItems();
    renderReceiptSummary();
    updateCreatePreview();
    el.createModal.classList.remove("hidden");
  }

  function closeCreateModal() {
    state.editDebtCreateId = null;
    const createTitle = document.getElementById("createTitle");
    if (createTitle) {
      createTitle.textContent = "Новая операция";
    }
    el.createModal.classList.add("hidden");
  }

  function openCreateModalForDebtEdit(payload) {
    if (!payload?.id) {
      return;
    }
    openCreateModal();
    state.editDebtCreateId = Number(payload.id);
    if (el.createEntryModeSwitch) {
      el.createEntryModeSwitch.classList.add("hidden");
    }
    const createTitle = document.getElementById("createTitle");
    if (createTitle) {
      createTitle.textContent = "Редактировать долг";
    }
    el.debtCounterparty.value = payload.counterparty || "";
    el.debtPrincipal.value = payload.principal || "";
    el.debtStartDate.value = payload.start_date || new Date().toISOString().slice(0, 10);
    el.debtDueDate.value = payload.due_date || "";
    el.debtNote.value = payload.note || "";
    setDebtDirection(payload.direction || "lend");
    setCreateEntryMode("debt");
    updateDebtDueHint();
    updateCreatePreview();
  }

  function openEditModal(item) {
    state.editOperationId = item.id;
    document.getElementById("editAmount").value = item.amount;
    document.getElementById("editDate").value = item.operation_date;
    document.getElementById("editNote").value = item.note || "";
    clearReceiptItems("edit");
    state.editReceiptItems = (Array.isArray(item.receipt_items) ? item.receipt_items : []).map((row) => createReceiptDraft({
      template_id: row.template_id || null,
      shop_name: row.shop_name || "",
      name: row.name || "",
      quantity: row.quantity || 0,
      unit_price: row.unit_price || 0,
      note: row.note || "",
    }, "edit"));
    const hasReceipt = state.editReceiptItems.length > 0;
    if (el.editReceiptEnabled) {
      el.editReceiptEnabled.checked = hasReceipt;
    }
    setReceiptEnabled(hasReceipt, "edit");
    setOperationKind("edit", item.kind);
    el.editCategory.value = item.category_id ? String(item.category_id) : "";
    updateEditPreview();
    el.editModal.classList.remove("hidden");
  }

  function closeEditModal() {
    state.editOperationId = null;
    clearReceiptItems("edit");
    setReceiptEnabled(false, "edit");
    el.editModal.classList.add("hidden");
  }

  function applySettingsUi() {
    const savedTz = state.preferences?.data?.ui?.timezone || "auto";
    if (el.timezoneSelect) {
      const hasOption = Array.from(el.timezoneSelect.options).some((opt) => opt.value === savedTz);
      el.timezoneSelect.value = hasOption ? savedTz : "auto";
    }
    applyDebtCurrencyUi();
  }

  function openPeriodCustomModal() {
    const today = new Date().toISOString().slice(0, 10);
    el.customDateTo.value = state.customDateTo || today;
    el.customDateFrom.value = state.customDateFrom || today;
    el.periodCustomModal.classList.remove("hidden");
  }

  function closePeriodCustomModal() {
    el.periodCustomModal.classList.add("hidden");
  }

  window.App.operationModal = {
    trackCategoryUsage,
    getCategoryMetaById,
    getCreateFormPreviewItem,
    updateCreatePreview,
    updateEditPreview,
    renderCreateCategoryPicker,
    openCreateCategoryPopover,
    closeCreateCategoryPopover,
    handleCreateCategoryPickerClick,
    handleCreateCategorySearchFocus,
    handleCreateCategorySearchInput,
    handleCreateCategorySearchKeydown,
    handleCreateCategoryOutsidePointer,
    handleReceiptItemsListInput,
    handleReceiptItemsListFocusIn,
    handleReceiptItemsListKeydown,
    handleReceiptItemsListClick,
    handleReceiptOutsidePointer,
    handlePullReceiptTotal,
    setReceiptEnabled,
    getCreateReceiptPayload,
    getEditReceiptPayload,
    renderReceiptSummary,
    onCategoryCreated,
    selectCreateCategory,
    handleCreatePreviewClick,
    setDebtDirection,
    setOperationKind,
    setCreateEntryMode,
    updateDebtDueHint,
    openCreateModal,
    openCreateModalForDebtEdit,
    closeCreateModal,
    openEditModal,
    closeEditModal,
    applySettingsUi,
    openPeriodCustomModal,
    closePeriodCustomModal,
  };
})();
