(() => {
  const { state, el, core } = window.App;
  const bulkUi = window.App.getRuntimeModule?.("bulk-ui");

  function getDashboardFeature() {
    return window.App.getRuntimeModule?.("dashboard") || {};
  }

  function getOperationsFeature() {
    return window.App.getRuntimeModule?.("operations") || {};
  }

  async function bulkDeleteOperations(ids) {
    for (const id of ids) {
      await core.requestJson(`/api/v1/operations/${id}`, {
        method: "DELETE",
        headers: core.authHeaders(),
      });
    }
    getOperationsFeature().invalidateAllTimeAnchor?.();
    state.selectedOperationIds.clear();
    const dashboardFeature = getDashboardFeature();
    const operationsFeature = getOperationsFeature();
    await Promise.all([
      dashboardFeature.loadDashboard?.(),
      dashboardFeature.loadDashboardOperations?.(),
      operationsFeature.loadOperations?.(),
    ].filter(Boolean));
  }

  async function bulkUpdateOperations(event) {
    event.preventDefault();
    const ids = Array.from(state.selectedOperationIds);
    if (!ids.length) {
      return;
    }
    const updates = {};
    if (el.bulkOpKind.value) {
      updates.kind = el.bulkOpKind.value;
    }
    if (el.bulkOpCategory.value) {
      updates.category_id = Number(el.bulkOpCategory.value);
    }
    if (el.bulkOpDate.value) {
      const parsedDate = core.parseDateInputValue(el.bulkOpDate.value);
      if (!parsedDate) {
        core.setStatus("Проверь дату массового редактирования");
        return;
      }
      updates.operation_date = parsedDate;
    }
    if (!Object.keys(updates).length) {
      core.setStatus("Заполни хотя бы одно поле для редактирования");
      return;
    }
    for (const id of ids) {
      await core.requestJson(`/api/v1/operations/${id}`, {
        method: "PATCH",
        headers: core.authHeaders(),
        body: JSON.stringify(updates),
      });
    }
    getOperationsFeature().invalidateAllTimeAnchor?.();
    bulkUi.closeBulkEditOperationsModal();
    state.selectedOperationIds.clear();
    const dashboardFeature = getDashboardFeature();
    const operationsFeature = getOperationsFeature();
    await Promise.all([
      dashboardFeature.loadDashboard?.(),
      dashboardFeature.loadDashboardOperations?.(),
      operationsFeature.loadOperations?.(),
    ].filter(Boolean));
  }

  function bindOperationBulkHandlers() {
    el.operationsBody.addEventListener("change", (event) => {
      const checkbox = event.target.closest("input[data-select-operation-id]");
      if (!checkbox) {
        return;
      }
      const id = Number(checkbox.dataset.selectOperationId);
      if (checkbox.checked) {
        state.selectedOperationIds.add(id);
      } else {
        state.selectedOperationIds.delete(id);
      }
      const row = checkbox.closest("tr[data-item]");
      if (row) {
        row.classList.toggle("row-selected", checkbox.checked);
      }
      bulkUi.updateOperationsBulkUi();
    });

    if (el.operationsSelectAll) {
      el.operationsSelectAll.addEventListener("change", () => {
        const checkboxes = Array.from(el.operationsBody.querySelectorAll("input[data-select-operation-id]"));
        for (const checkbox of checkboxes) {
          const id = Number(checkbox.dataset.selectOperationId);
          if (el.operationsSelectAll.checked) {
            state.selectedOperationIds.add(id);
            checkbox.checked = true;
          } else {
            state.selectedOperationIds.delete(id);
            checkbox.checked = false;
          }
          const row = checkbox.closest("tr[data-item]");
          if (row) {
            row.classList.toggle("row-selected", checkbox.checked);
          }
        }
        bulkUi.updateOperationsBulkUi();
      });
    }

    if (el.bulkEditOperationsBtn) {
      el.bulkEditOperationsBtn.addEventListener("click", () => {
        bulkUi.fillBulkOperationCategorySelect(el.bulkOpKind.value);
        bulkUi.openBulkEditOperationsModal();
      });
    }
    el.closeBulkEditOperationsModalBtn.addEventListener("click", bulkUi.closeBulkEditOperationsModal);
    el.bulkEditOperationsModal.addEventListener("click", (event) => {
      if (event.target === el.bulkEditOperationsModal) {
        bulkUi.closeBulkEditOperationsModal();
      }
    });
    el.bulkEditOperationsForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitBulkEditOperationsBtn"),
        pendingText: "Применение...",
        successMessage: "Изменения применены",
        errorPrefix: "Ошибка массового редактирования операций",
        action: () => bulkUpdateOperations(event),
      });
    });
    el.bulkOpKind.addEventListener("change", () => {
      bulkUi.fillBulkOperationCategorySelect(el.bulkOpKind.value);
    });

    if (el.bulkDeleteOperationsBtn) {
      el.bulkDeleteOperationsBtn.addEventListener("click", () => {
        const ids = Array.from(state.selectedOperationIds);
        core.runDestructiveAction({
          confirmMessage: `Удалить выбранные операции (${ids.length})?`,
          doDelete: async () => bulkDeleteOperations(ids),
          onDeleteError: "Не удалось удалить выбранные операции",
        });
      });
    }

  }

  window.App.bulkBindingsOperations = {
    bindOperationBulkHandlers,
  };
})();
