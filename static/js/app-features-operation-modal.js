(() => {
  const { state, el, core } = window.App;
  const categoryActions = window.App.actions;
  const CATEGORY_USAGE_KEY = "fa_category_usage_v1";
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
  const updateCreatePreview = preview?.updateCreatePreview || (() => {});
  const updateEditPreview = preview?.updateEditPreview || (() => {});
  const handleCreatePreviewClick = preview?.handleCreatePreviewClick || (() => {});
  const createOperationModalReceiptFeature = window.App.createOperationModalReceiptFeature;
  const receipt = createOperationModalReceiptFeature
    ? createOperationModalReceiptFeature({
      state,
      el,
      core,
      updateCreatePreview,
      updateEditPreview,
    })
    : {};
  const createReceiptDraft = receipt.createReceiptDraft;
  const clearReceiptItems = receipt.clearReceiptItems || (() => {});
  const setReceiptEnabled = receipt.setReceiptEnabled || (() => {});
  const renderReceiptItems = receipt.renderReceiptItems || (() => {});
  const renderReceiptSummary = receipt.renderReceiptSummary || (() => {});
  const loadReceiptTemplateHints = receipt.loadReceiptTemplateHints || (async () => {});
  const handleReceiptItemsListInput = receipt.handleReceiptItemsListInput || (() => {});
  const handleReceiptItemsListFocusIn = receipt.handleReceiptItemsListFocusIn || (() => {});
  const handleReceiptItemsListKeydown = receipt.handleReceiptItemsListKeydown || (() => {});
  const handleReceiptItemsListClick = receipt.handleReceiptItemsListClick || (() => {});
  const handleReceiptOutsidePointer = receipt.handleReceiptOutsidePointer || (() => {});
  const handlePullReceiptTotal = receipt.handlePullReceiptTotal || (() => {});
  const getCreateReceiptPayload = receipt.getCreateReceiptPayload || (() => []);
  const getEditReceiptPayload = receipt.getEditReceiptPayload || (() => []);
  function openCreateCategoryPopover() {
    if (el.opEntryMode.value === "debt") {
      return;
    }
    el.createCategoryPickerBlock.classList.remove("hidden");
  }
  function closeCreateCategoryPopover() {
    el.createCategoryPickerBlock.classList.add("hidden");
  }
  function openEditCategoryPopover() {
    el.editCategoryPickerBlock?.classList.remove("hidden");
  }
  function closeEditCategoryPopover() {
    el.editCategoryPickerBlock?.classList.add("hidden");
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
  function getEditCategoriesSorted(kind, query = "") {
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
  function renderEditCategoryPicker() {
    if (!el.editCategoryAll) {
      return;
    }
    const kind = el.editKind.value || "expense";
    const selectedId = el.editCategory.value ? Number(el.editCategory.value) : null;
    const selectedCategory = state.categories.find((item) => item.id === selectedId && item.kind === kind);
    const rawQuery = el.editCategorySearch?.value?.trim() || "";
    const query = selectedCategory && rawQuery.toLowerCase() === selectedCategory.name.toLowerCase() ? "" : rawQuery;
    const categories = getEditCategoriesSorted(kind, query);
    el.editCategoryAll.innerHTML = "";
    for (const item of categories) {
      el.editCategoryAll.appendChild(createCategoryChipButton(item, selectedId === item.id, query));
    }
    if (!categories.length) {
      el.editCategoryAll.innerHTML = query
        ? "<span class='muted-small'>Ничего не найдено</span>"
        : "<span class='muted-small'>Без категорий для выбранного типа</span>";
    }
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
  function selectEditCategory(categoryId, options = {}) {
    const value = categoryId ? String(categoryId) : "";
    el.editCategory.value = value;
    const categoryMeta = getCategoryMetaById(categoryId);
    if (!options.keepSearch && el.editCategorySearch) {
      el.editCategorySearch.value = categoryMeta?.name || "";
    }
    renderEditCategoryPicker();
    updateEditPreview();
    closeEditCategoryPopover();
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
  function handleEditCategorySearchFocus() {
    openEditCategoryPopover();
    renderEditCategoryPicker();
  }
  function handleEditCategorySearchInput() {
    if (el.editCategory.value) {
      el.editCategory.value = "";
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
    const matches = getEditCategoriesSorted(el.editKind.value || "expense", query);
    if (matches.length) {
      selectEditCategory(matches[0].id);
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
  function handleEditCategoryOutsidePointer(event) {
    if (el.editCategoryPickerBlock?.classList.contains("hidden")) {
      return;
    }
    if (event.target.closest("#editCategoryField")) {
      return;
    }
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
    if (!pending || pending !== createdName || !kindMatches) {
      state.pendingCreateCategoryFromOperation = "";
      return;
    }
    state.pendingCreateCategoryFromOperation = "";
    selectCreateCategory(createdCategory.id);
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
    } else if (submit) {
      submit.textContent = "Добавить";
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
      if (el.editCategory.value && !state.categories.some((item) => String(item.id) === el.editCategory.value && item.kind === kind)) {
        el.editCategory.value = "";
        if (el.editCategorySearch) {
          el.editCategorySearch.value = "";
        }
      }
      renderEditCategoryPicker();
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
    if (typeof createReceiptDraft === "function") {
      state.editReceiptItems = (Array.isArray(item.receipt_items) ? item.receipt_items : []).map((row) => createReceiptDraft({
        template_id: row.template_id || null,
        shop_name: row.shop_name || "",
        name: row.name || "",
        quantity: row.quantity || 0,
        unit_price: row.unit_price || 0,
        note: row.note || "",
      }, "edit"));
    } else {
      state.editReceiptItems = [];
    }
    const hasReceipt = state.editReceiptItems.length > 0;
    if (el.editReceiptEnabled) {
      el.editReceiptEnabled.checked = hasReceipt;
    }
    setReceiptEnabled(hasReceipt, "edit");
    el.editCategory.value = item.category_id ? String(item.category_id) : "";
    setOperationKind("edit", item.kind);
    selectEditCategory(item.category_id ? Number(item.category_id) : null);
    updateEditPreview();
    el.editModal.classList.remove("hidden");
  }
  function closeEditModal() {
    state.editOperationId = null;
    clearReceiptItems("edit");
    setReceiptEnabled(false, "edit");
    closeEditCategoryPopover();
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
    renderEditCategoryPicker,
    openCreateCategoryPopover,
    closeCreateCategoryPopover,
    openEditCategoryPopover,
    closeEditCategoryPopover,
    handleCreateCategoryPickerClick,
    handleEditCategoryPickerClick,
    handleCreateCategorySearchFocus,
    handleCreateCategorySearchInput,
    handleCreateCategorySearchKeydown,
    handleEditCategorySearchFocus,
    handleEditCategorySearchInput,
    handleEditCategorySearchKeydown,
    handleCreateCategoryOutsidePointer,
    handleEditCategoryOutsidePointer,
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
    selectEditCategory,
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
