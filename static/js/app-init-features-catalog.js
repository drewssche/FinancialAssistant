(() => {
  const { state, el, core, actions } = window.App;

  function bindCatalogFeatureHandlers(getCategoriesObserver, setCategoriesObserver) {
    let categorySearchDebounceId = null;
    let itemCatalogSearchDebounceId = null;

    if (el.itemCatalogSearchQ && actions.loadItemCatalog) {
      el.itemCatalogSearchQ.addEventListener("input", () => {
        if (itemCatalogSearchDebounceId) {
          clearTimeout(itemCatalogSearchDebounceId);
        }
        itemCatalogSearchDebounceId = setTimeout(() => {
          core.runAction({
            errorPrefix: "Ошибка поиска по каталогу позиций",
            action: () => actions.loadItemCatalog(),
          });
        }, 250);
      });
    }
    if (el.itemCatalogSortTabs && actions.setItemCatalogSortPreset) {
      el.itemCatalogSortTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-item-sort]");
        if (!btn) {
          return;
        }
        if (btn.dataset.itemSort === state.itemCatalogSortPreset) {
          return;
        }
        actions.setItemCatalogSortPreset(btn.dataset.itemSort);
      });
    }
    if (el.itemCatalogCollapseAllBtn && actions.collapseAllItemCatalogGroups) {
      el.itemCatalogCollapseAllBtn.addEventListener("click", () => {
        actions.collapseAllItemCatalogGroups();
      });
    }
    if (el.itemCatalogExpandAllBtn && actions.expandAllItemCatalogGroups) {
      el.itemCatalogExpandAllBtn.addEventListener("click", () => {
        actions.expandAllItemCatalogGroups();
      });
    }
    if (el.deleteAllItemTemplatesBtn && actions.deleteAllItemTemplatesFlow) {
      el.deleteAllItemTemplatesBtn.addEventListener("click", () => {
        actions.deleteAllItemTemplatesFlow().catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.itemCatalogBody && actions.handleItemCatalogBodyClick) {
      el.itemCatalogBody.addEventListener("click", (event) => {
        const deleteSourceBtn = event.target.closest("button[data-delete-item-source-name]");
        if (deleteSourceBtn) {
          if (actions.deleteItemSourceFlow) {
            actions.deleteItemSourceFlow(deleteSourceBtn.dataset.deleteItemSourceName || "").catch((err) => core.setStatus(String(err)));
          }
          return;
        }
        const editSourceBtn = event.target.closest("button[data-edit-item-source-name]");
        if (editSourceBtn) {
          if (actions.openEditSourceGroupModal) {
            actions.openEditSourceGroupModal(editSourceBtn.dataset.editItemSourceName || "");
          }
          return;
        }
        const deleteBtn = event.target.closest("button[data-delete-item-template-id]");
        if (deleteBtn) {
          const row = deleteBtn.closest("tr");
          const item = row ? JSON.parse(row.dataset.itemTemplate || "{}") : null;
          if (item?.id && actions.deleteItemTemplateFlow) {
            actions.deleteItemTemplateFlow(item).catch((err) => core.setStatus(String(err)));
          }
          return;
        }
        const editBtn = event.target.closest("button[data-edit-item-template-id]");
        if (editBtn) {
          const row = editBtn.closest("tr");
          const item = row ? JSON.parse(row.dataset.itemTemplate || "{}") : null;
          if (item?.id && actions.openItemTemplateModal) {
            actions.openItemTemplateModal(item);
          }
          return;
        }
        const historyBtn = event.target.closest("button[data-item-template-history-id]");
        if (historyBtn) {
          const row = historyBtn.closest("tr");
          const item = row ? JSON.parse(row.dataset.itemTemplate || "{}") : null;
          if (item?.id && actions.openItemTemplateHistoryModal) {
            actions.openItemTemplateHistoryModal(item).catch((err) => core.setStatus(String(err)));
          }
          return;
        }
        actions.handleItemCatalogBodyClick(event);
      });
    }

    el.categoryKindTabs.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-cat-kind]");
      if (!btn) {
        return;
      }
      state.categoryFilterKind = btn.dataset.catKind;
      core.syncSegmentedActive(el.categoryKindTabs, "cat-kind", state.categoryFilterKind);
      actions.loadCategoriesTable({ reset: true }).catch((err) => core.setStatus(String(err)));
    });

    el.categorySearchQ.addEventListener("input", () => {
      if (categorySearchDebounceId) {
        clearTimeout(categorySearchDebounceId);
      }
      categorySearchDebounceId = setTimeout(() => {
        actions.loadCategoriesTable({ reset: true }).catch((err) => core.setStatus(String(err)));
      }, 250);
    });

    el.createCategoryKind.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-cat-create-kind]");
      if (!btn) {
        return;
      }
      if (actions.setCategoryKind) {
        actions.setCategoryKind("create", btn.dataset.catCreateKind);
      }
    });

    el.editCategoryKindSwitch.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-cat-edit-kind]");
      if (!btn) {
        return;
      }
      actions.setCategoryKind("edit", btn.dataset.catEditKind);
    });

    el.categoriesBody.addEventListener("click", (event) => {
      if (actions.handleCategoriesGroupToggleClick && actions.handleCategoriesGroupToggleClick(event)) {
        return;
      }
      const editGroupBtn = event.target.closest("button[data-edit-group-id]");
      if (editGroupBtn) {
        const id = Number(editGroupBtn.dataset.editGroupId);
        const group = state.categoryGroups.find((item) => item.id === id);
        if (group && actions.openEditGroupModal) {
          actions.openEditGroupModal(group);
        }
        return;
      }
      const deleteGroupBtn = event.target.closest("button[data-delete-group-id]");
      if (deleteGroupBtn) {
        const id = Number(deleteGroupBtn.dataset.deleteGroupId);
        const group = state.categoryGroups.find((item) => item.id === id);
        if (group && actions.deleteGroupFlow) {
          actions.deleteGroupFlow(group).catch((err) => core.setStatus(String(err)));
        }
        return;
      }
      const deleteBtn = event.target.closest("button[data-delete-category-id]");
      if (deleteBtn) {
        const row = deleteBtn.closest("tr");
        const item = row ? JSON.parse(row.dataset.item || "{}") : null;
        if (item?.id) {
          actions.deleteCategoryFlow(item).catch((err) => core.setStatus(String(err)));
        }
        return;
      }
      const editBtn = event.target.closest("button[data-edit-category-id]");
      if (editBtn) {
        const row = editBtn.closest("tr");
        const item = row ? JSON.parse(row.dataset.item || "{}") : null;
        if (item?.id) {
          actions.openEditCategoryModal(item);
        }
      }
    });

    if (el.categoriesCollapseAllBtn && actions.collapseAllCategoryGroups) {
      el.categoriesCollapseAllBtn.addEventListener("click", () => {
        actions.collapseAllCategoryGroups();
      });
    }
    if (el.categoriesExpandAllBtn && actions.expandAllCategoryGroups) {
      el.categoriesExpandAllBtn.addEventListener("click", () => {
        actions.expandAllCategoryGroups();
      });
    }

    if (el.categoriesInfiniteSentinel && "IntersectionObserver" in window) {
      const existingObserver = getCategoriesObserver();
      if (existingObserver) {
        existingObserver.disconnect();
      }
      const observer = new IntersectionObserver(
        (entries) => {
          const entry = entries[0];
          if (!entry?.isIntersecting) {
            return;
          }
          if (state.activeSection !== "categories") {
            return;
          }
          if (!state.categoriesHasMore || state.categoriesLoading) {
            return;
          }
          actions.loadMoreCategoriesTable().catch((err) => core.setStatus(String(err)));
        },
        {
          root: null,
          rootMargin: "240px 0px",
          threshold: 0,
        },
      );
      observer.observe(el.categoriesInfiniteSentinel);
      setCategoriesObserver(observer);
    }
  }

  window.App.initFeatureCatalog = {
    bindCatalogFeatureHandlers,
  };
})();
