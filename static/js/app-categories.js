(() => {
  function getCategoryUi() {
    return window.App.getRuntimeModule?.("category-ui");
  }

  function getCategoryData() {
    return window.App.categoryData;
  }

  function getActionFacade() {
    return window.App.actions;
  }

  const categoryUi = getCategoryUi();
  const categoryData = getCategoryData();
  const publicCategoryActions = {
    setupCategoryIconPickers: categoryUi.setupCategoryIconPickers,
    closeIconPopovers: categoryUi.closeIconPopovers,
    openCreateCategoryModal: categoryUi.openCreateCategoryModal,
    closeCreateCategoryModal: categoryUi.closeCreateCategoryModal,
    fillGroupSelect: categoryUi.fillGroupSelect,
    setCategoryKind: categoryUi.setCategoryKind,
    populateCategorySelect: categoryUi.populateCategorySelect,
    renderCreateGroupPicker: categoryUi.renderCreateGroupPicker,
    renderEditGroupPicker: categoryUi.renderEditGroupPicker,
    handleCreateGroupSearchFocus: categoryUi.handleCreateGroupSearchFocus,
    handleCreateGroupSearchInput: categoryUi.handleCreateGroupSearchInput,
    handleCreateGroupSearchBlur: categoryUi.handleCreateGroupSearchBlur,
    handleCreateGroupSearchKeydown: categoryUi.handleCreateGroupSearchKeydown,
    handleEditGroupSearchFocus: categoryUi.handleEditGroupSearchFocus,
    handleEditGroupSearchInput: categoryUi.handleEditGroupSearchInput,
    handleEditGroupSearchBlur: categoryUi.handleEditGroupSearchBlur,
    handleEditGroupSearchKeydown: categoryUi.handleEditGroupSearchKeydown,
    handleCreateGroupPickerClick: categoryUi.handleCreateGroupPickerClick,
    handleEditGroupPickerClick: categoryUi.handleEditGroupPickerClick,
    handleCreateGroupOutsidePointer: categoryUi.handleCreateGroupOutsidePointer,
    selectCreateGroup: categoryUi.selectCreateGroup,
    selectEditGroup: categoryUi.selectEditGroup,
    groupCategoryIds: categoryUi.groupCategoryIds,
    updateCategoriesBulkUi: categoryUi.updateCategoriesBulkUi,
    renderCategories: categoryUi.renderCategories,
    handleCategoriesGroupToggleClick: categoryUi.handleCategoriesGroupToggleClick,
    collapseAllCategoryGroups: categoryUi.collapseAllCategoryGroups,
    expandAllCategoryGroups: categoryUi.expandAllCategoryGroups,

    loadCategoryGroups: categoryData.loadCategoryGroups,
    loadCategoryCatalog: categoryData.loadCategoryCatalog,
    loadCategoriesTable: categoryData.loadCategoriesTable,
    loadMoreCategoriesTable: categoryData.loadMoreCategoriesTable,
    loadCategories: categoryData.loadCategories,
    createCategory: categoryData.createCategory,
    updateCategory: categoryData.updateCategory,
    createGroup: categoryData.createGroup,
    updateGroup: categoryData.updateGroup,
    deleteGroupFlow: categoryData.deleteGroupFlow,
    deleteCategoryFlow: categoryData.deleteCategoryFlow,
    bulkDeleteCategories: categoryData.bulkDeleteCategories,
    bulkDeleteGroups: categoryData.bulkDeleteGroups,

    openEditCategoryModal: categoryUi.openEditCategoryModal,
    closeEditCategoryModal: categoryUi.closeEditCategoryModal,
    openEditGroupModal: categoryUi.openEditGroupModal,
    closeEditGroupModal: categoryUi.closeEditGroupModal,
  };

  window.App.registerRuntimeModule?.("category-actions", publicCategoryActions);
})();
