(() => {
  const { state, el, core, actions } = window.App;
  const bulkUi = window.App.bulkUi;
  const bulkUtils = window.App.bulkImportUtils;

  function ensureOperationCategoryCatalogLoaded() {
    if (state.categories.length) {
      return Promise.resolve();
    }
    if (actions.loadCategories) {
      return actions.loadCategories();
    }
    return Promise.resolve();
  }

  function buildOperationCategoryMaps() {
    const scoped = new Map();
    const generic = new Map();
    for (const category of state.categories || []) {
      const groupName = bulkUtils.normalizeCell(category.group_name || "");
      const scopedKey = bulkUtils.keyify(category.kind, groupName, category.name);
      scoped.set(scopedKey, category);
      const genericKey = bulkUtils.keyify(category.kind, category.name);
      const bucket = generic.get(genericKey) || [];
      bucket.push(category);
      generic.set(genericKey, bucket);
    }
    return { scoped, generic };
  }

  function renderOperationFeedback(plan) {
    if (!el.batchCreateFeedback) {
      return;
    }
    const parts = [];
    if (plan.validRows.length) {
      parts.push(`Готово к импорту: ${plan.validRows.length}`);
    }
    if (plan.errorCount) {
      parts.push(`Ошибок: ${plan.errorCount}`);
    }
    el.batchCreateFeedback.textContent = parts.join(" • ") || "Нет строк для импорта";
    el.batchCreateFeedback.classList.remove("hidden");
  }

  function renderOperationPreview(plan) {
    if (!el.batchCreatePreviewBody || !el.batchCreatePreview) {
      return;
    }
    el.batchCreatePreviewBody.innerHTML = plan.rows.map((row) => `
      <tr>
        <td data-label="#">${row.index}</td>
        <td data-label="Дата">${row.date || "—"}</td>
        <td data-label="Тип">${row.kindLabel || "—"}</td>
        <td data-label="Группа">${row.group || "—"}</td>
        <td data-label="Категория">${row.category || "—"}</td>
        <td data-label="Сумма">${row.amount || "—"}</td>
        <td data-label="Комментарий">${row.note || "—"}</td>
        <td data-label="Статус"><span class="${row.statusClass}">${row.statusText}</span></td>
      </tr>
    `).join("");
    el.batchCreatePreview.classList.remove("hidden");
  }

  function applyOperationPlan(plan) {
    state.batchOperationPlan = plan;
    renderOperationFeedback(plan);
    renderOperationPreview(plan);
    if (el.confirmBatchCreateBtn) {
      el.confirmBatchCreateBtn.textContent = `Импортировать ${plan.validRows.length} строк`;
      el.confirmBatchCreateBtn.disabled = plan.validRows.length === 0;
      el.confirmBatchCreateBtn.classList.toggle("hidden", plan.validRows.length === 0);
    }
  }

  function buildOperationPlan() {
    const lines = String(el.batchCreateInput?.value || "")
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    if (!lines.length) {
      throw new Error("Добавь хотя бы одну строку");
    }

    const categoryMaps = buildOperationCategoryMaps();
    const rows = [];
    const validRows = [];
    let errorCount = 0;

    for (const [idx, line] of lines.entries()) {
      const row = {
        index: idx + 1,
        date: "",
        kindLabel: "",
        group: "",
        category: "",
        amount: "",
        note: "",
        statusText: "Готово",
        statusClass: "bulk-import-status-ok",
      };
      const parts = String(line || "").split(";").map((part) => bulkUtils.normalizeCell(part));
      while (parts.length > 6 && parts[parts.length - 1] === "") {
        parts.pop();
      }
      if (parts.length < 4 || parts.length > 6) {
        row.statusText = "Неверный формат";
        row.statusClass = "bulk-import-status-error";
        rows.push(row);
        errorCount += 1;
        continue;
      }
      let dateRaw = "";
      let kindRaw = "";
      let groupRaw = "";
      let categoryRaw = "";
      let amountRaw = "";
      let noteValue = "";

      if (parts.length === 6) {
        [dateRaw, kindRaw, groupRaw, categoryRaw, amountRaw, noteValue = ""] = parts;
      } else if (parts.length === 5) {
        const [p0, p1, p2, p3, p4] = parts;
        const p3AsAmount = bulkUtils.normalizeAmount(p3).valid;
        const p4AsAmount = bulkUtils.normalizeAmount(p4).valid;
        if (!p3AsAmount && p4AsAmount) {
          [dateRaw, kindRaw, groupRaw, categoryRaw, amountRaw] = parts;
          noteValue = "";
        } else {
          [dateRaw, kindRaw, categoryRaw, amountRaw, noteValue = ""] = parts;
          groupRaw = "";
        }
      } else {
        [dateRaw, kindRaw, categoryRaw, amountRaw] = parts;
        groupRaw = "";
        noteValue = "";
      }
      const parsedDate = bulkUtils.parseFlexibleDate(dateRaw);
      row.date = core.formatDateRu(parsedDate || dateRaw);
      row.kindLabel = kindRaw;
      row.group = groupRaw;
      row.category = categoryRaw;
      row.amount = amountRaw;
      row.note = noteValue || "";

      const kind = bulkUtils.normalizeKind(kindRaw);
      if (!parsedDate) {
        row.statusText = "Неверная дата";
        row.statusClass = "bulk-import-status-error";
        rows.push(row);
        errorCount += 1;
        continue;
      }
      if (!kind) {
        row.statusText = "Неверный тип";
        row.statusClass = "bulk-import-status-error";
        rows.push(row);
        errorCount += 1;
        continue;
      }
      const normalizedGroup = bulkUtils.normalizeCell(groupRaw);
      const normalizedCategory = bulkUtils.normalizeCell(categoryRaw);
      let category = null;
      if (!normalizedCategory) {
        row.kindLabel = core.kindLabel(kind);
        row.group = normalizedGroup || "—";
        row.category = "Без категории";
      } else if (normalizedGroup) {
        category = categoryMaps.scoped.get(bulkUtils.keyify(kind, normalizedGroup, normalizedCategory)) || null;
      } else {
        const bucket = categoryMaps.generic.get(bulkUtils.keyify(kind, normalizedCategory)) || [];
        if (bucket.length === 1) {
          [category] = bucket;
        } else if (bucket.length > 1) {
          row.kindLabel = core.kindLabel(kind);
          row.group = "—";
          row.category = normalizedCategory || "—";
          row.statusText = "Уточни группу";
          row.statusClass = "bulk-import-status-error";
          rows.push(row);
          errorCount += 1;
          continue;
        }
      }
      if (normalizedCategory && !category) {
        row.kindLabel = core.kindLabel(kind);
        row.group = normalizedGroup || "—";
        row.category = normalizedCategory || "—";
        row.statusText = normalizedGroup ? "Категория/группа не найдены" : "Категория не найдена";
        row.statusClass = "bulk-import-status-error";
        rows.push(row);
        errorCount += 1;
        continue;
      }
      const amount = bulkUtils.normalizeAmount(amountRaw);
      if (!amount.valid) {
        row.kindLabel = core.kindLabel(kind);
        row.category = normalizedCategory;
        row.statusText = "Неверная сумма";
        row.statusClass = "bulk-import-status-error";
        rows.push(row);
        errorCount += 1;
        continue;
      }

      const note = bulkUtils.normalizeCell(noteValue || "");
      row.kindLabel = core.kindLabel(kind);
      row.group = normalizedCategory ? bulkUtils.normalizeCell(category?.group_name || normalizedGroup || "") : (normalizedGroup || "");
      row.category = normalizedCategory || "Без категории";
      row.amount = amount.value;
      row.note = note;
      rows.push(row);
      validRows.push({
        kind,
        operation_date: parsedDate,
        category_id: category ? Number(category.id) : null,
        amount: amount.value,
        note,
      });
    }

    return { rows, validRows, errorCount };
  }

  async function previewBatchCreateOperations(event) {
    event.preventDefault();
    await ensureOperationCategoryCatalogLoaded();
    applyOperationPlan(buildOperationPlan());
  }

  async function importBatchCreateOperations() {
    const plan = state.batchOperationPlan;
    if (!plan?.validRows?.length) {
      core.setStatus("Сначала проверь строки и дождись валидного предпросмотра");
      return;
    }
    let created = 0;
    for (const payload of plan.validRows) {
      await core.requestJson("/api/v1/operations", {
        method: "POST",
        headers: core.authHeaders(),
        body: JSON.stringify(payload),
      });
      created += 1;
    }
    if (actions.invalidateAllTimeAnchor) {
      actions.invalidateAllTimeAnchor();
    }
    if (el.batchCreateFeedback) {
      el.batchCreateFeedback.textContent = `Импорт завершен: создано ${created}, ошибок в предпросмотре ${plan.errorCount}`;
      el.batchCreateFeedback.classList.remove("hidden");
    }
    if (el.confirmBatchCreateBtn) {
      el.confirmBatchCreateBtn.disabled = true;
    }
    await Promise.all([actions.loadDashboard(), actions.loadDashboardOperations(), actions.loadOperations()]);
    core.setStatus(`Импорт операций завершен: создано ${created}`);
  }

  async function bulkDeleteOperations(ids) {
    for (const id of ids) {
      await core.requestJson(`/api/v1/operations/${id}`, {
        method: "DELETE",
        headers: core.authHeaders(),
      });
    }
    if (actions.invalidateAllTimeAnchor) {
      actions.invalidateAllTimeAnchor();
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
    if (actions.invalidateAllTimeAnchor) {
      actions.invalidateAllTimeAnchor();
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
        button: event.submitter || el.previewBatchCreateBtn,
        pendingText: "Проверка...",
        errorPrefix: "Ошибка проверки пакета операций",
        action: () => previewBatchCreateOperations(event),
      });
    });
    if (el.confirmBatchCreateBtn) {
      el.confirmBatchCreateBtn.addEventListener("click", () => {
        core.runAction({
          button: el.confirmBatchCreateBtn,
          pendingText: "Импорт...",
          errorPrefix: "Ошибка импорта операций",
          action: () => importBatchCreateOperations(),
        });
      });
    }

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
      if (el.deleteAllOperationsBtn.disabled) {
        return;
      }
      const ids = actions.getCurrentOperationItems().map((item) => item.id);
      if (!ids.length) {
        return;
      }
      core.runDestructiveAction({
        confirmMessage: `Удалить все загруженные операции (${ids.length})?`,
        doDelete: async () => bulkDeleteOperations(ids),
        onDeleteError: "Не удалось удалить операции",
      });
    });
  }

  window.App.bulkBindingsOperations = {
    bindOperationBulkHandlers,
  };
})();
