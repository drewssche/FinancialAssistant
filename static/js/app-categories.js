(() => {
  const categoryUi = window.App.categoryUi;
  const categoryData = window.App.categoryData;

  Object.assign(window.App.actions, {
    setupCategoryIconPickers: categoryUi.setupCategoryIconPickers,
    closeIconPopovers: categoryUi.closeIconPopovers,
    openCreateCategoryModal: categoryUi.openCreateCategoryModal,
    closeCreateCategoryModal: categoryUi.closeCreateCategoryModal,
    fillGroupSelect: categoryUi.fillGroupSelect,
    setCategoryKind: categoryUi.setCategoryKind,
    populateCategorySelect: categoryUi.populateCategorySelect,
    groupCategoryIds: categoryUi.groupCategoryIds,
    updateCategoriesBulkUi: categoryUi.updateCategoriesBulkUi,
    renderCategories: categoryUi.renderCategories,

    loadCategoryGroups: categoryData.loadCategoryGroups,
    loadCategories: categoryData.loadCategories,
    createCategory: categoryData.createCategory,
    updateCategory: categoryData.updateCategory,
    createGroup: categoryData.createGroup,
    updateGroup: categoryData.updateGroup,
    deleteGroupFlow: categoryData.deleteGroupFlow,
    deleteCategoryFlow: categoryData.deleteCategoryFlow,
    bulkDeleteCategories: categoryData.bulkDeleteCategories,
    bulkDeleteGroups: categoryData.bulkDeleteGroups,
    bulkUpdateCategories: categoryData.bulkUpdateCategories,

    openEditCategoryModal: categoryUi.openEditCategoryModal,
    closeEditCategoryModal: categoryUi.closeEditCategoryModal,
    openEditGroupModal: categoryUi.openEditGroupModal,
    closeEditGroupModal: categoryUi.closeEditGroupModal,
  });
})();
