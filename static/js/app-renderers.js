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
        <td><span class="amount-${kindClass}">${item.amount}</span></td>
        <td>${highlightText(noteText, searchQuery)}</td>
      `;
      return row;
    }

    if (preview) {
      row.innerHTML = `
        <td>${core.formatDateRu(item.operation_date)}</td>
        <td><span class="kind-pill kind-pill-${kindClass}">${highlightText(kindText, searchQuery)}</span></td>
        <td>${renderCategoryChip(category, searchQuery)}</td>
        <td><span class="amount-${kindClass}">${item.amount}</span></td>
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
      <td><span class="amount-${kindClass}">${item.amount}</span></td>
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
  });
})();
