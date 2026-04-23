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
      formatReceiptMoney,
      removeReceiptItem,
      updateCreatePreview,
      updateEditPreview,
      RECEIPT_TEMPLATES_CACHE_TTL_MS,
    } = deps;
    function getReceiptPickerFactory() {
      return window.App.getRuntimeModule?.("operation-modal-receipt-picker-factory");
    }

    const createOperationModalReceiptPickerFeature = getReceiptPickerFactory();
    const pickerFeature = createOperationModalReceiptPickerFeature
      ? createOperationModalReceiptPickerFeature({
        state,
        el,
        core,
        receiptUiState,
        normalizeReceiptName,
        getReceiptModeFromNode,
        RECEIPT_TEMPLATES_CACHE_TTL_MS,
      })
      : {};
    const getReceiptCategoriesSorted = pickerFeature.getReceiptCategoriesSorted || (() => []);
    const getReceiptTemplateMatch = pickerFeature.getReceiptTemplateMatch || (() => null);
    const getReceiptTemplateSuggestions = pickerFeature.getReceiptTemplateSuggestions || (() => []);
    const getReceiptShopSuggestions = pickerFeature.getReceiptShopSuggestions || (() => []);
    const upsertLocalReceiptTemplate = pickerFeature.upsertLocalReceiptTemplate || (() => null);
    const hideAllReceiptPickers = pickerFeature.hideAllReceiptPickers || (() => {});
    const renderReceiptShopPickerForRow = pickerFeature.renderReceiptShopPickerForRow || (() => {});
    const renderReceiptNamePickerForRow = pickerFeature.renderReceiptNamePickerForRow || (() => {});
    const openCreateCategoryFromReceipt = pickerFeature.openCreateCategoryFromReceipt || (() => {});
    const renderReceiptCategoryPickerForRow = pickerFeature.renderReceiptCategoryPickerForRow || (() => {});
    const loadReceiptTemplateHints = pickerFeature.loadReceiptTemplateHints || (async () => {});
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
          totalCell.innerHTML = `<span>Итого</span><strong>${formatReceiptMoney(receiptLineTotal(updated.item), mode)}</strong>`;
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
  window.App.registerRuntimeModule?.("operation-modal-receipt-interactions-factory", createOperationModalReceiptInteractionsFeature);
})();
