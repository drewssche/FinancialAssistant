(() => {
  function createPlansRenderFeature(deps) {
    const {
      state,
      core,
      getCategoryMetaById,
      getPlanBaseAmountValue,
    } = deps;

    function getPlanDisplayCategories(item) {
      const categories = core.getReceiptCategoryMetas
        ? core.getReceiptCategoryMetas(item?.receipt_items, item?.category_id, getCategoryMetaById)
        : [];
      if (categories.length) {
        return categories;
      }
      if (item?.category_name) {
        return [{
          id: item?.category_id ? Number(item.category_id) : null,
          name: item.category_name,
          icon: item.category_icon || null,
          accent_color: item.category_accent_color || null,
        }];
      }
      const fallback = getCategoryMetaById(item?.category_id);
      return fallback?.name ? [fallback] : [];
    }

    function formatPlanAmountHtml(item) {
      const originalAmount = Number((item?.original_amount ?? item?.amount) || 0);
      const currency = String(item?.currency || "BYN").toUpperCase();
      const baseCurrency = String(item?.base_currency || (core.getCurrencyConfig?.().code || "BYN")).toUpperCase();
      if (currency === baseCurrency) {
        return core.formatMoney(originalAmount, { currency });
      }
      const currentBaseAmount = getPlanBaseAmountValue(item);
      const currentRate = Number(item?.current_rate || 0);
      const rateDate = item?.current_rate_date ? core.formatDateRu(item.current_rate_date) : "";
      const secondary = currentRate > 0
        ? `≈ ${core.formatMoney(currentBaseAmount, { currency: baseCurrency })} по текущему курсу${rateDate ? ` · ${rateDate}` : ""}`
        : `≈ ${core.formatMoney(currentBaseAmount, { currency: baseCurrency })}`;
      return `
        <span class="plan-card-amount-primary">${core.formatMoney(originalAmount, { currency })}</span>
        <span class="muted-small plan-card-amount-secondary">${secondary}</span>
      `;
    }

    function dueProgressMeta(item) {
      const dueDate = String(item.due_date || "").trim();
      if (!dueDate) {
        return { label: "Без срока", tone: "none", percent: 0 };
      }
      const dueAt = new Date(`${dueDate}T23:59:59`);
      if (Number.isNaN(dueAt.getTime())) {
        return { label: `Срок: ${core.formatDateRu(dueDate)}`, tone: "none", percent: 0 };
      }
      const anchorRaw = item.progress_anchor_at || item.created_at || "";
      const anchorAt = anchorRaw ? new Date(anchorRaw) : null;
      const anchorMs = anchorAt && !Number.isNaN(anchorAt.getTime()) ? anchorAt.getTime() : Date.now();
      const totalMs = Math.max(86400000, dueAt.getTime() - anchorMs);
      const elapsedMs = Math.max(0, Date.now() - anchorMs);
      const percent = Math.max(0, Math.min(100, Math.round((elapsedMs / totalMs) * 100)));
      if (item.status === "overdue") {
        return { label: `Просрочен с ${core.formatDateRu(dueDate)}`, tone: "overdue", percent: 100 };
      }
      if (item.status === "due") {
        return { label: `Срок: ${core.formatDateRu(dueDate)}`, tone: "due", percent: Math.max(90, percent) };
      }
      return { label: `Срок: ${core.formatDateRu(dueDate)}`, tone: "upcoming", percent };
    }

    function planDueDaysBadge(item) {
      const dueDate = String(item?.due_date || "").trim();
      if (!dueDate) {
        return "";
      }
      const dueAt = new Date(`${dueDate}T23:59:59`);
      if (Number.isNaN(dueAt.getTime())) {
        return "";
      }
      if (item.status === "confirmed") {
        return "Закрыт";
      }
      if (item.status === "skipped") {
        return "Пропущен";
      }
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const dueDay = new Date(`${dueDate}T00:00:00`);
      const diffDays = Math.round((dueDay.getTime() - today.getTime()) / 86400000);
      if (diffDays < 0) {
        const overdueDays = Math.abs(diffDays);
        return overdueDays === 1 ? "Просрочен на 1 день" : `Просрочен на ${overdueDays} дн.`;
      }
      if (diffDays === 0) {
        return "Сегодня";
      }
      if (diffDays === 1) {
        return "Остался 1 день";
      }
      return `Осталось ${diffDays} дн.`;
    }

    function planDueDaysBadgeTone(progressTone) {
      if (progressTone === "overdue") {
        return "overdue";
      }
      if (progressTone === "due") {
        return "soon";
      }
      if (progressTone === "upcoming") {
        return "future";
      }
      return "none";
    }

    function recurrenceLabel(item) {
      if (!item.recurrence_enabled) {
        return "Разовый";
      }
      return item.recurrence_label || "Регулярный";
    }

    function statusLabel(status) {
      if (status === "overdue") {
        return "Просрочен";
      }
      if (status === "due") {
        return "К подтверждению";
      }
      if (status === "confirmed") {
        return "Подтвержден";
      }
      if (status === "skipped") {
        return "Пропущен";
      }
      return "Запланирован";
    }

    function formatDateTimeRu(value) {
      if (!value) {
        return "";
      }
      try {
        const date = value instanceof Date ? value : new Date(value);
        if (Number.isNaN(date.getTime())) {
          return String(value);
        }
        return new Intl.DateTimeFormat("ru-RU", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        }).format(date);
      } catch {
        return String(value);
      }
    }

    function getUserReminderTimeZone() {
      const preferred = String(state.preferences?.data?.ui?.timezone || "").trim();
      const browserTimeZone = String(state.preferences?.data?.ui?.browser_timezone || "").trim();
      if (preferred && preferred !== "auto") {
        return preferred;
      }
      if (browserTimeZone) {
        return browserTimeZone;
      }
      try {
        return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
      } catch {
        return "UTC";
      }
    }

    function reminderLabel(item) {
      if (!item?.next_reminder_at) {
        return "";
      }
      try {
        const reminderAt = new Date(item.next_reminder_at);
        if (Number.isNaN(reminderAt.getTime())) {
          return "";
        }
        if (reminderAt.getTime() <= Date.now() + 120000) {
          return "Напоминание скоро";
        }
        return `Напоминание ${new Intl.DateTimeFormat("ru-RU", {
          hour: "2-digit",
          minute: "2-digit",
          timeZone: getUserReminderTimeZone(),
        }).format(reminderAt)}`;
      } catch {
        return "";
      }
    }

    function historyEventLabel(eventType) {
      if (eventType === "confirmed") {
        return "Подтвержден";
      }
      if (eventType === "skipped") {
        return "Пропущен";
      }
      if (eventType === "reminded") {
        return "Напоминание";
      }
      return "Событие";
    }

    function renderPlanCard(item, options = {}) {
      const dashboardCompact = options.dashboardCompact === true;
      const hideActions = options.hideActions === true;
      const kindClass = item.kind === "income" ? "income" : "expense";
      const categoryChips = core.renderCategoryChipList
        ? core.renderCategoryChipList(getPlanDisplayCategories(item), "")
        : "<span class='muted-small'>Без категории</span>";
      const dateLabel = item.due_date ? core.formatDateRu(item.due_date) : "Без срока";
      const progress = dueProgressMeta(item);
      const dueDays = planDueDaysBadge(item);
      const dueDaysTone = planDueDaysBadgeTone(progress.tone);
      const kindLabel = item.kind === "income" ? "Доход" : "Расход";
      const hasReceiptItems = Array.isArray(item.receipt_items) && item.receipt_items.length > 0;
      const reminderText = reminderLabel(item);
      const reminderMeta = reminderText
        ? `<span class="meta-chip meta-chip-neutral">${core.escapeHtml(reminderText)}</span>`
        : "";
      const positionsMeta = hasReceiptItems
        ? `<button class="meta-chip-btn meta-chip-btn-neutral" type="button" data-plan-receipt-view-id="${item.id}">Чек</button>`
        : "";
      const noteMeta = item.note ? `<span class="muted-small">${core.highlightText(item.note, "")}</span>` : "";
      const showConfirm = item.status !== "confirmed" && item.status !== "skipped";
      const canEdit = !dashboardCompact && showConfirm;
      const canSkip = !dashboardCompact && item.recurrence_enabled && item.status !== "confirmed";
      const canDelete = !dashboardCompact;
      const showMenu = canEdit || canSkip || canDelete;
      const interactiveClass = canEdit ? " plan-card-interactive" : "";
      const interactiveAttrs = canEdit ? ` data-plan-card-edit-id="${item.id}" tabindex="0"` : "";
      return `
        <article class="panel plan-card plan-card-kind-${kindClass} plan-card-${item.status || "upcoming"}${interactiveClass}"${interactiveAttrs}>
          <div class="plan-card-topline">
            <div class="plan-card-top-meta">
              <span class="meta-chip meta-chip-neutral">${recurrenceLabel(item)}</span>
              <span class="meta-chip meta-chip-neutral">${statusLabel(item.status)}</span>
              ${reminderMeta}
            </div>
            ${showMenu ? `
              <div class="plan-card-menu-wrap">
                <button class="btn btn-secondary plan-card-menu-trigger" type="button" data-plan-menu-trigger="${item.id}" aria-label="Дополнительные действия">
                  <span aria-hidden="true">⋮</span>
                </button>
                <div class="app-popover hidden plan-card-actions-popover table-kebab-popover" data-plan-menu="${item.id}">
                  <div class="plan-card-actions-menu table-kebab-menu">
                    <button class="btn btn-secondary" type="button" data-activity-entity-type="plan" data-activity-entity-id="${item.id}">Журнал</button>
                    ${canEdit ? `<button class="btn btn-secondary" type="button" data-plan-action="edit" data-plan-id="${item.id}">Редактировать</button>` : ""}
                    ${canSkip ? `<button class="btn btn-secondary" type="button" data-plan-action="skip" data-plan-id="${item.id}">Пропустить</button>` : ""}
                    ${canDelete ? `<button class="btn btn-danger" type="button" data-plan-action="delete" data-plan-id="${item.id}">Удалить</button>` : ""}
                  </div>
                </div>
              </div>` : ""}
          </div>
          <div class="plan-card-row">
            <div class="plan-card-primary">
              <div class="plan-card-summary">
                <div class="plan-card-date">
                  <span class="muted-small">Дата</span>
                  <strong>${dateLabel}</strong>
                </div>
                <div class="plan-card-context">
                  <div class="plan-card-title-row">
                    <span class="kind-pill kind-pill-${kindClass}">${kindLabel}</span>
                    <div class="plan-card-category-list">${categoryChips}</div>
                    ${positionsMeta}
                  </div>
                  ${noteMeta ? `<div class="plan-card-meta">${noteMeta}</div>` : ""}
                </div>
              </div>
              <div class="plan-card-progress">
                <div class="plan-card-progress-head">
                  <span class="muted-small">${progress.label}</span>
                  ${dueDays ? `<span class="debt-due-days-badge debt-due-days-badge-${dueDaysTone}">${dueDays}</span>` : ""}
                </div>
                <div class="plan-card-progress-track">
                  <span class="plan-card-progress-bar plan-card-progress-bar-${progress.tone}" style="width:${progress.percent}%"></span>
                </div>
              </div>
            </div>
            <div class="plan-card-side">
              <div class="plan-card-amount-block">
                <span class="muted-small">Сумма</span>
                <strong class="plan-card-amount amount-${kindClass}">${formatPlanAmountHtml(item)}</strong>
              </div>
            ${hideActions ? "" : `
              <div class="actions row-actions plan-card-actions">
                ${showConfirm ? `<button class="btn btn-primary" type="button" data-plan-action="confirm" data-plan-id="${item.id}">В операцию</button>` : ""}
              </div>`}
            </div>
          </div>
        </article>
      `;
    }

    function renderHistoryCard(item) {
      const kindClass = item.kind === "income" ? "income" : "expense";
      const categoryChip = item.category_name
        ? core.renderCategoryChip({ name: item.category_name, icon: "", accent_color: null }, "")
        : "<span class='muted-small'>Без категории</span>";
      const eventLabel = historyEventLabel(item.event_type);
      const effectiveDate = item.effective_date ? core.formatDateRu(item.effective_date) : "Без даты";
      const createdAt = item.created_at ? formatDateTimeRu(item.created_at) : "";
      const operationMeta = item.operation_id
        ? `<button class="meta-chip-btn meta-chip-btn-neutral" type="button" data-plan-history-operation-id="${Number(item.operation_id)}">Операция #${Number(item.operation_id)}</button>`
        : "";
      return `
        <article class="panel plan-card plan-history-card plan-history-card-${item.event_type || "event"}">
          <div class="plan-card-main">
            <div class="plan-card-head">
              <div class="plan-card-title-row">
                ${categoryChip}
                <span class="meta-chip meta-chip-neutral">${eventLabel}</span>
              </div>
              <strong class="plan-card-amount amount-${kindClass}">${formatPlanAmountHtml(item)}</strong>
            </div>
            <div class="plan-card-meta">
              ${item.note ? `<strong>${core.highlightText(item.note, "")}</strong>` : ""}
              <span class="muted-small">Дата плана: ${effectiveDate}</span>
              ${createdAt ? `<span class="muted-small">Событие: ${createdAt}</span>` : ""}
              ${operationMeta}
            </div>
            <div class="actions row-actions plan-card-actions">
              <button class="btn btn-secondary" type="button" data-activity-entity-type="plan" data-activity-entity-id="${Number(item.plan_id)}">Журнал плана</button>
            </div>
          </div>
        </article>
      `;
    }

    return {
      renderPlanCard,
      renderHistoryCard,
      getPlanDisplayCategories,
      formatPlanAmountHtml,
    };
  }

  window.App.registerRuntimeModule?.("plans-render", createPlansRenderFeature);
})();
