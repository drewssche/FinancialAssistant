(() => {
  const { state, el, core, actions } = window.App;
  let bound = false;

  function bindFeatureHandlers() {
    let filterDebounceId = null;
    let categorySearchDebounceId = null;

    el.createForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitCreateOperationBtn"),
        pendingText: "Добавление...",
        successMessage: "Операция добавлена",
        errorPrefix: "Ошибка добавления операции",
        action: () => actions.createOperation(event),
      });
    });

    el.editForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitEditOperationBtn"),
        pendingText: "Сохранение...",
        successMessage: "Операция обновлена",
        errorPrefix: "Ошибка сохранения операции",
        action: () => actions.updateOperation(event),
      });
    });

    el.categoryModalForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitCreateCategoryBtn"),
        pendingText: "Добавление...",
        successMessage: "Категория добавлена",
        errorPrefix: "Ошибка добавления категории",
        action: () => actions.createCategory(event),
      });
    });

    el.editCategoryForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitEditCategoryBtn"),
        pendingText: "Сохранение...",
        successMessage: "Категория обновлена",
        errorPrefix: "Ошибка обновления категории",
        action: () => actions.updateCategory(event),
      });
    });

    el.editGroupForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitEditGroupBtn"),
        pendingText: "Сохранение...",
        successMessage: "Группа обновлена",
        errorPrefix: "Ошибка обновления группы",
        action: () => actions.updateGroup(event),
      });
    });

    for (const container of el.periodTabGroups) {
      container.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-period]");
        if (!btn) {
          return;
        }

        if (btn.dataset.period === "custom") {
          actions.openPeriodCustomModal();
          return;
        }

        if (btn.dataset.period === state.period) {
          return;
        }

        state.period = btn.dataset.period;
        core.syncAllPeriodTabs(state.period);
        core.runAction({
          successMessage: "Период сохранен",
          errorPrefix: "Ошибка сохранения периода",
          action: async () => {
            await actions.savePreferences();
            await Promise.all([actions.loadDashboard(), actions.loadDashboardOperations(), actions.loadOperations()]);
          },
        });
      });
    }

    el.periodCustomForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const from = el.customDateFrom.value;
      const to = el.customDateTo.value;
      if (!from || !to || from > to) {
        core.setStatus("Проверь диапазон дат");
        return;
      }

      state.customDateFrom = from;
      state.customDateTo = to;
      state.period = "custom";
      core.syncAllPeriodTabs("custom");
      core.runAction({
        button: event.submitter || document.getElementById("submitPeriodCustomBtn"),
        pendingText: "Применение...",
        successMessage: "Период сохранен",
        errorPrefix: "Ошибка сохранения периода",
        action: async () => {
          await actions.savePreferences();
          await Promise.all([actions.loadDashboard(), actions.loadDashboardOperations(), actions.loadOperations()]);
          actions.closePeriodCustomModal();
        },
      });
    });

    el.kindFilters.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-kind]");
      if (!btn) {
        return;
      }
      state.filterKind = btn.dataset.kind;
      core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
      core.runAction({
        errorPrefix: "Ошибка применения фильтра",
        action: () => actions.applyFilters(),
      });
    });

    el.filterQ.addEventListener("input", () => {
      if (filterDebounceId) {
        clearTimeout(filterDebounceId);
      }
      filterDebounceId = setTimeout(() => {
        core.runAction({
          errorPrefix: "Ошибка поиска",
          action: () => actions.applyRealtimeSearch(),
        });
      }, 300);
    });

    el.createKindSwitch.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-kind]");
      if (!btn) {
        return;
      }
      actions.setOperationKind("create", btn.dataset.kind);
    });

    el.editKindSwitch.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-kind]");
      if (!btn) {
        return;
      }
      actions.setOperationKind("edit", btn.dataset.kind);
    });

    el.operationsBody.addEventListener("click", (event) => {
      const deleteBtn = event.target.closest("button[data-delete-id]");
      if (deleteBtn) {
        const row = deleteBtn.closest("tr");
        const item = row ? JSON.parse(row.dataset.item || "{}") : null;
        if (item?.id) {
          actions.deleteOperationFlow(item).catch((err) => core.setStatus(String(err)));
        }
        return;
      }

      const editBtn = event.target.closest("button[data-edit-id]");
      if (!editBtn) {
        return;
      }
      const row = editBtn.closest("tr");
      const item = row ? JSON.parse(row.dataset.item || "{}") : null;
      if (item?.id) {
        actions.openEditModal(item);
      }
    });

    el.prevPageBtn.addEventListener("click", () => {
      if (state.page > 1) {
        state.page -= 1;
        actions.loadOperations().catch((err) => core.setStatus(String(err)));
      }
    });

    el.nextPageBtn.addEventListener("click", () => {
      const totalPages = Math.max(1, Math.ceil(state.total / state.pageSize));
      if (state.page < totalPages) {
        state.page += 1;
        actions.loadOperations().catch((err) => core.setStatus(String(err)));
      }
    });

    el.categoryKindTabs.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-cat-kind]");
      if (!btn) {
        return;
      }
      state.categoryFilterKind = btn.dataset.catKind;
      core.syncSegmentedActive(el.categoryKindTabs, "cat-kind", state.categoryFilterKind);
      actions.loadCategories().catch((err) => core.setStatus(String(err)));
    });

    el.categorySearchQ.addEventListener("input", () => {
      if (categorySearchDebounceId) {
        clearTimeout(categorySearchDebounceId);
      }
      categorySearchDebounceId = setTimeout(() => {
        actions.renderCategories();
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

    el.toastArea.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-toast-undo]");
      if (!btn) {
        return;
      }
      core.handleUndoClick(btn.dataset.toastUndo);
    });

    for (const id of ["opAmount", "opDate", "opNote"]) {
      const node = document.getElementById(id);
      if (node) {
        node.addEventListener("input", actions.updateCreatePreview);
        node.addEventListener("change", actions.updateCreatePreview);
      }
    }
    for (const id of ["editAmount", "editDate", "editNote"]) {
      const node = document.getElementById(id);
      if (node) {
        node.addEventListener("input", actions.updateEditPreview);
        node.addEventListener("change", actions.updateEditPreview);
      }
    }
    el.editCategory.addEventListener("change", () => {
      if (actions.updateEditPreview) {
        actions.updateEditPreview();
      }
    });

    el.opCategorySearch.addEventListener("input", () => {
      if (actions.renderCreateCategoryPicker) {
        actions.renderCreateCategoryPicker();
      }
    });
    el.opCategoryQuick.addEventListener("click", (event) => {
      if (actions.handleCreateCategoryPickerClick) {
        actions.handleCreateCategoryPickerClick(event);
      }
    });
    el.opCategoryAll.addEventListener("click", (event) => {
      if (actions.handleCreateCategoryPickerClick) {
        actions.handleCreateCategoryPickerClick(event);
      }
    });
  }

  function bindFeatureInit() {
    if (bound) {
      return;
    }
    bound = true;
    bindFeatureHandlers();
  }

  window.App.initFeatures = {
    bindFeatureInit,
  };
})();
