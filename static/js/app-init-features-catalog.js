(() => {
  const { state, el, core } = window.App;

  function getActions() {
    return window.App.actions || {};
  }

  function getCategoryActions() {
    return window.App.getRuntimeModule?.("category-actions") || {};
  }

  function getPickerUtils() {
    return window.App.getRuntimeModule?.("picker-utils");
  }

  function getCategoriesUiCoordinator() {
    return window.App.getRuntimeModule?.("categories-ui-coordinator");
  }

  function getCategoriesSectionCoordinator() {
    return window.App.getRuntimeModule?.("categories-section-coordinator");
  }

  function getItemCatalogUiCoordinator() {
    return window.App.getRuntimeModule?.("item-catalog-ui-coordinator");
  }

  function getItemCatalogSectionCoordinator() {
    return window.App.getRuntimeModule?.("item-catalog-section-coordinator");
  }

  function bindCatalogFeatureHandlers(getCategoriesObserver, setCategoriesObserver) {
    const actions = getActions();
    const categoryActions = getCategoryActions();
    const pickerUtils = getPickerUtils();
    const categoriesUiCoordinator = getCategoriesUiCoordinator();
    const categoriesSectionCoordinator = getCategoriesSectionCoordinator();
    const itemCatalogUiCoordinator = getItemCatalogUiCoordinator();
    const itemCatalogSectionCoordinator = getItemCatalogSectionCoordinator();

    itemCatalogSectionCoordinator?.bindItemCatalogSearch?.({
      el,
      core,
      loadItemCatalog: actions.loadItemCatalog,
    });
    itemCatalogSectionCoordinator?.bindItemCatalogSortTabs?.({
      el,
      state,
      setItemCatalogSortPresetAction: actions.setItemCatalogSortPreset,
    });
    itemCatalogSectionCoordinator?.bindItemCatalogCollapseExpand?.({
      el,
      collapseAllItemCatalogGroupsAction: actions.collapseAllItemCatalogGroups,
      expandAllItemCatalogGroupsAction: actions.expandAllItemCatalogGroups,
    });
    if (el.deleteAllItemTemplatesBtn && actions.deleteAllItemTemplatesFlow) {
      el.deleteAllItemTemplatesBtn.addEventListener("click", () => {
        actions.deleteAllItemTemplatesFlow().catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.itemCatalogBody && actions.handleItemCatalogBodyClick) {
      el.itemCatalogBody.addEventListener("click", (event) => {
        itemCatalogUiCoordinator?.handleItemCatalogBodyClick?.({
          event,
          pickerUtils,
          handleItemCatalogBodyClickAction: actions.handleItemCatalogBodyClick,
          deleteItemSourceFlow: actions.deleteItemSourceFlow,
          openEditSourceGroupModalAction: actions.openEditSourceGroupModal,
          deleteItemTemplateFlow: actions.deleteItemTemplateFlow,
          openItemTemplateModalAction: actions.openItemTemplateModal,
          openItemTemplateHistoryModalAction: actions.openItemTemplateHistoryModal,
          setStatus: (message) => core.setStatus(message),
        });
      });
    }

    categoriesSectionCoordinator?.bindCategoryKindTabs?.({
      el,
      state,
      core,
      loadCategoriesTable: categoryActions.loadCategoriesTable,
      setStatus: (message) => core.setStatus(message),
    });

    categoriesSectionCoordinator?.bindCategorySearch?.({
      el,
      loadCategoriesTable: categoryActions.loadCategoriesTable,
      setStatus: (message) => core.setStatus(message),
    });

    el.createCategoryKind.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-cat-create-kind]");
      if (!btn) {
        return;
      }
      if (categoryActions.setCategoryKind) {
        categoryActions.setCategoryKind("create", btn.dataset.catCreateKind);
      }
    });

    el.editCategoryKindSwitch.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-cat-edit-kind]");
      if (!btn) {
        return;
      }
      categoryActions.setCategoryKind("edit", btn.dataset.catEditKind);
    });

    el.categoriesBody.addEventListener("click", (event) => {
      categoriesUiCoordinator?.handleCategoriesBodyClick?.({
        event,
        state,
        pickerUtils,
        handleGroupToggleClick: categoryActions.handleCategoriesGroupToggleClick,
        openEditGroupModalAction: categoryActions.openEditGroupModal,
        deleteGroupFlow: (group) => categoryActions.deleteGroupFlow?.(group).catch((err) => core.setStatus(String(err))),
        deleteCategoryFlow: (item) => categoryActions.deleteCategoryFlow?.(item).catch((err) => core.setStatus(String(err))),
        openEditCategoryModalAction: categoryActions.openEditCategoryModal,
      });
    });

    categoriesSectionCoordinator?.bindCategoryCollapseExpand?.({
      el,
      collapseAllCategoryGroups: categoryActions.collapseAllCategoryGroups,
      expandAllCategoryGroups: categoryActions.expandAllCategoryGroups,
    });

    categoriesSectionCoordinator?.bindCategoriesInfiniteObserver?.({
      el,
      state,
      getCategoriesObserver,
      setCategoriesObserver,
      loadMoreCategoriesTable: categoryActions.loadMoreCategoriesTable,
      setStatus: (message) => core.setStatus(message),
    });
  }

  const api = {
    bindCatalogFeatureHandlers,
  };

  window.App.initFeatureCatalog = api;
  window.App.registerFeatureInitModule?.("catalog", api);
})();
