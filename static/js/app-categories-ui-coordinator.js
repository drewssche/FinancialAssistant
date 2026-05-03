(() => {
  window.App = window.App || {};

  function renderGroupedCategoryTable({
    body,
    groups,
    queryRaw,
    queryActive,
    readCollapsedSet,
    renderGroupHeaderRow,
    renderCategoryRow,
    updateBulkUi,
  }) {
    if (!body) {
      return;
    }
    body.innerHTML = "";
    if (!groups.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="4">Категории не найдены</td>';
      body.appendChild(row);
      updateBulkUi?.();
      return;
    }

    const collapsedSet = readCollapsedSet();
    for (const group of groups) {
      const isCollapsed = !queryActive && !group.isUngrouped && collapsedSet.has(group.key);
      body.appendChild(renderGroupHeaderRow(group, queryRaw, isCollapsed, queryActive));
      for (const child of group.children) {
        body.appendChild(
          renderCategoryRow(child, queryRaw, {
            groupId: group.id,
            groupKey: group.key,
            isCollapsed,
            groupLabel: group.isUngrouped
              ? "<span class='muted-small'>Без группы</span>"
              : "<span class='muted-small category-tree-mark'>↳</span>",
            groupAccentColor: group.accentColor || null,
          }),
        );
      }
    }
    updateBulkUi?.();
  }

  function toggleCollapsedGroupFromEvent({
    event,
    queryRaw,
    ungroupedKey,
    readCollapsedSet,
    persistCollapsedSet,
    rerender,
  }) {
    const btn = event.target.closest("button[data-category-group-toggle-key]");
    if (!btn) {
      return false;
    }
    const queryActive = Boolean(String(queryRaw || "").trim());
    const groupKey = String(btn.dataset.categoryGroupToggleKey || "");
    if (!groupKey || queryActive || groupKey === ungroupedKey) {
      return true;
    }
    const collapsedSet = readCollapsedSet();
    if (collapsedSet.has(groupKey)) {
      collapsedSet.delete(groupKey);
    } else {
      collapsedSet.add(groupKey);
    }
    persistCollapsedSet(collapsedSet);
    rerender();
    return true;
  }

  function collapseAllCategoryGroups({ queryRaw, groups, persistCollapsedSet, rerender }) {
    if (Boolean(String(queryRaw || "").trim())) {
      return;
    }
    const nextSet = new Set(groups.filter((group) => !group.isUngrouped).map((group) => group.key));
    persistCollapsedSet(nextSet);
    rerender();
  }

  function expandAllCategoryGroups({ persistCollapsedSet, rerender }) {
    persistCollapsedSet(new Set());
    rerender();
  }

  function openEditGroupModal({ group, el }) {
    if (!group || !el) {
      return;
    }
    el.editGroupId.value = String(group.id);
    el.editGroupName.value = group.name || "";
    const color = group.accent_color || "#ff8a3d";
    el.editGroupAccentColor.value = color;
    el.editGroupAccentColorHex.value = color;
    el.editGroupModal.classList.remove("hidden");
  }

  function closeEditGroupModal({ el }) {
    if (!el) {
      return;
    }
    el.editGroupId.value = "";
    el.editGroupModal.classList.add("hidden");
  }

  function openEditCategoryModal({ item, state, el, categoryUi }) {
    if (!item || !state || !el || !categoryUi) {
      return;
    }
    state.editCategoryId = item.id;
    el.editCategoryName.value = item.name || "";
    el.editCategoryIcon.value = item.icon || "";
    categoryUi.updateIconToggleLabel(el.editCategoryIconToggle, el.editCategoryIcon.value);
    categoryUi.closeIconPopovers();
    categoryUi.setCategoryKind("edit", item.kind || "expense");
    el.editCategoryGroup.value = item.group_id ? String(item.group_id) : "";
    const selected = state.categoryGroups.find((group) => String(group.id) === el.editCategoryGroup.value);
    if (el.editCategoryGroupSearch) {
      el.editCategoryGroupSearch.value = selected?.name || "";
    }
    categoryUi.renderEditGroupPicker();
    el.editCategoryModal.classList.remove("hidden");
  }

  function closeEditCategoryModal({ state, el, categoryUi }) {
    if (!state || !el || !categoryUi) {
      return;
    }
    state.editCategoryId = null;
    categoryUi.closeIconPopovers();
    if (el.editCategoryGroupPickerBlock) {
      el.editCategoryGroupPickerBlock.classList.add("hidden");
    }
    el.editCategoryModal.classList.add("hidden");
  }

  function toggleCategoriesCardMenu({ event, pickerUtils }) {
    const trigger = event.target.closest("button[data-mobile-card-menu-trigger], button[data-table-menu-trigger]");
    if (!trigger) {
      return false;
    }
    const mobileMenuId = String(trigger?.dataset.mobileCardMenuTrigger || "");
    const tableMenuId = String(trigger?.dataset.tableMenuTrigger || "");
    const menu = mobileMenuId
      ? document.querySelector(`.mobile-card-actions-popover[data-mobile-card-menu="${CSS.escape(mobileMenuId)}"]`)
      : tableMenuId
        ? document.querySelector(`.table-kebab-popover[data-table-menu="${CSS.escape(tableMenuId)}"]`)
        : null;
    if (!menu || !pickerUtils?.setPopoverOpen) {
      return true;
    }
    const ownerCard = trigger.closest(".category-mobile-card, .category-mobile-group-card");
    const ownerRow = trigger.closest("tr");
    const ownerCell = trigger.closest("td");
    const owners = [trigger, trigger.parentElement].filter(Boolean);
    const clearOpenState = () => {
      ownerCard?.classList.remove("mobile-card-menu-open");
      ownerCell?.classList.remove("mobile-card-menu-open-cell");
      ownerRow?.classList.remove("mobile-card-menu-open-row");
      ownerCell?.classList.remove("table-menu-open-cell");
      ownerRow?.classList.remove("table-menu-open-row");
    };
    const shouldOpen = menu.classList.contains("hidden");
    document.querySelectorAll(".mobile-card-actions-popover:not(.hidden), .table-kebab-popover:not(.hidden)").forEach((node) => {
      if (node !== menu) {
        pickerUtils.setPopoverOpen(node, false, {
          owners: Array.isArray(node.__appPopoverOwners) ? node.__appPopoverOwners : [],
        });
        (Array.isArray(node.__appPopoverOwners) ? node.__appPopoverOwners : []).forEach((owner) => owner?.blur?.());
        node.closest(".mobile-card-menu-open")?.classList.remove("mobile-card-menu-open");
        node.closest("td.mobile-card-menu-open-cell")?.classList.remove("mobile-card-menu-open-cell");
        node.closest("tr.mobile-card-menu-open-row")?.classList.remove("mobile-card-menu-open-row");
        node.closest(".table-menu-open-cell")?.classList.remove("table-menu-open-cell");
        node.closest(".table-menu-open-row")?.classList.remove("table-menu-open-row");
      }
    });
    pickerUtils.setPopoverOpen(menu, shouldOpen, { owners, onClose: clearOpenState });
    ownerCard?.classList.toggle("mobile-card-menu-open", shouldOpen);
    ownerCell?.classList.toggle("mobile-card-menu-open-cell", shouldOpen);
    if (ownerRow) {
      ownerRow.classList.toggle("mobile-card-menu-open-row", shouldOpen);
      ownerRow.classList.toggle("table-menu-open-row", shouldOpen);
    }
    ownerCell?.classList.toggle("table-menu-open-cell", shouldOpen);
    if (!shouldOpen) {
      clearOpenState();
      trigger?.blur?.();
    }
    return true;
  }

  function handleCategoriesBodyClick({
    event,
    state,
    pickerUtils,
    handleGroupToggleClick,
    openEditGroupModalAction,
    deleteGroupFlow,
    deleteCategoryFlow,
    openEditCategoryModalAction,
  }) {
    if (toggleCategoriesCardMenu({ event, pickerUtils })) {
      return true;
    }
    if (handleGroupToggleClick?.(event)) {
      return true;
    }
    const editGroupBtn = event.target.closest("button[data-edit-group-id]");
    if (editGroupBtn) {
      const id = Number(editGroupBtn.dataset.editGroupId);
      const group = state.categoryGroups.find((item) => item.id === id);
      if (group) {
        openEditGroupModalAction?.(group);
      }
      return true;
    }
    const deleteGroupBtn = event.target.closest("button[data-delete-group-id]");
    if (deleteGroupBtn) {
      const id = Number(deleteGroupBtn.dataset.deleteGroupId);
      const group = state.categoryGroups.find((item) => item.id === id);
      if (group) {
        deleteGroupFlow?.(group);
      }
      return true;
    }
    const deleteBtn = event.target.closest("button[data-delete-category-id]");
    if (deleteBtn) {
      const row = deleteBtn.closest("tr");
      const item = row
        ? JSON.parse(row.dataset.item || "{}")
        : state.categories.find((category) => Number(category.id) === Number(deleteBtn.dataset.deleteCategoryId || 0));
      if (item?.id) {
        deleteCategoryFlow?.(item);
      }
      return true;
    }
    const editBtn = event.target.closest("button[data-edit-category-id]");
    if (editBtn) {
      const row = editBtn.closest("tr");
      const item = row
        ? JSON.parse(row.dataset.item || "{}")
        : state.categories.find((category) => Number(category.id) === Number(editBtn.dataset.editCategoryId || 0));
      if (item?.id) {
        openEditCategoryModalAction?.(item);
      }
      return true;
    }
    const row = event.target.closest("tr[data-category-id]");
    if (!row) {
      return false;
    }
    if (event.target.closest("button, a, input, select, textarea, label, .app-popover")) {
      return true;
    }
    const item = JSON.parse(row.dataset.item || "{}");
    if (item?.id) {
      openEditCategoryModalAction?.(item);
    }
    return true;
  }

  const api = {
    renderGroupedCategoryTable,
    toggleCollapsedGroupFromEvent,
    collapseAllCategoryGroups,
    expandAllCategoryGroups,
    openEditGroupModal,
    closeEditGroupModal,
    openEditCategoryModal,
    closeEditCategoryModal,
    toggleCategoriesCardMenu,
    handleCategoriesBodyClick,
  };

  window.App.registerRuntimeModule?.("categories-ui-coordinator", api);
})();
