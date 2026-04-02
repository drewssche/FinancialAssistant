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
    const title = ` title="${escapeHtml(category.name)}"`;
    const icon = category.icon ? `<span class="category-chip-icon">${escapeHtml(category.icon)}</span>` : "";
    return `<span class="category-chip"${style}${title}>${icon}<span class="category-chip-text">${highlightText(category.name, searchQuery)}</span></span>`;
  }

  function renderCategoryChipList(categories, searchQuery = "") {
    const items = Array.isArray(categories) ? categories.filter((item) => item?.name) : [];
    if (!items.length) {
      return "<span class='muted-small'>Без категории</span>";
    }
    const stackClass = items.length > 1 ? " category-chip-list-stack" : "";
    return `<div class="category-chip-list${stackClass}">${items.map((item) => renderCategoryChip(item, searchQuery)).join("")}</div>`;
  }

  function getReceiptCategoryMetas(receiptItems, fallbackCategoryId, getCategoryMetaById) {
    const byKey = new Map();
    const fallbackId = Number(fallbackCategoryId || 0);
    for (const row of Array.isArray(receiptItems) ? receiptItems : []) {
      const explicitCategoryId = Number(row?.category_id || 0);
      const categoryId = explicitCategoryId > 0 ? explicitCategoryId : fallbackId;
      let meta = null;
      if (categoryId > 0 && typeof getCategoryMetaById === "function") {
        meta = getCategoryMetaById(categoryId);
      }
      if (!meta?.name && row?.category_name) {
        meta = {
          id: categoryId || null,
          name: row.category_name,
          icon: row.category_icon || null,
          accent_color: row.category_accent_color || null,
        };
      }
      if (!meta?.name) {
        continue;
      }
      const key = meta.id ? `id:${meta.id}` : `name:${String(meta.name).toLowerCase()}`;
      if (!byKey.has(key)) {
        byKey.set(key, meta);
      }
    }
    if (byKey.size > 0) {
      return Array.from(byKey.values());
    }
    if (fallbackId > 0 && typeof getCategoryMetaById === "function") {
      const fallbackMeta = getCategoryMetaById(fallbackId);
      return fallbackMeta?.name ? [fallbackMeta] : [];
    }
    return [];
  }

  function renderMetaChip(label, tone = "neutral") {
    return `<span class="meta-chip meta-chip-${escapeHtml(tone)}">${escapeHtml(label)}</span>`;
  }

  function renderOperationContextChips(item) {
    const chips = [];
    const hasReceiptItems = Array.isArray(item?.receipt_items) && item.receipt_items.length > 0;
    const settlementCurrency = String(item?.fx_settlement?.asset_currency || item?.settlement_asset_currency || "").toUpperCase();
    const hasFxSettlement = Boolean(item?.fx_settlement) || item?.has_fx_settlement === true;
    if (hasReceiptItems) {
      chips.push(renderMetaChip("Чек"));
    }
    if (hasFxSettlement) {
      chips.push(renderMetaChip(settlementCurrency ? `Валютная карта · ${settlementCurrency}` : "Валютная карта", "info"));
    }
    return chips.join("");
  }

  function renderInlineKebabMenu(menuId, itemsHtml, ariaLabel = "Действия", extraClass = "") {
    if (!menuId || !String(itemsHtml || "").trim()) {
      return "";
    }
    return `
      <div class="table-kebab-wrap ${escapeHtml(extraClass)}">
        <button class="btn btn-secondary table-kebab-trigger" type="button" data-table-menu-trigger="${escapeHtml(menuId)}" aria-label="${escapeHtml(ariaLabel)}">
          <span aria-hidden="true">⋮</span>
        </button>
        <div class="app-popover hidden table-kebab-popover" data-table-menu="${escapeHtml(menuId)}">
          <div class="table-kebab-menu">
            ${itemsHtml}
          </div>
        </div>
      </div>
    `;
  }

  function parseAmount(value) {
    const amount = Number(value || 0);
    return Number.isFinite(amount) ? amount : 0;
  }

  function formatMoney(value) {
    return core.formatMoney(parseAmount(value));
  }

  function formatOperationAmountHtml(item, kindClass = "expense") {
    const originalAmount = parseAmount(item?.original_amount ?? item?.amount);
    const currency = String(item?.currency || "BYN").toUpperCase();
    const baseAmount = parseAmount(item?.amount);
    const baseCurrency = String(item?.base_currency || "BYN").toUpperCase();
    const originalMoney = core.formatMoney(originalAmount, { currency });
    if (currency === baseCurrency) {
      return `<span class="amount-${kindClass}">${originalMoney}</span>`;
    }
    return `<span class="amount-${kindClass}">${originalMoney}</span><div class="muted-small">≈ ${core.formatMoney(baseAmount, { currency: baseCurrency })}</div>`;
  }

  function formatFlowAmountHtml(item) {
    const flowDirection = String(item?.flow_direction || "outflow");
    const kindClass = flowDirection === "inflow" ? "income" : "expense";
    return formatOperationAmountHtml(item, kindClass);
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
    const forgiven = parseAmount(debt?.forgiven_total);
    const settled = repaid + forgiven;
    const direction = debt?.direction === "borrow" ? "borrow" : "lend";
    if (principal <= 0) {
      return { percent: 0, tone: direction === "borrow" ? "borrow-danger" : "lend-ok" };
    }
    const percent = Math.max(0, Math.min(100, Math.round((settled / principal) * 100)));
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

  function debtDirectionActionLabel(direction) {
    return direction === "borrow" ? "Я взял" : "Я дал";
  }

  function debtDirectionBalanceLabel(direction) {
    return direction === "borrow" ? "Я должен" : "Мне должны";
  }

  function debtRepaymentEventLabel(direction) {
    return direction === "borrow" ? "Погашение: я вернул" : "Погашение: мне вернули";
  }

  function debtIssuanceEventLabel(direction) {
    return direction === "borrow" ? "Добавление: я взял в долг" : "Добавление: я дал в долг";
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
    const hasReceiptItems = Array.isArray(item.receipt_items) && item.receipt_items.length > 0;
    const categories = Array.isArray(options.categories) && options.categories.length
      ? options.categories
      : (category?.name ? [category] : []);
    const categoryHtml = renderCategoryChipList(categories, searchQuery);
    const contextChipsHtml = renderOperationContextChips(item);
    const categoryCellHtml = contextChipsHtml
      ? `<div class="operation-category-stack">${categoryHtml}${contextChipsHtml}</div>`
      : categoryHtml;
    const row = document.createElement("tr");
    row.classList.add(`kind-row-${kindClass}`);

    if (compact) {
      const selectCell = selectable
        ? `<td class="select-col" data-label="Выбор"><input class="table-checkbox" type="checkbox" data-select-operation-id="${item.id}" ${selected ? "checked" : ""} /></td>`
        : "";
      row.innerHTML = `
        ${selectCell}
        <td data-label="Дата">${core.formatDateRu(item.operation_date)}</td>
        <td data-label="Тип"><span class="kind-pill kind-pill-${kindClass}">${highlightText(kindText, searchQuery)}</span></td>
        <td data-label="Категория">${categoryCellHtml}</td>
        <td data-label="Сумма">${formatOperationAmountHtml(item, kindClass)}</td>
        <td class="mobile-note-cell" data-label="Комментарий">${highlightText(noteText, searchQuery)}</td>
      `;
      row.dataset.item = JSON.stringify(item);
      row.dataset.operationRowId = String(item.id);
      row.classList.add("table-record-open-row");
      if (selected) {
        row.classList.add("row-selected");
      }
      return row;
    }

    if (preview) {
      const previewCategoryCellHtml = contextChipsHtml
        ? `<div class="operation-category-stack">${categoryHtml}${contextChipsHtml}</div>`
        : categoryHtml;
      row.innerHTML = `
        <td>${core.formatDateRu(item.operation_date)}</td>
        <td><span class="kind-pill kind-pill-${kindClass}">${highlightText(kindText, searchQuery)}</span></td>
        <td>${previewCategoryCellHtml}</td>
        <td>${formatOperationAmountHtml(item, kindClass)}</td>
        <td>${highlightText(noteText, searchQuery)}</td>
        <td><span class="muted-small">—</span></td>
      `;
      row.classList.add("preview-row");
      return row;
    }

    const selectCell = selectable
      ? `<td class="select-col" data-label="Выбор"><input class="table-checkbox" type="checkbox" data-select-operation-id="${item.id}" ${selected ? "checked" : ""} /></td>`
      : "";

    const receiptCellHtml = hasReceiptItems
      ? `<button class="meta-chip-btn meta-chip-btn-neutral" type="button" data-receipt-view-id="${item.id}">Чек</button>`
      : "<span class='muted-small'>—</span>";
    const menuItems = `
      ${hasReceiptItems ? `<button class="btn btn-secondary" data-receipt-view-id="${item.id}">Позиции</button>` : ""}
      <button class="btn btn-secondary" data-edit-id="${item.id}">Редактировать</button>
      <button class="btn btn-danger" data-delete-id="${item.id}">Удалить</button>
    `;
    row.innerHTML = `
      ${selectCell}
      <td data-label="Дата">${core.formatDateRu(item.operation_date)}</td>
      <td data-label="Тип"><span class="kind-pill kind-pill-${kindClass}">${highlightText(kindText, searchQuery)}</span></td>
      <td data-label="Категория">${contextChipsHtml ? `<div class="operation-category-stack">${categoryHtml}${contextChipsHtml}</div>` : categoryHtml}</td>
      <td data-label="Чек" class="operation-receipt-chip-cell">${receiptCellHtml}</td>
      <td data-label="Сумма">${formatOperationAmountHtml(item, kindClass)}</td>
      <td class="mobile-note-cell" data-label="Комментарий">${highlightText(noteText, searchQuery)}</td>
      <td class="mobile-actions-cell table-kebab-cell" data-label="Действия">
        ${renderInlineKebabMenu(`operation-${item.id}`, menuItems, "Действия операции", "operation-row-kebab")}
      </td>
    `;
    row.dataset.item = JSON.stringify(item);
    row.dataset.operationRowId = String(item.id);
    row.classList.add("table-record-open-row");
    if (selected) {
      row.classList.add("row-selected");
    }
    return row;
  }

  function createMoneyFlowRow(item, options = {}) {
    const searchQuery = options.searchQuery || "";
    const selectable = options.selectable === true;
    const selected = options.selected === true;
    const flowDirection = String(item?.flow_direction || "outflow");
    const kindClass = flowDirection === "inflow" ? "income" : "expense";
    const sourceKind = String(item?.source_kind || "operation");
    const directionLabel = flowDirection === "inflow" ? "Приток" : "Отток";
    const sourceCode = sourceKind === "debt" ? "DEBT" : sourceKind === "fx" ? "FX" : "OP";
    const sourceLabel = sourceKind === "debt"
      ? "Долг"
      : sourceKind === "fx"
        ? "Валюта"
        : "Операция";
    const title = item?.title || "Событие";
    const subtitle = item?.subtitle || "";
    const noteText = item?.note || "";
    const eventTone = sourceKind === "debt"
      ? (flowDirection === "inflow" ? "positive" : "negative")
      : sourceKind === "fx"
        ? (String(item?.trade_side || "") === "sell" ? "positive" : "negative")
        : "neutral";
    const sourceTone = sourceKind === "debt" ? "warning" : sourceKind === "fx" ? "info" : "neutral";
    const receiptCategories = sourceKind === "operation"
      ? getReceiptCategoryMetas(item?.receipt_items, item?.category_id, null)
      : [];
    const eventChips = [];
    if (sourceKind === "debt") {
      eventChips.push(renderMetaChip(title, eventTone));
    } else if (sourceKind === "fx") {
      eventChips.push(renderMetaChip(String(item?.trade_side || "") === "sell" ? "FX: Продажа" : "FX: Покупка", eventTone));
    } else {
      eventChips.push(renderMetaChip(title, "neutral"));
      if (item?.has_fx_settlement) {
        const settlementCurrency = String(item?.settlement_asset_currency || "").toUpperCase();
        eventChips.push(renderMetaChip(settlementCurrency ? `Валютная карта · ${settlementCurrency}` : "Валютная карта", "info"));
      }
    }
    if (item?.counterparty_name && sourceKind !== "debt") {
      eventChips.push(renderMetaChip(item.counterparty_name, "neutral"));
    }
    if (item?.asset_currency && item?.quote_currency) {
      eventChips.push(renderMetaChip(`${item.asset_currency}/${item.quote_currency}`, "info"));
    }
    const categoryMeta = item?.category_name
      ? {
        id: item.category_id || null,
        name: item.category_name,
        icon: item.category_icon || null,
        accent_color: item.category_accent_color || null,
      }
      : null;
    const receiptCategoryHtml = receiptCategories.length
      ? renderCategoryChipList(receiptCategories, searchQuery)
      : "";
    const operationContextChipsHtml = sourceKind === "operation"
      ? renderOperationContextChips(item)
      : "";
    const contextTitleHtml = `<div class="money-flow-title">${highlightText(title, searchQuery)}</div>`;
    const contextSubtitleHtml = subtitle
      ? `<div class="muted-small money-flow-subtitle">${highlightText(subtitle, searchQuery)}</div>`
      : "";
    const categoryCellHtml = categoryMeta
      ? renderCategoryChip(categoryMeta, searchQuery)
      : sourceKind === "operation" && receiptCategoryHtml
        ? (operationContextChipsHtml
          ? `<div class="operation-category-stack">${receiptCategoryHtml}${operationContextChipsHtml}</div>`
          : receiptCategoryHtml)
      : receiptCategoryHtml
        ? `<div class="money-flow-context">${receiptCategoryHtml}${contextSubtitleHtml}</div>`
        : `<div class="money-flow-context">${contextTitleHtml}${contextSubtitleHtml}</div>`;
    const sourceCellHtml = `
      <div class="operation-category-stack money-flow-source-stack">
        ${renderMetaChip(sourceCode, "neutral")}
        ${renderMetaChip(sourceLabel, sourceTone)}
        ${eventChips.join("")}
      </div>
    `;
    let menuItems = "";
    if (sourceKind === "operation" && item?.source_id) {
      menuItems = [
        `<button class="btn btn-secondary" data-open-source-kind="operation" data-open-source-id="${item.source_id || ""}">Редактировать</button>`,
        `<button class="btn btn-danger" data-delete-operation-source-id="${item.source_id || ""}">Удалить</button>`,
      ].join("");
    } else if (sourceKind === "fx" && item?.source_id) {
      menuItems = [
        `<button class="btn btn-secondary" data-open-source-kind="fx" data-open-source-id="${item.source_id || ""}">${escapeHtml(item?.open_label || "Открыть")}</button>`,
        `<button class="btn btn-danger" data-delete-fx-source-id="${item.source_id || ""}">Удалить</button>`,
      ].join("");
    } else if (item?.can_open_source) {
      menuItems = `<button class="btn btn-secondary" data-open-source-kind="${sourceKind}" data-open-source-id="${item.source_id || ""}">${escapeHtml(item?.open_label || "Открыть")}</button>`;
    }
    const selectCell = selectable
      ? `<td class="select-col" data-label="Выбор"><input class="table-checkbox" type="checkbox" data-select-operation-id="${escapeHtml(item.id)}" ${selected ? "checked" : ""} /></td>`
      : "<td class=\"select-col\" data-label=\"Выбор\"><span class=\"muted-small\">—</span></td>";
    const row = document.createElement("tr");
    row.classList.add(`kind-row-${kindClass}`);
    row.classList.add(`money-flow-row-source-${sourceKind}`);
    if (sourceKind === "fx") {
      row.classList.add(`money-flow-row-fx-${String(item?.trade_side || "buy") === "sell" ? "sell" : "buy"}`);
    }
    row.innerHTML = `
      ${selectCell}
      <td data-label="Дата">${core.formatDateRu(item.event_date)}</td>
      <td data-label="Тип"><span class="kind-pill kind-pill-${kindClass}">${highlightText(directionLabel, searchQuery)}</span></td>
      <td data-label="Контекст">${categoryCellHtml}</td>
      <td data-label="Источник">${sourceCellHtml}</td>
      <td data-label="Сумма">${formatFlowAmountHtml(item)}</td>
      <td class="mobile-note-cell" data-label="Комментарий">${highlightText(noteText, searchQuery)}</td>
      <td class="mobile-actions-cell table-kebab-cell" data-label="Действия">
        ${menuItems ? renderInlineKebabMenu(`money-flow-${escapeHtml(item.id)}`, menuItems, "Действия движения", "operation-row-kebab") : "<span class='muted-small'>—</span>"}
      </td>
    `;
    row.dataset.item = JSON.stringify(item);
    row.dataset.moneyFlowRowId = String(item.id || "");
    if (sourceKind === "operation" && item?.source_id) {
      row.dataset.operationRowId = String(item.source_id);
    }
    if (selected) {
      row.classList.add("row-selected");
    }
    row.dataset.moneyFlowSource = sourceKind;
    row.dataset.moneyFlowSourceCode = sourceCode;
    return row;
  }

  Object.assign(core, {
    escapeHtml,
    highlightText,
    renderCategoryChip,
    renderCategoryChipList,
    getReceiptCategoryMetas,
    renderMetaChip,
    renderInlineKebabMenu,
    createOperationRow,
    createMoneyFlowRow,
    debtUi: {
      parseAmount,
      formatMoney,
      parseIsoDate,
      parseIsoDateEnd,
      debtDueState,
      debtDueProgress,
      debtDueDaysBadge,
      debtRepaymentProgress,
      debtDirectionActionLabel,
      debtDirectionBalanceLabel,
      debtRepaymentEventLabel,
      debtIssuanceEventLabel,
    },
  });
})();
