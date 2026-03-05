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
    const query = el.opCategorySearch.value.trim();
    const allCategories = getCreateCategoriesSorted(kind, query);
    const quickCategories = query ? [] : allCategories.slice(0, 3);
    const selectedCategory = allCategories.find((item) => item.id === selectedId);
    if (!query && selectedId && selectedCategory && !quickCategories.some((item) => item.id === selectedId)) {
      quickCategories.unshift(selectedCategory);
    }

    el.opCategoryQuick.innerHTML = "";
    if (!query && !quickCategories.length) {
      el.opCategoryQuick.innerHTML = "<span class='muted-small'>Без категорий для выбранного типа</span>";
    } else if (!query) {
      for (const item of quickCategories) {
        const chip = createCategoryChipButton(item, selectedId === item.id, query);
        el.opCategoryQuick.appendChild(chip);
      }
      if (allCategories.length > 3) {
        const moreChip = document.createElement("button");
        moreChip.type = "button";
        moreChip.className = "chip-btn chip-btn-more";
        moreChip.dataset.toggleMore = "1";
        moreChip.innerHTML = `<span class="category-chip">${state.createModalCategoryExpanded ? "Скрыть" : "Еще"}</span>`;
        el.opCategoryQuick.appendChild(moreChip);
      }
    }

    const shouldShowAll = state.createModalCategoryExpanded || Boolean(query);
    el.opCategoryAll.classList.toggle("hidden", !shouldShowAll);

    if (shouldShowAll) {
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
    } else {
      el.opCategoryAll.innerHTML = "";
    }
  }

  function updateCreatePreview() {
    el.createPreviewBody.innerHTML = "";
    el.createPreviewBody.appendChild(
      core.createOperationRow(getCreateFormPreviewItem(), {
        preview: true,
        category: getCreateFormCategoryMeta(),
      }),
    );
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
    if (!options.keepSearch) {
      el.opCategorySearch.value = "";
      state.createModalCategoryExpanded = false;
    }
    renderCreateCategoryPicker();
    updateCreatePreview();
  }

  function openCreateCategoryFromOperation(searchText) {
    const trimmed = searchText.trim();
    state.pendingCreateCategoryFromOperation = trimmed;
    if (categoryActions.openCreateCategoryModal) {
      categoryActions.openCreateCategoryModal({
        kind: el.opKind.value || "expense",
        prefillName: trimmed,
        reset: true,
      });
    }
  }

  function handleCreateCategoryPickerClick(event) {
    const toggleBtn = event.target.closest("button[data-toggle-more]");
    if (toggleBtn) {
      state.createModalCategoryExpanded = !state.createModalCategoryExpanded;
      renderCreateCategoryPicker();
      return;
    }
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
    const dateInput = document.getElementById("opDate");
    if (!dateInput.value) {
      dateInput.value = new Date().toISOString().slice(0, 10);
    }
    setOperationKind("create", el.opKind.value || "expense");
    el.opCategory.value = "";
    el.opCategorySearch.value = "";
    el.opCategoryAll.classList.add("hidden");
    state.createModalCategoryExpanded = false;
    renderCreateCategoryPicker();
    updateCreatePreview();
    el.createModal.classList.remove("hidden");
  }

  function closeCreateModal() {
    el.createModal.classList.add("hidden");
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
    handleCreateCategoryPickerClick,
    onCategoryCreated,
    selectCreateCategory,
    setOperationKind,
    openCreateModal,
    closeCreateModal,
    openEditModal,
    closeEditModal,
    applySettingsUi,
    openPeriodCustomModal,
    closePeriodCustomModal,
  };
})();
