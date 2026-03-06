(() => {
  const { state, el, core, actions } = window.App;
  const bulkUi = window.App.bulkUi;

  async function bulkUpdateCategories(event) {
    event.preventDefault();
    const ids = Array.from(state.selectedCategoryIds);
    if (!ids.length) {
      return;
    }
    await actions.bulkUpdateCategories(ids, el.bulkCategoryGroup.value);
    bulkUi.closeBulkEditCategoriesModal();
  }

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

    el.categoriesBody.addEventListener("change", (event) => {
      const groupCheckbox = event.target.closest("input[data-select-group-id]");
      if (groupCheckbox) {
        const groupId = Number(groupCheckbox.dataset.selectGroupId);
        const ids = actions.groupCategoryIds ? actions.groupCategoryIds(groupId) : [];
        if (groupCheckbox.checked) {
          state.selectedGroupIds.add(groupId);
          for (const id of ids) {
            state.selectedCategoryIds.add(id);
          }
        } else {
          state.selectedGroupIds.delete(groupId);
          for (const id of ids) {
            state.selectedCategoryIds.delete(id);
          }
        }
        const row = groupCheckbox.closest("tr");
        if (row) {
          row.classList.toggle("row-selected", groupCheckbox.checked);
        }
        for (const id of ids) {
          const categoryCheckbox = el.categoriesBody.querySelector(`input[data-select-category-id="${id}"]`);
          if (categoryCheckbox && !categoryCheckbox.disabled) {
            categoryCheckbox.checked = groupCheckbox.checked;
            const categoryRow = categoryCheckbox.closest("tr");
            if (categoryRow) {
              categoryRow.classList.toggle("row-selected", categoryCheckbox.checked);
            }
          }
        }
        actions.updateCategoriesBulkUi();
        bulkUi.syncCategorySelectAll();
        return;
      }

      const checkbox = event.target.closest("input[data-select-category-id]");
      if (!checkbox) {
        return;
      }
      const id = Number(checkbox.dataset.selectCategoryId);
      if (checkbox.checked) {
        state.selectedCategoryIds.add(id);
      } else {
        state.selectedCategoryIds.delete(id);
      }
      const groupId = Number(checkbox.dataset.categoryGroupId || 0);
      if (groupId) {
        state.selectedGroupIds.delete(groupId);
        bulkUi.syncGroupCheckboxState(groupId);
      }
      const row = checkbox.closest("tr");
      if (row) {
        row.classList.toggle("row-selected", checkbox.checked);
      }
      actions.updateCategoriesBulkUi();
      bulkUi.syncCategorySelectAll();
    });

    el.categoriesSelectAll.addEventListener("change", () => {
      const categoryCheckboxes = Array.from(el.categoriesBody.querySelectorAll("input[data-select-category-id]"))
        .filter((item) => !item.disabled);
      const groupCheckboxes = Array.from(el.categoriesBody.querySelectorAll("input[data-select-group-id]"))
        .filter((item) => !item.disabled);

      for (const checkbox of categoryCheckboxes) {
        const id = Number(checkbox.dataset.selectCategoryId);
        if (el.categoriesSelectAll.checked) {
          state.selectedCategoryIds.add(id);
          checkbox.checked = true;
        } else {
          state.selectedCategoryIds.delete(id);
          checkbox.checked = false;
        }
        const row = checkbox.closest("tr[data-item]");
        if (row) {
          row.classList.toggle("row-selected", checkbox.checked);
        }
      }

      for (const checkbox of groupCheckboxes) {
        const id = Number(checkbox.dataset.selectGroupId);
        if (el.categoriesSelectAll.checked) {
          state.selectedGroupIds.add(id);
          checkbox.checked = true;
          checkbox.indeterminate = false;
        } else {
          state.selectedGroupIds.delete(id);
          checkbox.checked = false;
          checkbox.indeterminate = false;
        }
        const row = checkbox.closest("tr");
        if (row) {
          row.classList.toggle("row-selected", checkbox.checked);
        }
      }
      actions.updateCategoriesBulkUi();
      bulkUi.syncCategorySelectAll();
    });

    el.categoriesBody.addEventListener("click", (event) => {
      if (event.target.closest("button,input,a,select,textarea,label")) {
        return;
      }
      const row = event.target.closest("tr");
      if (!row) {
        return;
      }
      const rowCheckbox = row.querySelector("input[data-select-category-id], input[data-select-group-id]");
      if (!rowCheckbox || rowCheckbox.disabled) {
        return;
      }
      rowCheckbox.checked = !rowCheckbox.checked;
      rowCheckbox.dispatchEvent(new Event("change", { bubbles: true }));
    });

    el.bulkEditCategoriesBtn.addEventListener("click", bulkUi.openBulkEditCategoriesModal);
    el.closeBulkEditCategoriesModalBtn.addEventListener("click", bulkUi.closeBulkEditCategoriesModal);
    el.bulkEditCategoriesModal.addEventListener("click", (event) => {
      if (event.target === el.bulkEditCategoriesModal) {
        bulkUi.closeBulkEditCategoriesModal();
      }
    });
    el.bulkEditCategoriesForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitBulkEditCategoriesBtn"),
        pendingText: "Применение...",
        successMessage: "Категории обновлены",
        errorPrefix: "Ошибка массового редактирования категорий",
        action: () => bulkUpdateCategories(event),
      });
    });

    el.bulkDeleteCategoriesBtn.addEventListener("click", () => {
      const categoryIds = Array.from(state.selectedCategoryIds);
      const groupIds = Array.from(state.selectedGroupIds);
      core.runDestructiveAction({
        confirmMessage: `Удалить выбранные объекты (${categoryIds.length + groupIds.length})?`,
        doDelete: async () => {
          if (categoryIds.length) {
            await actions.bulkDeleteCategories(categoryIds);
          }
          if (groupIds.length && actions.bulkDeleteGroups) {
            await actions.bulkDeleteGroups(groupIds);
          }
          state.selectedCategoryIds.clear();
          state.selectedGroupIds.clear();
        },
        onDeleteError: "Не удалось удалить выбранные категории",
      });
    });

    el.deleteAllCategoriesBtn.addEventListener("click", () => {
      const categoryIds = bulkUi.visibleCategoryIds();
      const groupIds = bulkUi.visibleGroupIds();
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
          state.selectedCategoryIds.clear();
          state.selectedGroupIds.clear();
        },
        onDeleteError: "Не удалось удалить категории",
      });
    });
  }

  window.App.bulkBindingsCategories = {
    bindCategoryBulkHandlers,
  };
})();
