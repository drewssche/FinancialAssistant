(() => {
  const { state, el, core } = window.App;
  const escapeHtml = core.escapeHtml || ((value) => String(value ?? ""));

  let rows = [];
  let activeStatus = "all";
  let selectedIds = new Set();
  let requestController = null;
  let bound = false;

  const STATUS_META = {
    overdue: { label: "Просрочено", tone: "danger" },
    due: { label: "Пора сегодня", tone: "danger" },
    upcoming: { label: "Скоро", tone: "positive" },
    snoozed: { label: "Отложено", tone: "neutral" },
    awaiting_purchase: { label: "Ждём покупку", tone: "neutral" },
    unconfigured: { label: "Не настроено", tone: "muted" },
  };

  function getCatalogFeature() {
    return window.App.getRuntimeModule?.("item-catalog") || {};
  }

  function getOperationModal() {
    return window.App.getRuntimeModule?.("operation-modal") || {};
  }

  function getPlansFeature() {
    return window.App.getRuntimeModule?.("plans") || {};
  }

  function normalizeNumber(value, fallback = 0) {
    const parsed = Number(String(value ?? "").replace(",", "."));
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function formatQuantity(value) {
    const amount = normalizeNumber(value, 0);
    return amount.toLocaleString("ru-RU", { maximumFractionDigits: 3 });
  }

  function statusMatches(row) {
    if (activeStatus === "due") {
      return row.status === "due" || row.status === "overdue";
    }
    if (activeStatus === "upcoming") {
      return row.status === "upcoming" || row.status === "snoozed";
    }
    if (activeStatus === "configured") {
      return Boolean(row.recommendation_enabled);
    }
    if (activeStatus === "unconfigured") {
      return !row.recommendation_enabled;
    }
    if (activeStatus === "candidates") {
      return Boolean(row.candidate);
    }
    return true;
  }

  function getVisibleRows() {
    const query = String(el.itemRecommendationsSearchQ?.value || "").trim().toLowerCase();
    return rows.filter((row) => {
      if (!statusMatches(row)) {
        return false;
      }
      if (!query) {
        return true;
      }
      return String(row.name || "").toLowerCase().includes(query)
        || String(row.shop_name || "").toLowerCase().includes(query);
    });
  }

  function renderKpis() {
    if (!el.itemRecommendationsKpiGrid) {
      return;
    }
    const configured = rows.filter((row) => row.recommendation_enabled).length;
    const due = rows.filter((row) => row.status === "due" || row.status === "overdue").length;
    const candidates = rows.filter((row) => row.candidate).length;
    el.itemRecommendationsKpiGrid.innerHTML = `
      <article class="analytics-kpi-card analytics-kpi-neutral">
        <div class="muted-small">Настроено</div>
        <strong>${configured}</strong>
      </article>
      <article class="analytics-kpi-card analytics-kpi-negative">
        <div class="muted-small">Пора купить</div>
        <strong>${due}</strong>
      </article>
      <article class="analytics-kpi-card analytics-kpi-positive">
        <div class="muted-small">Кандидатов</div>
        <strong>${candidates}</strong>
      </article>
    `;
  }

  function renderBulkState(visibleRows = getVisibleRows()) {
    const selectedCount = selectedIds.size;
    el.itemRecommendationBulkBar?.classList.toggle("hidden", selectedCount === 0);
    if (el.itemRecommendationSelectedCount) {
      el.itemRecommendationSelectedCount.textContent = `Выбрано: ${selectedCount}`;
    }
    const visibleIds = visibleRows.map((row) => Number(row.template_id));
    const selectedVisible = visibleIds.filter((id) => selectedIds.has(id)).length;
    if (el.itemRecommendationsSelectAll) {
      el.itemRecommendationsSelectAll.checked = visibleIds.length > 0 && selectedVisible === visibleIds.length;
      el.itemRecommendationsSelectAll.indeterminate = selectedVisible > 0 && selectedVisible < visibleIds.length;
    }
  }

  function renderRow(row) {
    const catalogItem = (state.itemCatalogItems || []).find((entry) => Number(entry?.id || 0) === Number(row.template_id))
      || (state.itemCatalogAllItems || []).find((entry) => Number(entry?.id || 0) === Number(row.template_id))
      || {};
    const imageId = row.image_id || catalogItem.image_id;
    const itemThumb = window.App.getRuntimeModule?.("catalog-media")?.renderThumb?.(imageId, {
      kind: "item",
      size: "row",
      alt: row.name || "Позиция",
      fallback: String(row.name || "П").slice(0, 1),
    }) || "";
    const status = STATUS_META[row.status] || STATUS_META.unconfigured;
    const lastPurchase = row.last_purchase_date
      ? `${core.formatDateRu(row.last_purchase_date)} · ${formatQuantity(row.last_quantity)} шт.`
      : "Покупок ещё нет";
    const nextDate = row.effective_date
      ? core.formatDateRu(row.effective_date)
      : row.recommendation_enabled ? "После первой покупки" : "—";
    const nextMeta = row.snoozed_until && row.status === "snoozed"
      ? `Отложено с ${row.next_date ? core.formatDateRu(row.next_date) : "—"}`
      : row.days_until === null || row.days_until === undefined
        ? ""
        : row.days_until < 0
          ? `${Math.abs(row.days_until)} дн. назад`
          : row.days_until === 0 ? "Сегодня" : `Через ${row.days_until} дн.`;
    const candidate = row.candidate
      ? '<span class="item-recommendation-candidate">Часто покупается</span>'
      : "";
    return `
      <tr data-recommendation-template-id="${Number(row.template_id)}">
        <td data-label="Выбор">
          <input class="item-recommendation-select" type="checkbox" ${selectedIds.has(Number(row.template_id)) ? "checked" : ""} aria-label="Выбрать ${escapeHtml(row.name)}" />
        </td>
        <td data-label="Позиция">
          <div class="item-recommendation-identity">
            ${itemThumb}
            <div class="item-recommendation-identity-main">
              <button class="catalog-item-open item-recommendation-title" data-recommendation-manage-action="edit" type="button">${escapeHtml(row.name)}</button>
              <div class="muted-small">${escapeHtml(row.shop_name || "Без источника")} · ${Number(row.use_count || 0)} покупок</div>
              ${candidate}
            </div>
          </div>
        </td>
        <td data-label="Последняя покупка">
          <span>${escapeHtml(lastPurchase)}</span>
        </td>
        <td data-label="Настройка">
          <div class="item-recommendation-settings">
            <label class="item-recommendation-enabled">
              <input data-recommendation-enabled type="checkbox" ${row.recommendation_enabled ? "checked" : ""} />
              <span>Включено</span>
            </label>
            <label><input data-recommendation-interval type="number" min="1" max="3650" step="1" value="${Number(row.interval_days || 30)}" /><span>дн.</span></label>
            <label><span>на</span><input data-recommendation-quantity type="number" min="0.001" max="100000" step="0.001" value="${escapeHtml(row.base_quantity || 1)}" /><span>шт.</span></label>
          </div>
        </td>
        <td data-label="Следующая дата">
          <div>${escapeHtml(nextDate)}</div>
          ${nextMeta ? `<div class="muted-small">${escapeHtml(nextMeta)}</div>` : ""}
        </td>
        <td data-label="Статус"><span class="item-recommendation-status is-${status.tone}">${status.label}</span></td>
        <td data-label="Действия">
          <div class="item-recommendation-actions">
            <button class="btn btn-primary btn-xs" data-recommendation-manage-action="save" type="button">Сохранить</button>
            <button class="btn btn-secondary btn-xs" data-recommendation-manage-action="receipt" type="button">В чек</button>
            <button class="btn btn-secondary btn-xs" data-recommendation-manage-action="plan" type="button">В план</button>
            <button class="btn btn-ghost btn-xs" data-recommendation-manage-action="snooze" type="button" ${row.recommendation_enabled ? "" : "disabled"}>+7 дней</button>
            <button class="btn btn-ghost btn-xs" data-recommendation-manage-action="edit" type="button">Карточка</button>
          </div>
        </td>
      </tr>
    `;
  }

  function render() {
    renderKpis();
    const visibleRows = getVisibleRows();
    if (el.itemRecommendationsBody) {
      el.itemRecommendationsBody.innerHTML = visibleRows.length
        ? visibleRows.map(renderRow).join("")
        : '<tr><td colspan="7" class="item-recommendations-empty">По этому фильтру позиций нет</td></tr>';
    }
    renderBulkState(visibleRows);
  }

  async function load(options = {}) {
    if (requestController) {
      requestController.abort();
    }
    const controller = new AbortController();
    requestController = controller;
    el.itemRecommendationsView?.classList.add("is-loading");
    try {
      const payload = await core.requestJson("/api/v1/operations/item-recommendations/manage", {
        headers: core.authHeaders(),
        signal: controller.signal,
      });
      rows = Array.isArray(payload) ? payload : [];
      selectedIds = new Set(Array.from(selectedIds).filter((id) => rows.some((row) => Number(row.template_id) === id)));
      render();
      if (options.refreshCatalog) {
        await getCatalogFeature().loadItemCatalog?.({ force: true });
      }
    } catch (err) {
      if (!core.isAbortError?.(err)) {
        throw err;
      }
    } finally {
      if (requestController === controller) {
        requestController = null;
      }
      el.itemRecommendationsView?.classList.remove("is-loading");
    }
  }

  function setView(view, options = {}) {
    const activeView = ["positions", "brands", "recommendations"].includes(view) ? view : "positions";
    state.itemCatalogView = activeView;
    el.itemCatalogPositionsView?.classList.toggle("hidden", activeView !== "positions");
    el.itemBrandsView?.classList.toggle("hidden", activeView !== "brands");
    el.itemRecommendationsView?.classList.toggle("hidden", activeView !== "recommendations");
    el.itemCatalogViewTabs?.querySelectorAll("[data-item-catalog-view]").forEach((button) => {
      button.classList.toggle("active", button.dataset.itemCatalogView === activeView);
    });
    if (activeView === "recommendations" && (options.force || rows.length === 0)) {
      load().catch((err) => core.setStatus(`Не удалось загрузить рекомендации: ${String(err)}`));
    }
    if (activeView === "brands") {
      window.App.getRuntimeModule?.("item-brands")?.ensureItemBrandsLoaded?.({ force: options.force === true })
        .catch((err) => core.setStatus(`Не удалось загрузить бренды: ${String(err)}`));
    }
  }

  function setPreferredView(view) {
    setView(view, { force: view === "recommendations" });
  }

  function rowFromNode(node) {
    const rowNode = node?.closest?.("tr[data-recommendation-template-id]");
    const templateId = Number(rowNode?.dataset.recommendationTemplateId || 0);
    return {
      node: rowNode,
      item: rows.find((row) => Number(row.template_id) === templateId),
      templateId,
    };
  }

  async function saveRow(button, rowNode, item) {
    const enabled = Boolean(rowNode.querySelector("[data-recommendation-enabled]")?.checked);
    const intervalDays = normalizeNumber(rowNode.querySelector("[data-recommendation-interval]")?.value, 0);
    const baseQuantity = normalizeNumber(rowNode.querySelector("[data-recommendation-quantity]")?.value, 0);
    if (enabled && (!Number.isInteger(intervalDays) || intervalDays < 1 || baseQuantity <= 0)) {
      throw new Error("Укажите запас от 1 дня и количество больше нуля");
    }
    await core.requestJson(`/api/v1/operations/item-templates/${Number(item.template_id)}`, {
      method: "PATCH",
      headers: core.authHeaders(),
      body: JSON.stringify({
        recommendation_enabled: enabled,
        recommendation_mode: "manual",
        recommendation_interval_days: intervalDays || item.interval_days || 30,
        recommendation_base_quantity: String(baseQuantity || item.base_quantity || 1),
        recommendation_snoozed_until: enabled ? item.snoozed_until : null,
      }),
    });
    core.showToast?.("Настройка рекомендации сохранена", { type: "success" });
    await load({ refreshCatalog: true });
  }

  async function handleRowAction(event) {
    const select = event.target.closest(".item-recommendation-select");
    if (select) {
      const { templateId } = rowFromNode(select);
      if (select.checked) {
        selectedIds.add(templateId);
      } else {
        selectedIds.delete(templateId);
      }
      renderBulkState();
      return;
    }
    const button = event.target.closest("button[data-recommendation-manage-action]");
    if (!button) {
      return;
    }
    const { node, item, templateId } = rowFromNode(button);
    if (!item || !node) {
      return;
    }
    const action = button.dataset.recommendationManageAction;
    if (action === "receipt") {
      getOperationModal().openCreateReceiptWithItem?.(item);
      return;
    }
    if (action === "plan") {
      getPlansFeature().openCreatePlanWithReceiptItem?.(item);
      return;
    }
    if (action === "edit") {
      const catalogItem = (state.itemCatalogItems || []).find((entry) => Number(entry?.id || 0) === templateId) || {};
      getCatalogFeature().openItemTemplateModal?.({
        ...catalogItem,
        id: templateId,
        shop_name: item.shop_name,
        name: item.name,
        last_category_id: item.category_id,
        latest_unit_price: item.latest_unit_price,
        image_id: item.image_id ?? catalogItem.image_id ?? null,
        source_id: item.source_id ?? catalogItem.source_id ?? null,
        source_image_id: item.source_image_id ?? catalogItem.source_image_id ?? null,
        brand_id: item.brand_id ?? catalogItem.brand_id ?? null,
        brand_name: item.brand_name ?? catalogItem.brand_name ?? null,
        brand_accent_color: item.brand_accent_color ?? catalogItem.brand_accent_color ?? null,
        brand_image_id: item.brand_image_id ?? catalogItem.brand_image_id ?? null,
        brand_is_archived: item.brand_is_archived ?? catalogItem.brand_is_archived ?? false,
        recommendation_enabled: item.recommendation_enabled,
        recommendation_mode: item.recommendation_mode,
        recommendation_interval_days: item.interval_days,
        recommendation_base_quantity: item.base_quantity,
        recommendation_next_date: item.next_date,
        recommendation_snoozed_until: item.snoozed_until,
      });
      return;
    }
    core.runAction({
      button,
      pendingText: action === "save" ? "Сохраняем…" : "Откладываем…",
      errorPrefix: "Не удалось обновить рекомендацию",
      action: async () => {
        if (action === "save") {
          await saveRow(button, node, item);
          return;
        }
        if (action === "snooze") {
          await core.requestJson(`/api/v1/operations/item-recommendations/${templateId}/snooze`, {
            method: "POST",
            headers: core.authHeaders(),
            body: JSON.stringify({ days: 7 }),
          });
          core.showToast?.("Рекомендация отложена на 7 дней", { type: "success" });
          await load({ refreshCatalog: true });
        }
      },
    });
  }

  async function runBulkAction(button, action) {
    const templateIds = Array.from(selectedIds);
    if (!templateIds.length) {
      return;
    }
    const payload = { template_ids: templateIds, action };
    if (action === "enable") {
      const intervalDays = normalizeNumber(el.itemRecommendationBulkInterval?.value, 0);
      const baseQuantity = normalizeNumber(el.itemRecommendationBulkQuantity?.value, 0);
      if (!Number.isInteger(intervalDays) || intervalDays < 1 || baseQuantity <= 0) {
        core.setStatus("Укажите корректный запас и количество для массового включения");
        return;
      }
      payload.interval_days = intervalDays;
      payload.base_quantity = String(baseQuantity);
    }
    if (action === "snooze") {
      payload.snooze_days = 7;
    }
    core.runAction({
      button,
      pendingText: "Применяем…",
      errorPrefix: "Не удалось применить массовое действие",
      action: async () => {
        const result = await core.requestJson("/api/v1/operations/item-recommendations/bulk", {
          method: "POST",
          headers: core.authHeaders(),
          body: JSON.stringify(payload),
        });
        selectedIds.clear();
        core.showToast?.(`Обновлено позиций: ${Number(result.updated || 0)}`, { type: "success" });
        await load({ refreshCatalog: true });
      },
    });
  }

  function bind() {
    if (bound) {
      return;
    }
    bound = true;
    el.itemCatalogViewTabs?.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-item-catalog-view]");
      if (button) {
        setView(button.dataset.itemCatalogView);
      }
    });
    el.itemRecommendationStatusTabs?.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-recommendation-status]");
      if (!button) {
        return;
      }
      activeStatus = button.dataset.recommendationStatus || "all";
      el.itemRecommendationStatusTabs.querySelectorAll("[data-recommendation-status]").forEach((node) => {
        node.classList.toggle("active", node === button);
      });
      render();
    });
    let searchTimer = null;
    el.itemRecommendationsSearchQ?.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(render, 140);
    });
    el.itemRecommendationsBody?.addEventListener("click", (event) => {
      handleRowAction(event).catch((err) => core.setStatus(String(err)));
    });
    el.itemRecommendationsSelectAll?.addEventListener("change", () => {
      for (const row of getVisibleRows()) {
        const id = Number(row.template_id);
        if (el.itemRecommendationsSelectAll.checked) {
          selectedIds.add(id);
        } else {
          selectedIds.delete(id);
        }
      }
      render();
    });
    el.clearSelectedRecommendationsBtn?.addEventListener("click", () => {
      selectedIds.clear();
      render();
    });
    el.refreshItemRecommendationsBtn?.addEventListener("click", () => {
      core.runAction({
        button: el.refreshItemRecommendationsBtn,
        pendingText: "Обновляем…",
        errorPrefix: "Не удалось обновить рекомендации",
        action: () => load(),
      });
    });
    el.enableSelectedRecommendationsBtn?.addEventListener("click", () => runBulkAction(el.enableSelectedRecommendationsBtn, "enable"));
    el.snoozeSelectedRecommendationsBtn?.addEventListener("click", () => runBulkAction(el.snoozeSelectedRecommendationsBtn, "snooze"));
    el.disableSelectedRecommendationsBtn?.addEventListener("click", () => {
      core.showConfirm?.(`Отключить рекомендации у ${selectedIds.size} позиций?`, () => {
        runBulkAction(el.disableSelectedRecommendationsBtn, "disable");
      }, { title: "Отключение рекомендаций", confirmLabel: "Отключить" });
    });
    setView(state.itemCatalogView || "positions");
  }

  window.App.registerRuntimeModule?.("item-recommendation-manager", {
    bind,
    load,
    render,
    setPreferredView,
  });
})();
