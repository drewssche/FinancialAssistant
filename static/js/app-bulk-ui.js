(() => {
  const { state, el, core } = window.App;

  function resetBatchCreateState() {
    state.batchOperationPlan = null;
    if (el.batchCreateForm) {
      el.batchCreateForm.reset();
    }
    if (el.batchCreateInput) {
      el.batchCreateInput.value = "";
    }
    if (el.batchCreateFeedback) {
      el.batchCreateFeedback.textContent = "";
      el.batchCreateFeedback.classList.add("hidden");
    }
    if (el.batchCreatePreview) {
      el.batchCreatePreview.classList.add("hidden");
    }
    if (el.batchCreatePreviewBody) {
      el.batchCreatePreviewBody.innerHTML = "";
    }
    if (el.confirmBatchCreateBtn) {
      el.confirmBatchCreateBtn.textContent = "Импортировать 0 строк";
      el.confirmBatchCreateBtn.disabled = true;
      el.confirmBatchCreateBtn.classList.add("hidden");
    }
  }

  function resetBatchCategoryState() {
    state.batchCategoryPlan = null;
    if (el.batchCategoryForm) {
      el.batchCategoryForm.reset();
    }
    if (el.batchCategoryMode) {
      el.batchCategoryMode.value = "categories";
    }
    if (el.batchCategoryModeTabs) {
      core.syncSegmentedActive(el.batchCategoryModeTabs, "batch-category-mode", "categories");
    }
    if (el.batchCategoryHint) {
      el.batchCategoryHint.innerHTML = 'Категории: <code>тип;название;группа</code>. Пустая группа = «Без группы».';
    }
    if (el.batchCategoryInput) {
      el.batchCategoryInput.value = "";
    }
    if (el.batchCategoryFeedback) {
      el.batchCategoryFeedback.textContent = "";
      el.batchCategoryFeedback.classList.add("hidden");
    }
    if (el.batchCategoryPreview) {
      el.batchCategoryPreview.classList.add("hidden");
    }
    if (el.batchCategoryPreviewBody) {
      el.batchCategoryPreviewBody.innerHTML = "";
    }
    if (el.confirmBatchCategoryBtn) {
      el.confirmBatchCategoryBtn.textContent = "Импортировать 0 строк";
      el.confirmBatchCategoryBtn.disabled = true;
      el.confirmBatchCategoryBtn.classList.add("hidden");
    }
  }

  function resetBatchItemTemplateState() {
    state.batchItemTemplatePlan = null;
    if (el.batchItemTemplateForm) {
      el.batchItemTemplateForm.reset();
    }
    if (el.batchItemTemplateInput) {
      el.batchItemTemplateInput.value = "";
    }
    if (el.batchItemTemplateFeedback) {
      el.batchItemTemplateFeedback.textContent = "";
      el.batchItemTemplateFeedback.classList.add("hidden");
    }
    if (el.batchItemTemplatePreview) {
      el.batchItemTemplatePreview.classList.add("hidden");
    }
    if (el.batchItemTemplatePreviewBody) {
      el.batchItemTemplatePreviewBody.innerHTML = "";
    }
    if (el.confirmBatchItemTemplateBtn) {
      el.confirmBatchItemTemplateBtn.textContent = "Импортировать 0 строк";
      el.confirmBatchItemTemplateBtn.disabled = true;
      el.confirmBatchItemTemplateBtn.classList.add("hidden");
    }
  }

  function openBatchCreateModal() {
    resetBatchCreateState();
    el.batchCreateModal.classList.remove("hidden");
  }

  function closeBatchCreateModal() {
    el.batchCreateModal.classList.add("hidden");
  }

  function openBatchCategoryModal() {
    resetBatchCategoryState();
    el.batchCategoryModal.classList.remove("hidden");
  }

  function closeBatchCategoryModal() {
    el.batchCategoryModal.classList.add("hidden");
  }

  function openBatchItemTemplateModal() {
    resetBatchItemTemplateState();
    el.batchItemTemplateModal.classList.remove("hidden");
  }

  function closeBatchItemTemplateModal() {
    el.batchItemTemplateModal.classList.add("hidden");
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
    const totalCount = Number(state.total || 0);
    const visibleCount = operationIds.length;
    const selectedCount = operationIds.filter((id) => state.selectedOperationIds.has(id)).length;
    el.operationsSelectedCount.textContent =
      selectedCount > 0 ? `Выбрано: ${selectedCount} из ${visibleCount}` : `Всего: ${totalCount}`;
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

  const api = {
    openBatchCreateModal,
    closeBatchCreateModal,
    openBatchCategoryModal,
    closeBatchCategoryModal,
    openBatchItemTemplateModal,
    closeBatchItemTemplateModal,
    openCreateGroupModal,
    closeCreateGroupModal,
    openBulkEditOperationsModal,
    closeBulkEditOperationsModal,
    visibleOperationIds,
    syncOperationSelectAll,
    updateOperationsBulkUi,
    fillBulkOperationCategorySelect,
    resetBatchCreateState,
    resetBatchCategoryState,
    resetBatchItemTemplateState,
  };

  window.App.registerRuntimeModule?.("bulk-ui", api);
})();
