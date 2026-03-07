(() => {
  function build({
    state,
    el,
    core,
    getSelectedCreateCategoryId,
    getCategoryMetaById,
  }) {
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
      const now = new Date();
      const due = new Date(`${dueDateValue}T23:59:59`);
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
        .filter((item) => Number(item?.quantity || 0) > 0 && Number(item?.unit_price || 0) > 0 && String(item?.name || "").trim());
      const receiptTotal = receiptItems.reduce((acc, item) => {
        const qty = Number(item.quantity || 0);
        const price = Number(item.unit_price || 0);
        if (!Number.isFinite(qty) || !Number.isFinite(price)) {
          return acc;
        }
        return acc + qty * price;
      }, 0);
      const amountRaw = document.getElementById("opAmount").value;
      const amountResolved = String(amountRaw || "").trim()
        ? amountRaw
        : (el.opReceiptEnabled?.checked && receiptTotal > 0 ? receiptTotal : 0);
      const noteRaw = document.getElementById("opNote").value || "";
      return {
        id: 0,
        operation_date: document.getElementById("opDate").value || new Date().toISOString().slice(0, 10),
        kind: el.opKind.value || "expense",
        category_id: getSelectedCreateCategoryId(),
        amount: core.formatAmount(amountResolved),
        note: noteRaw,
      };
    }

    function getEditFormPreviewItem() {
      return {
        id: state.editOperationId || 0,
        operation_date: document.getElementById("editDate").value || new Date().toISOString().slice(0, 10),
        kind: el.editKind.value || "expense",
        category_id: el.editCategory.value ? Number(el.editCategory.value) : null,
        amount: core.formatAmount(document.getElementById("editAmount").value),
        note: document.getElementById("editNote").value || "",
      };
    }

    function updateCreatePreview() {
      el.createPreviewBody.innerHTML = "";
      if (el.opEntryMode.value === "debt") {
        const row = document.createElement("tr");
        const direction = el.debtDirection.value === "borrow" ? "borrow" : "lend";
        const directionLabel = core.debtUi.debtDirectionActionLabel(direction);
        const directionClass = direction === "borrow" ? "expense" : "income";
        const debtDate = el.debtStartDate.value || new Date().toISOString().slice(0, 10);
        const debtDueDate = el.debtDueDate.value || "";
        const debtCounterparty = (el.debtCounterparty.value || "").trim();
        const debtPrincipal = core.formatMoney(el.debtPrincipal.value || 0);
        const debtNote = (el.debtNote.value || "").trim();
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
      const previewItem = getCreateFormPreviewItem();
      const category = getCategoryMetaById(previewItem.category_id);
      const row = document.createElement("tr");
      const kindClass = previewItem.kind === "income" ? "income" : "expense";
      const categoryHtml = core.renderCategoryChip(category);
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
      row.appendChild(createPreviewCellButton("Категория", categoryHtml, "opCategorySearch"));
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
      el.editPreviewBody.appendChild(
        core.createOperationRow(item, {
          preview: true,
          category: getCategoryMetaById(item.category_id),
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
