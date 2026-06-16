(() => {
  const { el, core } = window.App;
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
        ${renderChanges(item.changes)}
        ${renderMetadataDisplay(item.metadata_display)}
      </article>
    `).join("");
  }

  async function openActivityModal(entityType, entityId) {
    if (!el.activityModal || !el.activityList) {
      return;
    }
    const label = entityLabels[entityType] || "карточки";
    if (el.activityModalTitle) {
      el.activityModalTitle.textContent = "Журнал действий";
    }
    if (el.activityModalSubtitle) {
      el.activityModalSubtitle.textContent = `История ${label}`;
    }
    el.activityList.innerHTML = "<div class='muted-small'>Загрузка журнала...</div>";
    el.activityModal.classList.remove("hidden");
    core.bringModalToFront?.(el.activityModal);
    try {
      const params = new URLSearchParams({
        entity_type: entityType,
        entity_id: String(entityId),
        page_size: "100",
      });
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
  };
  window.App.registerRuntimeModule?.("activity", api);
})();
