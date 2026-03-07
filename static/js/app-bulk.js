(() => {
  const { actions } = window.App;
  const bulkUi = window.App.bulkUi;
  const bulkBindings = window.App.bulkBindings;

  bulkBindings.bindBulkHandlers();

  Object.assign(actions, {
    openBatchCreateModal: bulkUi.openBatchCreateModal,
    closeBatchCreateModal: bulkUi.closeBatchCreateModal,
    openBatchCategoryModal: bulkUi.openBatchCategoryModal,
    closeBatchCategoryModal: bulkUi.closeBatchCategoryModal,
    openBatchItemTemplateModal: bulkUi.openBatchItemTemplateModal,
    closeBatchItemTemplateModal: bulkUi.closeBatchItemTemplateModal,
    openCreateGroupModal: bulkUi.openCreateGroupModal,
    closeCreateGroupModal: bulkUi.closeCreateGroupModal,
    openBulkEditOperationsModal: bulkUi.openBulkEditOperationsModal,
    closeBulkEditOperationsModal: bulkUi.closeBulkEditOperationsModal,
    updateOperationsBulkUi: bulkUi.updateOperationsBulkUi,
  });
})();
