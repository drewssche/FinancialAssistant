(() => {
  function build({
    state,
    el,
    core,
    getSelectedCreateCategoryId,
    getCategoryMetaById,
    getDebtPreviewSnapshot,
  }) {
    function getReceiptSummaryCategories(receiptItems, fallbackCategoryId = null) {
      const categories = core.getReceiptCategoryMetas
        ? core.getReceiptCategoryMetas(receiptItems, fallbackCategoryId, getCategoryMetaById)
        : [];
      if (categories.length) {
        return categories;
      }
      const fallback = getCategoryMetaById(fallbackCategoryId);
      return fallback?.name ? [fallback] : [];
    }

    function focusCreateField(targetId) {
      const target = document.getElementById(targetId);
      if (!target) {
        return;
      }
      if (targetId === "createKindSwitch" || targetId === "createDebtDirectionSwitch") {
        const activeSelector = targetId === "createKindSwitch" ? "button[data-kind].active" : "button[data-debt-direction].active";
        const anySelector = targetId === "createKindSwitch" ? "button[data-kind]" : "button[data-debt-direction]";
        const activeKindBtn = target.querySelector(activeSelector) || target.querySelector(anySelector);
        if (activeKindBtn) {
          activeKindBtn.focus();
        }
        return;
      }
      target.focus();
    }

    function formatDueRelativeLabel(startDateValue, dueDateValue) {
      if (!dueDateValue) {
        return "Без срока";
      }
      const dueIso = core.parseDateInputValue(dueDateValue);
      if (!dueIso) {
        return "Без срока";
      }
      const now = new Date();
      const due = new Date(`${dueIso}T23:59:59`);
      if (Number.isNaN(due.getTime())) {
        return "Без срока";
      }
      const diffMs = due.getTime() - now.getTime();
      const dayMs = 86400000;
      const days = Math.ceil(diffMs / dayMs);
      if (days < 0) {
        return `Просрочено: ${Math.abs(days)} д.`;
      }
      if (days <= 13) {
        return `Осталось: ${days} д.`;
      }
      const weeks = Math.ceil(days / 7);
      if (weeks <= 8) {
        return `Осталось: ${weeks} нед.`;
      }
      const months = Math.ceil(days / 30);
      if (months <= 24) {
        return `Осталось: ${months} мес.`;
      }
      const years = Math.ceil(days / 365);
      return `Осталось: ${years} г.`;
    }

    function updateDebtDueHint() {
      if (!el.debtDueHint) {
        return;
      }
      const label = formatDueRelativeLabel(el.debtStartDate?.value || "", el.debtDueDate?.value || "");
      el.debtDueHint.textContent = label;
      el.debtDueHint.classList.remove("debt-due-inline-soon", "debt-due-inline-overdue");
      if (label.startsWith("Просрочено")) {
        el.debtDueHint.classList.add("debt-due-inline-overdue");
      } else if (label.includes("д.") || label.includes("нед.")) {
        const daysLeft = Number((label.match(/\d+/) || [0])[0]);
        if (!Number.isNaN(daysLeft) && daysLeft <= 7) {
          el.debtDueHint.classList.add("debt-due-inline-soon");
        }
      }
    }

    function createPreviewCellButton(label, value, targetId, extraClass = "") {
      const td = document.createElement("td");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `preview-cell-btn ${extraClass}`.trim();
      btn.dataset.focusTarget = targetId;
      btn.setAttribute("aria-label", label);
      btn.innerHTML = value;
      td.appendChild(btn);
      return td;
    }

    function getCreateFormPreviewItem() {
      const receiptItems = (Array.isArray(state.createReceiptItems) ? state.createReceiptItems : [])
        .filter((item) => Number(item?.quantity || 0) > 0 && Number(item?.unit_price || 0) > 0 && String(item?.name || "").trim())
        .map((item) => ({
          category_id: item.category_id ? Number(item.category_id) : null,
          quantity: item.quantity,
          unit_price: item.unit_price,
          name: item.name,
        }));
      const receiptTotal = receiptItems.reduce((acc, item) => {
        const qty = Number(item.quantity || 0);
        const price = Number(item.unit_price || 0);
        if (!Number.isFinite(qty) || !Number.isFinite(price)) {
          return acc;
        }
        return acc + qty * price;
      }, 0);
      const amountRaw = document.getElementById("opAmount").value;
      const parsedAmount = core.resolveMoneyInput(amountRaw);
      const amountResolved = !parsedAmount.empty
        ? parsedAmount.previewValue
        : (el.opOperationMode?.value === "receipt" && receiptTotal > 0 ? receiptTotal : 0);
      const noteRaw = document.getElementById("opNote").value || "";
      const operationDate = core.parseDateInputValue(document.getElementById("opDate").value) || core.getTodayIso();
      return {
        id: 0,
        operation_date: operationDate,
        kind: el.opKind.value || "expense",
        category_id: getSelectedCreateCategoryId(),
        amount: core.formatAmount(amountResolved),
        note: noteRaw,
        receipt_items: el.opOperationMode?.value === "receipt" ? receiptItems : [],
      };
    }

    function getEditFormPreviewItem() {
      const operationDate = core.parseDateInputValue(document.getElementById("editDate").value) || core.getTodayIso();
      const amountResolved = core.resolveMoneyInput(document.getElementById("editAmount").value);
      return {
        id: state.editOperationId || 0,
        operation_date: operationDate,
        kind: el.editKind.value || "expense",
        category_id: el.editCategory.value ? Number(el.editCategory.value) : null,
        amount: amountResolved.previewFormatted,
        note: document.getElementById("editNote").value || "",
        receipt_items: el.editOperationMode?.value === "receipt" ? (state.editReceiptItems || []) : [],
      };
    }

    function updateCreatePreview() {
      el.createPreviewBody.innerHTML = "";
      if (el.createPlanPreviewCard) {
        el.createPlanPreviewCard.classList.add("hidden");
        el.createPlanPreviewCard.innerHTML = "";
      }
      if (el.createPreviewTableWrap) {
        el.createPreviewTableWrap.classList.remove("hidden");
      }
      if (el.createPreviewTitle) {
        el.createPreviewTitle.textContent = "Превью строки в таблице";
      }
      if (el.opEntryMode.value === "debt") {
        const row = document.createElement("tr");
        const snapshot = typeof getDebtPreviewSnapshot === "function" ? getDebtPreviewSnapshot() : null;
        const direction = snapshot?.direction === "borrow" ? "borrow" : "lend";
        const directionLabel = core.debtUi.debtDirectionActionLabel(direction);
        const directionClass = direction === "borrow" ? "expense" : "income";
        const debtDate = snapshot?.startDate || core.parseDateInputValue(el.debtStartDate.value) || core.getTodayIso();
        const debtDueDate = snapshot?.dueDate || core.parseDateInputValue(el.debtDueDate.value) || "";
        const debtCounterparty = snapshot?.counterparty || (el.debtCounterparty.value || "").trim();
        const debtPrincipal = core.formatMoney(snapshot?.principalValue ?? core.resolveMoneyInput(el.debtPrincipal.value || 0).previewValue);
        const debtNote = snapshot?.note ?? (el.debtNote.value || "").trim();
        row.classList.add("preview-row", `kind-row-${directionClass}`);
        row.appendChild(createPreviewCellButton("Дата", core.formatDateRu(debtDate), "debtStartDate"));
        row.appendChild(
          createPreviewCellButton(
            "Направление",
            `<span class="debt-direction-pill debt-direction-pill-${direction}">${directionLabel}</span>`,
            "createDebtDirectionSwitch",
          ),
        );
        row.appendChild(createPreviewCellButton("Контрагент", core.highlightText(debtCounterparty || "Без имени", ""), "debtCounterparty"));
        row.appendChild(createPreviewCellButton("Сумма", debtPrincipal, "debtPrincipal"));
        row.appendChild(createPreviewCellButton("Срок", debtDueDate ? core.formatDateRu(debtDueDate) : "Без срока", "debtDueDate"));
        row.appendChild(createPreviewCellButton("Комментарий", core.highlightText(debtNote || "", ""), "debtNote", "preview-cell-note"));
        el.createPreviewBody.appendChild(row);
        updateDebtDueHint();
        return;
      }
      if (state.createFlowMode === "plan") {
        const previewItem = getCreateFormPreviewItem();
        const recurrenceEnabled = (el.planScheduleMode?.value || "oneoff") === "recurring";
        const frequency = el.planRecurrenceFrequency?.value || "monthly";
        const interval = Math.max(1, Number(el.planRecurrenceInterval?.value || 1));
        const workdaysOnlyEnabled = String(el.planRecurrenceWorkdaysOnly?.value || "off") === "on";
        const monthEndEnabled = String(el.planRecurrenceMonthEnd?.value || "off") === "on";
        const recurrenceLabel = !recurrenceEnabled
          ? "Разовый"
          : frequency === "weekly"
            ? "Еженедельно"
            : frequency === "daily"
              ? (workdaysOnlyEnabled ? "По будням" : "Ежедневно")
              : frequency === "yearly"
                ? "Ежегодно"
                : (monthEndEnabled ? "В последний день месяца" : "Ежемесячно");
        const planItem = {
          ...previewItem,
          due_date: previewItem.operation_date,
          status: "upcoming",
          recurrence_enabled: recurrenceEnabled,
          recurrence_frequency: recurrenceEnabled ? frequency : null,
          recurrence_interval: recurrenceEnabled ? interval : 1,
          recurrence_weekdays: recurrenceEnabled && frequency === "weekly"
            ? Array.from(el.planRecurrenceWeekdays?.querySelectorAll("button[data-plan-weekday].active") || []).map((button) => Number(button.dataset.planWeekday || 0))
            : [],
          recurrence_workdays_only: recurrenceEnabled && frequency === "daily" ? workdaysOnlyEnabled : false,
          recurrence_month_end: recurrenceEnabled && frequency === "monthly" ? monthEndEnabled : false,
          recurrence_label: recurrenceLabel,
        };
        if (el.createPreviewTitle) {
          el.createPreviewTitle.textContent = "Превью строки в таблице";
        }
        if (el.createPreviewTableWrap) {
          el.createPreviewTableWrap.classList.add("hidden");
        }
        if (el.createPlanPreviewCard) {
          const renderPlanCardMarkup = window.App.featurePlans?.renderPlanCardMarkup;
          el.createPlanPreviewCard.classList.remove("hidden");
          el.createPlanPreviewCard.innerHTML = typeof renderPlanCardMarkup === "function"
            ? renderPlanCardMarkup(planItem, { hideActions: true })
            : "";
        }
        return;
      }
      const previewItem = getCreateFormPreviewItem();
      const receiptMode = el.opOperationMode?.value === "receipt";
      const categories = receiptMode
        ? getReceiptSummaryCategories(previewItem.receipt_items, previewItem.category_id)
        : (() => {
          const category = getCategoryMetaById(previewItem.category_id);
          return category?.name ? [category] : [];
        })();
      const row = document.createElement("tr");
      const kindClass = previewItem.kind === "income" ? "income" : "expense";
      const categoryHtml = core.renderCategoryChipList
        ? core.renderCategoryChipList(categories, "")
        : "<span class='muted-small'>Без категории</span>";
      const categoryCellHtml = receiptMode
        ? `<div class="operation-category-stack">${categoryHtml}${core.renderMetaChip("Чек")}</div>`
        : categoryHtml;
      const noteText = core.highlightText(previewItem.note || "", "");
      row.classList.add("preview-row", `kind-row-${kindClass}`);
      row.appendChild(createPreviewCellButton("Дата", core.formatDateRu(previewItem.operation_date), "opDate"));
      row.appendChild(
        createPreviewCellButton(
          "Тип",
          `<span class="kind-pill kind-pill-${kindClass}">${core.kindLabel(previewItem.kind)}</span>`,
          "createKindSwitch",
        ),
      );
      row.appendChild(createPreviewCellButton("Категория", categoryCellHtml, "opCategorySearch"));
      row.appendChild(createPreviewCellButton("Сумма", `<span class="amount-${kindClass}">${core.formatMoney(previewItem.amount)}</span>`, "opAmount"));
      row.appendChild(createPreviewCellButton("Комментарий", noteText, "opNote", "preview-cell-note"));
      el.createPreviewBody.appendChild(row);
    }

    function updateEditPreview() {
      if (!el.editPreviewBody) {
        return;
      }
      const item = getEditFormPreviewItem();
      el.editPreviewBody.innerHTML = "";
      const categories = el.editOperationMode?.value === "receipt"
        ? getReceiptSummaryCategories(item.receipt_items, item.category_id)
        : (() => {
          const fallback = getCategoryMetaById(item.category_id);
          return fallback?.name ? [fallback] : [];
        })();
      el.editPreviewBody.appendChild(
        core.createOperationRow(item, {
          preview: true,
          category: categories[0] || null,
          categories,
        }),
      );
    }

    function handleCreatePreviewClick(event) {
      const btn = event.target.closest("button[data-focus-target]");
      if (!btn) {
        return;
      }
      focusCreateField(btn.dataset.focusTarget || "");
    }

    return {
      formatDueRelativeLabel,
      updateDebtDueHint,
      getCreateFormPreviewItem,
      getEditFormPreviewItem,
      updateCreatePreview,
      updateEditPreview,
      handleCreatePreviewClick,
    };
  }

  window.App.operationModalPreview = {
    build,
  };
})();
