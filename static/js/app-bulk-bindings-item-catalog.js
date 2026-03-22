(() => {
  const { state, el, core, actions } = window.App;
  const bulkUi = window.App.getRuntimeModule?.("bulk-ui");
  const bulkUtils = window.App.bulkImportUtils;

  function getItemCatalogFeature() {
    return window.App.getRuntimeModule?.("item-catalog") || {};
  }

  function clearItemCatalogPreview() {
    state.batchItemTemplatePlan = null;
    if (el.batchItemTemplateFeedback) {
      el.batchItemTemplateFeedback.textContent = "";
      el.batchItemTemplateFeedback.classList.add("hidden");
    }
    if (el.batchItemTemplatePreview) {
      el.batchItemTemplatePreview.classList.add("hidden");
    }
    if (el.batchItemTemplatePreviewBody) {
      el.batchItemTemplatePreviewBody.innerHTML = "";
    }
    if (el.confirmBatchItemTemplateBtn) {
      el.confirmBatchItemTemplateBtn.textContent = "Импортировать 0 строк";
      el.confirmBatchItemTemplateBtn.disabled = true;
      el.confirmBatchItemTemplateBtn.classList.add("hidden");
    }
  }

  function renderItemCatalogFeedback(plan) {
    if (!el.batchItemTemplateFeedback) {
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
    el.batchItemTemplateFeedback.textContent = parts.join(" • ") || "Нет строк для импорта";
    el.batchItemTemplateFeedback.classList.remove("hidden");
  }

  function renderItemCatalogPreview(plan) {
    if (!el.batchItemTemplatePreviewBody || !el.batchItemTemplatePreview) {
      return;
    }
    el.batchItemTemplatePreviewBody.innerHTML = plan.rows.map((row) => `
      <tr>
        <td data-label="#">${row.index}</td>
        <td data-label="Источник">${row.source || "—"}</td>
        <td data-label="Позиция">${row.name || "—"}</td>
        <td data-label="Цена">${row.price || "—"}</td>
        <td data-label="Статус"><span class="${row.statusClass}">${row.statusText}</span></td>
      </tr>
    `).join("");
    el.batchItemTemplatePreview.classList.remove("hidden");
  }

  function applyItemCatalogPlan(plan) {
    state.batchItemTemplatePlan = plan;
    renderItemCatalogFeedback(plan);
    renderItemCatalogPreview(plan);
    if (el.confirmBatchItemTemplateBtn) {
      el.confirmBatchItemTemplateBtn.textContent = `Импортировать ${plan.validRows.length} строк`;
      el.confirmBatchItemTemplateBtn.disabled = plan.validRows.length === 0;
      el.confirmBatchItemTemplateBtn.classList.toggle("hidden", plan.validRows.length === 0);
    }
  }

  function buildItemCatalogPlan() {
    const lines = String(el.batchItemTemplateInput?.value || "")
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    if (!lines.length) {
      throw new Error("Добавь хотя бы одну строку");
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
        source: "",
        name: "",
        price: "",
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
      const [sourceRaw, nameRaw, priceRaw = ""] = parts;
      const source = bulkUtils.normalizeCell(sourceRaw);
      const name = bulkUtils.normalizeCell(nameRaw);
      row.source = source || "Без источника";
      row.name = name;
      if (!name) {
        row.statusText = "Пустое название";
        row.statusClass = "bulk-import-status-error";
        rows.push(row);
        errorCount += 1;
        continue;
      }
      const key = bulkUtils.keyify(source || "__no_shop__", name);
      if (seen.has(key)) {
        row.statusText = "Дубль в пакете, будет пропущен";
        row.statusClass = "bulk-import-status-warn";
        rows.push(row);
        warningCount += 1;
        skippedCount += 1;
        continue;
      }
      seen.add(key);
      let price = null;
      if (priceRaw) {
        const normalized = bulkUtils.normalizeAmount(priceRaw);
        if (!normalized.valid) {
          row.price = priceRaw;
          row.statusText = "Неверная цена";
          row.statusClass = "bulk-import-status-error";
          rows.push(row);
          errorCount += 1;
          continue;
        }
        price = normalized.value;
        row.price = normalized.value;
      } else {
        row.price = "—";
      }
      if (!source) {
        row.statusText = "Без источника";
        row.statusClass = "bulk-import-status-warn";
        warningCount += 1;
      }
      rows.push(row);
      validRows.push({
        shop_name: source || null,
        name,
        latest_unit_price: price,
      });
    }

    return { rows, validRows, errorCount, warningCount, skippedCount };
  }

  async function previewBatchItemTemplates(event) {
    event.preventDefault();
    applyItemCatalogPlan(buildItemCatalogPlan());
  }

  function persistImportedSources(rows) {
    if (!state.preferences) {
      return;
    }
    state.preferences.data = state.preferences.data || {};
    state.preferences.data.ui = state.preferences.data.ui || {};
    const existing = Array.isArray(state.preferences.data.ui.item_catalog_sources)
      ? state.preferences.data.ui.item_catalog_sources
      : [];
    const byKey = new Map(existing.map((item) => [bulkUtils.keyify(item), item]));
    for (const row of rows) {
      if (row.shop_name) {
        byKey.set(bulkUtils.keyify(row.shop_name), row.shop_name);
      }
    }
    state.preferences.data.ui.item_catalog_sources = Array.from(byKey.values());
  }

  async function importBatchItemTemplates() {
    const plan = state.batchItemTemplatePlan;
    if (!plan?.validRows?.length) {
      core.setStatus("Сначала проверь строки и дождись валидного предпросмотра");
      return;
    }
    let created = 0;
    for (const payload of plan.validRows) {
      await core.requestJson("/api/v1/operations/item-templates", {
        method: "POST",
        headers: core.authHeaders(),
        body: JSON.stringify(payload),
      });
      created += 1;
    }
    persistImportedSources(plan.validRows);
    core.invalidateUiRequestCache("item-catalog");
    await getItemCatalogFeature().loadItemCatalog?.({ force: true });
    if (el.batchItemTemplateFeedback) {
      el.batchItemTemplateFeedback.textContent =
        `Импорт завершен: обработано ${created}, пропущено ${plan.skippedCount}, предупреждений ${plan.warningCount}, ошибок ${plan.errorCount}`;
      el.batchItemTemplateFeedback.classList.remove("hidden");
    }
    if (el.confirmBatchItemTemplateBtn) {
      el.confirmBatchItemTemplateBtn.disabled = true;
    }
    core.setStatus(`Импорт позиций завершен: обработано ${created}`);
  }

  function bindItemCatalogBulkHandlers() {
    if (el.closeBatchItemTemplateModalBtn) {
      el.closeBatchItemTemplateModalBtn.addEventListener("click", bulkUi.closeBatchItemTemplateModal);
    }
    if (el.batchItemTemplateModal) {
      el.batchItemTemplateModal.addEventListener("click", (event) => {
        if (event.target === el.batchItemTemplateModal) {
          bulkUi.closeBatchItemTemplateModal();
        }
      });
    }
    if (el.batchItemTemplateForm) {
      el.batchItemTemplateForm.addEventListener("submit", (event) => {
        core.runAction({
          button: event.submitter || el.previewBatchItemTemplateBtn,
          pendingText: "Проверка...",
          errorPrefix: "Ошибка проверки пакета позиций",
          action: () => previewBatchItemTemplates(event),
        });
      });
    }
    if (el.confirmBatchItemTemplateBtn) {
      el.confirmBatchItemTemplateBtn.addEventListener("click", () => {
        core.runAction({
          button: el.confirmBatchItemTemplateBtn,
          pendingText: "Импорт...",
          errorPrefix: "Ошибка импорта позиций",
          action: () => importBatchItemTemplates(),
        });
      });
    }
  }

  window.App.bulkBindingsItemCatalog = {
    bindItemCatalogBulkHandlers,
    clearItemCatalogPreview,
  };
})();
