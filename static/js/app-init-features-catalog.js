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
    const itemCatalogFeature = window.App.getRuntimeModule?.("item-catalog") || {};
    const itemBrandsFeature = window.App.getRuntimeModule?.("item-brands") || {};

    itemBrandsFeature.bind?.();
    el.itemCatalogViewTabs?.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-item-catalog-view]");
      if (button) {
        actions.setItemCatalogView?.(button.dataset.itemCatalogView);
      }
    });
    actions.setItemCatalogView?.(state.itemCatalogView || "positions");

    if (el.itemTemplateBrandSearch) {
      el.itemTemplateBrandSearch.addEventListener("focus", () => itemCatalogFeature.handleItemTemplateBrandSearchFocus?.());
      el.itemTemplateBrandSearch.addEventListener("click", () => itemCatalogFeature.handleItemTemplateBrandSearchFocus?.());
      el.itemTemplateBrandSearch.addEventListener("input", () => itemCatalogFeature.handleItemTemplateBrandSearchInput?.());
      el.itemTemplateBrandSearch.addEventListener("keydown", (event) => itemCatalogFeature.handleItemTemplateBrandSearchKeydown?.(event));
      el.itemTemplateBrandSearch.addEventListener("focusout", (event) => itemCatalogFeature.handleItemTemplateBrandSearchFocusOut?.(event));
    }
    el.itemTemplateBrandAll?.addEventListener("click", (event) => itemCatalogFeature.handleItemTemplateBrandPickerClick?.(event));

    el.itemTemplateHistoryBtn?.addEventListener("click", () => {
      const itemId = Number(el.itemTemplateHistoryBtn.dataset.itemTemplateHistoryId || 0);
      const item = (state.itemCatalogItems || []).find((row) => Number(row?.id || 0) === itemId);
      if (item) {
        actions.openItemTemplateHistoryModal?.(item).catch((err) => core.setStatus(String(err)));
      }
    });
    el.itemTemplateHistoryBody?.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-delete-item-template-price-id]");
      if (!button) {
        return;
      }
      actions.deleteItemTemplatePriceFlow?.(
        Number(button.dataset.itemTemplateId || 0),
        Number(button.dataset.deleteItemTemplatePriceId || 0),
      );
    });
    el.sourceGroupCreateItemBtn?.addEventListener("click", () => {
      const sourceName = String(el.sourceGroupCreateItemBtn.dataset.createItemTemplateSourceName || "").trim();
      if (!sourceName) {
        return;
      }
      actions.closeSourceGroupModal?.();
      actions.openItemTemplateModal?.({ shop_name: sourceName });
    });
    el.editGroupCreateCategoryBtn?.addEventListener("click", () => {
      const groupId = Number(el.editGroupCreateCategoryBtn.dataset.createCategoryGroupId || 0);
      const kind = String(el.editGroupCreateCategoryBtn.dataset.createCategoryKind || "expense");
      if (!groupId) {
        return;
      }
      categoryActions.closeEditGroupModal?.();
      categoryActions.openCreateCategoryModal?.({ groupId, kind });
    });

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
          state,
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
    document.addEventListener("click", (event) => {
      if (!event.target.closest(".mobile-card-actions-popover[data-mobile-card-menu^=\"item-\"], .table-kebab-popover[data-table-menu^=\"item-\"]")) {
        return;
      }
      itemCatalogUiCoordinator?.handleItemCatalogBodyClick?.({
        event,
        state,
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
        openCreateCategoryModalAction: categoryActions.openCreateCategoryModal,
        openEditGroupModalAction: categoryActions.openEditGroupModal,
        deleteGroupFlow: (group) => categoryActions.deleteGroupFlow?.(group).catch((err) => core.setStatus(String(err))),
        deleteCategoryFlow: (item) => categoryActions.deleteCategoryFlow?.(item).catch((err) => core.setStatus(String(err))),
        openEditCategoryModalAction: categoryActions.openEditCategoryModal,
      });
    });
    document.addEventListener("click", (event) => {
      if (!event.target.closest(".mobile-card-actions-popover[data-mobile-card-menu^=\"category-\"], .table-kebab-popover[data-table-menu^=\"category-\"]")) {
        return;
      }
      categoriesUiCoordinator?.handleCategoriesBodyClick?.({
        event,
        state,
        pickerUtils,
        handleGroupToggleClick: categoryActions.handleCategoriesGroupToggleClick,
        openCreateCategoryModalAction: categoryActions.openCreateCategoryModal,
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
