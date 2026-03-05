(() => {
  const { state, el, core, actions } = window.App;
  const bulkUi = window.App.bulkUi;

  async function batchCreateOperations(event) {
    event.preventDefault();
    const lines = el.batchCreateInput.value
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    if (!lines.length) {
      core.setStatus("Добавь хотя бы одну строку");
      return;
    }
    for (const line of lines) {
      const [kind, amount, operationDate, note = ""] = line.split(";").map((part) => part.trim());
      if (!kind || !amount || !operationDate) {
        throw new Error(`Неверный формат строки: ${line}`);
      }
      await core.requestJson("/api/v1/operations", {
        method: "POST",
        headers: core.authHeaders(),
        body: JSON.stringify({
          kind,
          amount,
          operation_date: operationDate,
          note,
          category_id: null,
        }),
      });
    }
    el.batchCreateInput.value = "";
    bulkUi.closeBatchCreateModal();
    await Promise.all([actions.loadDashboard(), actions.loadDashboardOperations(), actions.loadOperations()]);
  }

  async function bulkDeleteOperations(ids) {
    for (const id of ids) {
      await core.requestJson(`/api/v1/operations/${id}`, {
        method: "DELETE",
        headers: core.authHeaders(),
      });
    }
    state.selectedOperationIds.clear();
    await Promise.all([actions.loadDashboard(), actions.loadDashboardOperations(), actions.loadOperations()]);
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
      updates.operation_date = el.bulkOpDate.value;
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
    bulkUi.closeBulkEditOperationsModal();
    state.selectedOperationIds.clear();
    await Promise.all([actions.loadDashboard(), actions.loadDashboardOperations(), actions.loadOperations()]);
  }

  function bindOperationBulkHandlers() {
    el.closeBatchCreateModalBtn.addEventListener("click", bulkUi.closeBatchCreateModal);
    el.batchCreateModal.addEventListener("click", (event) => {
      if (event.target === el.batchCreateModal) {
        bulkUi.closeBatchCreateModal();
      }
    });
    el.batchCreateForm.addEventListener("submit", (event) => {
      core.runAction({
        button: event.submitter || document.getElementById("submitBatchCreateBtn"),
        pendingText: "Добавление...",
        successMessage: "Пакет операций добавлен",
        errorPrefix: "Ошибка массового добавления",
        action: () => batchCreateOperations(event),
      });
    });

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

    el.operationsBody.addEventListener("click", (event) => {
      if (event.target.closest("button")) {
        return;
      }
      const checkbox = event.target.closest("input[data-select-operation-id]");
      if (checkbox) {
        return;
      }
      const row = event.target.closest("tr[data-item]");
      if (!row) {
        return;
      }
      const rowCheckbox = row.querySelector("input[data-select-operation-id]");
      if (!rowCheckbox) {
        return;
      }
      rowCheckbox.checked = !rowCheckbox.checked;
      rowCheckbox.dispatchEvent(new Event("change", { bubbles: true }));
    });

    el.bulkEditOperationsBtn.addEventListener("click", () => {
      bulkUi.fillBulkOperationCategorySelect(el.bulkOpKind.value);
      bulkUi.openBulkEditOperationsModal();
    });
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

    el.bulkDeleteOperationsBtn.addEventListener("click", () => {
      const ids = Array.from(state.selectedOperationIds);
      core.runDestructiveAction({
        confirmMessage: `Удалить выбранные операции (${ids.length})?`,
        doDelete: async () => bulkDeleteOperations(ids),
        onDeleteError: "Не удалось удалить выбранные операции",
      });
    });

    el.deleteAllOperationsBtn.addEventListener("click", () => {
      const ids = actions.getCurrentOperationItems().map((item) => item.id);
      core.runDestructiveAction({
        confirmMessage: `Удалить все операции на текущей странице (${ids.length})?`,
        doDelete: async () => bulkDeleteOperations(ids),
        onDeleteError: "Не удалось удалить операции",
      });
    });
  }

  window.App.bulkBindingsOperations = {
    bindOperationBulkHandlers,
  };
})();
