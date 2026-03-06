(() => {
  const { state, el, core } = window.App;

  const CATEGORY_ICON_POOL = [
    "🍽️",
    "🍔",
    "☕",
    "🏠",
    "🧹",
    "🧺",
    "🚕",
    "🚇",
    "🚌",
    "🚗",
    "⛽",
    "🛒",
    "🍎",
    "🥗",
    "🍕",
    "💊",
    "🏥",
    "🧘",
    "💇",
    "🎓",
    "📚",
    "💼",
    "💻",
    "🎮",
    "🎬",
    "🎵",
    "⚽",
    "🎁",
    "💡",
    "📱",
    "🛠️",
    "🧾",
    "💰",
    "📈",
    "🏦",
    "💳",
    "🧳",
    "✈️",
    "🏨",
    "🐾",
    "👶",
    "🧸",
    "🔧",
    "📦",
  ];

  function updateIconToggleLabel(toggleNode, iconValue) {
    if (!toggleNode) {
      return;
    }
    toggleNode.textContent = iconValue || "+";
  }

  function closeIconPopovers() {
    el.categoryIconPopover.classList.add("hidden");
    el.editCategoryIconPopover.classList.add("hidden");
  }

  function bindIconPopoverOnce(popoverNode) {
    if (!popoverNode || popoverNode.dataset.boundClick === "1") {
      return;
    }
    popoverNode.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-icon]");
      if (!btn) {
        return;
      }
      const hiddenId = popoverNode.dataset.hiddenTarget;
      const toggleId = popoverNode.dataset.toggleTarget;
      const hiddenNode = hiddenId ? document.getElementById(hiddenId) : null;
      const toggleNode = toggleId ? document.getElementById(toggleId) : null;
      if (!hiddenNode) {
        return;
      }
      hiddenNode.value = btn.dataset.icon || "";
      for (const option of popoverNode.querySelectorAll(".icon-option")) {
        option.classList.toggle("active", option === btn);
      }
      updateIconToggleLabel(toggleNode, hiddenNode.value);
      popoverNode.classList.add("hidden");
    });
    popoverNode.dataset.boundClick = "1";
  }

  function renderIconPopover(popoverNode, hiddenNode, toggleNode) {
    if (!popoverNode || !hiddenNode || !toggleNode) {
      return;
    }
    popoverNode.dataset.hiddenTarget = hiddenNode.id || "";
    popoverNode.dataset.toggleTarget = toggleNode.id || "";
    bindIconPopoverOnce(popoverNode);
    popoverNode.innerHTML = "";
    const emptyButton = document.createElement("button");
    emptyButton.type = "button";
    emptyButton.className = "icon-option icon-option-empty";
    emptyButton.dataset.icon = "";
    emptyButton.textContent = "∅";
    emptyButton.title = "Без иконки";
    if (!hiddenNode.value) {
      emptyButton.classList.add("active");
    }
    popoverNode.appendChild(emptyButton);
    for (const icon of CATEGORY_ICON_POOL) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "icon-option";
      button.dataset.icon = icon;
      button.textContent = icon;
      if (hiddenNode.value === icon) {
        button.classList.add("active");
      }
      popoverNode.appendChild(button);
    }
  }

  function setupCategoryIconPickers() {
    renderIconPopover(el.categoryIconPopover, el.categoryIcon, el.categoryIconToggle);
    renderIconPopover(el.editCategoryIconPopover, el.editCategoryIcon, el.editCategoryIconToggle);
    updateIconToggleLabel(el.categoryIconToggle, el.categoryIcon.value);
    updateIconToggleLabel(el.editCategoryIconToggle, el.editCategoryIcon.value);
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
    const categoryIds = Array.from(el.categoriesBody.querySelectorAll("input[data-select-category-id]"))
      .filter((item) => !item.disabled)
      .map((item) => Number(item.dataset.selectCategoryId));
    const groupIds = Array.from(el.categoriesBody.querySelectorAll("input[data-select-group-id]"))
      .filter((item) => !item.disabled)
      .map((item) => Number(item.dataset.selectGroupId));
    const selectedCategoryCount = categoryIds.filter((id) => state.selectedCategoryIds.has(id)).length;
    const selectedGroupCount = groupIds.filter((id) => state.selectedGroupIds.has(id)).length;
    const selectedVisibleCount = selectedCategoryCount + selectedGroupCount;
    if (selectedVisibleCount === 0) {
      el.categoriesSelectedCount.textContent = "Ничего не выбрано";
    } else if (selectedGroupCount > 0 && selectedCategoryCount > 0) {
      el.categoriesSelectedCount.textContent = `Выбрано: ${selectedVisibleCount} (группы: ${selectedGroupCount}, категории: ${selectedCategoryCount})`;
    } else if (selectedGroupCount > 0) {
      el.categoriesSelectedCount.textContent = `Выбрано: ${selectedVisibleCount} (группы: ${selectedGroupCount})`;
    } else {
      el.categoriesSelectedCount.textContent = `Выбрано: ${selectedVisibleCount} (категории: ${selectedCategoryCount})`;
    }
    const hasSelection = selectedVisibleCount > 0;
    const canBulkEdit = selectedCategoryCount > 0 && selectedGroupCount === 0;

    // Keep action zone width stable when nothing is selected to avoid sticky-bar jumps.
    if (!hasSelection) {
      el.bulkEditCategoriesBtn.classList.remove("hidden-action");
      el.bulkDeleteCategoriesBtn.classList.remove("hidden-action");
      el.bulkEditCategoriesBtn.classList.add("is-reserved-hidden");
      el.bulkDeleteCategoriesBtn.classList.add("is-reserved-hidden");
    } else {
      el.bulkEditCategoriesBtn.classList.remove("is-reserved-hidden");
      el.bulkDeleteCategoriesBtn.classList.remove("is-reserved-hidden");
      el.bulkEditCategoriesBtn.classList.toggle("hidden-action", !canBulkEdit);
      el.bulkDeleteCategoriesBtn.classList.remove("hidden-action");
    }

    const totalCount = categoryIds.length + groupIds.length;
    el.categoriesSelectAll.checked = totalCount > 0 && selectedVisibleCount === totalCount;
    el.categoriesSelectAll.indeterminate = selectedVisibleCount > 0 && selectedVisibleCount < totalCount;
  }

  function openEditGroupModal(group) {
    if (!group) {
      return;
    }
    el.editGroupId.value = String(group.id);
    el.editGroupName.value = group.name || "";
    const color = group.accent_color || "#ff8a3d";
    el.editGroupAccentColor.value = color;
    el.editGroupAccentColorHex.value = color;
    el.editGroupModal.classList.remove("hidden");
  }

  function closeEditGroupModal() {
    el.editGroupId.value = "";
    el.editGroupModal.classList.add("hidden");
  }

  function openEditCategoryModal(item) {
    state.editCategoryId = item.id;
    el.editCategoryName.value = item.name || "";
    el.editCategoryIcon.value = item.icon || "";
    updateIconToggleLabel(el.editCategoryIconToggle, el.editCategoryIcon.value);
    closeIconPopovers();
    setCategoryKind("edit", item.kind || "expense");
    el.editCategoryGroup.value = item.group_id ? String(item.group_id) : "";
    const selected = state.categoryGroups.find((group) => String(group.id) === el.editCategoryGroup.value);
    if (el.editCategoryGroupSearch) {
      el.editCategoryGroupSearch.value = selected?.name || "";
    }
    renderEditGroupPicker();
    el.editCategoryModal.classList.remove("hidden");
  }

  function closeEditCategoryModal() {
    state.editCategoryId = null;
    closeIconPopovers();
    closeEditGroupPopover();
    el.editCategoryModal.classList.add("hidden");
  }

  function groupCategoryIds(groupId) {
    return state.categoryTableItems.filter((item) => item.group_id === groupId && !item.is_system).map((item) => item.id);
  }

  function renderCategoryRow(item, query, options = {}) {
    const kindClass = item.kind === "income" ? "income" : "expense";
    const tr = document.createElement("tr");
    tr.classList.add(`kind-row-${kindClass}`);
    tr.dataset.item = JSON.stringify(item);
    tr.dataset.itemType = "category";
    tr.dataset.categoryId = String(item.id);
    if (options.groupId) {
      tr.dataset.groupId = String(options.groupId);
      tr.classList.add("category-child-row");
    }
    if (state.selectedCategoryIds.has(item.id)) {
      tr.classList.add("row-selected");
    }
    const actionCell = item.is_system
      ? "<span class='muted-small'>Защищено</span>"
      : `<div class='actions row-actions'><button class='btn btn-secondary' data-edit-category-id='${item.id}'>Редактировать</button><button class='btn btn-danger' data-delete-category-id='${item.id}'>Удалить</button></div>`;
    const leftBorderColor = options.groupAccentColor || "rgba(77, 98, 130, 0.45)";
    const groupCell = options.groupName
      ? `<div class="group-cell-inline"><span class='muted-small category-tree-mark'>↳</span>${core.renderCategoryChip(
          { name: options.groupName, icon: null, accent_color: options.groupAccentColor || null },
          query,
        )}</div>`
      : options.groupLabel || "<span class='muted-small'>Без группы</span>";
    const nameCell = core.renderCategoryChip({ name: item.name, icon: item.icon || item.group_icon, accent_color: item.group_accent_color }, query);
    tr.innerHTML = `
      <td class="select-col" style="border-left: 3px solid ${leftBorderColor};"><input class="table-checkbox" type="checkbox" data-select-category-id="${item.id}" data-category-group-id="${options.groupId || ""}" ${state.selectedCategoryIds.has(item.id) ? "checked" : ""} ${item.is_system ? "disabled" : ""} /></td>
      <td>${groupCell}</td>
      <td>${nameCell}</td>
      <td><span class="kind-pill kind-pill-${kindClass}">${core.highlightText(core.kindLabel(item.kind), query)}</span></td>
      <td>${actionCell}</td>
    `;
    return tr;
  }

  function renderGroupRow(group, query) {
    const kindClass = group.kind === "income" ? "income" : "expense";
    const tr = document.createElement("tr");
    tr.classList.add("group-row", `kind-row-${kindClass}`);
    tr.dataset.itemType = "group";
    tr.dataset.groupId = String(group.id);
    if (state.selectedGroupIds.has(group.id)) {
      tr.classList.add("row-selected");
    }
    const leftBorderColor = group.accent_color || "rgba(77, 98, 130, 0.45)";
    tr.innerHTML = `
      <td class="select-col" style="border-left: 3px solid ${leftBorderColor};"><input class="table-checkbox" type="checkbox" data-select-group-id="${group.id}" ${state.selectedGroupIds.has(group.id) ? "checked" : ""} /></td>
      <td>${core.renderCategoryChip({ name: group.name, icon: null, accent_color: group.accent_color || null }, query)}</td>
      <td><span class="muted-small">Группа</span></td>
      <td><span class="kind-pill kind-pill-${kindClass}">${core.highlightText(core.kindLabel(group.kind), query)}</span></td>
      <td><div class='actions row-actions'><button class='btn btn-secondary' data-edit-group-id='${group.id}'>Редактировать</button><button class='btn btn-danger' data-delete-group-id='${group.id}'>Удалить</button></div></td>
    `;
    return tr;
  }

  function renderCategories() {
    const query = el.categorySearchQ.value.trim().toLowerCase();
    const rows = state.categoryTableItems.filter((item) => {
      if (!query) {
        return true;
      }
      const groupName = (item.group_name || "").toLowerCase();
      return (
        item.name.toLowerCase().includes(query) ||
        core.kindLabel(item.kind).toLowerCase().includes(query) ||
        groupName.includes(query)
      );
    });

    const displayQuery = el.categorySearchQ.value.trim();
    const allRows = [];
    const pushRow = (node) => {
      allRows.push(node);
    };

    const ungrouped = rows
      .filter((item) => !item.group_id)
      .sort((a, b) => a.name.localeCompare(b.name, "ru"));
    for (const item of ungrouped) {
      pushRow(renderCategoryRow(item, displayQuery));
    }

    const groups = state.categoryGroups
      .filter((group) => state.categoryFilterKind === "all" || group.kind === state.categoryFilterKind)
      .sort((a, b) => a.name.localeCompare(b.name, "ru"));

    for (const group of groups) {
      const groupMatchesQuery = query ? group.name.toLowerCase().includes(query) : false;
      const childrenSource = groupMatchesQuery ? state.categoryTableItems : rows;
      const children = childrenSource
        .filter((item) => item.group_id === group.id)
        .sort((a, b) => a.name.localeCompare(b.name, "ru"));
      if (!children.length && query && !groupMatchesQuery) {
        continue;
      }
      pushRow(renderGroupRow(group, displayQuery));
      for (const child of children) {
        const groupLabel = "<span class='muted-small category-tree-mark'>↳</span>";
        pushRow(
          renderCategoryRow(child, displayQuery, {
            groupId: group.id,
            groupLabel,
            groupName: group.name,
            groupAccentColor: group.accent_color || null,
          }),
        );
      }
    }

    el.categoriesBody.innerHTML = "";
    if (!allRows.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="5">Категории не найдены</td>';
      el.categoriesBody.appendChild(row);
      updateCategoriesBulkUi();
      return;
    }
    for (const rowNode of allRows) {
      el.categoriesBody.appendChild(rowNode);
    }
    updateCategoriesBulkUi();
  }

  window.App.categoryUi = {
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
  };
})();
