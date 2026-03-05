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
  }

  function setCategoryKind(mode, kind) {
    if (mode === "create") {
      el.categoryKind.value = kind;
      core.syncSegmentedActive(el.createCategoryKind, "cat-create-kind", kind);
      fillGroupSelect(el.categoryGroup, kind, "Без группы");
      return;
    }
    if (mode === "edit") {
      el.editCategoryKind.value = kind;
      core.syncSegmentedActive(el.editCategoryKindSwitch, "cat-edit-kind", kind);
      fillGroupSelect(el.editCategoryGroup, kind, "Без группы");
    }
  }

  function openCreateCategoryModal(options = {}) {
    const kind = options.kind || "expense";
    const prefillName = typeof options.prefillName === "string" ? options.prefillName.trim() : "";
    const resetForm = options.reset !== false;

    if (resetForm) {
      el.categoryName.value = prefillName;
      el.categoryGroup.value = "";
      el.categoryIcon.value = "";
      updateIconToggleLabel(el.categoryIconToggle, "");
      closeIconPopovers();
    } else if (prefillName) {
      el.categoryName.value = prefillName;
    }

    setCategoryKind("create", kind);
    el.createCategoryModal.classList.remove("hidden");
  }

  function closeCreateCategoryModal(clearPending = true) {
    closeIconPopovers();
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
    const totalCount = categoryIds.length + groupIds.length;
    const baseSummary = `Групп: ${groupIds.length} • Категорий: ${categoryIds.length} • Всего: ${totalCount}`;
    el.categoriesSelectedCount.textContent =
      selectedVisibleCount > 0
        ? `Выбрано: ${selectedVisibleCount} из ${totalCount} • ${baseSummary}`
        : baseSummary;
    el.bulkEditCategoriesBtn.classList.toggle("hidden-action", selectedCategoryCount === 0 || selectedGroupCount > 0);
    el.bulkDeleteCategoriesBtn.classList.toggle("hidden-action", selectedVisibleCount === 0);
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
    el.editCategoryModal.classList.remove("hidden");
  }

  function closeEditCategoryModal() {
    state.editCategoryId = null;
    closeIconPopovers();
    el.editCategoryModal.classList.add("hidden");
  }

  function groupCategoryIds(groupId) {
    return state.categories.filter((item) => item.group_id === groupId && !item.is_system).map((item) => item.id);
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
    tr.innerHTML = `
      <td class="select-col" style="border-left: 3px solid ${leftBorderColor};"><input class="table-checkbox" type="checkbox" data-select-category-id="${item.id}" data-category-group-id="${options.groupId || ""}" ${state.selectedCategoryIds.has(item.id) ? "checked" : ""} ${item.is_system ? "disabled" : ""} /></td>
      <td>${options.groupLabel || "<span class='muted-small'>Без группы</span>"}</td>
      <td>${core.renderCategoryChip({ name: item.name, icon: item.icon || item.group_icon, accent_color: item.group_accent_color }, query)}</td>
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
    const rows = state.categories.filter((item) => {
      if (state.categoryFilterKind !== "all" && item.kind !== state.categoryFilterKind) {
        return false;
      }
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

    el.categoriesBody.innerHTML = "";
    if (!rows.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="5">Категории не найдены</td>';
      el.categoriesBody.appendChild(row);
      return;
    }

    const displayQuery = el.categorySearchQ.value.trim();
    const ungrouped = rows
      .filter((item) => !item.group_id)
      .sort((a, b) => a.name.localeCompare(b.name, "ru"));
    for (const item of ungrouped) {
      el.categoriesBody.appendChild(renderCategoryRow(item, displayQuery));
    }

    const groups = state.categoryGroups
      .filter((group) => state.categoryFilterKind === "all" || group.kind === state.categoryFilterKind)
      .sort((a, b) => a.name.localeCompare(b.name, "ru"));

    for (const group of groups) {
      const children = rows
        .filter((item) => item.group_id === group.id)
        .sort((a, b) => a.name.localeCompare(b.name, "ru"));
      if (!children.length && query && !group.name.toLowerCase().includes(query)) {
        continue;
      }
      el.categoriesBody.appendChild(renderGroupRow(group, displayQuery));
      for (const child of children) {
        const groupLabel = "<span class='muted-small category-tree-mark'>↳</span>";
        el.categoriesBody.appendChild(
          renderCategoryRow(child, displayQuery, {
            groupId: group.id,
            groupLabel,
            groupAccentColor: group.accent_color || null,
          }),
        );
      }
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
    updateCategoriesBulkUi,
    openEditGroupModal,
    closeEditGroupModal,
    openEditCategoryModal,
    closeEditCategoryModal,
    groupCategoryIds,
    renderCategories,
  };
})();
