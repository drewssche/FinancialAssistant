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
      inheritReceiptShopFromFirstRow,
      ensureTrailingReceiptRow,
      renderReceiptItems,
      renderReceiptSummary,
      receiptLineTotal,
      receiptDiscountToggleLabel,
      formatReceiptMoney,
      resizeReceiptNameTextarea,
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
    const getReceiptBrandSuggestions = pickerFeature.getReceiptBrandSuggestions || (() => []);
    const getReceiptShopSuggestions = pickerFeature.getReceiptShopSuggestions || (() => []);
    const upsertLocalReceiptTemplate = pickerFeature.upsertLocalReceiptTemplate || (() => null);
    const hideAllReceiptPickers = pickerFeature.hideAllReceiptPickers || (() => {});
    const renderReceiptShopPickerForRow = pickerFeature.renderReceiptShopPickerForRow || (() => {});
    const renderReceiptBrandPickerForRow = pickerFeature.renderReceiptBrandPickerForRow || (() => {});
    const renderReceiptNamePickerForRow = pickerFeature.renderReceiptNamePickerForRow || (() => {});
    const openCreateCategoryFromReceipt = pickerFeature.openCreateCategoryFromReceipt || (() => {});
    const renderReceiptCategoryPickerForRow = pickerFeature.renderReceiptCategoryPickerForRow || (() => {});
    const loadReceiptTemplateHints = pickerFeature.loadReceiptTemplateHints || (async () => {});

    function getDraftBrandPayload(item) {
      return {
        brand_id: item?.brand_id ? Number(item.brand_id) : null,
        brand_name: normalizeReceiptName(item?.brand_name || "") || null,
        brand_accent_color: item?.brand_accent_color || null,
        brand_image_id: item?.brand_image_id || null,
        brand_is_archived: Boolean(item?.brand_is_archived),
      };
    }

    function applyReceiptTemplateToItem(rowItem, template) {
      if (!rowItem || !template) {
        return;
      }
      rowItem.name = template.name;
      rowItem.template_id = template.id;
      rowItem.item_image_id = template.image_id || null;
      rowItem.source_id = template.source_id || null;
      rowItem.source_image_id = template.source_image_id || null;
      rowItem.shop_name = normalizeReceiptName(template.shop_name || rowItem.shop_name || "");
      rowItem.brand_id = template.brand_id ? Number(template.brand_id) : null;
      rowItem.brand_name = normalizeReceiptName(template.brand_name || "");
      rowItem.brand_accent_color = template.brand_accent_color || null;
      rowItem.brand_image_id = template.brand_image_id || null;
      rowItem.brand_is_archived = Boolean(template.brand_is_archived);
      rowItem.brand_touched = false;
      if (!rowItem.category_id && template.last_category_id) {
        rowItem.category_id = Number(template.last_category_id);
      }
      if (!rowItem.unit_price || Number(rowItem.unit_price) <= 0) {
        rowItem.unit_price = template.latest_unit_price || 0;
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
        event.target.title = updated.item.name || "Позиция";
      } else if (field === "shop_name") {
        event.target.title = updated.item.shop_name || "Источник";
      } else if (field === "brand_search") {
        event.target.title = normalizeReceiptName(event.target.value) || "Бренд не выбран";
      }
      if (field === "name") {
        const token = normalizeReceiptName(event.target.value).toLowerCase();
        const matched = getReceiptTemplateMatch(token, updated.item.shop_name || "", updated.item.brand_id);
        if (matched) {
          applyReceiptTemplateToItem(updated.item, matched);
          if (Number(updated.item.unit_price) > 0) {
            const rowPriceInput = row.querySelector('[data-receipt-field="unit_price"]');
            if (rowPriceInput) {
              rowPriceInput.value = core.formatAmount(updated.item.unit_price);
            }
          }
          upsertLocalReceiptTemplate(updated.item.name, updated.item.unit_price, updated.item.shop_name || "", getDraftBrandPayload(updated.item));
        } else {
          updated.item.template_id = null;
        }
        resizeReceiptNameTextarea?.(event.target);
      }
      if (field === "shop_name" || field === "name") {
        inheritReceiptShopFromFirstRow(draftId, mode);
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
        const discountToggle = row.querySelector("button[data-receipt-discount-toggle]");
        if (discountToggle && receiptDiscountToggleLabel) {
          discountToggle.textContent = receiptDiscountToggleLabel(updated.item);
        }
      }
      if (field === "category_search") {
        updated.item.category_id = null;
      }
      if (field === "shop_name") {
        renderReceiptShopPickerForRow(row, updated.item, event.target.value);
      }
      if (field === "brand_search") {
        renderReceiptBrandPickerForRow(row, updated.item, event.target.value);
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
          if (field === "brand_search") {
            const restoredRow = restoredInput.closest("[data-receipt-item-id]");
            const restoredItem = getReceiptItemByDraftId(draftId, mode);
            if (restoredRow && restoredItem) {
              renderReceiptBrandPickerForRow(restoredRow, restoredItem, restoredInput.value);
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
    function handleReceiptItemsListFocusOut(event) {
      const brandInput = event.target.closest('[data-receipt-field="brand_search"]');
      if (brandInput) {
        const row = brandInput.closest("[data-receipt-item-id]");
        const draftId = Number(row?.dataset.receiptItemId || 0);
        const mode = getReceiptModeFromNode(row);
        window.setTimeout(() => {
          const item = getReceiptItemByDraftId(draftId, mode);
          const currentInput = getReceiptContext(mode).listNode?.querySelector(
            `[data-receipt-item-id="${draftId}"] [data-receipt-field="brand_search"]`,
          );
          if (currentInput) {
            currentInput.value = normalizeReceiptName(item?.brand_name || "");
            currentInput.title = currentInput.value || "Бренд не выбран";
          }
        }, 0);
        return;
      }
      const input = event.target.closest('[data-receipt-field="unit_price"], [data-receipt-field="regular_unit_price"]');
      if (!input) {
        return;
      }
      const row = input.closest("[data-receipt-item-id]");
      if (!row) {
        return;
      }
      const draftId = Number(row.dataset.receiptItemId || 0);
      const field = input.dataset.receiptField;
      const mode = getReceiptModeFromNode(row);
      const resolved = core.resolveMoneyInput?.(input.value || "");
      if (!resolved || resolved.empty) {
        return;
      }
      if (!resolved.valid) {
        input.classList.add("input-invalid");
        return;
      }
      input.classList.remove("input-invalid");
      input.value = resolved.formatted;
      updateReceiptItemField(draftId, field, resolved.formatted, mode);
      renderReceiptSummary(mode);
      if (mode === "create") {
        updateCreatePreview();
      } else {
        updateEditPreview();
      }
    }
    function handleReceiptItemsListFocusIn(event) {
      const input = event.target.closest('[data-receipt-field="name"], [data-receipt-field="shop_name"], [data-receipt-field="brand_search"], [data-receipt-field="category_search"]');
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
      if (field === "brand_search") {
        renderReceiptBrandPickerForRow(row, rowItem, input.value);
        return;
      }
      if (field === "category_search") {
        renderReceiptCategoryPickerForRow(row, rowItem, input.value);
        return;
      }
      renderReceiptNamePickerForRow(row, rowItem, input.value);
    }
    function handleReceiptItemsListKeydown(event) {
      const input = event.target.closest('[data-receipt-field="name"], [data-receipt-field="shop_name"], [data-receipt-field="brand_search"], [data-receipt-field="category_search"]');
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
          : input.dataset.receiptField === "brand_search"
            ? row.querySelector(".receipt-brand-picker")
          : input.dataset.receiptField === "category_search"
            ? row.querySelector(".receipt-category-picker")
            : row.querySelector(".receipt-name-picker");
        picker?.classList.add("hidden");
        receiptUiState.activePicker = null;
        if (input.dataset.receiptField === "brand_search") {
          input.value = normalizeReceiptName(rowItem.brand_name || "");
          input.title = input.value || "Бренд не выбран";
        }
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
        updateReceiptItemField(draftId, "shop_name", firstShop, mode);
        inheritReceiptShopFromFirstRow(draftId, mode);
        commitReceiptRowMutation(mode);
        return;
      }
      if (field === "brand_search") {
        const normalizedQuery = query.toLowerCase();
        const brands = getReceiptBrandSuggestions(query);
        const selected = brands.find((brand) => normalizeReceiptName(brand.name).toLowerCase() === normalizedQuery) || brands[0] || null;
        updateReceiptItemField(draftId, "brand_id", selected?.id || null, mode);
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
      const exact = getReceiptTemplateMatch(query, rowItem.shop_name || "", rowItem.brand_id);
      const first = exact || getReceiptTemplateSuggestions(query, rowItem.shop_name || "", 1, rowItem.brand_id)[0] || null;
      if (first) {
        applyReceiptTemplateToItem(rowItem, first);
      } else {
        rowItem.name = query;
        rowItem.template_id = null;
      }
      inheritReceiptShopFromFirstRow(draftId, mode);
      commitReceiptRowMutation(mode);
      const nextInput = getReceiptContext(mode).listNode?.querySelector(
        `[data-receipt-item-id="${rowItem.draft_id}"] [data-receipt-field="name"]`,
      );
      nextInput?.blur();
    }
    function handleReceiptItemsListClick(event) {
      const cardButton = event.target.closest("button[data-open-receipt-template-card]");
      if (cardButton) {
        hideAllReceiptPickers();
        core.runAction({
          errorPrefix: "Не удалось открыть карточку позиции",
          action: () => window.App.getRuntimeModule?.("catalog-media")?.openItemTemplateCard?.(
            Number(cardButton.dataset.openReceiptTemplateCard || 0),
          ),
        });
        return;
      }
      const shopBtn = event.target.closest("button[data-receipt-shop-name], button[data-receipt-create-shop]");
      if (shopBtn) {
        const draftId = Number(shopBtn.dataset.receiptItemId || 0);
        const row = shopBtn.closest("[data-receipt-item-id]");
        const mode = getReceiptModeFromNode(row);
        const rowItem = getReceiptItemByDraftId(draftId, mode);
        if (rowItem) {
          updateReceiptItemField(
            draftId,
            "shop_name",
            shopBtn.dataset.receiptShopName || shopBtn.dataset.receiptCreateShop || "",
            mode,
          );
          inheritReceiptShopFromFirstRow(draftId, mode);
          receiptUiState.activePicker = null;
          commitReceiptRowMutation(mode);
        }
        return;
      }
      const brandBtn = event.target.closest("button[data-receipt-brand-id], button[data-receipt-brand-clear]");
      if (brandBtn) {
        const draftId = Number(brandBtn.dataset.receiptItemId || 0);
        const row = brandBtn.closest("[data-receipt-item-id]");
        const mode = getReceiptModeFromNode(row);
        const rowItem = getReceiptItemByDraftId(draftId, mode);
        if (rowItem) {
          updateReceiptItemField(draftId, "brand_id", brandBtn.dataset.receiptBrandId || null, mode);
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
          applyReceiptTemplateToItem(rowItem, template);
          if (!rowItem.quantity || Number(rowItem.quantity) <= 0) {
            rowItem.quantity = 1;
          }
          inheritReceiptShopFromFirstRow(draftId, mode);
          upsertLocalReceiptTemplate(rowItem.name, rowItem.unit_price, rowItem.shop_name || "", getDraftBrandPayload(rowItem));
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
          const createdTemplate = upsertLocalReceiptTemplate(rowItem.name, rowItem.unit_price, rowItem.shop_name || "", getDraftBrandPayload(rowItem));
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
      const discountBtn = event.target.closest("button[data-receipt-discount-toggle]");
      if (discountBtn) {
        const draftId = Number(discountBtn.dataset.receiptDiscountToggle || 0);
        const row = discountBtn.closest("[data-receipt-item-id]");
        const mode = getReceiptModeFromNode(row);
        const rowItem = getReceiptItemByDraftId(draftId, mode);
        if (rowItem) {
          updateReceiptItemField(draftId, "is_discounted", !rowItem.is_discounted, mode);
          commitReceiptRowMutation(mode);
        }
        return;
      }
      const discountTypeBtn = event.target.closest("button[data-receipt-discount-type]");
      if (discountTypeBtn) {
        const draftId = Number(discountTypeBtn.dataset.receiptItemId || 0);
        const row = discountTypeBtn.closest("[data-receipt-item-id]");
        const mode = getReceiptModeFromNode(row);
        if (getReceiptItemByDraftId(draftId, mode)) {
          updateReceiptItemField(draftId, "discount_type", discountTypeBtn.dataset.receiptDiscountType || "promo", mode);
          commitReceiptRowMutation(mode);
        }
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
      const insideBrandCell = event.target.closest(".receipt-brand-cell");
      const insideBrandPicker = event.target.closest(".receipt-brand-picker");
      const insideActiveNameCell = event.target.closest(".receipt-name-cell");
      const insidePicker = event.target.closest(".receipt-name-picker");
      const insideCategoryCell = event.target.closest(".receipt-category-cell");
      const insideCategoryPicker = event.target.closest(".receipt-category-picker");
      if (insideShopCell || insideShopPicker || insideBrandCell || insideBrandPicker || insideActiveNameCell || insidePicker || insideCategoryCell || insideCategoryPicker) {
        return;
      }
      hideAllReceiptPickers();
    }
    return {
      loadReceiptTemplateHints,
      hideAllReceiptPickers,
      handleReceiptItemsListInput,
      handleReceiptItemsListFocusOut,
      handleReceiptItemsListFocusIn,
      handleReceiptItemsListKeydown,
      handleReceiptItemsListClick,
      handleReceiptOutsidePointer,
    };
  }
  window.App = window.App || {};
  window.App.registerRuntimeModule?.("operation-modal-receipt-interactions-factory", createOperationModalReceiptInteractionsFeature);
})();
