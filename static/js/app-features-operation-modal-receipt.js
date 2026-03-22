(() => {
  function createOperationModalReceiptFeature(deps) {
    const {
      state,
      el,
      core,
      updateCreatePreview,
      updateEditPreview,
    } = deps;

    const RECEIPT_TEMPLATES_CACHE_TTL_MS = 20000;
    const receiptUiState = {
      activePicker: null,
      localTemplateSeq: 0,
      hintsPromise: null,
      hintsLoadedAt: 0,
    };

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

    function getReceiptOperationKind(mode = "create") {
      return mode === "edit" ? (el.editKind?.value || "expense") : (el.opKind?.value || "expense");
    }

    function getReceiptDefaultCategoryId(mode = "create") {
      return mode === "edit"
        ? (el.editCategory?.value ? Number(el.editCategory.value) : null)
        : (el.opCategory?.value ? Number(el.opCategory.value) : null);
    }

    function isReceiptModeEnabled(mode = "create") {
      return mode === "edit"
        ? el.editOperationMode?.value === "receipt"
        : el.opOperationMode?.value === "receipt";
    }

    function createReceiptDraft(seed = {}, mode = "create") {
      const ctx = getReceiptContext(mode);
      const hasQuantity = seed.quantity !== undefined && seed.quantity !== null && String(seed.quantity).trim() !== "";
      const hasUnitPrice = seed.unit_price !== undefined && seed.unit_price !== null && String(seed.unit_price).trim() !== "";
      state[ctx.seqKey] = Number(state[ctx.seqKey] || 0) + 1;
      return {
        draft_id: state[ctx.seqKey],
        template_id: seed.template_id || null,
        category_id: seed.category_id ? Number(seed.category_id) : null,
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
      } else if (key === "category_id") {
        item.category_id = value ? Number(value) : null;
      } else if (key === "note") {
        item.note = value || "";
      }
      return {
        item,
        hadName,
        hasName: hasReceiptRowName(item),
      };
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
        const pickerMode = receiptUiState.activePicker?.mode || "create";
        const activeDraftId = Number(receiptUiState.activePicker?.draft_id || 0);
        const activeField = receiptUiState.activePicker?.field || "";
        const shopPickerOpen = activeDraftId === Number(item.draft_id) && activeField === "shop_name" && pickerMode === mode;
        const namePickerOpen = activeDraftId === Number(item.draft_id) && activeField === "name" && pickerMode === mode;
        const categoryPickerOpen = activeDraftId === Number(item.draft_id) && activeField === "category_id" && pickerMode === mode;
        const hasOpenPicker = shopPickerOpen || namePickerOpen || categoryPickerOpen;
        const explicitCategoryId = item.category_id ? Number(item.category_id) : null;
        const effectiveCategoryId = explicitCategoryId || getReceiptDefaultCategoryId(mode);
        const categoryMeta = effectiveCategoryId
          ? (state.categories || []).find((entry) => Number(entry.id) === effectiveCategoryId)
          : null;
        const categorySource = explicitCategoryId ? "explicit" : (categoryMeta ? "default" : "none");
        return `
          <div class="receipt-item-row ${hasOpenPicker ? "has-open-popover" : ""}" data-receipt-mode="${mode}" data-receipt-item-id="${item.draft_id}">
            <div class="receipt-shop-cell ${shopPickerOpen ? "has-open-popover" : ""}">
              <input type="text" data-receipt-field="shop_name" value="${esc(item.shop_name || "")}" placeholder="Источник" />
              <div class="receipt-shop-picker app-popover ${shopPickerOpen ? "" : "hidden"}"></div>
            </div>
            <div class="receipt-name-cell ${namePickerOpen ? "has-open-popover" : ""}">
              <input type="text" data-receipt-field="name" value="${esc(item.name)}" placeholder="Позиция" />
              <span class="receipt-new-badge ${item.name && !item.template_id ? "" : "hidden"}">Новая позиция</span>
              <div class="receipt-name-picker app-popover ${namePickerOpen ? "" : "hidden"}"></div>
            </div>
            <div class="receipt-category-cell ${categoryPickerOpen ? "has-open-popover" : ""}">
              <span class="receipt-category-badge ${categorySource === "default" ? "" : "hidden"}">По умолчанию</span>
              <input
                type="text"
                data-receipt-field="category_search"
                value="${esc(categoryMeta?.name || "")}"
                data-receipt-category-source="${categorySource}"
                data-receipt-effective-category-id="${effectiveCategoryId || ""}"
                placeholder="Категория"
                autocomplete="off"
              />
              <div class="receipt-category-picker app-popover ${categoryPickerOpen ? "" : "hidden"}"></div>
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
      const resolvedAmount = core.resolveMoneyInput(ctx.amountNode?.value || 0);
      const diff = !resolvedAmount.empty ? asMoney(resolvedAmount.previewValue - total) : 0;
      ctx.diffNode.textContent = core.formatMoney(diff, { withCurrency: false });
      ctx.diffNode.classList.toggle("receipt-diff-warn", !resolvedAmount.empty && Math.abs(diff) >= 0.01);
    }

    function removeReceiptItem(draftId, mode = "create") {
      const ctx = getReceiptContext(mode);
      state[ctx.itemsKey] = getReceiptItems(mode).filter((entry) => Number(entry.draft_id) !== Number(draftId));
      if (Number(receiptUiState.activePicker?.draft_id || 0) === Number(draftId) && (receiptUiState.activePicker?.mode || "create") === mode) {
        receiptUiState.activePicker = null;
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

    const createOperationModalReceiptInteractionsFeature = window.App.getRuntimeModule?.("operation-modal-receipt-interactions-factory");
    const interactions = createOperationModalReceiptInteractionsFeature
      ? createOperationModalReceiptInteractionsFeature({
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
      })
      : {};

    const loadReceiptTemplateHints = interactions.loadReceiptTemplateHints || (async () => {});
    const hideAllReceiptPickers = interactions.hideAllReceiptPickers || (() => {
      receiptUiState.activePicker = null;
    });
    const handleReceiptItemsListInput = interactions.handleReceiptItemsListInput || (() => {});
    const handleReceiptItemsListFocusIn = interactions.handleReceiptItemsListFocusIn || (() => {});
    const handleReceiptItemsListKeydown = interactions.handleReceiptItemsListKeydown || (() => {});
    const handleReceiptItemsListClick = interactions.handleReceiptItemsListClick || (() => {});
    const handleReceiptOutsidePointer = interactions.handleReceiptOutsidePointer || (() => {});

    function setReceiptEnabled(enabled, mode = "create") {
      const ctx = getReceiptContext(mode);
      const isEnabled = enabled === true;
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
        hideAllReceiptPickers();
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
      hideAllReceiptPickers();
      renderReceiptItems(mode);
      renderReceiptSummary(mode);
    }

    function syncReceiptCategoriesToKind(mode = "create") {
      const kind = getReceiptOperationKind(mode);
      const allowedIds = new Set(
        (state.categories || [])
          .filter((item) => item.kind === kind)
          .map((item) => Number(item.id)),
      );
      for (const item of getReceiptItems(mode)) {
        if (item.category_id && !allowedIds.has(Number(item.category_id))) {
          item.category_id = null;
        }
      }
      renderReceiptItems(mode);
      renderReceiptSummary(mode);
    }

    function getCreateReceiptPayload() {
      if (!isReceiptModeEnabled("create")) {
        return [];
      }
      const defaultCategoryId = el.opCategory?.value ? Number(el.opCategory.value) : null;
      return getReceiptItems("create")
        .map((item) => ({
          category_id: item.category_id ? Number(item.category_id) : defaultCategoryId,
          shop_name: normalizeReceiptName(item.shop_name || "") || null,
          name: normalizeReceiptName(item.name),
          quantity: String(asQty(item.quantity || 0)),
          unit_price: core.formatAmount(item.unit_price || 0),
        }))
        .filter((item) => item.name && Number(item.quantity) > 0 && Number(item.unit_price) > 0);
    }

    function getEditReceiptPayload() {
      if (!isReceiptModeEnabled("edit")) {
        return [];
      }
      const defaultCategoryId = el.editCategory?.value ? Number(el.editCategory.value) : null;
      return getReceiptItems("edit")
        .map((item) => ({
          category_id: item.category_id ? Number(item.category_id) : defaultCategoryId,
          shop_name: normalizeReceiptName(item.shop_name || "") || null,
          name: normalizeReceiptName(item.name),
          quantity: String(asQty(item.quantity || 0)),
          unit_price: core.formatAmount(item.unit_price || 0),
        }))
        .filter((item) => item.name && Number(item.quantity) > 0 && Number(item.unit_price) > 0);
    }

    return {
      createReceiptDraft,
      clearReceiptItems,
      setReceiptEnabled,
      renderReceiptItems,
      renderReceiptSummary,
      loadReceiptTemplateHints,
      handleReceiptItemsListInput,
      handleReceiptItemsListFocusIn,
      handleReceiptItemsListKeydown,
      handleReceiptItemsListClick,
      handleReceiptOutsidePointer,
      handlePullReceiptTotal,
      getCreateReceiptPayload,
      getEditReceiptPayload,
      syncReceiptCategoriesToKind,
    };
  }

  window.App = window.App || {};
  window.App.registerRuntimeModule?.("operation-modal-receipt-factory", createOperationModalReceiptFeature);
})();
