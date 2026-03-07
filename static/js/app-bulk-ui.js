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

  function visibleOperationIds() {
    return Array.from(el.operationsBody.querySelectorAll("input[data-select-operation-id]"))
      .map((node) => Number(node.dataset.selectOperationId));
  }

  function syncOperationSelectAll() {
    const operationIds = visibleOperationIds();
    const selectedCount = operationIds.filter((id) => state.selectedOperationIds.has(id)).length;
    el.operationsSelectAll.checked = operationIds.length > 0 && selectedCount === operationIds.length;
    el.operationsSelectAll.indeterminate = selectedCount > 0 && selectedCount < operationIds.length;
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
    visibleOperationIds,
    syncOperationSelectAll,
    updateOperationsBulkUi,
    fillBulkOperationCategorySelect,
  };
})();
