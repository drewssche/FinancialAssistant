(() => {
  const { state, el, core, actions } = window.App;
  const bulkUi = window.App.getRuntimeModule?.("bulk-ui");
  const bulkUtils = window.App.bulkImportUtils;

  function ensureCategoryCatalogLoaded() {
    if (state.categories.length || state.categoryGroups.length) {
      return Promise.resolve();
    }
    if (actions.loadCategories) {
      return actions.loadCategories();
    }
    return Promise.resolve();
  }

  function clearCategoryBulkPreview() {
    state.batchCategoryPlan = null;
    if (el.batchCategoryFeedback) {
      el.batchCategoryFeedback.textContent = "";
      el.batchCategoryFeedback.classList.add("hidden");
    }
    if (el.batchCategoryPreview) {
      el.batchCategoryPreview.classList.add("hidden");
    }
    if (el.batchCategoryPreviewBody) {
      el.batchCategoryPreviewBody.innerHTML = "";
    }
    if (el.confirmBatchCategoryBtn) {
      el.confirmBatchCategoryBtn.textContent = "Импортировать 0 строк";
      el.confirmBatchCategoryBtn.disabled = true;
      el.confirmBatchCategoryBtn.classList.add("hidden");
    }
  }

  function setBatchCategoryMode(mode) {
    const normalized = mode === "groups" ? "groups" : "categories";
    el.batchCategoryMode.value = normalized;
    core.syncSegmentedActive(el.batchCategoryModeTabs, "batch-category-mode", normalized);
    if (el.batchCategoryHint) {
      el.batchCategoryHint.innerHTML = normalized === "groups"
        ? 'Группы: <code>тип;название</code>. Дубли будут пропущены.'
        : 'Категории: <code>тип;название;группа</code>. Пустая группа = «Без группы», неизвестная группа будет предупреждением и импортом в «Без группы».';
    }
    clearCategoryBulkPreview();
  }

  function renderCategoryFeedback(plan) {
    if (!el.batchCategoryFeedback) {
      return;
    }
    const parts = [];
    if (plan.validRows.length) {
      parts.push(`Готово к импорту: ${plan.validRows.length}`);
    }
    if (plan.warningCount) {
      parts.push(`Предупреждений: ${plan.warningCount}`);
    }
    if (plan.skippedCount) {
      parts.push(`Пропусков: ${plan.skippedCount}`);
    }
    if (plan.errorCount) {
      parts.push(`Ошибок: ${plan.errorCount}`);
    }
    el.batchCategoryFeedback.textContent = parts.join(" • ") || "Нет строк для импорта";
    el.batchCategoryFeedback.classList.remove("hidden");
  }

  function renderCategoryPreview(plan) {
    if (!el.batchCategoryPreviewBody || !el.batchCategoryPreview) {
      return;
    }
    el.batchCategoryPreviewBody.innerHTML = plan.rows.map((row) => `
      <tr>
        <td data-label="#">${row.index}</td>
        <td data-label="Тип">${row.kindLabel || "—"}</td>
        <td data-label="Название">${row.name || "—"}</td>
        <td data-label="Группа">${row.group || "—"}</td>
        <td data-label="Статус"><span class="${row.statusClass}">${row.statusText}</span></td>
      </tr>
    `).join("");
    el.batchCategoryPreview.classList.remove("hidden");
  }

  function applyCategoryPlan(plan) {
    state.batchCategoryPlan = plan;
    renderCategoryFeedback(plan);
    renderCategoryPreview(plan);
    if (el.confirmBatchCategoryBtn) {
      el.confirmBatchCategoryBtn.textContent = `Импортировать ${plan.validRows.length} строк`;
      el.confirmBatchCategoryBtn.disabled = plan.validRows.length === 0;
      el.confirmBatchCategoryBtn.classList.toggle("hidden", plan.validRows.length === 0);
    }
  }

  function buildGroupImportPlan(lines) {
    const existingGroups = new Map();
    for (const group of state.categoryGroups || []) {
      existingGroups.set(bulkUtils.keyify(group.kind, group.name), group);
    }
    const seen = new Set();
    const rows = [];
    const validRows = [];
    let errorCount = 0;
    let warningCount = 0;
    let skippedCount = 0;

    for (const [idx, line] of lines.entries()) {
      const row = {
        index: idx + 1,
        kindLabel: "",
        name: "",
        group: "—",
        statusText: "Готово",
        statusClass: "bulk-import-status-ok",
      };
      const parts = bulkUtils.splitStrict(line, 2, 2);
      if (!parts) {
        row.statusText = "Неверный формат";
        row.statusClass = "bulk-import-status-error";
        rows.push(row);
        errorCount += 1;
        continue;
      }
      const [kindRaw, nameRaw] = parts;
      const kind = bulkUtils.normalizeKind(kindRaw);
      const name = bulkUtils.normalizeCell(nameRaw);
      row.kindLabel = kind ? core.kindLabel(kind) : kindRaw;
      row.name = name;
      if (!kind) {
        row.statusText = "Неверный тип";
        row.statusClass = "bulk-import-status-error";
        rows.push(row);
        errorCount += 1;
        continue;
      }
      if (!name) {
        row.statusText = "Пустое название";
        row.statusClass = "bulk-import-status-error";
        rows.push(row);
        errorCount += 1;
        continue;
      }
      const key = bulkUtils.keyify(kind, name);
      if (existingGroups.has(key) || seen.has(key)) {
        row.statusText = "Дубль, будет пропущен";
        row.statusClass = "bulk-import-status-warn";
        rows.push(row);
        warningCount += 1;
        skippedCount += 1;
        continue;
      }
      seen.add(key);
      rows.push(row);
      validRows.push({ name, kind, accent_color: null });
    }

    return { mode: "groups", rows, validRows, errorCount, warningCount, skippedCount };
  }

  function buildCategoryImportPlan(lines) {
    const existingCategories = new Map();
    const groupsByKey = new Map();
    for (const item of state.categories || []) {
      existingCategories.set(bulkUtils.keyify(item.kind, item.name), item);
    }
    for (const group of state.categoryGroups || []) {
      groupsByKey.set(bulkUtils.keyify(group.kind, group.name), group);
    }
    const seen = new Set();
    const rows = [];
    const validRows = [];
    let errorCount = 0;
    let warningCount = 0;
    let skippedCount = 0;

    for (const [idx, line] of lines.entries()) {
      const row = {
        index: idx + 1,
        kindLabel: "",
        name: "",
        group: "Без группы",
        statusText: "Готово",
        statusClass: "bulk-import-status-ok",
      };
      const parts = bulkUtils.splitStrict(line, 2, 3);
      if (!parts) {
        row.statusText = "Неверный формат";
        row.statusClass = "bulk-import-status-error";
        rows.push(row);
        errorCount += 1;
        continue;
      }
      const [kindRaw, nameRaw, groupRaw = ""] = parts;
      const kind = bulkUtils.normalizeKind(kindRaw);
      const name = bulkUtils.normalizeCell(nameRaw);
      const groupName = bulkUtils.normalizeCell(groupRaw);
      row.kindLabel = kind ? core.kindLabel(kind) : kindRaw;
      row.name = name;
      row.group = groupName || "Без группы";

      if (!kind) {
        row.statusText = "Неверный тип";
        row.statusClass = "bulk-import-status-error";
        rows.push(row);
        errorCount += 1;
        continue;
      }
      if (!name) {
        row.statusText = "Пустое название";
        row.statusClass = "bulk-import-status-error";
        rows.push(row);
        errorCount += 1;
        continue;
      }
      const key = bulkUtils.keyify(kind, name);
      if (existingCategories.has(key) || seen.has(key)) {
        row.statusText = "Дубль, будет пропущен";
        row.statusClass = "bulk-import-status-warn";
        rows.push(row);
        warningCount += 1;
        skippedCount += 1;
        continue;
      }
      let groupId = null;
      if (groupName) {
        const group = groupsByKey.get(bulkUtils.keyify(kind, groupName));
        if (group) {
          groupId = Number(group.id);
        } else {
          row.statusText = "Группа не найдена, будет «Без группы»";
          row.statusClass = "bulk-import-status-warn";
          warningCount += 1;
        }
      }
      seen.add(key);
      rows.push(row);
      validRows.push({ name, kind, group_id: groupId, icon: null });
    }

    return { mode: "categories", rows, validRows, errorCount, warningCount, skippedCount };
  }

  function buildCategoryPlan() {
    const lines = String(el.batchCategoryInput?.value || "")
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    if (!lines.length) {
      throw new Error("Добавь хотя бы одну строку");
    }
    return el.batchCategoryMode.value === "groups"
      ? buildGroupImportPlan(lines)
      : buildCategoryImportPlan(lines);
  }

  async function previewBatchCategory(event) {
    event.preventDefault();
    await ensureCategoryCatalogLoaded();
    applyCategoryPlan(buildCategoryPlan());
  }

  async function importBatchCategory() {
    const plan = state.batchCategoryPlan;
    if (!plan?.validRows?.length) {
      core.setStatus("Сначала проверь строки и дождись валидного предпросмотра");
      return;
    }
    let created = 0;
    for (const payload of plan.validRows) {
      await core.requestJson(plan.mode === "groups" ? "/api/v1/categories/groups" : "/api/v1/categories", {
        method: "POST",
        headers: core.authHeaders(),
        body: JSON.stringify(payload),
      });
      created += 1;
    }
    core.invalidateUiRequestCache("categories");
    core.invalidateUiRequestCache("operations");
    await actions.loadCategories();
    if (el.batchCategoryFeedback) {
      el.batchCategoryFeedback.textContent =
        `Импорт завершен: создано ${created}, пропущено ${plan.skippedCount}, предупреждений ${plan.warningCount}, ошибок ${plan.errorCount}`;
      el.batchCategoryFeedback.classList.remove("hidden");
    }
    if (el.confirmBatchCategoryBtn) {
      el.confirmBatchCategoryBtn.disabled = true;
    }
    core.setStatus(`Импорт ${plan.mode === "groups" ? "групп" : "категорий"} завершен: создано ${created}`);
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

    if (el.batchCategoryModeTabs) {
      el.batchCategoryModeTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-batch-category-mode]");
        if (!btn) {
          return;
        }
        setBatchCategoryMode(btn.dataset.batchCategoryMode);
      });
    }
    if (el.closeBatchCategoryModalBtn) {
      el.closeBatchCategoryModalBtn.addEventListener("click", bulkUi.closeBatchCategoryModal);
    }
    if (el.batchCategoryModal) {
      el.batchCategoryModal.addEventListener("click", (event) => {
        if (event.target === el.batchCategoryModal) {
          bulkUi.closeBatchCategoryModal();
        }
      });
    }
    if (el.batchCategoryForm) {
      el.batchCategoryForm.addEventListener("submit", (event) => {
        core.runAction({
          button: event.submitter || el.previewBatchCategoryBtn,
          pendingText: "Проверка...",
          errorPrefix: "Ошибка проверки пакета категорий",
          action: () => previewBatchCategory(event),
        });
      });
    }
    if (el.confirmBatchCategoryBtn) {
      el.confirmBatchCategoryBtn.addEventListener("click", () => {
        core.runAction({
          button: el.confirmBatchCategoryBtn,
          pendingText: "Импорт...",
          errorPrefix: "Ошибка импорта категорий",
          action: () => importBatchCategory(),
        });
      });
    }

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
