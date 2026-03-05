(() => {
  const { actions } = window.App;
  const bulkUi = window.App.bulkUi;
  const bulkBindings = window.App.bulkBindings;

  bulkBindings.bindBulkHandlers();

  Object.assign(actions, {
    openBatchCreateModal: bulkUi.openBatchCreateModal,
    closeBatchCreateModal: bulkUi.closeBatchCreateModal,
    openCreateGroupModal: bulkUi.openCreateGroupModal,
    closeCreateGroupModal: bulkUi.closeCreateGroupModal,
    openBulkEditOperationsModal: bulkUi.openBulkEditOperationsModal,
    closeBulkEditOperationsModal: bulkUi.closeBulkEditOperationsModal,
    openBulkEditCategoriesModal: bulkUi.openBulkEditCategoriesModal,
    closeBulkEditCategoriesModal: bulkUi.closeBulkEditCategoriesModal,
    updateOperationsBulkUi: bulkUi.updateOperationsBulkUi,
  });
})();
