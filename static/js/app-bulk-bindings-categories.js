(() => {
  const { state, el, core } = window.App;

  function getCategoryActions() {
    return window.App.getRuntimeModule?.("category-actions") || {};
  }

  function bindCategoryBulkHandlers() {
    el.deleteAllCategoriesBtn.addEventListener("click", () => {
      if (el.deleteAllCategoriesBtn.disabled) {
        return;
      }
      const visibleCategoryIds = new Set(
        Array.from(el.categoriesBody.querySelectorAll("tr[data-item-type='category'][data-category-id]"))
          .map((row) => Number(row.dataset.categoryId))
          .filter((id) => Number.isFinite(id) && id > 0),
      );
      const visibleGroupIds = new Set(
        Array.from(el.categoriesBody.querySelectorAll("tr[data-item-type='group'][data-group-id]"))
          .map((row) => Number(row.dataset.groupId))
          .filter((id) => Number.isFinite(id) && id > 0),
      );
      const categoryIds = state.categoryTableItems
        .filter((item) => visibleCategoryIds.has(Number(item.id)) && !item.is_system)
        .map((item) => Number(item.id));
      const groupIds = state.categoryGroups
        .filter((group) => visibleGroupIds.has(Number(group.id)))
        .map((group) => Number(group.id));
      const total = categoryIds.length + groupIds.length;
      if (!total) {
        return;
      }
      core.runDestructiveAction({
        confirmMessage: `Удалить все объекты в текущем списке (${total})?`,
        doDelete: async () => {
          const categoryActions = getCategoryActions();
          if (categoryIds.length) {
            await categoryActions.bulkDeleteCategories?.(categoryIds);
          }
          if (groupIds.length && categoryActions.bulkDeleteGroups) {
            await categoryActions.bulkDeleteGroups(groupIds);
          }
        },
        onDeleteError: "Не удалось удалить категории",
      });
    });
  }

  window.App.bulkBindingsCategories = {
    bindCategoryBulkHandlers,
  };
})();
