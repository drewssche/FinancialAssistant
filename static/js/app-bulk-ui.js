(() => {
  const { state, el, core } = window.App;

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
    if (!el.operationsSelectAll) {
      return;
    }
    const operationIds = visibleOperationIds();
    const selectedCount = operationIds.filter((id) => state.selectedOperationIds.has(id)).length;
    el.operationsSelectAll.checked = operationIds.length > 0 && selectedCount === operationIds.length;
    el.operationsSelectAll.indeterminate = selectedCount > 0 && selectedCount < operationIds.length;
  }

  function updateOperationsBulkUi() {
    const operationIds = visibleOperationIds();
    const totalCount = Number(state.total || 0);
    const visibleCount = operationIds.length;
    const selectedCount = operationIds.filter((id) => state.selectedOperationIds.has(id)).length;
    if (el.operationsSelectedCount) {
      el.operationsSelectedCount.textContent =
        selectedCount > 0 ? `Выбрано: ${selectedCount} из ${visibleCount}` : `Всего: ${totalCount}`;
    }
    el.bulkEditOperationsBtn?.classList.toggle("hidden-action", selectedCount === 0);
    el.bulkDeleteOperationsBtn?.classList.toggle("hidden-action", selectedCount === 0);
    syncOperationSelectAll();
  }

  function fillBulkOperationCategorySelect(kind = "") {
    el.bulkOpCategory.innerHTML = '<option value="">Категория (не менять)</option>';
    const filtered = state.categories.filter((item) => !kind || item.kind === kind);
    for (const item of filtered) {
      el.bulkOpCategory.appendChild(core.createCategoryOption(item));
    }
  }

  const api = {
    openCreateGroupModal,
    closeCreateGroupModal,
    openBulkEditOperationsModal,
    closeBulkEditOperationsModal,
    visibleOperationIds,
    syncOperationSelectAll,
    updateOperationsBulkUi,
    fillBulkOperationCategorySelect,
  };

  window.App.registerRuntimeModule?.("bulk-ui", api);
})();
