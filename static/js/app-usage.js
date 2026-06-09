(() => {
  const { el, core } = window.App;
  let currentUsage = null;

  const usageLabels = {
    category: {
      title: "Операции с категорией",
      subtitle: "Где используется категория",
      empty: "Операций с этой категорией пока нет",
    },
    item_template: {
      title: "Операции с позицией",
      subtitle: "Где используется позиция каталога",
      empty: "Операций с этой позицией пока нет",
    },
  };

  function getOperationsFeature() {
    return window.App.getRuntimeModule?.("operations") || {};
  }

  function configureUsageButton(button, entityType, entityId, entityName = "") {
    if (!button) {
      return;
    }
    const normalizedId = Number(entityId || 0);
    if (!entityType || !normalizedId) {
      button.classList.add("hidden");
      button.removeAttribute("data-usage-entity-type");
      button.removeAttribute("data-usage-entity-id");
      button.removeAttribute("data-usage-entity-name");
      return;
    }
    button.dataset.usageEntityType = entityType;
    button.dataset.usageEntityId = String(normalizedId);
    button.dataset.usageEntityName = entityName || "";
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

  function formatDate(value) {
    return value ? core.formatDateRu(value) : "—";
  }

  function usageParams(entityType, entityId) {
    const params = new URLSearchParams({
      source: "operation",
      page: "1",
      page_size: "100",
      sort_by: "operation_date",
      sort_dir: "desc",
    });
    if (entityType === "category") {
      params.set("category_id", String(entityId));
    }
    if (entityType === "item_template") {
      params.set("item_template_id", String(entityId));
    }
    return params;
  }

  function renderUsageKpi(summary, items) {
    if (!el.usageKpi) {
      return;
    }
    const count = Number(summary?.total || 0);
    const income = Number(summary?.income_total || 0);
    const expense = Number(summary?.expense_total || 0);
    const balance = Number(summary?.balance || 0);
    const lastUsed = Array.isArray(items) && items.length ? items[0]?.event_date : "";
    const balanceTone = balance > 0.000001
      ? "analytics-kpi-chip-positive"
      : balance < -0.000001
        ? "analytics-kpi-chip-negative"
        : "analytics-kpi-chip-neutral";
    el.usageKpi.innerHTML = `
      <span class="analytics-kpi-chip analytics-kpi-chip-neutral">Операций: ${count}</span>
      <span class="analytics-kpi-chip analytics-kpi-chip-positive">Приток: ${core.formatMoney(income)}</span>
      <span class="analytics-kpi-chip analytics-kpi-chip-negative">Отток: ${core.formatMoney(expense)}</span>
      <span class="analytics-kpi-chip ${balanceTone}">Поток: ${core.formatMoney(balance)}</span>
      <span class="analytics-kpi-chip analytics-kpi-chip-neutral">Последнее: ${formatDate(lastUsed)}</span>
    `;
  }

  function renderUsageList(items, emptyText) {
    if (!el.usageList) {
      return;
    }
    if (!Array.isArray(items) || !items.length) {
      el.usageList.innerHTML = `<div class="muted-small">${core.escapeHtml(emptyText)}</div>`;
      return;
    }
    el.usageList.innerHTML = items.map((item) => {
      const direction = item.flow_direction === "inflow" ? "Приток" : "Отток";
      const tone = item.flow_direction === "inflow" ? "income" : "expense";
      const title = item.title || item.category_name || "Операция";
      const subtitle = item.subtitle || "";
      return `
        <article class="activity-event usage-event">
          <div class="activity-event-head">
            <strong>${core.escapeHtml(title)}</strong>
            <span class="muted-small">${core.escapeHtml(formatDate(item.event_date))}</span>
          </div>
          <div class="usage-event-body">
            <span class="kind-pill kind-pill-${tone}">${direction}</span>
            <strong>${core.formatMoney(item.amount || 0, { currency: item.base_currency || item.currency || undefined })}</strong>
            ${subtitle ? `<span class="muted-small">${core.escapeHtml(subtitle)}</span>` : ""}
            ${item.note ? `<span class="muted-small">${core.escapeHtml(item.note)}</span>` : ""}
          </div>
        </article>
      `;
    }).join("");
  }

  async function openUsageModal(entityType, entityId, entityName = "") {
    const normalizedId = Number(entityId || 0);
    if (!el.usageModal || !el.usageList || !normalizedId) {
      return;
    }
    const labels = usageLabels[entityType] || usageLabels.category;
    currentUsage = {
      entityType,
      entityId: normalizedId,
      entityName: entityName || "",
    };
    if (el.usageModalTitle) {
      el.usageModalTitle.textContent = labels.title;
    }
    if (el.usageModalSubtitle) {
      el.usageModalSubtitle.textContent = entityName ? `${labels.subtitle}: ${entityName}` : labels.subtitle;
    }
    if (el.usageKpi) {
      el.usageKpi.innerHTML = "";
    }
    el.usageList.innerHTML = "<div class='muted-small'>Загрузка операций...</div>";
    el.usageModal.classList.remove("hidden");
    const params = usageParams(entityType, normalizedId);
    try {
      const [listPayload, summaryPayload] = await Promise.all([
        core.requestJson(`/api/v1/operations/money-flow?${params.toString()}`, {
          headers: core.authHeaders(),
        }),
        core.requestJson(`/api/v1/operations/money-flow/summary?${params.toString()}`, {
          headers: core.authHeaders(),
        }),
      ]);
      const items = listPayload.items || [];
      renderUsageKpi(summaryPayload, items);
      renderUsageList(items, labels.empty);
    } catch (err) {
      el.usageList.innerHTML = `<div class="form-error">Не удалось загрузить операции: ${core.escapeHtml(String(err?.message || err))}</div>`;
    }
  }

  function closeUsageModal() {
    el.usageModal?.classList.add("hidden");
  }

  function openCurrentUsageInOperations() {
    if (!currentUsage) {
      return;
    }
    const operations = getOperationsFeature();
    closeUsageModal();
    if (currentUsage.entityType === "category") {
      operations.openOperationsForCategory?.(currentUsage.entityId, currentUsage.entityName);
      return;
    }
    if (currentUsage.entityType === "item_template") {
      operations.openOperationsForItemTemplate?.(currentUsage.entityId, currentUsage.entityName);
    }
  }

  function bindUsageUi() {
    document.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-usage-entity-type][data-usage-entity-id]");
      if (!btn) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      closeOpenActionPopover(btn);
      const entityType = btn.dataset.usageEntityType || "";
      const entityId = Number(btn.dataset.usageEntityId || 0);
      const entityName = btn.dataset.usageEntityName || "";
      core.runAction({
        errorPrefix: "Ошибка открытия операций",
        action: () => openUsageModal(entityType, entityId, entityName),
      });
    });
    el.closeUsageModalBtn?.addEventListener("click", closeUsageModal);
    el.usageModal?.addEventListener("click", (event) => {
      if (event.target === el.usageModal) {
        closeUsageModal();
      }
    });
    el.openUsageInOperationsBtn?.addEventListener("click", openCurrentUsageInOperations);
  }

  const api = {
    bindUsageUi,
    configureUsageButton,
    openUsageModal,
    closeUsageModal,
  };

  window.App.registerRuntimeModule?.("usage", api);
})();
