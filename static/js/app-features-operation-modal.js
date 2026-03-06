(() => {
  const { state, el, core } = window.App;
  const categoryActions = window.App.actions;
  const CATEGORY_USAGE_KEY = "fa_category_usage_v1";

  function readCategoryUsage() {
    try {
      const raw = localStorage.getItem(CATEGORY_USAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  }

  function writeCategoryUsage(usage) {
    localStorage.setItem(CATEGORY_USAGE_KEY, JSON.stringify(usage));
  }

  function trackCategoryUsage(categoryId) {
    if (!categoryId) {
      return;
    }
    const usage = readCategoryUsage();
    const key = String(categoryId);
    usage[key] = Number(usage[key] || 0) + 1;
    writeCategoryUsage(usage);
  }

  function getSelectedCreateCategoryId() {
    return el.opCategory.value ? Number(el.opCategory.value) : null;
  }

  function getCategoryMetaById(categoryId) {
    if (!categoryId) {
      return null;
    }
    const category = state.categories.find((item) => item.id === categoryId);
    if (!category) {
      return null;
    }
    return {
      id: category.id,
      name: category.name,
      icon: category.icon || category.group_icon || null,
      accent_color: category.group_accent_color || null,
      kind: category.kind,
      group_name: category.group_name || "",
    };
  }

  function getCreateFormCategoryMeta() {
    return getCategoryMetaById(getSelectedCreateCategoryId());
  }

  function openCreateCategoryPopover() {
    if (el.opEntryMode.value === "debt") {
      return;
    }
    el.createCategoryPickerBlock.classList.remove("hidden");
  }

  function closeCreateCategoryPopover() {
    el.createCategoryPickerBlock.classList.add("hidden");
  }

  function getCreateCategoriesSorted(kind, query = "") {
    const usage = readCategoryUsage();
    const normalizedQuery = query.trim().toLowerCase();
    return state.categories
      .filter((item) => item.kind === kind)
      .filter((item) => {
        if (!normalizedQuery) {
          return true;
        }
        return item.name.toLowerCase().includes(normalizedQuery) || (item.group_name || "").toLowerCase().includes(normalizedQuery);
      })
      .map((item) => ({ ...item, usage: Number(usage[String(item.id)] || 0) }))
      .sort((a, b) => {
        if (b.usage !== a.usage) {
          return b.usage - a.usage;
        }
        const colorA = (a.group_accent_color || "~").toLowerCase();
        const colorB = (b.group_accent_color || "~").toLowerCase();
        if (colorA !== colorB) {
          return colorA.localeCompare(colorB, "ru");
        }
        const groupA = (a.group_name || "~").toLowerCase();
        const groupB = (b.group_name || "~").toLowerCase();
        if (groupA !== groupB) {
          return groupA.localeCompare(groupB, "ru");
        }
        return a.name.localeCompare(b.name, "ru");
      });
  }

  function createCategoryChipButton(category, selected, searchQuery = "") {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip-btn";
    if (selected) {
      btn.classList.add("active");
    }
    btn.dataset.categoryId = String(category.id);
    btn.innerHTML = core.renderCategoryChip(
      {
        name: category.name,
        icon: category.icon || category.group_icon || null,
        accent_color: category.group_accent_color || null,
      },
      searchQuery,
    );
    return btn;
  }

  function renderCreateCategoryPicker() {
    const kind = el.opKind.value || "expense";
    const selectedId = getSelectedCreateCategoryId();
    const selectedCategory = state.categories.find((item) => item.id === selectedId && item.kind === kind);
    const rawQuery = el.opCategorySearch.value.trim();
    const query = selectedCategory && rawQuery.toLowerCase() === selectedCategory.name.toLowerCase() ? "" : rawQuery;
    const allCategories = getCreateCategoriesSorted(kind, query);

    el.opCategoryAll.innerHTML = "";
    for (const item of allCategories) {
      const chip = createCategoryChipButton(item, selectedId === item.id, query);
      el.opCategoryAll.appendChild(chip);
    }
    if (!allCategories.length && query) {
      const createChip = document.createElement("button");
      createChip.type = "button";
      createChip.className = "chip-btn chip-btn-create";
      createChip.dataset.createCategory = query;
      createChip.textContent = `+ Создать категорию «${query}»`;
      el.opCategoryAll.appendChild(createChip);
    }
    if (!allCategories.length && !query) {
      el.opCategoryAll.innerHTML = "<span class='muted-small'>Без категорий для выбранного типа</span>";
    }
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

  function setDebtDirection(direction) {
    const nextDirection = direction === "borrow" ? "borrow" : "lend";
    el.debtDirection.value = nextDirection;
    core.syncSegmentedActive(el.createDebtDirectionSwitch, "debt-direction", nextDirection);
    updateCreatePreview();
  }

  function applyDebtCurrencyUi() {
    core.applyMoneyInputs();
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

  function updateCreatePreview() {
    el.createPreviewBody.innerHTML = "";
    if (el.opEntryMode.value === "debt") {
      const row = document.createElement("tr");
      const direction = el.debtDirection.value === "borrow" ? "borrow" : "lend";
      const directionLabel = direction === "borrow" ? "Я взял" : "Я дал";
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
    const category = getCreateFormCategoryMeta();
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

  function selectCreateCategory(categoryId, options = {}) {
    const value = categoryId ? String(categoryId) : "";
    el.opCategory.value = value;
    const categoryMeta = getCreateFormCategoryMeta();
    if (!options.keepSearch) {
      el.opCategorySearch.value = categoryMeta?.name || "";
    }
    renderCreateCategoryPicker();
    updateCreatePreview();
    closeCreateCategoryPopover();
  }

  function handleCreatePreviewClick(event) {
    const btn = event.target.closest("button[data-focus-target]");
    if (!btn) {
      return;
    }
    focusCreateField(btn.dataset.focusTarget || "");
  }

  function handleCreateCategorySearchFocus() {
    openCreateCategoryPopover();
    renderCreateCategoryPicker();
  }

  function handleCreateCategorySearchInput() {
    if (el.opCategory.value) {
      el.opCategory.value = "";
    }
    openCreateCategoryPopover();
    renderCreateCategoryPicker();
    updateCreatePreview();
  }

  function handleCreateCategorySearchKeydown(event) {
    if (event.key === "Escape") {
      closeCreateCategoryPopover();
      return;
    }
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    const query = el.opCategorySearch.value.trim();
    const matches = getCreateCategoriesSorted(el.opKind.value || "expense", query);
    if (matches.length) {
      selectCreateCategory(matches[0].id);
      return;
    }
    if (query) {
      openCreateCategoryFromOperation(query);
    }
  }

  function handleCreateCategoryOutsidePointer(event) {
    if (el.createCategoryPickerBlock.classList.contains("hidden")) {
      return;
    }
    if (event.target.closest("#createCategoryField")) {
      return;
    }
    closeCreateCategoryPopover();
  }

  function openCreateCategoryFromOperation(searchText) {
    const trimmed = searchText.trim();
    state.pendingCreateCategoryFromOperation = trimmed;
    closeCreateCategoryPopover();
    if (categoryActions.openCreateCategoryModal) {
      categoryActions.openCreateCategoryModal({
        kind: el.opKind.value || "expense",
        prefillName: trimmed,
        reset: true,
      });
    }
  }

  function handleCreateCategoryPickerClick(event) {
    const createBtn = event.target.closest("button[data-create-category]");
    if (createBtn) {
      openCreateCategoryFromOperation(createBtn.dataset.createCategory || "");
      return;
    }
    const chipBtn = event.target.closest("button[data-category-id]");
    if (!chipBtn) {
      return;
    }
    selectCreateCategory(Number(chipBtn.dataset.categoryId || 0));
  }

  function onCategoryCreated(createdCategory) {
    if (!createdCategory) {
      return;
    }
    const pending = (state.pendingCreateCategoryFromOperation || "").trim().toLowerCase();
    const createdName = String(createdCategory.name || "").trim().toLowerCase();
    const kindMatches = createdCategory.kind === (el.opKind.value || "expense");
    if (!pending || pending !== createdName || !kindMatches) {
      state.pendingCreateCategoryFromOperation = "";
      return;
    }
    state.pendingCreateCategoryFromOperation = "";
    selectCreateCategory(createdCategory.id);
  }

  function getCreateFormPreviewItem() {
    return {
      id: 0,
      operation_date: document.getElementById("opDate").value || new Date().toISOString().slice(0, 10),
      kind: el.opKind.value || "expense",
      category_id: getSelectedCreateCategoryId(),
      amount: core.formatAmount(document.getElementById("opAmount").value),
      note: document.getElementById("opNote").value || "",
    };
  }

  function setCreateEntryMode(mode) {
    const nextMode = mode === "debt" ? "debt" : "operation";
    el.opEntryMode.value = nextMode;
    core.syncSegmentedActive(el.createEntryModeSwitch, "entry-mode", nextMode);
    const isDebt = nextMode === "debt";
    el.createKindSwitch.classList.toggle("hidden", isDebt);
    el.createCategoryField.classList.toggle("hidden", isDebt);
    const opAmount = document.getElementById("opAmount");
    const opDate = document.getElementById("opDate");
    const opNote = document.getElementById("opNote");
    if (opAmount) {
      opAmount.classList.toggle("hidden", isDebt);
      opAmount.required = !isDebt;
    }
    if (opDate) {
      opDate.classList.toggle("hidden", isDebt);
      opDate.required = !isDebt;
    }
    if (opNote) {
      opNote.classList.toggle("hidden", isDebt);
      opNote.placeholder = isDebt ? "Комментарий (долг)" : "Комментарий";
    }
    el.createDebtFields.classList.toggle("hidden", !isDebt);
    if (el.createPreviewHeadOperation && el.createPreviewHeadDebt) {
      el.createPreviewHeadOperation.classList.toggle("hidden", isDebt);
      el.createPreviewHeadDebt.classList.toggle("hidden", !isDebt);
    }
    if (isDebt) {
      closeCreateCategoryPopover();
    }
    el.debtCounterparty.required = isDebt;
    el.debtPrincipal.required = isDebt;
    el.debtStartDate.required = isDebt;
    const submit = document.getElementById("submitCreateOperationBtn");
    if (isDebt) {
      if (!el.debtStartDate.value) {
        el.debtStartDate.value = new Date().toISOString().slice(0, 10);
      }
      if (submit) {
        submit.textContent = state.editDebtCreateId ? "Сохранить долг" : "Создать долг";
      }
    } else {
      if (submit) {
        submit.textContent = "Добавить";
      }
    }
    updateCreatePreview();
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

  function setOperationKind(mode, kind) {
    if (mode === "create") {
      el.opKind.value = kind;
      core.syncSegmentedActive(el.createKindSwitch, "kind", kind);
      categoryActions.populateCategorySelect(el.opCategory, el.opCategory.value, kind);
      if (el.opCategory.value && !state.categories.some((item) => String(item.id) === el.opCategory.value && item.kind === kind)) {
        el.opCategory.value = "";
        el.opCategorySearch.value = "";
      }
      renderCreateCategoryPicker();
      updateCreatePreview();
      return;
    }

    if (mode === "edit") {
      el.editKind.value = kind;
      core.syncSegmentedActive(el.editKindSwitch, "kind", kind);
      categoryActions.populateCategorySelect(el.editCategory, el.editCategory.value, kind);
      updateEditPreview();
    }
  }

  function openCreateModal() {
    state.editDebtCreateId = null;
    const createTitle = document.getElementById("createTitle");
    if (createTitle) {
      createTitle.textContent = "Новая операция";
    }
    const dateInput = document.getElementById("opDate");
    if (!dateInput.value) {
      dateInput.value = new Date().toISOString().slice(0, 10);
    }
    setOperationKind("create", el.opKind.value || "expense");
    el.opCategory.value = "";
    el.opCategorySearch.value = "";
    closeCreateCategoryPopover();
    el.debtCounterparty.value = "";
    el.debtPrincipal.value = "";
    el.debtStartDate.value = "";
    el.debtDueDate.value = "";
    el.debtNote.value = "";
    setDebtDirection("lend");
    applyDebtCurrencyUi();
    updateDebtDueHint();
    setCreateEntryMode("operation");
    renderCreateCategoryPicker();
    updateCreatePreview();
    el.createModal.classList.remove("hidden");
  }

  function closeCreateModal() {
    state.editDebtCreateId = null;
    const createTitle = document.getElementById("createTitle");
    if (createTitle) {
      createTitle.textContent = "Новая операция";
    }
    el.createModal.classList.add("hidden");
  }

  function openCreateModalForDebtEdit(payload) {
    if (!payload?.id) {
      return;
    }
    openCreateModal();
    state.editDebtCreateId = Number(payload.id);
    const createTitle = document.getElementById("createTitle");
    if (createTitle) {
      createTitle.textContent = "Редактировать долг";
    }
    el.debtCounterparty.value = payload.counterparty || "";
    el.debtPrincipal.value = payload.principal || "";
    el.debtStartDate.value = payload.start_date || new Date().toISOString().slice(0, 10);
    el.debtDueDate.value = payload.due_date || "";
    el.debtNote.value = payload.note || "";
    setDebtDirection(payload.direction || "lend");
    setCreateEntryMode("debt");
    updateDebtDueHint();
    updateCreatePreview();
  }

  function openEditModal(item) {
    state.editOperationId = item.id;
    document.getElementById("editAmount").value = item.amount;
    document.getElementById("editDate").value = item.operation_date;
    document.getElementById("editNote").value = item.note || "";
    setOperationKind("edit", item.kind);
    el.editCategory.value = item.category_id ? String(item.category_id) : "";
    updateEditPreview();
    el.editModal.classList.remove("hidden");
  }

  function closeEditModal() {
    state.editOperationId = null;
    el.editModal.classList.add("hidden");
  }

  function applySettingsUi() {
    const savedTz = state.preferences?.data?.ui?.timezone || "auto";
    if (el.timezoneSelect) {
      const hasOption = Array.from(el.timezoneSelect.options).some((opt) => opt.value === savedTz);
      el.timezoneSelect.value = hasOption ? savedTz : "auto";
    }
    applyDebtCurrencyUi();
  }

  function openPeriodCustomModal() {
    const today = new Date().toISOString().slice(0, 10);
    el.customDateTo.value = state.customDateTo || today;
    el.customDateFrom.value = state.customDateFrom || today;
    el.periodCustomModal.classList.remove("hidden");
  }

  function closePeriodCustomModal() {
    el.periodCustomModal.classList.add("hidden");
  }

  window.App.operationModal = {
    trackCategoryUsage,
    getCategoryMetaById,
    getCreateFormPreviewItem,
    updateCreatePreview,
    updateEditPreview,
    renderCreateCategoryPicker,
    openCreateCategoryPopover,
    closeCreateCategoryPopover,
    handleCreateCategoryPickerClick,
    handleCreateCategorySearchFocus,
    handleCreateCategorySearchInput,
    handleCreateCategorySearchKeydown,
    handleCreateCategoryOutsidePointer,
    onCategoryCreated,
    selectCreateCategory,
    handleCreatePreviewClick,
    setDebtDirection,
    setOperationKind,
    setCreateEntryMode,
    updateDebtDueHint,
    openCreateModal,
    openCreateModalForDebtEdit,
    closeCreateModal,
    openEditModal,
    closeEditModal,
    applySettingsUi,
    openPeriodCustomModal,
    closePeriodCustomModal,
  };
})();
