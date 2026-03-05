(() => {
  const { state, el, core } = window.App;
  const categoryActions = window.App.actions;
  const dashboardFeatures = window.App.featureDashboard;
  const sessionFeatures = window.App.featureSession;
  const operationModal = window.App.operationModal;
  let operationsRawItems = [];
  const getCategoryMetaById = operationModal.getCategoryMetaById;
  const trackCategoryUsage = operationModal.trackCategoryUsage;
  const getCreateFormPreviewItem = operationModal.getCreateFormPreviewItem;
  const updateCreatePreview = operationModal.updateCreatePreview;
  const updateEditPreview = operationModal.updateEditPreview;
  const renderCreateCategoryPicker = operationModal.renderCreateCategoryPicker;
  const handleCreateCategoryPickerClick = operationModal.handleCreateCategoryPickerClick;
  const onCategoryCreated = operationModal.onCategoryCreated;
  const selectCreateCategory = operationModal.selectCreateCategory;
  const setOperationKind = operationModal.setOperationKind;
  const openCreateModal = operationModal.openCreateModal;
  const closeCreateModal = operationModal.closeCreateModal;
  const openEditModal = operationModal.openEditModal;
  const closeEditModal = operationModal.closeEditModal;
  const openPeriodCustomModal = operationModal.openPeriodCustomModal;
  const closePeriodCustomModal = operationModal.closePeriodCustomModal;
  const loadMe = sessionFeatures.loadMe;
  const loadPreferences = sessionFeatures.loadPreferences;
  const savePreferences = sessionFeatures.savePreferences;
  const saveSettings = sessionFeatures.saveSettings;
  const logout = sessionFeatures.logout;
  const devLogin = sessionFeatures.devLogin;
  const bootstrapApp = sessionFeatures.bootstrapApp;
  const loadDashboard = dashboardFeatures.loadDashboard;
  const loadDashboardOperations = dashboardFeatures.loadDashboardOperations;

  function buildOperationsQuery() {
    const { dateFrom, dateTo } = core.getPeriodBounds(state.period);
    el.operationsPeriodLabel.textContent = core.formatPeriodLabel(dateFrom, dateTo);
    const params = new URLSearchParams({
      page: String(state.page),
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
    const totalPages = Math.max(1, Math.ceil(state.total / state.pageSize));
    el.pageInfo.textContent = `Страница ${state.page} из ${totalPages} (${state.total})`;
    el.prevPageBtn.disabled = state.page <= 1;
    el.nextPageBtn.disabled = state.page >= totalPages;
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

  async function loadOperations() {
    const data = await core.requestJson(`/api/v1/operations?${buildOperationsQuery().toString()}`, {
      headers: core.authHeaders(),
    });
    state.total = data.total;
    operationsRawItems = data.items;
    renderOperations(operationsRawItems);
    renderPagination();
  }

  async function createOperation(event) {
    event.preventDefault();
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
    trackCategoryUsage(payload.category_id);

    document.getElementById("opAmount").value = "";
    document.getElementById("opNote").value = "";
    el.opCategory.value = "";
    el.opCategorySearch.value = "";
    state.createModalCategoryExpanded = false;
    renderCreateCategoryPicker();
    updateCreatePreview();

    state.page = 1;
    closeCreateModal();
    await Promise.all([loadDashboard(), loadOperations(), loadDashboardOperations()]);
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
    trackCategoryUsage(payload.category_id);

    closeEditModal();
    await Promise.all([loadDashboard(), loadOperations(), loadDashboardOperations()]);
  }

  async function deleteOperationFlow(item) {
    core.runDestructiveAction({
      confirmMessage: "Удалить операцию?",
      doDelete: async () => {
        await core.requestJson(`/api/v1/operations/${item.id}`, {
          method: "DELETE",
          headers: core.authHeaders(),
        });
      },
      onAfterDelete: async () => {
        const totalPages = Math.max(1, Math.ceil((state.total - 1) / state.pageSize));
        if (state.page > totalPages) {
          state.page = totalPages;
        }
        await Promise.all([loadDashboard(), loadOperations(), loadDashboardOperations()]);
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
        await Promise.all([loadDashboard(), loadOperations(), loadDashboardOperations()]);
        return "Операция восстановлена";
      },
      onDeleteError: "Не удалось удалить операцию",
    });
  }

  async function applyFilters() {
    state.page = 1;
    await savePreferences();
    await loadOperations();
  }

  async function applyRealtimeSearch() {
    renderOperations(operationsRawItems);
    await savePreferences();
  }

  async function refreshAll() {
    const results = await Promise.allSettled([
      loadDashboard(),
      loadOperations(),
      loadDashboardOperations(),
      categoryActions.loadCategories(),
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
    updateEditPreview,
    renderCreateCategoryPicker,
    handleCreateCategoryPickerClick,
    onCategoryCreated,
    selectCreateCategory,
    setOperationKind,
    openCreateModal,
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
    applySectionUi: previousActions.applySectionUi,
    switchSection: previousActions.switchSection,
    renderTodayLabel: previousActions.renderTodayLabel,
    loadDashboard,
    loadDashboardOperations,
    loadOperations,
    refreshOperationsView,
    getCurrentOperationItems,
    fillGroupSelect: categoryActions.fillGroupSelect,
    setCategoryKind: categoryActions.setCategoryKind,
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
