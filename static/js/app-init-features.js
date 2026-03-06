(() => {
  const { state, el, core, actions } = window.App;
  let bound = false;
  let operationsObserver = null;
  let categoriesObserver = null;

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
          errorPrefix: "Ошибка сохранения периода",
          action: async () => {
            if (state.period === "all_time" && actions.ensureAllTimeBounds) {
              await actions.ensureAllTimeBounds();
            }
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
      if (actions.invalidateAllTimeAnchor) {
        actions.invalidateAllTimeAnchor();
      }
      core.runAction({
        button: event.submitter || document.getElementById("submitPeriodCustomBtn"),
        pendingText: "Применение...",
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

    if (el.operationsSortTabs && actions.setOperationsSortPreset) {
      el.operationsSortTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-op-sort]");
        if (!btn) {
          return;
        }
        if (btn.dataset.opSort === state.operationSortPreset) {
          return;
        }
        core.runAction({
          errorPrefix: "Ошибка сортировки операций",
          action: () => actions.setOperationsSortPreset(btn.dataset.opSort),
        });
      });
    }

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

    if (el.createEntryModeSwitch) {
      el.createEntryModeSwitch.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-entry-mode]");
        if (!btn || !actions.setCreateEntryMode) {
          return;
        }
        actions.setCreateEntryMode(btn.dataset.entryMode);
      });
    }

    if (el.createDebtDirectionSwitch) {
      el.createDebtDirectionSwitch.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-debt-direction]");
        if (!btn || !actions.setDebtDirection) {
          return;
        }
        actions.setDebtDirection(btn.dataset.debtDirection);
      });
    }

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

    if (el.operationsInfiniteSentinel && "IntersectionObserver" in window) {
      if (operationsObserver) {
        operationsObserver.disconnect();
      }
      operationsObserver = new IntersectionObserver(
        (entries) => {
          const entry = entries[0];
          if (!entry?.isIntersecting) {
            return;
          }
          if (state.activeSection !== "operations") {
            return;
          }
          if (!state.operationsHasMore || state.operationsLoading) {
            return;
          }
          actions.loadMoreOperations().catch((err) => core.setStatus(String(err)));
        },
        {
          root: null,
          rootMargin: "240px 0px",
          threshold: 0,
        },
      );
      operationsObserver.observe(el.operationsInfiniteSentinel);
    }

    if (el.categoriesInfiniteSentinel && "IntersectionObserver" in window) {
      if (categoriesObserver) {
        categoriesObserver.disconnect();
      }
      categoriesObserver = new IntersectionObserver(
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
      categoriesObserver.observe(el.categoriesInfiniteSentinel);
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
      const closeBtn = event.target.closest("button[data-toast-close]");
      if (closeBtn && core.dismissToast) {
        core.dismissToast(closeBtn.dataset.toastClose);
        return;
      }
      const btn = event.target.closest("button[data-toast-undo]");
      if (!btn) {
        return;
      }
      core.handleUndoClick(btn.dataset.toastUndo);
    });

    if (window.App.initFeatureDebts?.bindDebtFeatureHandlers) {
      window.App.initFeatureDebts.bindDebtFeatureHandlers();
    }
    if (window.App.initFeaturePickers?.bindPickerFeatureHandlers) {
      window.App.initFeaturePickers.bindPickerFeatureHandlers();
    }
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
