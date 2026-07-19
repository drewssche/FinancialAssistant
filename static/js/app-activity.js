(() => {
  const { state, el, core } = window.App;
  let recentItems = [];
  let recentLoadPromise = null;
  let recentRefreshTimer = null;
  const entityLabels = {
    operation: "операции",
    debt: "долга",
    plan: "плана",
    category: "категории",
    category_group: "группы категорий",
    item_template: "позиции каталога",
    currency_trade: "валютной сделки",
    currency_portfolio: "валютного портфеля",
  };

  function configureActivityButton(button, entityType, entityId) {
    if (!button) {
      return;
    }
    const normalizedId = Number(entityId || 0);
    if (!entityType || !normalizedId) {
      button.classList.add("hidden");
      button.removeAttribute("data-activity-entity-type");
      button.removeAttribute("data-activity-entity-id");
      return;
    }
    button.dataset.activityEntityType = entityType;
    button.dataset.activityEntityId = String(normalizedId);
    button.classList.remove("hidden");
  }

  function closeOpenActionPopover(target) {
    const popover = target?.closest?.(".app-popover");
    const pickerUtils = window.App.getRuntimeModule?.("picker-utils") || {};
    if (!popover || !pickerUtils?.setPopoverOpen) {
      return;
    }
    const owners = Array.isArray(popover.__appPopoverOwners) ? popover.__appPopoverOwners : [];
    const onClose = typeof popover.__appPopoverOnClose === "function" ? popover.__appPopoverOnClose : null;
    pickerUtils.setPopoverOpen(popover, false, { owners });
    owners.forEach((owner) => owner?.blur?.());
    onClose?.();
  }

  function formatEventDate(value) {
    if (!value) {
      return "";
    }
    try {
      return new Date(value).toLocaleString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return String(value);
    }
  }

  function formatRelativeDate(value) {
    const timestamp = new Date(value || "").getTime();
    if (!Number.isFinite(timestamp)) return "";
    const diffSeconds = Math.round((timestamp - Date.now()) / 1000);
    const formatter = new Intl.RelativeTimeFormat("ru-RU", { numeric: "auto" });
    if (Math.abs(diffSeconds) < 60) return formatter.format(diffSeconds, "second");
    const diffMinutes = Math.round(diffSeconds / 60);
    if (Math.abs(diffMinutes) < 60) return formatter.format(diffMinutes, "minute");
    const diffHours = Math.round(diffMinutes / 60);
    if (Math.abs(diffHours) < 24) return formatter.format(diffHours, "hour");
    const diffDays = Math.round(diffHours / 24);
    if (Math.abs(diffDays) < 7) return formatter.format(diffDays, "day");
    return formatEventDate(value);
  }

  function setActivityCenterOpen(isOpen) {
    const next = Boolean(isOpen);
    el.activityCenterDrawer?.classList.toggle("hidden", !next);
    el.activityCenterOverlay?.classList.toggle("hidden", !next);
    el.activityCenterDrawer?.setAttribute("aria-hidden", next ? "false" : "true");
    el.activityCenterOverlay?.setAttribute("aria-hidden", next ? "false" : "true");
    el.activityCenterToggleBtn?.setAttribute("aria-expanded", next ? "true" : "false");
    document.body.classList.toggle("activity-center-open", next);
    if (next) {
      el.activityCenterBadge?.classList.add("hidden");
    }
  }

  function closeActivityCenter() {
    setActivityCenterOpen(false);
  }

  function actionButton(eventId, action, label, icon) {
    return `<button class="activity-center-action-btn" type="button" data-activity-center-event-id="${Number(eventId)}" data-activity-center-action="${action}" aria-label="${core.escapeHtml(label)}" title="${core.escapeHtml(label)}"><span aria-hidden="true">${icon}</span></button>`;
  }

  function renderRecentEvents(items) {
    if (!el.activityCenterList) return;
    recentItems = Array.isArray(items) ? items : [];
    if (!recentItems.length) {
      el.activityCenterList.innerHTML = '<div class="activity-center-state muted-small">Действий пока нет</div>';
      return;
    }
    el.activityCenterList.innerHTML = recentItems.map((item) => {
      const actions = Array.isArray(item.available_actions) ? item.available_actions : [];
      const quickActions = [
        actions.includes("edit") ? actionButton(item.id, "edit", "Редактировать", "✎") : "",
        actions.includes("restore") ? actionButton(item.id, "restore", "Восстановить", "↶") : "",
      ].join("");
      const clickLabel = item.entity_exists ? "Открыть запись" : "Открыть подробности";
      return `
        <article class="activity-center-event" data-activity-center-event="${Number(item.id)}">
          <button class="activity-center-event-main" type="button" data-activity-center-event-id="${Number(item.id)}" data-activity-center-action="open" aria-label="${clickLabel}">
            <span class="activity-center-event-title-row">
              <strong class="activity-center-event-title">${core.escapeHtml(item.title || "Событие")}</strong>
              <time class="activity-center-event-time" datetime="${core.escapeHtml(item.created_at || "")}" title="${core.escapeHtml(formatEventDate(item.created_at))}">${core.escapeHtml(formatRelativeDate(item.created_at))}</time>
            </span>
            <span class="activity-center-event-entity">${core.escapeHtml(item.entity_label || "")}</span>
            ${item.entity_summary ? `<span class="activity-center-event-summary">${core.escapeHtml(item.entity_summary)}</span>` : ""}
          </button>
          ${quickActions ? `<div class="activity-center-event-actions">${quickActions}</div>` : ""}
        </article>
      `;
    }).join("");
  }

  async function loadRecentActivity({ force = false } = {}) {
    if (recentLoadPromise && !force) return recentLoadPromise;
    if (el.activityCenterList && !recentItems.length) {
      el.activityCenterList.innerHTML = '<div class="activity-center-state muted-small">Загрузка...</div>';
    }
    recentLoadPromise = core.requestJson("/api/v1/activity?page=1&page_size=7", {
      headers: core.authHeaders(),
    }).then((payload) => {
      renderRecentEvents(payload.items || []);
      return payload;
    }).catch((err) => {
      if (el.activityCenterList) {
        el.activityCenterList.innerHTML = `<div class="activity-center-state form-error">Не удалось загрузить действия: ${core.escapeHtml(String(err?.message || err))}</div>`;
      }
      throw err;
    }).finally(() => {
      recentLoadPromise = null;
    });
    return recentLoadPromise;
  }

  async function toggleActivityCenter() {
    const shouldOpen = el.activityCenterDrawer?.classList.contains("hidden") !== false;
    setActivityCenterOpen(shouldOpen);
    if (shouldOpen) {
      await loadRecentActivity({ force: true });
    }
  }

  function findRecentEvent(eventId) {
    return recentItems.find((item) => Number(item.id) === Number(eventId)) || null;
  }

  async function openActivityEntity(item) {
    if (!item) return;
    if (!item.entity_exists) {
      closeActivityCenter();
      await openActivityModal(item.entity_type, item.entity_id);
      return;
    }
    closeActivityCenter();
    const navigation = window.App.actions || {};
    const operationModal = window.App.getRuntimeModule?.("operation-modal") || {};
    if (item.entity_type === "operation") {
      const operation = await core.requestJson(`/api/v1/operations/${Number(item.entity_id)}`, { headers: core.authHeaders() });
      await operationModal.openEditModal?.(operation);
      return;
    }
    if (item.entity_type === "debt") {
      await navigation.switchSection?.("debts");
      const debts = window.App.getRuntimeModule?.("debts") || {};
      await debts.loadDebtsCards?.({ force: true });
      await debts.openEditDebtModal?.(Number(item.entity_id));
      return;
    }
    if (item.entity_type === "plan") {
      await navigation.switchSection?.("plans");
      if (item.available_actions?.includes("edit")) {
        await window.App.getRuntimeModule?.("plans")?.openPlanEdit?.(Number(item.entity_id));
      }
      return;
    }
    if (item.entity_type === "category" || item.entity_type === "category_group") {
      await navigation.switchSection?.("categories");
      const categories = window.App.getRuntimeModule?.("category-actions") || {};
      await Promise.all([categories.loadCategoryGroups?.(), categories.loadCategoryCatalog?.()]);
      if (item.entity_type === "category") {
        const entity = (state.categories || []).find((row) => Number(row.id) === Number(item.entity_id));
        if (entity) categories.openEditCategoryModal?.(entity);
      } else {
        const entity = (state.categoryGroups || []).find((row) => Number(row.id) === Number(item.entity_id));
        if (entity) categories.openEditGroupModal?.(entity);
      }
      return;
    }
    if (item.entity_type === "item_template") {
      await navigation.switchSection?.("item_catalog");
      const catalog = window.App.getRuntimeModule?.("item-catalog") || {};
      await catalog.loadItemCatalog?.({ force: true });
      const entity = (state.itemCatalogItems || []).find((row) => Number(row.id) === Number(item.entity_id));
      if (entity) catalog.openItemTemplateModal?.(entity);
      return;
    }
    if (item.entity_type === "currency_trade") {
      await navigation.switchSection?.("currency");
      await window.App.getRuntimeModule?.("currency")?.openCurrencyTradeEdit?.(Number(item.entity_id));
      return;
    }
    if (item.entity_type === "currency_portfolio") {
      await navigation.switchSection?.("currency");
      return;
    }
    await openActivityModal(item.entity_type, item.entity_id);
  }

  async function restoreActivityEntity(item) {
    if (!item || !Array.isArray(item.available_actions) || !item.available_actions.includes("restore")) return;
    const endpoint = item.entity_type === "operation"
      ? `/api/v1/operations/${Number(item.entity_id)}/restore`
      : item.entity_type === "category"
        ? `/api/v1/categories/${Number(item.entity_id)}/restore`
        : "";
    if (!endpoint) return;
    core.showConfirm(`Восстановить «${item.entity_label || item.title}»?`, async () => {
      await core.requestJson(endpoint, { method: "POST", headers: core.authHeaders() });
      core.invalidateUiRequestCache?.();
      core.notify("Запись восстановлена", { type: "success" });
      await loadRecentActivity({ force: true });
    }, {
      title: "Восстановление",
      confirmLabel: "Восстановить",
      confirmTone: "primary",
    });
  }

  async function handleActivityCenterAction(action, eventId) {
    const item = findRecentEvent(eventId);
    if (!item) return;
    if (action === "restore") {
      await restoreActivityEntity(item);
      return;
    }
    await openActivityEntity(item);
  }

  function renderChanges(changes) {
    if (!Array.isArray(changes) || !changes.length) {
      return "";
    }
    return `
      <ul class="activity-change-list">
        ${changes.map((change) => `
          <li>
            <span>${core.escapeHtml(change.label || change.field || "Поле")}</span>
            <strong>${core.escapeHtml(change.old_display ?? "")}</strong>
            <span aria-hidden="true">→</span>
            <strong>${core.escapeHtml(change.new_display ?? "")}</strong>
          </li>
        `).join("")}
      </ul>
    `;
  }

  function renderMetadataDisplay(items) {
    if (!Array.isArray(items) || !items.length) {
      return "";
    }
    return `
      <div class="activity-metadata-list">
        ${items.map((item) => `<span class="meta-chip meta-chip-info">${core.escapeHtml(item)}</span>`).join("")}
      </div>
    `;
  }

  function renderEvents(items) {
    if (!el.activityList) {
      return;
    }
    if (!Array.isArray(items) || !items.length) {
      el.activityList.innerHTML = "<div class='muted-small'>Журнал пока пуст</div>";
      return;
    }
    el.activityList.innerHTML = items.map((item) => `
      <article class="activity-event">
        <div class="activity-event-head">
          <strong>${core.escapeHtml(item.title || "Событие")}</strong>
          <span class="muted-small">${core.escapeHtml(formatEventDate(item.created_at))}</span>
        </div>
        ${(item.entity_label || item.entity_summary) ? `
          <div class="activity-event-context">
            ${item.entity_label ? `<strong>${core.escapeHtml(item.entity_label)}</strong>` : ""}
            ${item.entity_summary ? `<span>${core.escapeHtml(item.entity_summary)}</span>` : ""}
          </div>
        ` : ""}
        ${renderChanges(item.changes)}
        ${renderMetadataDisplay(item.metadata_display)}
      </article>
    `).join("");
  }

  async function openActivityModal(entityType = "", entityId = 0) {
    if (!el.activityModal || !el.activityList) {
      return;
    }
    const normalizedId = Number(entityId || 0);
    const isEntityHistory = Boolean(entityType && normalizedId);
    const label = entityLabels[entityType] || "карточки";
    if (el.activityModalTitle) {
      el.activityModalTitle.textContent = "Журнал действий";
    }
    if (el.activityModalSubtitle) {
      el.activityModalSubtitle.textContent = isEntityHistory ? `История ${label}` : "Все изменения по разделам";
    }
    el.activityList.innerHTML = "<div class='muted-small'>Загрузка журнала...</div>";
    el.activityModal.classList.remove("hidden");
    core.bringModalToFront?.(el.activityModal);
    try {
      const params = new URLSearchParams({ page_size: "100" });
      if (isEntityHistory) {
        params.set("entity_type", entityType);
        params.set("entity_id", String(normalizedId));
      }
      const payload = await core.requestJson(`/api/v1/activity?${params.toString()}`, {
        headers: core.authHeaders(),
      });
      renderEvents(payload.items || []);
    } catch (err) {
      el.activityList.innerHTML = `<div class="form-error">Не удалось загрузить журнал: ${core.escapeHtml(String(err?.message || err))}</div>`;
    }
  }

  function closeActivityModal() {
    el.activityModal?.classList.add("hidden");
    core.markModalClosed?.(el.activityModal);
  }

  function bindActivityUi() {
    document.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-activity-entity-type][data-activity-entity-id]");
      if (!btn) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      closeOpenActionPopover(btn);
      const entityType = btn.dataset.activityEntityType || "";
      const entityId = Number(btn.dataset.activityEntityId || 0);
      if (!entityType || !entityId) {
        return;
      }
      core.runAction({
        errorPrefix: "Ошибка открытия журнала",
        action: () => openActivityModal(entityType, entityId),
      });
    });
    el.closeActivityModalBtn?.addEventListener("click", closeActivityModal);
    el.activityCenterToggleBtn?.addEventListener("click", () => {
      toggleActivityCenter().catch((err) => core.setStatus(String(err)));
    });
    el.activityCenterCloseBtn?.addEventListener("click", closeActivityCenter);
    el.activityCenterOverlay?.addEventListener("click", closeActivityCenter);
    el.activityCenterAllBtn?.addEventListener("click", () => {
      closeActivityCenter();
      openActivityModal().catch((err) => core.setStatus(String(err)));
    });
    el.activityCenterList?.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-activity-center-event-id][data-activity-center-action]");
      if (!button) return;
      core.runAction({
        errorPrefix: "Не удалось выполнить действие",
        action: () => handleActivityCenterAction(button.dataset.activityCenterAction, Number(button.dataset.activityCenterEventId)),
      });
    });
    document.addEventListener("app:activity-changed", () => {
      clearTimeout(recentRefreshTimer);
      if (el.activityCenterDrawer?.classList.contains("hidden")) {
        el.activityCenterBadge?.classList.remove("hidden");
        return;
      }
      recentRefreshTimer = setTimeout(() => {
        loadRecentActivity({ force: true }).catch(() => {});
      }, 180);
    });
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible" && !el.activityCenterDrawer?.classList.contains("hidden")) {
        loadRecentActivity({ force: true }).catch(() => {});
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !el.activityCenterDrawer?.classList.contains("hidden")) {
        closeActivityCenter();
      }
    });
    el.activityModal?.addEventListener("click", (event) => {
      if (event.target === el.activityModal) {
        closeActivityModal();
      }
    });
  }

  const api = {
    bindActivityUi,
    configureActivityButton,
    openActivityModal,
    closeActivityModal,
    loadRecentActivity,
    toggleActivityCenter,
    closeActivityCenter,
  };
  window.App.registerRuntimeModule?.("activity", api);
})();
