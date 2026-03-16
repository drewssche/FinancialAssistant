(() => {
  function createOperationModalCategoryFeature(deps) {
    const {
      state,
      el,
      core,
      categoryActions,
      renderReceiptItems,
      renderReceiptSummary,
      updateCreatePreview,
      updateEditPreview,
      isCreateReceiptMode,
      isEditReceiptMode,
      getSelectedCreateCategoryId,
      getCategoryMetaById,
    } = deps;

    const pickerUtils = window.App.pickerUtils;
    const CATEGORY_USAGE_KEY = pickerUtils.DEFAULT_CATEGORY_USAGE_KEY;

    function writeCategoryUsage(usage) {
      localStorage.setItem(CATEGORY_USAGE_KEY, JSON.stringify(usage));
    }

    function trackCategoryUsage(categoryId) {
      if (!categoryId) {
        return;
      }
      const usage = pickerUtils.readUsageMap(CATEGORY_USAGE_KEY);
      const key = String(categoryId);
      usage[key] = Number(usage[key] || 0) + 1;
      writeCategoryUsage(usage);
    }

    function getCreateFormCategoryMeta() {
      return getCategoryMetaById(getSelectedCreateCategoryId());
    }

    function updateCreateCategoryFieldUi() {
      if (!el.opCategorySearch) {
        return;
      }
      el.opCategorySearch.placeholder = isCreateReceiptMode() ? "Категория по умолчанию" : "Категория";
    }

    function updateEditCategoryFieldUi() {
      if (!el.editCategorySearch) {
        return;
      }
      el.editCategorySearch.placeholder = isEditReceiptMode() ? "Категория по умолчанию" : "Категория";
    }

    function openCreateCategoryPopover() {
      if (el.opEntryMode.value === "debt") {
        return;
      }
      pickerUtils.setPopoverOpen(el.createCategoryPickerBlock, true, {
        owners: [el.createCategoryField],
        onClose: closeCreateCategoryPopover,
      });
    }

    function closeCreateCategoryPopover() {
      pickerUtils.setPopoverOpen(el.createCategoryPickerBlock, false, { owners: [el.createCategoryField] });
    }

    function openEditCategoryPopover() {
      pickerUtils.setPopoverOpen(el.editCategoryPickerBlock, true, {
        owners: [el.editCategoryField],
        onClose: closeEditCategoryPopover,
      });
    }

    function closeEditCategoryPopover() {
      pickerUtils.setPopoverOpen(el.editCategoryPickerBlock, false, { owners: [el.editCategoryField] });
    }

    function getCategoriesSorted(kind, query = "") {
      return pickerUtils.sortCategoriesByUsage(
        state.categories.filter((item) => item.kind === kind),
        query,
        CATEGORY_USAGE_KEY,
      );
    }

    function createCategoryChipButton(category, selected, searchQuery = "") {
      return pickerUtils.createChipButton({
        datasetName: "categoryId",
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

    function createNoCategoryChipButton(selected) {
      return pickerUtils.createMetaChipButton({
        datasetName: "categoryId",
        datasetValue: "",
        selected,
        label: "Без категории",
        core,
      });
    }

    function renderCategoryPicker(options = {}) {
      const {
        kind,
        selectedId,
        searchValue,
        targetNode,
        createQueryDataset = null,
      } = options;
      if (!targetNode) {
        return;
      }
      const selectedCategory = state.categories.find((item) => item.id === selectedId && item.kind === kind);
      const rawQuery = String(searchValue || "").trim();
      const query = selectedCategory && rawQuery.toLowerCase() === selectedCategory.name.toLowerCase() ? "" : rawQuery;
      const categories = getCategoriesSorted(kind, query);
      targetNode.innerHTML = "";
      targetNode.appendChild(createNoCategoryChipButton(!selectedId));
      for (const item of categories) {
        targetNode.appendChild(createCategoryChipButton(item, selectedId === item.id, query));
      }
      if (!categories.length && query && createQueryDataset) {
        const createChip = pickerUtils.createActionChipButton({
          datasetName: createQueryDataset,
          datasetValue: query,
          label: `+ Создать категорию «${query}»`,
        });
        targetNode.appendChild(createChip);
      }
      if (!categories.length && !query) {
        targetNode.innerHTML = "<span class='muted-small'>Без категорий для выбранного типа</span>";
      }
      if (!categories.length && query && !createQueryDataset) {
        targetNode.innerHTML = "<span class='muted-small'>Ничего не найдено</span>";
      }
    }

    function renderCreateCategoryPicker() {
      renderCategoryPicker({
        kind: el.opKind.value || "expense",
        selectedId: getSelectedCreateCategoryId(),
        searchValue: el.opCategorySearch.value,
        targetNode: el.opCategoryAll,
        createQueryDataset: "createCategory",
      });
    }

    function renderEditCategoryPicker() {
      renderCategoryPicker({
        kind: el.editKind.value || "expense",
        selectedId: el.editCategory.value ? Number(el.editCategory.value) : null,
        searchValue: el.editCategorySearch?.value || "",
        targetNode: el.editCategoryAll,
      });
    }

    function selectCreateCategory(categoryId, options = {}) {
      const value = categoryId ? String(categoryId) : "";
      el.opCategory.value = value;
      const categoryMeta = getCreateFormCategoryMeta();
      if (!options.keepSearch) {
        el.opCategorySearch.value = categoryMeta?.name || "";
      }
      if (isCreateReceiptMode()) {
        renderReceiptItems("create");
        renderReceiptSummary("create");
      }
      renderCreateCategoryPicker();
      updateCreatePreview();
      closeCreateCategoryPopover();
    }

    function selectEditCategory(categoryId, options = {}) {
      const value = categoryId ? String(categoryId) : "";
      el.editCategory.value = value;
      const categoryMeta = getCategoryMetaById(categoryId);
      if (!options.keepSearch && el.editCategorySearch) {
        el.editCategorySearch.value = categoryMeta?.name || "";
      }
      if (isEditReceiptMode()) {
        renderReceiptItems("edit");
        renderReceiptSummary("edit");
      }
      renderEditCategoryPicker();
      updateEditPreview();
      closeEditCategoryPopover();
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

    function handleCreateCategorySearchFocus() {
      openCreateCategoryPopover();
      renderCreateCategoryPicker();
    }

    function handleCreateCategorySearchInput() {
      if (el.opCategory.value) {
        el.opCategory.value = "";
      }
      if (isCreateReceiptMode()) {
        renderReceiptItems("create");
        renderReceiptSummary("create");
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
      const matches = getCategoriesSorted(el.opKind.value || "expense", query);
      if (matches.length) {
        selectCreateCategory(matches[0].id);
        return;
      }
      if (query) {
        openCreateCategoryFromOperation(query);
      }
    }

    function handleEditCategorySearchFocus() {
      openEditCategoryPopover();
      renderEditCategoryPicker();
    }

    function handleEditCategorySearchInput() {
      if (el.editCategory.value) {
        el.editCategory.value = "";
      }
      if (isEditReceiptMode()) {
        renderReceiptItems("edit");
        renderReceiptSummary("edit");
      }
      openEditCategoryPopover();
      renderEditCategoryPicker();
      updateEditPreview();
    }

    function handleEditCategorySearchKeydown(event) {
      if (event.key === "Escape") {
        closeEditCategoryPopover();
        return;
      }
      if (event.key !== "Enter") {
        return;
      }
      event.preventDefault();
      const query = el.editCategorySearch.value.trim();
      const matches = getCategoriesSorted(el.editKind.value || "expense", query);
      if (matches.length) {
        selectEditCategory(matches[0].id);
      }
    }

    function handleCreateCategoryOutsidePointer(event) {
      pickerUtils.closePopoverOnOutside(event, {
        popover: el.createCategoryPickerBlock,
        scopes: [el.createCategoryField],
        onClose: closeCreateCategoryPopover,
      });
    }

    function handleEditCategoryOutsidePointer(event) {
      pickerUtils.closePopoverOnOutside(event, {
        popover: el.editCategoryPickerBlock,
        scopes: [el.editCategoryField],
        onClose: closeEditCategoryPopover,
      });
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

    function handleEditCategoryPickerClick(event) {
      const chipBtn = event.target.closest("button[data-category-id]");
      if (!chipBtn) {
        return;
      }
      selectEditCategory(Number(chipBtn.dataset.categoryId || 0));
    }

    function onCategoryCreated(createdCategory) {
      if (!createdCategory) {
        return;
      }
      const pending = (state.pendingCreateCategoryFromOperation || "").trim().toLowerCase();
      const createdName = String(createdCategory.name || "").trim().toLowerCase();
      const kindMatches = createdCategory.kind === (el.opKind.value || "expense");
      if (pending && pending === createdName && kindMatches) {
        state.pendingCreateCategoryFromOperation = "";
        selectCreateCategory(createdCategory.id);
      }
      state.pendingCreateCategoryFromOperation = "";

      const pendingReceipt = state.pendingCreateCategoryFromReceipt;
      if (!pendingReceipt) {
        return;
      }
      const receiptCreatedName = String(createdCategory.name || "").trim().toLowerCase();
      const receiptPendingName = String(pendingReceipt.query || "").trim().toLowerCase();
      if (receiptCreatedName !== receiptPendingName || createdCategory.kind !== pendingReceipt.kind) {
        state.pendingCreateCategoryFromReceipt = null;
        return;
      }
      const targetItems = pendingReceipt.mode === "edit" ? state.editReceiptItems : state.createReceiptItems;
      const rowItem = Array.isArray(targetItems)
        ? targetItems.find((item) => Number(item.draft_id) === Number(pendingReceipt.draft_id))
        : null;
      if (rowItem) {
        rowItem.category_id = Number(createdCategory.id);
      }
      state.pendingCreateCategoryFromReceipt = null;
      renderReceiptItems(pendingReceipt.mode === "edit" ? "edit" : "create");
      renderReceiptSummary(pendingReceipt.mode === "edit" ? "edit" : "create");
      if (pendingReceipt.mode === "edit") {
        updateEditPreview();
      } else {
        updateCreatePreview();
      }
    }

    return {
      trackCategoryUsage,
      updateCreateCategoryFieldUi,
      updateEditCategoryFieldUi,
      openCreateCategoryPopover,
      closeCreateCategoryPopover,
      openEditCategoryPopover,
      closeEditCategoryPopover,
      renderCreateCategoryPicker,
      renderEditCategoryPicker,
      handleCreateCategorySearchFocus,
      handleCreateCategorySearchInput,
      handleCreateCategorySearchKeydown,
      handleEditCategorySearchFocus,
      handleEditCategorySearchInput,
      handleEditCategorySearchKeydown,
      handleCreateCategoryOutsidePointer,
      handleEditCategoryOutsidePointer,
      handleCreateCategoryPickerClick,
      handleEditCategoryPickerClick,
      onCategoryCreated,
      selectCreateCategory,
      selectEditCategory,
    };
  }

  window.App = window.App || {};
  window.App.createOperationModalCategoryFeature = createOperationModalCategoryFeature;
})();
