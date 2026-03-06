(() => {
  const { state, el, core } = window.App;

  function openBatchCreateModal() {
    el.batchCreateModal.classList.remove("hidden");
  }

  function closeBatchCreateModal() {
    el.batchCreateModal.classList.add("hidden");
  }

  function openCreateGroupModal() {
    el.groupKind.value = "expense";
    core.syncSegmentedActive(el.createGroupKind, "group-create-kind", "expense");
    el.createGroupModal.classList.remove("hidden");
  }

  function closeCreateGroupModal() {
    el.createGroupModal.classList.add("hidden");
  }

  function openBulkEditOperationsModal() {
    el.bulkEditOperationsModal.classList.remove("hidden");
  }

  function closeBulkEditOperationsModal() {
    el.bulkEditOperationsModal.classList.add("hidden");
  }

  function openBulkEditCategoriesModal() {
    el.bulkEditCategoriesModal.classList.remove("hidden");
  }

  function closeBulkEditCategoriesModal() {
    el.bulkEditCategoriesModal.classList.add("hidden");
  }

  function visibleOperationIds() {
    return Array.from(el.operationsBody.querySelectorAll("input[data-select-operation-id]"))
      .map((node) => Number(node.dataset.selectOperationId));
  }

  function visibleCategoryIds() {
    return Array.from(el.categoriesBody.querySelectorAll("input[data-select-category-id]"))
      .filter((node) => !node.disabled)
      .map((node) => Number(node.dataset.selectCategoryId));
  }

  function visibleGroupIds() {
    return Array.from(el.categoriesBody.querySelectorAll("input[data-select-group-id]"))
      .filter((node) => !node.disabled)
      .map((node) => Number(node.dataset.selectGroupId));
  }

  function syncOperationSelectAll() {
    const operationIds = visibleOperationIds();
    const selectedCount = operationIds.filter((id) => state.selectedOperationIds.has(id)).length;
    el.operationsSelectAll.checked = operationIds.length > 0 && selectedCount === operationIds.length;
    el.operationsSelectAll.indeterminate = selectedCount > 0 && selectedCount < operationIds.length;
  }

  function syncCategorySelectAll() {
    const categoryIds = visibleCategoryIds();
    const groupIds = visibleGroupIds();
    const selectedCategoryCount = categoryIds.filter((id) => state.selectedCategoryIds.has(id)).length;
    const selectedGroupCount = groupIds.filter((id) => state.selectedGroupIds.has(id)).length;
    const total = categoryIds.length + groupIds.length;
    const selected = selectedCategoryCount + selectedGroupCount;
    el.categoriesSelectAll.checked = total > 0 && selected === total;
    el.categoriesSelectAll.indeterminate = selected > 0 && selected < total;
  }

  function syncGroupCheckboxState(groupId) {
    const actions = window.App.actions;
    const groupCheckbox = el.categoriesBody.querySelector(`input[data-select-group-id="${groupId}"]`);
    if (!groupCheckbox) {
      return;
    }
    const categoryIds = actions.groupCategoryIds ? actions.groupCategoryIds(groupId) : [];
    const selectedCount = categoryIds.filter((id) => state.selectedCategoryIds.has(id)).length;
    groupCheckbox.checked = false;
    groupCheckbox.indeterminate = selectedCount > 0;
  }

  function updateOperationsBulkUi() {
    const operationIds = visibleOperationIds();
    const totalCount = operationIds.length;
    const selectedCount = operationIds.filter((id) => state.selectedOperationIds.has(id)).length;
    el.operationsSelectedCount.textContent =
      selectedCount > 0 ? `Выбрано: ${selectedCount} из ${totalCount}` : `Всего: ${totalCount}`;
    el.bulkEditOperationsBtn.classList.toggle("hidden-action", selectedCount === 0);
    el.bulkDeleteOperationsBtn.classList.toggle("hidden-action", selectedCount === 0);
    syncOperationSelectAll();
  }

  function fillBulkOperationCategorySelect(kind = "") {
    el.bulkOpCategory.innerHTML = '<option value="">Категория (не менять)</option>';
    const filtered = state.categories.filter((item) => !kind || item.kind === kind);
    for (const item of filtered) {
      const option = document.createElement("option");
      option.value = String(item.id);
      option.textContent = item.name;
      el.bulkOpCategory.appendChild(option);
    }
  }

  window.App.bulkUi = {
    openBatchCreateModal,
    closeBatchCreateModal,
    openCreateGroupModal,
    closeCreateGroupModal,
    openBulkEditOperationsModal,
    closeBulkEditOperationsModal,
    openBulkEditCategoriesModal,
    closeBulkEditCategoriesModal,
    visibleOperationIds,
    visibleCategoryIds,
    visibleGroupIds,
    syncOperationSelectAll,
    syncCategorySelectAll,
    syncGroupCheckboxState,
    updateOperationsBulkUi,
    fillBulkOperationCategorySelect,
  };
})();
