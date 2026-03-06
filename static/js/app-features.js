(() => {
  const { state, el, core } = window.App;
  const categoryActions = window.App.actions;
  const dashboardFeatures = window.App.featureDashboard;
  const debtFeatures = window.App.featureDebts;
  const sessionFeatures = window.App.featureSession;
  const operationModal = window.App.operationModal;
  let operationsRawItems = [];
  const getCategoryMetaById = operationModal.getCategoryMetaById;
  const trackCategoryUsage = operationModal.trackCategoryUsage;
  const getCreateFormPreviewItem = operationModal.getCreateFormPreviewItem;
  const updateCreatePreview = operationModal.updateCreatePreview;
  const updateDebtDueHint = operationModal.updateDebtDueHint;
  const updateEditPreview = operationModal.updateEditPreview;
  const renderCreateCategoryPicker = operationModal.renderCreateCategoryPicker;
  const handleCreateCategoryPickerClick = operationModal.handleCreateCategoryPickerClick;
  const handleCreateCategorySearchFocus = operationModal.handleCreateCategorySearchFocus;
  const handleCreateCategorySearchInput = operationModal.handleCreateCategorySearchInput;
  const handleCreateCategorySearchKeydown = operationModal.handleCreateCategorySearchKeydown;
  const handleCreateCategoryOutsidePointer = operationModal.handleCreateCategoryOutsidePointer;
  const onCategoryCreated = operationModal.onCategoryCreated;
  const selectCreateCategory = operationModal.selectCreateCategory;
  const handleCreatePreviewClick = operationModal.handleCreatePreviewClick;
  const setOperationKind = operationModal.setOperationKind;
  const setDebtDirection = operationModal.setDebtDirection;
  const setCreateEntryMode = operationModal.setCreateEntryMode;
  const openCreateModal = operationModal.openCreateModal;
  const openCreateModalForDebtEdit = operationModal.openCreateModalForDebtEdit;
  const closeCreateModal = operationModal.closeCreateModal;
  const openEditModal = operationModal.openEditModal;
  const closeEditModal = operationModal.closeEditModal;
  const openPeriodCustomModal = operationModal.openPeriodCustomModal;
  const closePeriodCustomModal = operationModal.closePeriodCustomModal;
  const loadMe = sessionFeatures.loadMe;
  const loadPreferences = sessionFeatures.loadPreferences;
  const savePreferences = sessionFeatures.savePreferences;
  const saveSettings = sessionFeatures.saveSettings;
  const applyInterfaceSettingsUi = sessionFeatures.applyInterfaceSettingsUi;
  const previewInterfaceSettingsUi = sessionFeatures.previewInterfaceSettingsUi;
  const deleteMe = sessionFeatures.deleteMe;
  const logout = sessionFeatures.logout;
  const devLogin = sessionFeatures.devLogin;
  const bootstrapApp = sessionFeatures.bootstrapApp;
  const loadDashboard = dashboardFeatures.loadDashboard;
  const loadDashboardOperations = dashboardFeatures.loadDashboardOperations;
  const loadDebtsCards = debtFeatures.loadDebtsCards;
  const openDebtRepaymentModal = debtFeatures.openDebtRepaymentModal;
  const closeDebtRepaymentModal = debtFeatures.closeDebtRepaymentModal;
  const submitDebtRepayment = debtFeatures.submitDebtRepayment;
  const updateRepaymentDeltaHint = debtFeatures.updateRepaymentDeltaHint;
  const openDebtHistoryModal = debtFeatures.openDebtHistoryModal;
  const closeDebtHistoryModal = debtFeatures.closeDebtHistoryModal;
  const setDebtStatusFilter = debtFeatures.setDebtStatusFilter;
  const applyDebtSearch = debtFeatures.applyDebtSearch;
  const openEditDebtModal = debtFeatures.openEditDebtModal;
  const closeEditDebtModal = debtFeatures.closeEditDebtModal;
  const submitEditDebt = debtFeatures.submitEditDebt;
  const deleteDebtFlow = debtFeatures.deleteDebtFlow;

  function invalidateAllTimeAnchor() {
    state.firstOperationDate = "";
    state.allTimeAnchorResolved = false;
  }

  async function ensureAllTimeBounds(force = false) {
    if (state.period !== "all_time") {
      return;
    }
    if (state.allTimeAnchorResolved && !force) {
      return;
    }
    const params = new URLSearchParams({
      page: "1",
      page_size: "1",
      sort_by: "operation_date",
      sort_dir: "asc",
    });
    const data = await core.requestJson(`/api/v1/operations?${params.toString()}`, {
      headers: core.authHeaders(),
    });
    state.firstOperationDate = data.items?.[0]?.operation_date || "";
    state.allTimeAnchorResolved = true;
  }

  function buildOperationsQuery(page) {
    const { dateFrom, dateTo } = core.getPeriodBounds(state.period);
    el.operationsPeriodLabel.textContent = core.formatPeriodLabel(dateFrom, dateTo);
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(state.pageSize),
      sort_by: "operation_date",
      sort_dir: "desc",
      date_from: dateFrom,
      date_to: dateTo,
    });

    if (state.filterKind) {
      params.set("kind", state.filterKind);
    }
    return params;
  }

  function renderPagination() {
    const loaded = operationsRawItems.length;
    el.pageInfo.textContent = `Загружено ${loaded} из ${state.total}`;
    el.prevPageBtn.disabled = true;
    el.nextPageBtn.disabled = !state.operationsHasMore;
  }

  function appendUniqueOperations(items) {
    const existing = new Set(operationsRawItems.map((item) => item.id));
    for (const item of items) {
      if (!existing.has(item.id)) {
        operationsRawItems.push(item);
      }
    }
  }

  function getCategoryNameById(categoryId) {
    if (!categoryId) {
      return "";
    }
    const category = state.categories.find((item) => item.id === categoryId);
    return category?.name || "";
  }

  function matchesRealtimeQuery(item, queryLower) {
    if (!queryLower) {
      return true;
    }
    const kindRu = core.kindLabel(item.kind).toLowerCase();
    const note = String(item.note || "").toLowerCase();
    const categoryName = getCategoryNameById(item.category_id).toLowerCase();
    return kindRu.includes(queryLower) || note.includes(queryLower) || categoryName.includes(queryLower);
  }

  function renderOperations(items) {
    const query = el.filterQ.value.trim();
    const queryLower = query.toLowerCase();
    const filtered = items.filter((item) => matchesRealtimeQuery(item, queryLower));
    const visibleIds = new Set(filtered.map((item) => item.id));
    for (const id of Array.from(state.selectedOperationIds)) {
      if (!visibleIds.has(id)) {
        state.selectedOperationIds.delete(id);
      }
    }
    el.operationsBody.innerHTML = "";
    if (!filtered.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="7">Нет операций</td>';
      el.operationsBody.appendChild(row);
      return;
    }
    for (const item of filtered) {
      el.operationsBody.appendChild(
        core.createOperationRow(item, {
          searchQuery: query,
          category: getCategoryMetaById(item.category_id),
          selectable: true,
          selected: state.selectedOperationIds.has(item.id),
        }),
      );
    }
    if (window.App.actions.updateOperationsBulkUi) {
      window.App.actions.updateOperationsBulkUi();
    }
  }

  async function loadOperations(options = {}) {
    await ensureAllTimeBounds();
    const reset = options.reset !== false;
    if (state.operationsLoading) {
      return;
    }
    if (!reset && !state.operationsHasMore) {
      return;
    }

    if (reset) {
      state.page = 1;
      state.operationsHasMore = true;
      operationsRawItems = [];
      state.selectedOperationIds.clear();
    }

    state.operationsLoading = true;
    const requestPage = state.page;
    try {
      const data = await core.requestJson(`/api/v1/operations?${buildOperationsQuery(requestPage).toString()}`, {
        headers: core.authHeaders(),
      });
      state.total = data.total;
      if (reset) {
        operationsRawItems = data.items.slice();
      } else {
        appendUniqueOperations(data.items);
      }
      if (data.items.length > 0) {
        state.page = requestPage + 1;
      }
      state.operationsHasMore = operationsRawItems.length < state.total && data.items.length > 0;
      renderOperations(operationsRawItems);
      renderPagination();
    } finally {
      state.operationsLoading = false;
    }
  }

  async function loadMoreOperations() {
    await loadOperations({ reset: false });
  }

  async function createOperation(event) {
    event.preventDefault();
    if (el.opEntryMode.value === "debt") {
      const payload = {
        counterparty: el.debtCounterparty.value.trim(),
        direction: el.debtDirection.value,
        principal: el.debtPrincipal.value,
        start_date: el.debtStartDate.value,
        due_date: el.debtDueDate.value || null,
        note: el.debtNote.value.trim() || null,
      };
      const isEditDebt = Number(state.editDebtCreateId || 0) > 0;
      const url = isEditDebt ? `/api/v1/debts/${state.editDebtCreateId}` : "/api/v1/debts";
      await core.requestJson(url, {
        method: isEditDebt ? "PATCH" : "POST",
        headers: core.authHeaders(),
        body: JSON.stringify(payload),
      });
      state.editDebtCreateId = null;
      closeCreateModal();
      await Promise.all([loadDebtsCards(), loadDashboard()]);
      return;
    }
    const payload = {
      kind: el.opKind.value,
      category_id: el.opCategory.value ? Number(el.opCategory.value) : null,
      amount: document.getElementById("opAmount").value,
      operation_date: document.getElementById("opDate").value,
      note: document.getElementById("opNote").value,
    };

    await core.requestJson("/api/v1/operations", {
      method: "POST",
      headers: core.authHeaders(),
      body: JSON.stringify(payload),
    });
    invalidateAllTimeAnchor();
    trackCategoryUsage(payload.category_id);

    document.getElementById("opAmount").value = "";
    document.getElementById("opNote").value = "";
    el.opCategory.value = "";
    el.opCategorySearch.value = "";
    renderCreateCategoryPicker();
    updateCreatePreview();

    closeCreateModal();
    await Promise.all([loadDashboard(), loadOperations({ reset: true }), loadDashboardOperations()]);
  }

  async function updateOperation(event) {
    event.preventDefault();
    if (!state.editOperationId) {
      return;
    }

    const payload = {
      kind: el.editKind.value,
      category_id: el.editCategory.value ? Number(el.editCategory.value) : null,
      amount: document.getElementById("editAmount").value,
      operation_date: document.getElementById("editDate").value,
      note: document.getElementById("editNote").value,
    };

    await core.requestJson(`/api/v1/operations/${state.editOperationId}`, {
      method: "PATCH",
      headers: core.authHeaders(),
      body: JSON.stringify(payload),
    });
    invalidateAllTimeAnchor();
    trackCategoryUsage(payload.category_id);

    closeEditModal();
    await Promise.all([loadDashboard(), loadOperations({ reset: true }), loadDashboardOperations()]);
  }

  async function deleteOperationFlow(item) {
    core.runDestructiveAction({
      confirmMessage: "Удалить операцию?",
      doDelete: async () => {
        await core.requestJson(`/api/v1/operations/${item.id}`, {
          method: "DELETE",
          headers: core.authHeaders(),
        });
        invalidateAllTimeAnchor();
      },
      onAfterDelete: async () => {
        await Promise.all([loadDashboard(), loadOperations({ reset: true }), loadDashboardOperations()]);
      },
      toastMessage: "Операция удалена",
      undoAction: async () => {
        await core.requestJson("/api/v1/operations", {
          method: "POST",
          headers: core.authHeaders(),
          body: JSON.stringify({
            kind: item.kind,
            category_id: item.category_id,
            amount: item.amount,
            operation_date: item.operation_date,
            note: item.note,
          }),
        });
        invalidateAllTimeAnchor();
        await Promise.all([loadDashboard(), loadOperations({ reset: true }), loadDashboardOperations()]);
        return "Операция восстановлена";
      },
      onDeleteError: "Не удалось удалить операцию",
    });
  }

  async function applyFilters() {
    await savePreferences();
    await loadOperations({ reset: true });
  }

  async function applyRealtimeSearch() {
    renderOperations(operationsRawItems);
    await savePreferences();
  }

  async function refreshAll() {
    const results = await Promise.allSettled([
      loadDashboard(),
      loadOperations({ reset: true }),
      loadDashboardOperations(),
      categoryActions.loadCategories(),
      loadDebtsCards(),
    ]);
    const rejected = results.filter((item) => item.status === "rejected");
    if (rejected.length > 0) {
      const firstError = rejected[0];
      const message = firstError.reason instanceof Error ? firstError.reason.message : String(firstError.reason);
      core.setStatus(`Часть данных не загружена: ${message}`);
    }
  }

  function refreshOperationsView() {
    renderOperations(operationsRawItems);
  }

  function getCurrentOperationItems() {
    return operationsRawItems.slice();
  }

  const previousActions = window.App.actions;

  window.App.actions = {
    ...previousActions,
    getCreateFormPreviewItem,
    updateCreatePreview,
    updateDebtDueHint,
    updateEditPreview,
    renderCreateCategoryPicker,
    handleCreateCategorySearchFocus,
    handleCreateCategorySearchInput,
    handleCreateCategorySearchKeydown,
    handleCreateCategoryOutsidePointer,
    handleCreateCategoryPickerClick,
    onCategoryCreated,
    selectCreateCategory,
    handleCreatePreviewClick,
    setOperationKind,
    setDebtDirection,
    setCreateEntryMode,
    openCreateModal,
    openCreateModalForDebtEdit,
    closeCreateModal,
    openEditModal,
    closeEditModal,
    openCreateCategoryModal: categoryActions.openCreateCategoryModal,
    closeCreateCategoryModal: categoryActions.closeCreateCategoryModal,
    openPeriodCustomModal,
    closePeriodCustomModal,
    loadMe,
    loadPreferences,
    savePreferences,
    saveSettings,
    applyInterfaceSettingsUi,
    previewInterfaceSettingsUi,
    deleteMe,
    applySectionUi: previousActions.applySectionUi,
    switchSection: previousActions.switchSection,
    renderTodayLabel: previousActions.renderTodayLabel,
    loadDashboard,
    loadDashboardOperations,
    loadDebtsCards,
    openDebtRepaymentModal,
    closeDebtRepaymentModal,
    submitDebtRepayment,
    updateRepaymentDeltaHint,
    openDebtHistoryModal,
    closeDebtHistoryModal,
    setDebtStatusFilter,
    applyDebtSearch,
    openEditDebtModal,
    closeEditDebtModal,
    submitEditDebt,
    deleteDebtFlow,
    ensureAllTimeBounds,
    invalidateAllTimeAnchor,
    loadOperations,
    loadMoreOperations,
    refreshOperationsView,
    getCurrentOperationItems,
    fillGroupSelect: categoryActions.fillGroupSelect,
    setCategoryKind: categoryActions.setCategoryKind,
    renderCreateGroupPicker: categoryActions.renderCreateGroupPicker,
    renderEditGroupPicker: categoryActions.renderEditGroupPicker,
    handleCreateGroupSearchFocus: categoryActions.handleCreateGroupSearchFocus,
    handleCreateGroupSearchInput: categoryActions.handleCreateGroupSearchInput,
    handleCreateGroupSearchBlur: categoryActions.handleCreateGroupSearchBlur,
    handleCreateGroupSearchKeydown: categoryActions.handleCreateGroupSearchKeydown,
    handleEditGroupSearchFocus: categoryActions.handleEditGroupSearchFocus,
    handleEditGroupSearchInput: categoryActions.handleEditGroupSearchInput,
    handleEditGroupSearchBlur: categoryActions.handleEditGroupSearchBlur,
    handleEditGroupSearchKeydown: categoryActions.handleEditGroupSearchKeydown,
    handleCreateGroupPickerClick: categoryActions.handleCreateGroupPickerClick,
    handleEditGroupPickerClick: categoryActions.handleEditGroupPickerClick,
    handleCreateGroupOutsidePointer: categoryActions.handleCreateGroupOutsidePointer,
    selectCreateGroup: categoryActions.selectCreateGroup,
    renderCategories: categoryActions.renderCategories,
    updateCategoriesBulkUi: categoryActions.updateCategoriesBulkUi,
    loadCategories: categoryActions.loadCategories,
    createCategory: categoryActions.createCategory,
    createGroup: categoryActions.createGroup,
    openEditGroupModal: categoryActions.openEditGroupModal,
    closeEditGroupModal: categoryActions.closeEditGroupModal,
    updateGroup: categoryActions.updateGroup,
    deleteGroupFlow: categoryActions.deleteGroupFlow,
    openEditCategoryModal: categoryActions.openEditCategoryModal,
    closeEditCategoryModal: categoryActions.closeEditCategoryModal,
    updateCategory: categoryActions.updateCategory,
    groupCategoryIds: categoryActions.groupCategoryIds,
    bulkDeleteCategories: categoryActions.bulkDeleteCategories,
    bulkDeleteGroups: categoryActions.bulkDeleteGroups,
    bulkUpdateCategories: categoryActions.bulkUpdateCategories,
    deleteCategoryFlow: categoryActions.deleteCategoryFlow,
    createOperation,
    updateOperation,
    deleteOperationFlow,
    applyFilters,
    applyRealtimeSearch,
    refreshAll,
    logout,
    devLogin,
    bootstrapApp,
  };
})();
