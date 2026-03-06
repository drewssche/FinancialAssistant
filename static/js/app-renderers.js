(() => {
  const { core } = window.App;

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function escapeRegExp(value) {
    return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function highlightText(value, query) {
    const safeText = escapeHtml(value);
    if (!query) {
      return safeText;
    }
    const pattern = new RegExp(`(${escapeRegExp(query)})`, "ig");
    return safeText.replace(pattern, "<mark class=\"search-highlight\">$1</mark>");
  }

  function renderCategoryChip(category, searchQuery = "") {
    if (!category?.name) {
      return "<span class='muted-small'>Без категории</span>";
    }
    const style = category.accent_color
      ? ` style="border-color:${escapeHtml(category.accent_color)}66;background:${escapeHtml(category.accent_color)}22;"`
      : "";
    const icon = category.icon ? `<span class="category-chip-icon">${escapeHtml(category.icon)}</span>` : "";
    return `<span class="category-chip"${style}>${icon}<span>${highlightText(category.name, searchQuery)}</span></span>`;
  }

  function parseAmount(value) {
    const amount = Number(value || 0);
    return Number.isFinite(amount) ? amount : 0;
  }

  function formatMoney(value) {
    return core.formatMoney(parseAmount(value));
  }

  function parseIsoDate(value) {
    if (!value) {
      return null;
    }
    const dt = new Date(`${value}T00:00:00`);
    return Number.isNaN(dt.getTime()) ? null : dt;
  }

  function parseIsoDateEnd(value) {
    if (!value) {
      return null;
    }
    const dt = new Date(`${value}T23:59:59`);
    return Number.isNaN(dt.getTime()) ? null : dt;
  }

  function debtDueState(debt, now = new Date()) {
    const outstanding = parseAmount(debt?.outstanding_total);
    if (outstanding <= 0) {
      return "closed";
    }
    const due = parseIsoDateEnd(debt?.due_date);
    if (!due) {
      return "none";
    }
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const diffDays = Math.floor((due.getTime() - todayStart.getTime()) / 86400000);
    if (diffDays < 0) {
      return "overdue";
    }
    if (diffDays <= 7) {
      return "soon";
    }
    return "future";
  }

  function debtDueProgress(debt, dueState, now = new Date()) {
    if (!debt?.due_date) {
      return null;
    }
    const due = parseIsoDateEnd(debt.due_date);
    const start = parseIsoDate(debt.start_date);
    if (!due || !start) {
      return null;
    }
    const totalMs = Math.max(86400000, due.getTime() - start.getTime());
    const elapsedMs = Math.max(0, now.getTime() - start.getTime());
    let percent = Math.round((elapsedMs / totalMs) * 100);
    percent = Math.max(0, Math.min(100, percent));
    let tone = "ok";
    if (dueState === "overdue") {
      tone = "danger";
      percent = 100;
    } else if (dueState === "soon" || percent >= 85) {
      tone = "warn";
    }
    return { percent, tone };
  }

  function debtDueDaysBadge(debt, dueState, now = new Date()) {
    if (!debt?.due_date) {
      return "";
    }
    const due = parseIsoDateEnd(debt.due_date);
    if (!due) {
      return "";
    }
    const diff = due.getTime() - now.getTime();
    const days = Math.ceil(diff / 86400000);
    if (dueState === "overdue") {
      return `Просрочено: ${Math.abs(days)} д.`;
    }
    if (dueState === "closed") {
      return "Закрыт";
    }
    return `Осталось: ${Math.max(0, days)} д.`;
  }

  function debtRepaymentProgress(debt) {
    const principal = parseAmount(debt?.principal);
    const repaid = parseAmount(debt?.repaid_total);
    const direction = debt?.direction === "borrow" ? "borrow" : "lend";
    if (principal <= 0) {
      return { percent: 0, tone: direction === "borrow" ? "borrow-danger" : "lend-ok" };
    }
    const percent = Math.max(0, Math.min(100, Math.round((repaid / principal) * 100)));
    if (direction === "borrow") {
      if (percent >= 100) {
        return { percent, tone: "borrow-ok" };
      }
      if (percent >= 40) {
        return { percent, tone: "borrow-warn" };
      }
      return { percent, tone: "borrow-danger" };
    }
    if (percent >= 100) {
      return { percent, tone: "lend-ok" };
    }
    if (percent >= 40) {
      return { percent, tone: "lend-warn" };
    }
    return { percent, tone: "lend-muted" };
  }

  function createOperationRow(item, options = {}) {
    const preview = options.preview === true;
    const compact = options.compact === true;
    const selectable = options.selectable === true;
    const selected = options.selected === true;
    const searchQuery = options.searchQuery || "";
    const category = options.category || null;
    const kindClass = item.kind === "income" ? "income" : "expense";
    const kindText = core.kindLabel(item.kind);
    const noteText = item.note || "";
    const row = document.createElement("tr");
    row.classList.add(`kind-row-${kindClass}`);

    if (compact) {
      const selectCell = selectable
        ? `<td class="select-col"><input class="table-checkbox" type="checkbox" data-select-operation-id="${item.id}" ${selected ? "checked" : ""} /></td>`
        : "";
      row.innerHTML = `
        ${selectCell}
        <td>${core.formatDateRu(item.operation_date)}</td>
        <td><span class="kind-pill kind-pill-${kindClass}">${highlightText(kindText, searchQuery)}</span></td>
        <td>${renderCategoryChip(category, searchQuery)}</td>
        <td><span class="amount-${kindClass}">${core.formatMoney(item.amount)}</span></td>
        <td>${highlightText(noteText, searchQuery)}</td>
      `;
      return row;
    }

    if (preview) {
      row.innerHTML = `
        <td>${core.formatDateRu(item.operation_date)}</td>
        <td><span class="kind-pill kind-pill-${kindClass}">${highlightText(kindText, searchQuery)}</span></td>
        <td>${renderCategoryChip(category, searchQuery)}</td>
        <td><span class="amount-${kindClass}">${core.formatMoney(item.amount)}</span></td>
        <td>${highlightText(noteText, searchQuery)}</td>
        <td>
          <div class="actions">
            <button class="btn btn-secondary" disabled>Редактировать</button>
            <button class="btn btn-danger" disabled>Удалить</button>
          </div>
        </td>
      `;
      row.classList.add("preview-row");
      return row;
    }

    const selectCell = selectable
      ? `<td class="select-col"><input class="table-checkbox" type="checkbox" data-select-operation-id="${item.id}" ${selected ? "checked" : ""} /></td>`
      : "";

    row.innerHTML = `
      ${selectCell}
      <td>${core.formatDateRu(item.operation_date)}</td>
      <td><span class="kind-pill kind-pill-${kindClass}">${highlightText(kindText, searchQuery)}</span></td>
      <td>${renderCategoryChip(category, searchQuery)}</td>
      <td><span class="amount-${kindClass}">${core.formatMoney(item.amount)}</span></td>
      <td>${highlightText(noteText, searchQuery)}</td>
      <td>
        <div class="actions row-actions">
          <button class="btn btn-secondary" data-edit-id="${item.id}">Редактировать</button>
          <button class="btn btn-danger" data-delete-id="${item.id}">Удалить</button>
        </div>
      </td>
    `;
    row.dataset.item = JSON.stringify(item);
    if (selected) {
      row.classList.add("row-selected");
    }
    return row;
  }

  Object.assign(core, {
    highlightText,
    renderCategoryChip,
    createOperationRow,
    debtUi: {
      parseAmount,
      formatMoney,
      parseIsoDate,
      parseIsoDateEnd,
      debtDueState,
      debtDueProgress,
      debtDueDaysBadge,
      debtRepaymentProgress,
    },
  });
})();
