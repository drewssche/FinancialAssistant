(() => {
  const { state, el, core } = window.App;
  function getCategoryActions() {
    return window.App.getRuntimeModule?.("category-actions") || {};
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
  let getDebtPreviewSnapshot = null;
  const previewModule = window.App.getRuntimeModule?.("operation-modal-preview");
  const preview = previewModule?.build({
    state,
    el,
    core,
    getSelectedCreateCategoryId,
    getCategoryMetaById,
    getDebtPreviewSnapshot: () => (typeof getDebtPreviewSnapshot === "function" ? getDebtPreviewSnapshot() : null),
  });
  const updateDebtDueHint = preview?.updateDebtDueHint || (() => {});
  const getCreateFormPreviewItem = preview?.getCreateFormPreviewItem || (() => ({}));
  const updateCreatePreview = preview?.updateCreatePreview || (() => {});
  const updateEditPreview = preview?.updateEditPreview || (() => {});
  const handleCreatePreviewClick = preview?.handleCreatePreviewClick || (() => {});
  const createOperationModalReceiptFeature = window.App.getRuntimeModule?.("operation-modal-receipt-factory");
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
  const syncReceiptCategoriesToKind = receipt.syncReceiptCategoriesToKind || (() => {});
  const createOperationModalDebtCounterpartyFeature = window.App.getRuntimeModule?.("operation-modal-debt-counterparty-factory");

  function isCreateReceiptMode() {
    return el.opOperationMode?.value === "receipt";
  }

  function isEditReceiptMode() {
    return el.editOperationMode?.value === "receipt";
  }
  function setDebtDirection(direction) {
    const nextDirection = direction === "borrow" ? "borrow" : "lend";
    el.debtDirection.value = nextDirection;
    core.syncSegmentedActive(el.createDebtDirectionSwitch, "debt-direction", nextDirection);
    updateCreatePreview();
  }
  function setCurrencySide(side) {
    const nextSide = side === "sell" ? "sell" : "buy";
    if (el.currencySide) {
      el.currencySide.value = nextSide;
    }
    if (el.createCurrencySideSwitch) {
      core.syncSegmentedActive(el.createCurrencySideSwitch, "currency-side", nextSide);
    }
    updateCreatePreview();
  }
  function syncOperationCurrencyFields(mode = "create") {
    const isEdit = mode === "edit";
    const currencySelect = isEdit ? el.editCurrency : el.opCurrency;
    const fxRateField = isEdit ? el.editFxRateField : el.opFxRateField;
    const fxRateInput = isEdit ? el.editFxRate : el.opFxRate;
    const baseCurrency = core.getCurrencyConfig?.().code || "BYN";
    const selectedCurrency = String(currencySelect?.value || baseCurrency).toUpperCase();
    const needsFxRate = selectedCurrency !== baseCurrency;
    fxRateField?.classList.toggle("hidden", !needsFxRate);
    if (fxRateInput) {
      fxRateInput.required = needsFxRate;
      if (!needsFxRate) {
        fxRateInput.value = "1";
      } else if (!String(fxRateInput.value || "").trim()) {
        fxRateInput.value = "1";
      }
    }
  }
  function applyDebtCurrencyUi() {
    core.applyMoneyInputs();
  }
  const debtCounterpartyFeature = createOperationModalDebtCounterpartyFeature
    ? createOperationModalDebtCounterpartyFeature({
      state,
      el,
      core,
      getCurrentDebtEditId: () => Number(state.editDebtCreateId || 0),
      getCurrentDebtDirection: () => (el.debtDirection?.value === "borrow" ? "borrow" : "lend"),
      getCurrentDebtPrincipalValue: () => {
        const resolved = core.resolveMoneyInput(el.debtPrincipal?.value || 0);
        return Number(resolved.previewValue || 0);
      },
      getCurrentDebtStartDate: () => core.parseDateInputValue(el.debtStartDate?.value || "") || core.getTodayIso(),
      getCurrentDebtDueDate: () => core.parseDateInputValue(el.debtDueDate?.value || "") || "",
      getCurrentDebtNote: () => String(el.debtNote?.value || "").trim(),
      updateCreatePreview,
    })
    : {};
  getDebtPreviewSnapshot = debtCounterpartyFeature.getDebtPreviewSnapshot || null;
  function setCreateOperationMode(mode) {
    const nextMode = mode === "receipt" ? "receipt" : "common";
    if (el.opOperationMode) {
      el.opOperationMode.value = nextMode;
    }
    if (el.createOperationModeSwitch) {
      core.syncSegmentedActive(el.createOperationModeSwitch, "operation-mode", nextMode);
    }
    el.opReceiptBlock?.classList.toggle("hidden", el.opEntryMode?.value === "debt" || el.opEntryMode?.value === "currency" || nextMode !== "receipt");
    setReceiptEnabled(nextMode === "receipt", "create");
    updateCreateCategoryFieldUi();
    renderCreateCategoryPicker();
    renderDebtCounterpartyPicker();
    updateCreatePreview();
  }
  function setEditOperationMode(mode) {
    const nextMode = mode === "receipt" ? "receipt" : "common";
    if (el.editOperationMode) {
      el.editOperationMode.value = nextMode;
    }
    if (el.editOperationModeSwitch) {
      core.syncSegmentedActive(el.editOperationModeSwitch, "operation-mode", nextMode);
    }
    el.editReceiptBlock?.classList.toggle("hidden", nextMode !== "receipt");
    setReceiptEnabled(nextMode === "receipt", "edit");
    updateEditCategoryFieldUi();
    renderEditCategoryPicker();
    updateEditPreview();
  }
  function setCreateEntryMode(mode) {
    const nextMode = mode === "debt" ? "debt" : mode === "currency" ? "currency" : "operation";
    el.opEntryMode.value = nextMode;
    core.syncSegmentedActive(el.createEntryModeSwitch, "entry-mode", nextMode);
    const isDebt = nextMode === "debt";
    const isCurrency = nextMode === "currency";
    el.createKindSwitch.classList.toggle("hidden", isDebt || isCurrency);
    el.createOperationModeSwitch?.classList.toggle("hidden", isDebt || isCurrency);
    el.createCategoryField.classList.toggle("hidden", isDebt || isCurrency);
    el.opReceiptBlock?.classList.toggle("hidden", isDebt || isCurrency || !isCreateReceiptMode());
    const opAmountField = document.getElementById("opAmountCompound");
    const opAmount = document.getElementById("opAmount");
    const opFxRateField = document.getElementById("opFxRateField");
    const opDateField = document.getElementById("opDateField");
    const opDate = document.getElementById("opDate");
    const opNote = document.getElementById("opNote");
    if (opAmountField) {
      opAmountField.classList.toggle("hidden", isDebt || isCurrency);
    }
    if (opAmount) {
      opAmount.required = !isDebt && !isCurrency;
      if (!isDebt && !isCurrency && isCreateReceiptMode()) {
        opAmount.required = false;
      }
    }
    if (opFxRateField) {
      opFxRateField.classList.toggle("hidden", isDebt || isCurrency || (el.opCurrency?.value || (core.getCurrencyConfig?.().code || "BYN")) === (core.getCurrencyConfig?.().code || "BYN"));
    }
    if (opDateField) {
      opDateField.classList.toggle("hidden", isDebt || isCurrency);
    }
    if (opDate) {
      opDate.required = !isDebt && !isCurrency;
    }
    if (opNote) {
      opNote.classList.toggle("hidden", isDebt || isCurrency);
      opNote.placeholder = isDebt ? "Комментарий (долг)" : "Комментарий";
    }
    el.createDebtFields.classList.toggle("hidden", !isDebt);
    el.createCurrencyFields?.classList.toggle("hidden", !isCurrency);
    if (el.createPreviewHeadOperation && el.createPreviewHeadDebt) {
      el.createPreviewHeadOperation.classList.toggle("hidden", isDebt || isCurrency);
      el.createPreviewHeadDebt.classList.toggle("hidden", !isDebt);
    }
    if (el.createPreviewHeadCurrency) {
      el.createPreviewHeadCurrency.classList.toggle("hidden", !isCurrency);
    }
    if (isDebt || isCurrency) {
      closeCreateCategoryPopover();
      closeDebtCounterpartyPopover();
    }
    el.debtCounterparty.required = isDebt;
    el.debtPrincipal.required = isDebt;
    el.debtStartDate.required = isDebt;
    const submit = document.getElementById("submitCreateOperationBtn");
    if (isDebt) {
      if (!el.debtStartDate.value) {
        core.syncDateFieldValue(el.debtStartDate, core.getTodayIso());
      }
      renderDebtCounterpartyPicker();
      if (submit) {
        submit.textContent = state.editDebtCreateId ? "Сохранить долг" : "Создать долг";
      }
    } else if (isCurrency) {
      if (el.currencyTradeDateModal && !el.currencyTradeDateModal.value) {
        core.syncDateFieldValue(el.currencyTradeDateModal, core.getTodayIso());
      }
      if (submit) {
        submit.textContent = "Сохранить валютную сделку";
      }
    } else if (submit) {
      submit.textContent = "Добавить";
    }
    if (!isDebt && !isCurrency) {
      updateCreateCategoryFieldUi();
    }
    updateCreatePreview();
  }
  function setOperationKind(mode, kind) {
    if (mode === "create") {
      el.opKind.value = kind;
      core.syncSegmentedActive(el.createKindSwitch, "kind", kind);
      getCategoryActions().populateCategorySelect?.(el.opCategory, el.opCategory.value, kind);
      if (el.opCategory.value && !state.categories.some((item) => String(item.id) === el.opCategory.value && item.kind === kind)) {
        el.opCategory.value = "";
        el.opCategorySearch.value = "";
      }
      renderCreateCategoryPicker();
      syncReceiptCategoriesToKind("create");
      updateCreatePreview();
      return;
    }
    if (mode === "edit") {
      el.editKind.value = kind;
      core.syncSegmentedActive(el.editKindSwitch, "kind", kind);
      getCategoryActions().populateCategorySelect?.(el.editCategory, el.editCategory.value, kind);
      if (el.editCategory.value && !state.categories.some((item) => String(item.id) === el.editCategory.value && item.kind === kind)) {
        el.editCategory.value = "";
        if (el.editCategorySearch) {
          el.editCategorySearch.value = "";
        }
      }
      renderEditCategoryPicker();
      syncReceiptCategoriesToKind("edit");
      updateEditPreview();
    }
  }
  function ensureCategoryCatalogReady(mode = "create") {
    if (Array.isArray(state.categories) && state.categories.length > 0) {
      return Promise.resolve();
    }
    if (!getCategoryActions().loadCategoryCatalog) {
      return Promise.resolve();
    }
    return getCategoryActions().loadCategoryCatalog().then(() => {
      if (mode === "edit") {
        renderEditCategoryPicker();
        renderReceiptItems("edit");
        renderReceiptSummary("edit");
        updateEditPreview();
      } else {
        renderCreateCategoryPicker();
        renderReceiptItems("create");
        renderReceiptSummary("create");
        updateCreatePreview();
      }
    }).catch(() => {});
  }

  async function openCreateModal() {
    await ensureCategoryCatalogReady("create");
    state.createFlowMode = "operation";
    state.editPlanId = null;
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
      core.syncDateFieldValue(dateInput, core.getTodayIso());
    }
    setOperationKind("create", el.opKind.value || "expense");
    el.opCategory.value = "";
    el.opCategorySearch.value = "";
    clearReceiptItems("create");
    setCreateOperationMode("common");
    closeCreateCategoryPopover();
    closeDebtCounterpartyPopover();
    el.debtCounterparty.value = "";
    el.debtPrincipal.value = "";
    el.debtStartDate.value = "";
    el.debtDueDate.value = "";
    el.debtNote.value = "";
    if (el.currencyAsset) {
      el.currencyAsset.value = "USD";
    }
    if (el.currencyQuote) {
      el.currencyQuote.value = "BYN";
    }
    if (el.currencyTradeDateModal) {
      core.syncDateFieldValue(el.currencyTradeDateModal, core.getTodayIso());
    }
    if (el.currencyQuantity) {
      el.currencyQuantity.value = "";
    }
    if (el.currencyUnitPrice) {
      el.currencyUnitPrice.value = "";
    }
    if (el.currencyFee) {
      el.currencyFee.value = "";
    }
    if (el.currencyNote) {
      el.currencyNote.value = "";
    }
    if (el.opCurrency) {
      el.opCurrency.value = core.getCurrencyConfig?.().code || "BYN";
    }
    if (el.opFxRate) {
      el.opFxRate.value = "1";
    }
    if (el.planRecurrenceBlock) {
      el.planRecurrenceBlock.classList.add("hidden");
    }
    if (el.planScheduleMode) {
      el.planScheduleMode.value = "oneoff";
    }
    if (el.planScheduleModeSwitch) {
      core.syncSegmentedActive(el.planScheduleModeSwitch, "plan-schedule-mode", "oneoff");
    }
    if (el.planRecurrenceFields) {
      el.planRecurrenceFields.classList.add("hidden");
    }
    if (el.planRecurrenceFrequency) {
      el.planRecurrenceFrequency.value = "monthly";
    }
    if (el.planRecurrenceInterval) {
      el.planRecurrenceInterval.value = "1";
    }
    if (el.planRecurrenceWorkdaysOnly) {
      el.planRecurrenceWorkdaysOnly.value = "off";
    }
    if (el.planRecurrenceWorkdaysSwitch) {
      core.syncSegmentedActive(el.planRecurrenceWorkdaysSwitch, "plan-workdays-only", "off");
    }
    if (el.planRecurrenceMonthEnd) {
      el.planRecurrenceMonthEnd.value = "off";
    }
    if (el.planRecurrenceMonthEndSwitch) {
      core.syncSegmentedActive(el.planRecurrenceMonthEndSwitch, "plan-month-end", "off");
    }
    if (el.planRecurrenceEndDate) {
      core.syncDateFieldValue(el.planRecurrenceEndDate, "");
    }
    if (el.planRecurrenceWeekdays) {
      Array.from(el.planRecurrenceWeekdays.querySelectorAll("button[data-plan-weekday]")).forEach((button) => {
        button.classList.remove("active");
      });
    }
    el.planRecurrenceWeeklyBlock?.classList.add("hidden");
    el.planRecurrenceWorkdaysWrap?.classList.add("hidden");
    el.planRecurrenceMonthEndWrap?.classList.add("hidden");
    setDebtDirection("lend");
    setCurrencySide("buy");
    syncOperationCurrencyFields("create");
    syncOperationCurrencyFields("edit");
    applyDebtCurrencyUi();
    updateDebtDueHint();
    setCreateEntryMode("operation");
    renderCreateCategoryPicker();
    renderDebtCounterpartyPicker();
    loadReceiptTemplateHints().catch(() => {});
    renderReceiptItems();
    renderReceiptSummary();
    updateCreatePreview();
    el.createModal.classList.remove("hidden");
  }
  function closeCreateModal() {
    state.createFlowMode = "operation";
    state.editPlanId = null;
    state.editDebtCreateId = null;
    const createTitle = document.getElementById("createTitle");
    if (createTitle) {
      createTitle.textContent = "Новая операция";
    }
    el.createModal.classList.add("hidden");
  }
  async function openCreateModalForDebtEdit(payload) {
    if (!payload?.id) {
      return;
    }
    await openCreateModal();
    state.editDebtCreateId = Number(payload.id);
    if (el.createEntryModeSwitch) {
      el.createEntryModeSwitch.classList.add("hidden");
    }
    const createTitle = document.getElementById("createTitle");
    if (createTitle) {
      createTitle.textContent = "Редактировать долг";
    }
    selectDebtCounterparty(payload.counterparty || "", { keepOpen: false });
    el.debtPrincipal.value = payload.principal || "";
    core.syncDateFieldValue(el.debtStartDate, payload.start_date || core.getTodayIso());
    core.syncDateFieldValue(el.debtDueDate, payload.due_date || "");
    el.debtNote.value = payload.note || "";
    setDebtDirection(payload.direction || "lend");
    setCreateEntryMode("debt");
    updateDebtDueHint();
    renderDebtCounterpartyPicker();
    updateCreatePreview();
  }
  async function openCreateModalForCurrency() {
    await openCreateModal();
    setCreateEntryMode("currency");
  }
  async function openEditModal(item) {
    await ensureCategoryCatalogReady("edit");
    state.editOperationId = item.id;
    document.getElementById("editAmount").value = item.original_amount || item.amount;
    if (el.editCurrency) {
      el.editCurrency.value = item.currency || "BYN";
    }
    if (el.editFxRate) {
      el.editFxRate.value = item.fx_rate || "1";
    }
    core.syncDateFieldValue(document.getElementById("editDate"), item.operation_date);
    document.getElementById("editNote").value = item.note || "";
    clearReceiptItems("edit");
    if (typeof createReceiptDraft === "function") {
      state.editReceiptItems = (Array.isArray(item.receipt_items) ? item.receipt_items : []).map((row) => createReceiptDraft({
        template_id: row.template_id || null,
        category_id: row.category_id || null,
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
    el.editCategory.value = item.category_id ? String(item.category_id) : "";
    setOperationKind("edit", item.kind);
    syncOperationCurrencyFields("edit");
    selectEditCategory(item.category_id ? Number(item.category_id) : null);
    setEditOperationMode(hasReceipt ? "receipt" : "common");
    updateEditPreview();
    el.editModal.classList.remove("hidden");
  }
  function closeEditModal() {
    state.editOperationId = null;
    clearReceiptItems("edit");
    setEditOperationMode("common");
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
    const today = core.getTodayIso();
    core.syncDateFieldValue(el.customDateTo, state.customDateTo || today);
    core.syncDateFieldValue(el.customDateFrom, state.customDateFrom || today);
    el.periodCustomModal.classList.remove("hidden");
  }
  function closePeriodCustomModal() {
    el.periodCustomModal.classList.add("hidden");
  }
  const createOperationModalCategoryFeature = window.App.getRuntimeModule?.("operation-modal-category-factory");
  const categoryFeature = createOperationModalCategoryFeature
    ? createOperationModalCategoryFeature({
      state,
      el,
      core,
      categoryActions: getCategoryActions(),
      renderReceiptItems,
      renderReceiptSummary,
      updateCreatePreview,
      updateEditPreview,
      isCreateReceiptMode,
      isEditReceiptMode,
      getSelectedCreateCategoryId,
      getCategoryMetaById,
    })
    : {};
  const trackCategoryUsage = categoryFeature.trackCategoryUsage || (() => {});
  const updateCreateCategoryFieldUi = categoryFeature.updateCreateCategoryFieldUi || (() => {});
  const updateEditCategoryFieldUi = categoryFeature.updateEditCategoryFieldUi || (() => {});
  const openCreateCategoryPopover = categoryFeature.openCreateCategoryPopover || (() => {});
  const closeCreateCategoryPopover = categoryFeature.closeCreateCategoryPopover || (() => {});
  const openEditCategoryPopover = categoryFeature.openEditCategoryPopover || (() => {});
  const closeEditCategoryPopover = categoryFeature.closeEditCategoryPopover || (() => {});
  const renderCreateCategoryPicker = categoryFeature.renderCreateCategoryPicker || (() => {});
  const renderEditCategoryPicker = categoryFeature.renderEditCategoryPicker || (() => {});
  const handleCreateCategorySearchFocus = categoryFeature.handleCreateCategorySearchFocus || (() => {});
  const handleCreateCategorySearchInput = categoryFeature.handleCreateCategorySearchInput || (() => {});
  const handleCreateCategorySearchKeydown = categoryFeature.handleCreateCategorySearchKeydown || (() => {});
  const renderDebtCounterpartyPicker = debtCounterpartyFeature.renderDebtCounterpartyPicker || (() => {});
  const openDebtCounterpartyPopover = debtCounterpartyFeature.openDebtCounterpartyPopover || (() => {});
  const closeDebtCounterpartyPopover = debtCounterpartyFeature.closeDebtCounterpartyPopover || (() => {});
  const handleDebtCounterpartySearchFocus = debtCounterpartyFeature.handleDebtCounterpartySearchFocus || (() => {});
  const handleDebtCounterpartySearchInput = debtCounterpartyFeature.handleDebtCounterpartySearchInput || (() => {});
  const handleDebtCounterpartySearchKeydown = debtCounterpartyFeature.handleDebtCounterpartySearchKeydown || (() => {});
  const handleEditCategorySearchFocus = categoryFeature.handleEditCategorySearchFocus || (() => {});
  const handleEditCategorySearchInput = categoryFeature.handleEditCategorySearchInput || (() => {});
  const handleEditCategorySearchKeydown = categoryFeature.handleEditCategorySearchKeydown || (() => {});
  const handleCreateCategoryOutsidePointer = categoryFeature.handleCreateCategoryOutsidePointer || (() => {});
  const handleDebtCounterpartyOutsidePointer = debtCounterpartyFeature.handleDebtCounterpartyOutsidePointer || (() => {});
  const handleEditCategoryOutsidePointer = categoryFeature.handleEditCategoryOutsidePointer || (() => {});
  const handleCreateCategoryPickerClick = categoryFeature.handleCreateCategoryPickerClick || (() => {});
  const handleDebtCounterpartyPickerClick = debtCounterpartyFeature.handleDebtCounterpartyPickerClick || (() => {});
  const handleEditCategoryPickerClick = categoryFeature.handleEditCategoryPickerClick || (() => {});
  const onCategoryCreated = categoryFeature.onCategoryCreated || (() => {});
  const selectCreateCategory = categoryFeature.selectCreateCategory || (() => {});
  const selectDebtCounterparty = debtCounterpartyFeature.selectDebtCounterparty || (() => {});
  const selectEditCategory = categoryFeature.selectEditCategory || (() => {});
  const api = {
    trackCategoryUsage,
    getCategoryMetaById,
    getCreateFormPreviewItem,
    updateCreatePreview,
    updateEditPreview,
    renderCreateCategoryPicker,
    renderDebtCounterpartyPicker,
    renderEditCategoryPicker,
    openCreateCategoryPopover,
    closeCreateCategoryPopover,
    openDebtCounterpartyPopover,
    closeDebtCounterpartyPopover,
    openEditCategoryPopover,
    closeEditCategoryPopover,
    handleCreateCategoryPickerClick,
    handleDebtCounterpartyPickerClick,
    handleEditCategoryPickerClick,
    handleCreateCategorySearchFocus,
    handleCreateCategorySearchInput,
    handleCreateCategorySearchKeydown,
    handleDebtCounterpartySearchFocus,
    handleDebtCounterpartySearchInput,
    handleDebtCounterpartySearchKeydown,
    handleEditCategorySearchFocus,
    handleEditCategorySearchInput,
    handleEditCategorySearchKeydown,
    handleCreateCategoryOutsidePointer,
    handleDebtCounterpartyOutsidePointer,
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
    selectDebtCounterparty,
    selectEditCategory,
    createReceiptDraft,
    clearReceiptItems,
    renderReceiptItems,
    handleCreatePreviewClick,
    setDebtDirection,
    setCurrencySide,
    setOperationKind,
    setCreateEntryMode,
    setCreateOperationMode,
    setEditOperationMode,
    syncOperationCurrencyFields,
    updateDebtDueHint,
    openCreateModal,
    openCreateModalForCurrency,
    openCreateModalForDebtEdit,
    closeCreateModal,
    openEditModal,
    closeEditModal,
    applySettingsUi,
    openPeriodCustomModal,
    closePeriodCustomModal,
  };

  window.App.operationModal = api;
  window.App.registerRuntimeModule?.("operation-modal", api);
})();
