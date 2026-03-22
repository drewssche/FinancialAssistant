(() => {
  const { state, el, core } = window.App;

  function updateIconToggleLabel(toggleNode, iconValue) {
    if (window.App.categoryIconUi?.updateIconToggleLabel) {
      window.App.categoryIconUi.updateIconToggleLabel(toggleNode, iconValue);
    }
  }

  function closeIconPopovers() {
    if (window.App.categoryIconUi?.closeIconPopovers) {
      window.App.categoryIconUi.closeIconPopovers();
    }
  }

  function setupCategoryIconPickers() {
    if (window.App.categoryIconUi?.setupCategoryIconPickers) {
      window.App.categoryIconUi.setupCategoryIconPickers();
    }
  }

  function fillGroupSelect(selectNode, kind, emptyLabel = "Без группы") {
    if (!selectNode) {
      return;
    }
    const current = selectNode.value;
    selectNode.innerHTML = "";
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = emptyLabel;
    selectNode.appendChild(empty);

    const groups = state.categoryGroups.filter((group) => !kind || group.kind === kind);
    for (const group of groups) {
      const option = document.createElement("option");
      option.value = String(group.id);
      option.textContent = group.name;
      selectNode.appendChild(option);
    }

    if (current && Array.from(selectNode.options).some((item) => item.value === current)) {
      selectNode.value = current;
    }
    if (selectNode === el.categoryGroup) {
      renderCreateGroupPicker();
    }
  }

  function getCreateSelectedGroupId() {
    return el.categoryGroup.value ? Number(el.categoryGroup.value) : null;
  }

  function getEditSelectedGroupId() {
    return el.editCategoryGroup.value ? Number(el.editCategoryGroup.value) : null;
  }

  function getCreateGroupsSorted(kind, query = "") {
    const normalizedQuery = query.trim().toLowerCase();
    return state.categoryGroups
      .filter((group) => !kind || group.kind === kind)
      .filter((group) => {
        if (!normalizedQuery) {
          return true;
        }
        return String(group.name || "").toLowerCase().includes(normalizedQuery);
      })
      .sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""), "ru"));
  }

  function openCreateGroupPopover() {
    if (!el.createCategoryGroupPickerBlock) {
      return;
    }
    el.createCategoryGroupPickerBlock.classList.remove("hidden");
  }

  function closeCreateGroupPopover() {
    if (!el.createCategoryGroupPickerBlock) {
      return;
    }
    el.createCategoryGroupPickerBlock.classList.add("hidden");
  }

  function openEditGroupPopover() {
    if (!el.editCategoryGroupPickerBlock) {
      return;
    }
    el.editCategoryGroupPickerBlock.classList.remove("hidden");
  }

  function closeEditGroupPopover() {
    if (!el.editCategoryGroupPickerBlock) {
      return;
    }
    el.editCategoryGroupPickerBlock.classList.add("hidden");
  }

  function renderCreateGroupPicker() {
    if (!el.categoryGroupAll) {
      return;
    }
    const kind = el.categoryKind.value || "expense";
    const selectedId = getCreateSelectedGroupId();
    const query = el.categoryGroupSearch?.value?.trim() || "";
    const groups = getCreateGroupsSorted(kind, query);
    el.categoryGroupAll.innerHTML = "";

    const noneBtn = document.createElement("button");
    noneBtn.type = "button";
    noneBtn.className = "chip-btn";
    if (!selectedId) {
      noneBtn.classList.add("active");
    }
    noneBtn.dataset.groupId = "";
    noneBtn.innerHTML = "<span class='muted-small'>Без группы</span>";
    el.categoryGroupAll.appendChild(noneBtn);

    for (const group of groups) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chip-btn";
      if (selectedId === group.id) {
        btn.classList.add("active");
      }
      btn.dataset.groupId = String(group.id);
      btn.innerHTML = core.renderCategoryChip({ name: group.name, icon: null, accent_color: group.accent_color || null }, query);
      el.categoryGroupAll.appendChild(btn);
    }

    if (!groups.length && query) {
      const empty = document.createElement("span");
      empty.className = "muted-small";
      empty.textContent = "Группы не найдены";
      el.categoryGroupAll.appendChild(empty);
    }
  }

  function renderEditGroupPicker() {
    if (!el.editCategoryGroupAll) {
      return;
    }
    const kind = el.editCategoryKind.value || "expense";
    const selectedId = getEditSelectedGroupId();
    const query = el.editCategoryGroupSearch?.value?.trim() || "";
    const groups = getCreateGroupsSorted(kind, query);
    el.editCategoryGroupAll.innerHTML = "";

    const noneBtn = document.createElement("button");
    noneBtn.type = "button";
    noneBtn.className = "chip-btn";
    if (!selectedId) {
      noneBtn.classList.add("active");
    }
    noneBtn.dataset.groupId = "";
    noneBtn.innerHTML = "<span class='muted-small'>Без группы</span>";
    el.editCategoryGroupAll.appendChild(noneBtn);

    for (const group of groups) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chip-btn";
      if (selectedId === group.id) {
        btn.classList.add("active");
      }
      btn.dataset.groupId = String(group.id);
      btn.innerHTML = core.renderCategoryChip({ name: group.name, icon: null, accent_color: group.accent_color || null }, query);
      el.editCategoryGroupAll.appendChild(btn);
    }

    if (!groups.length && query) {
      const empty = document.createElement("span");
      empty.className = "muted-small";
      empty.textContent = "Группы не найдены";
      el.editCategoryGroupAll.appendChild(empty);
    }
  }

  function selectCreateGroup(groupId, options = {}) {
    const value = groupId ? String(groupId) : "";
    el.categoryGroup.value = value;
    const selected = state.categoryGroups.find((group) => String(group.id) === value);
    if (!options.keepSearch && el.categoryGroupSearch) {
      el.categoryGroupSearch.value = selected?.name || "";
    }
    renderCreateGroupPicker();
    closeCreateGroupPopover();
  }

  function selectEditGroup(groupId, options = {}) {
    const value = groupId ? String(groupId) : "";
    el.editCategoryGroup.value = value;
    const selected = state.categoryGroups.find((group) => String(group.id) === value);
    if (!options.keepSearch && el.editCategoryGroupSearch) {
      el.editCategoryGroupSearch.value = selected?.name || "";
    }
    renderEditGroupPicker();
    closeEditGroupPopover();
  }

  function handleCreateGroupSearchFocus() {
    openCreateGroupPopover();
    renderCreateGroupPicker();
  }

  function handleCreateGroupSearchInput() {
    if (el.categoryGroup.value) {
      el.categoryGroup.value = "";
    }
    openCreateGroupPopover();
    renderCreateGroupPicker();
  }

  function handleCreateGroupSearchBlur() {
    window.setTimeout(() => {
      const active = document.activeElement;
      if (active && active.closest("#createCategoryGroupField")) {
        return;
      }
      closeCreateGroupPopover();
    }, 0);
  }

  function handleEditGroupSearchFocus() {
    openEditGroupPopover();
    renderEditGroupPicker();
  }

  function handleEditGroupSearchInput() {
    if (el.editCategoryGroup.value) {
      el.editCategoryGroup.value = "";
    }
    openEditGroupPopover();
    renderEditGroupPicker();
  }

  function handleEditGroupSearchBlur() {
    window.setTimeout(() => {
      const active = document.activeElement;
      if (active && active.closest("#editCategoryGroupField")) {
        return;
      }
      closeEditGroupPopover();
    }, 0);
  }

  function handleCreateGroupSearchKeydown(event) {
    if (event.key === "Escape") {
      closeCreateGroupPopover();
      return;
    }
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    const query = el.categoryGroupSearch.value.trim();
    const kind = el.categoryKind.value || "expense";
    const groups = getCreateGroupsSorted(kind, query);
    if (groups.length) {
      selectCreateGroup(groups[0].id);
    }
  }

  function handleCreateGroupPickerClick(event) {
    const btn = event.target.closest("button[data-group-id]");
    if (!btn) {
      return;
    }
    const groupId = btn.dataset.groupId ? Number(btn.dataset.groupId) : null;
    selectCreateGroup(groupId);
  }

  function handleEditGroupSearchKeydown(event) {
    if (event.key === "Escape") {
      closeEditGroupPopover();
      return;
    }
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    const query = el.editCategoryGroupSearch.value.trim();
    const kind = el.editCategoryKind.value || "expense";
    const groups = getCreateGroupsSorted(kind, query);
    if (groups.length) {
      selectEditGroup(groups[0].id);
    }
  }

  function handleEditGroupPickerClick(event) {
    const btn = event.target.closest("button[data-group-id]");
    if (!btn) {
      return;
    }
    const groupId = btn.dataset.groupId ? Number(btn.dataset.groupId) : null;
    selectEditGroup(groupId);
  }

  function handleCreateGroupOutsidePointer(event) {
    if (
      el.createCategoryGroupPickerBlock &&
      !el.createCategoryGroupPickerBlock.classList.contains("hidden") &&
      !event.target.closest("#createCategoryGroupField")
    ) {
      closeCreateGroupPopover();
    }
    if (
      el.editCategoryGroupPickerBlock &&
      !el.editCategoryGroupPickerBlock.classList.contains("hidden") &&
      !event.target.closest("#editCategoryGroupField")
    ) {
      closeEditGroupPopover();
    }
  }

  function setCategoryKind(mode, kind) {
    if (mode === "create") {
      el.categoryKind.value = kind;
      core.syncSegmentedActive(el.createCategoryKind, "cat-create-kind", kind);
      fillGroupSelect(el.categoryGroup, kind, "Без группы");
      const selected = state.categoryGroups.find((group) => String(group.id) === el.categoryGroup.value);
      if (el.categoryGroup.value && (!selected || selected.kind !== kind)) {
        el.categoryGroup.value = "";
        if (el.categoryGroupSearch) {
          el.categoryGroupSearch.value = "";
        }
      }
      renderCreateGroupPicker();
      return;
    }
    if (mode === "edit") {
      el.editCategoryKind.value = kind;
      core.syncSegmentedActive(el.editCategoryKindSwitch, "cat-edit-kind", kind);
      fillGroupSelect(el.editCategoryGroup, kind, "Без группы");
      const selected = state.categoryGroups.find((group) => String(group.id) === el.editCategoryGroup.value);
      if (el.editCategoryGroup.value && (!selected || selected.kind !== kind)) {
        el.editCategoryGroup.value = "";
        if (el.editCategoryGroupSearch) {
          el.editCategoryGroupSearch.value = "";
        }
      }
      renderEditGroupPicker();
    }
  }

  function openCreateCategoryModal(options = {}) {
    const kind = options.kind || "expense";
    const prefillName = typeof options.prefillName === "string" ? options.prefillName.trim() : "";
    const resetForm = options.reset !== false;

    if (resetForm) {
      el.categoryName.value = prefillName;
      el.categoryGroup.value = "";
      if (el.categoryGroupSearch) {
        el.categoryGroupSearch.value = "";
      }
      el.categoryIcon.value = "";
      updateIconToggleLabel(el.categoryIconToggle, "");
      closeIconPopovers();
      closeCreateGroupPopover();
    } else if (prefillName) {
      el.categoryName.value = prefillName;
    }

    setCategoryKind("create", kind);
    renderCreateGroupPicker();
    el.createCategoryModal.classList.remove("hidden");
  }

  function closeCreateCategoryModal(clearPending = true) {
    closeIconPopovers();
    closeCreateGroupPopover();
    el.createCategoryModal.classList.add("hidden");
    if (clearPending) {
      state.pendingCreateCategoryFromOperation = "";
      state.pendingCreateCategoryFromReceipt = null;
    }
  }

  function populateCategorySelect(selectNode, selectedId, kind) {
    selectNode.innerHTML = "";
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "Без категории";
    selectNode.appendChild(empty);

    const filtered = state.categories.filter((item) => item.kind === kind);
    for (const item of filtered) {
      const option = document.createElement("option");
      option.value = String(item.id);
      option.textContent = item.name;
      selectNode.appendChild(option);
    }

    selectNode.value = selectedId ? String(selectedId) : "";
  }

  function updateCategoriesBulkUi() {
    if (window.App.categoryTableUi?.updateCategoriesBulkUi) {
      window.App.categoryTableUi.updateCategoriesBulkUi();
    }
  }

  function openEditGroupModal(group) {
    if (window.App.categoryTableUi?.openEditGroupModal) {
      window.App.categoryTableUi.openEditGroupModal(group);
    }
  }

  function closeEditGroupModal() {
    if (window.App.categoryTableUi?.closeEditGroupModal) {
      window.App.categoryTableUi.closeEditGroupModal();
    }
  }

  function openEditCategoryModal(item) {
    if (window.App.categoryTableUi?.openEditCategoryModal) {
      window.App.categoryTableUi.openEditCategoryModal(item);
    }
  }

  function closeEditCategoryModal() {
    if (window.App.categoryTableUi?.closeEditCategoryModal) {
      window.App.categoryTableUi.closeEditCategoryModal();
    }
  }

  function groupCategoryIds(groupId) {
    if (window.App.categoryTableUi?.groupCategoryIds) {
      return window.App.categoryTableUi.groupCategoryIds(groupId);
    }
    return [];
  }

  function renderCategories() {
    if (window.App.categoryTableUi?.renderCategories) {
      window.App.categoryTableUi.renderCategories();
    }
  }

  function handleCategoriesGroupToggleClick(event) {
    if (window.App.categoryTableUi?.handleCategoriesGroupToggleClick) {
      return window.App.categoryTableUi.handleCategoriesGroupToggleClick(event);
    }
    return false;
  }

  function collapseAllCategoryGroups() {
    if (window.App.categoryTableUi?.collapseAllCategoryGroups) {
      window.App.categoryTableUi.collapseAllCategoryGroups();
    }
  }

  function expandAllCategoryGroups() {
    if (window.App.categoryTableUi?.expandAllCategoryGroups) {
      window.App.categoryTableUi.expandAllCategoryGroups();
    }
  }

  const api = {
    updateIconToggleLabel,
    closeIconPopovers,
    setupCategoryIconPickers,
    openCreateCategoryModal,
    closeCreateCategoryModal,
    fillGroupSelect,
    setCategoryKind,
    populateCategorySelect,
    renderCreateGroupPicker,
    renderEditGroupPicker,
    handleCreateGroupSearchFocus,
    handleCreateGroupSearchInput,
    handleCreateGroupSearchBlur,
    handleCreateGroupSearchKeydown,
    handleEditGroupSearchFocus,
    handleEditGroupSearchInput,
    handleEditGroupSearchBlur,
    handleEditGroupSearchKeydown,
    handleCreateGroupPickerClick,
    handleEditGroupPickerClick,
    handleCreateGroupOutsidePointer,
    selectCreateGroup,
    selectEditGroup,
    updateCategoriesBulkUi,
    openEditGroupModal,
    closeEditGroupModal,
    openEditCategoryModal,
    closeEditCategoryModal,
    groupCategoryIds,
    renderCategories,
    handleCategoriesGroupToggleClick,
    collapseAllCategoryGroups,
    expandAllCategoryGroups,
  };

  window.App.categoryUi = api;
  window.App.registerRuntimeModule?.("category-ui", api);
})();
