(() => {
  const { state, el, core } = window.App;

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
    window.App.categoryUi.updateIconToggleLabel(el.editCategoryIconToggle, el.editCategoryIcon.value);
    window.App.categoryUi.closeIconPopovers();
    window.App.categoryUi.setCategoryKind("edit", item.kind || "expense");
    el.editCategoryGroup.value = item.group_id ? String(item.group_id) : "";
    const selected = state.categoryGroups.find((group) => String(group.id) === el.editCategoryGroup.value);
    if (el.editCategoryGroupSearch) {
      el.editCategoryGroupSearch.value = selected?.name || "";
    }
    window.App.categoryUi.renderEditGroupPicker();
    el.editCategoryModal.classList.remove("hidden");
  }

  function closeEditCategoryModal() {
    state.editCategoryId = null;
    window.App.categoryUi.closeIconPopovers();
    if (el.editCategoryGroupPickerBlock) {
      el.editCategoryGroupPickerBlock.classList.add("hidden");
    }
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

  window.App.categoryTableUi = {
    updateCategoriesBulkUi,
    openEditGroupModal,
    closeEditGroupModal,
    openEditCategoryModal,
    closeEditCategoryModal,
    groupCategoryIds,
    renderCategories,
  };
})();
