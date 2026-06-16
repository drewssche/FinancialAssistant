(() => {
  const { actions } = window.App;
  const bulkUi = window.App.getRuntimeModule?.("bulk-ui");
  const categoryActions = window.App.getRuntimeModule?.("category-actions");
  const bulkBindings = window.App.bulkBindings;

  bulkBindings.bindBulkHandlers();

  Object.assign(actions, {
    openBatchCreateModal: bulkUi.openBatchCreateModal,
    closeBatchCreateModal: bulkUi.closeBatchCreateModal,
    openBatchCategoryModal: bulkUi.openBatchCategoryModal,
    closeBatchCategoryModal: bulkUi.closeBatchCategoryModal,
    openBatchItemTemplateModal: bulkUi.openBatchItemTemplateModal,
    closeBatchItemTemplateModal: bulkUi.closeBatchItemTemplateModal,
    openCreateGroupModal: categoryActions.openCreateGroupModal,
    closeCreateGroupModal: categoryActions.closeCreateGroupModal,
    openBulkEditOperationsModal: bulkUi.openBulkEditOperationsModal,
    closeBulkEditOperationsModal: bulkUi.closeBulkEditOperationsModal,
    updateOperationsBulkUi: bulkUi.updateOperationsBulkUi,
  });
})();
