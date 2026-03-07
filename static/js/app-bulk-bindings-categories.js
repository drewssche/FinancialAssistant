(() => {
  const { el, core, actions } = window.App;
  const bulkUi = window.App.bulkUi;

  function bindCategoryBulkHandlers() {
    el.closeCreateGroupModalBtn.addEventListener("click", bulkUi.closeCreateGroupModal);
    el.createGroupModal.addEventListener("click", (event) => {
      if (event.target === el.createGroupModal) {
        bulkUi.closeCreateGroupModal();
      }
    });
    el.groupModalForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitCreateGroupBtn"),
        pendingText: "Создание...",
        successMessage: "Группа создана",
        errorPrefix: "Ошибка создания группы",
        action: () => actions.createGroup(event),
      });
    });
    el.createGroupKind.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-group-create-kind]");
      if (!btn) {
        return;
      }
      el.groupKind.value = btn.dataset.groupCreateKind;
      core.syncSegmentedActive(el.createGroupKind, "group-create-kind", el.groupKind.value);
    });

    el.deleteAllCategoriesBtn.addEventListener("click", () => {
      const categoryIds = Array.from(el.categoriesBody.querySelectorAll("tr[data-item-type='category'][data-category-id]"))
        .map((row) => Number(row.dataset.categoryId))
        .filter((id) => Number.isFinite(id) && id > 0);
      const groupIds = Array.from(el.categoriesBody.querySelectorAll("tr[data-item-type='group'][data-group-id]"))
        .map((row) => Number(row.dataset.groupId))
        .filter((id) => Number.isFinite(id) && id > 0);
      const total = categoryIds.length + groupIds.length;
      core.runDestructiveAction({
        confirmMessage: `Удалить все объекты в текущем списке (${total})?`,
        doDelete: async () => {
          if (categoryIds.length) {
            await actions.bulkDeleteCategories(categoryIds);
          }
          if (groupIds.length && actions.bulkDeleteGroups) {
            await actions.bulkDeleteGroups(groupIds);
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
