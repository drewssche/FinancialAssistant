(() => {
  const { state, el, core, actions } = window.App;
  let bound = false;
  let operationsObserver = null;
  let categoriesObserver = null;

  function bindFeatureHandlers() {
    let filterDebounceId = null;
    let categorySearchDebounceId = null;
    let debtSearchDebounceId = null;

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

    if (el.debtStatusTabs && actions.setDebtStatusFilter) {
      el.debtStatusTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-debt-status]");
        if (!btn) {
          return;
        }
        actions.setDebtStatusFilter(btn.dataset.debtStatus);
      });
    }

    if (el.debtSearchQ && actions.applyDebtSearch) {
      el.debtSearchQ.addEventListener("input", () => {
        if (debtSearchDebounceId) {
          clearTimeout(debtSearchDebounceId);
        }
        debtSearchDebounceId = setTimeout(() => {
          actions.applyDebtSearch().catch((err) => core.setStatus(String(err)));
        }, 250);
      });
    }

    if (el.debtsCards && actions.openDebtRepaymentModal) {
      el.debtsCards.addEventListener("click", (event) => {
        const editBtn = event.target.closest("button[data-edit-debt-id]");
        if (editBtn && actions.openEditDebtModal) {
          actions.openEditDebtModal(Number(editBtn.dataset.editDebtId || 0));
          return;
        }

        const historyBtn = event.target.closest("button[data-history-debt-id]");
        if (historyBtn && actions.openDebtHistoryModal) {
          actions.openDebtHistoryModal(Number(historyBtn.dataset.historyDebtId || 0));
          return;
        }

        const deleteBtn = event.target.closest("button[data-delete-debt-id]");
        if (deleteBtn && actions.deleteDebtFlow) {
          actions.deleteDebtFlow(Number(deleteBtn.dataset.deleteDebtId || 0));
          return;
        }

        const btn = event.target.closest("button[data-repay-debt-id]");
        if (!btn || btn.disabled) {
          return;
        }
        actions.openDebtRepaymentModal(Number(btn.dataset.repayDebtId || 0));
      });
    }

    if (el.debtRepaymentForm && actions.submitDebtRepayment) {
      el.debtRepaymentForm.addEventListener("submit", (event) => {
        core.runAction({
          button: event.submitter || el.submitDebtRepaymentBtn,
          pendingText: "Сохранение...",
          successMessage: "Погашение добавлено",
          errorPrefix: "Ошибка добавления погашения",
          action: () => actions.submitDebtRepayment(event),
        });
      });
    }

    if (el.repaymentPresetRow && el.repaymentAmount) {
      el.repaymentPresetRow.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-repayment-preset]");
        if (!btn) {
          return;
        }
        const ratio = Number(btn.dataset.repaymentPreset || 0);
        const outstanding = Number(el.repaymentOutstanding?.textContent || 0);
        if (!Number.isFinite(ratio) || ratio <= 0 || !Number.isFinite(outstanding) || outstanding <= 0) {
          return;
        }
        el.repaymentAmount.value = (outstanding * ratio).toFixed(2);
        if (actions.updateRepaymentDeltaHint) {
          actions.updateRepaymentDeltaHint();
        }
      });
    }
    if (el.repaymentAmount && actions.updateRepaymentDeltaHint) {
      el.repaymentAmount.addEventListener("input", () => {
        actions.updateRepaymentDeltaHint();
      });
    }

    if (el.editDebtForm && actions.submitEditDebt) {
      el.editDebtForm.addEventListener("submit", (event) => {
        core.runAction({
          button: event.submitter || el.submitEditDebtBtn,
          pendingText: "Сохранение...",
          successMessage: "Долг обновлен",
          errorPrefix: "Ошибка обновления долга",
          action: () => actions.submitEditDebt(event),
        });
      });
    }

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

    for (const id of ["opAmount", "opDate", "opNote"]) {
      const node = document.getElementById(id);
      if (node) {
        node.addEventListener("input", actions.updateCreatePreview);
        node.addEventListener("change", actions.updateCreatePreview);
      }
    }
    for (const id of ["debtCounterparty", "debtPrincipal", "debtStartDate", "debtDueDate", "debtNote"]) {
      const node = document.getElementById(id);
      if (node) {
        node.addEventListener("input", actions.updateCreatePreview);
        node.addEventListener("change", actions.updateCreatePreview);
      }
    }
    if (actions.updateDebtDueHint) {
      const dueNodes = [document.getElementById("debtStartDate"), document.getElementById("debtDueDate")];
      for (const node of dueNodes) {
        if (!node) {
          continue;
        }
        node.addEventListener("input", actions.updateDebtDueHint);
        node.addEventListener("change", actions.updateDebtDueHint);
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

    el.opCategorySearch.addEventListener("focus", () => {
      if (actions.handleCreateCategorySearchFocus) {
        actions.handleCreateCategorySearchFocus();
      }
    });
    el.opCategorySearch.addEventListener("click", () => {
      if (actions.handleCreateCategorySearchFocus) {
        actions.handleCreateCategorySearchFocus();
      }
    });
    el.opCategorySearch.addEventListener("input", () => {
      if (actions.handleCreateCategorySearchInput) {
        actions.handleCreateCategorySearchInput();
      }
    });
    el.opCategorySearch.addEventListener("keydown", (event) => {
      if (actions.handleCreateCategorySearchKeydown) {
        actions.handleCreateCategorySearchKeydown(event);
      }
    });
    if (el.opCategoryAll) {
      el.opCategoryAll.addEventListener("click", (event) => {
        if (actions.handleCreateCategoryPickerClick) {
          actions.handleCreateCategoryPickerClick(event);
        }
      });
    }

    if (el.categoryGroupSearch) {
      el.categoryGroupSearch.addEventListener("focus", () => {
        if (actions.handleCreateGroupSearchFocus) {
          actions.handleCreateGroupSearchFocus();
        }
      });
      el.categoryGroupSearch.addEventListener("click", () => {
        if (actions.handleCreateGroupSearchFocus) {
          actions.handleCreateGroupSearchFocus();
        }
      });
      el.categoryGroupSearch.addEventListener("input", () => {
        if (actions.handleCreateGroupSearchInput) {
          actions.handleCreateGroupSearchInput();
        }
      });
      el.categoryGroupSearch.addEventListener("blur", () => {
        if (actions.handleCreateGroupSearchBlur) {
          actions.handleCreateGroupSearchBlur();
        }
      });
      el.categoryGroupSearch.addEventListener("keydown", (event) => {
        if (actions.handleCreateGroupSearchKeydown) {
          actions.handleCreateGroupSearchKeydown(event);
        }
      });
    }
    if (el.categoryGroupAll) {
      el.categoryGroupAll.addEventListener("click", (event) => {
        if (actions.handleCreateGroupPickerClick) {
          actions.handleCreateGroupPickerClick(event);
        }
      });
    }
    if (el.editCategoryGroupSearch) {
      el.editCategoryGroupSearch.addEventListener("focus", () => {
        if (actions.handleEditGroupSearchFocus) {
          actions.handleEditGroupSearchFocus();
        }
      });
      el.editCategoryGroupSearch.addEventListener("click", () => {
        if (actions.handleEditGroupSearchFocus) {
          actions.handleEditGroupSearchFocus();
        }
      });
      el.editCategoryGroupSearch.addEventListener("input", () => {
        if (actions.handleEditGroupSearchInput) {
          actions.handleEditGroupSearchInput();
        }
      });
      el.editCategoryGroupSearch.addEventListener("blur", () => {
        if (actions.handleEditGroupSearchBlur) {
          actions.handleEditGroupSearchBlur();
        }
      });
      el.editCategoryGroupSearch.addEventListener("keydown", (event) => {
        if (actions.handleEditGroupSearchKeydown) {
          actions.handleEditGroupSearchKeydown(event);
        }
      });
    }
    if (el.editCategoryGroupAll) {
      el.editCategoryGroupAll.addEventListener("click", (event) => {
        if (actions.handleEditGroupPickerClick) {
          actions.handleEditGroupPickerClick(event);
        }
      });
    }

    if (el.createPreviewBody) {
      el.createPreviewBody.addEventListener("click", (event) => {
        if (actions.handleCreatePreviewClick) {
          actions.handleCreatePreviewClick(event);
        }
      });
    }

    document.addEventListener("pointerdown", (event) => {
      if (actions.handleCreateCategoryOutsidePointer) {
        actions.handleCreateCategoryOutsidePointer(event);
      }
      if (actions.handleCreateGroupOutsidePointer) {
        actions.handleCreateGroupOutsidePointer(event);
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
