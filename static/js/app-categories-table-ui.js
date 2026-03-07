(() => {
  const { state, el, core } = window.App;
  const CATEGORY_UNGROUPED_KEY = "ungrouped";
  const DEFAULT_GROUP_ACCENT = "#4d6282";
  const DEFAULT_GROUP_ACCENT_BY_KIND = {
    expense: "#ff8a3d",
    income: "#49be78",
  };

  function normalizeHexColor(value) {
    const raw = String(value || "").trim();
    const match = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(raw);
    if (!match) {
      return "";
    }
    const hex = match[1];
    if (hex.length === 3) {
      return `#${hex.split("").map((char) => char + char).join("")}`.toLowerCase();
    }
    return `#${hex.toLowerCase()}`;
  }

  function hexToRgba(hex, alpha) {
    const normalized = normalizeHexColor(hex);
    if (!normalized) {
      return `rgba(77, 98, 130, ${alpha})`;
    }
    const r = Number.parseInt(normalized.slice(1, 3), 16);
    const g = Number.parseInt(normalized.slice(3, 5), 16);
    const b = Number.parseInt(normalized.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function resolveGroupAccent(colorValue, kind = "") {
    const accent = normalizeHexColor(colorValue)
      || DEFAULT_GROUP_ACCENT_BY_KIND[String(kind || "").toLowerCase()]
      || DEFAULT_GROUP_ACCENT;
    return {
      accent,
      soft: hexToRgba(accent, 0.2),
    };
  }

  function getCategoryGroupKey(groupId) {
    return groupId ? `group:${groupId}` : CATEGORY_UNGROUPED_KEY;
  }

  function readCollapsedCategoryGroups() {
    const list = state.preferences?.data?.ui?.categories_collapsed_groups
      || state.preferences?.data?.ui?.categories_collapsed_group_keys;
    if (!Array.isArray(list)) {
      return new Set();
    }
    return new Set(list.map((item) => String(item)));
  }

  function writeCollapsedCategoryGroups(nextSet) {
    if (!state.preferences) {
      return;
    }
    state.preferences.data = state.preferences.data || {};
    state.preferences.data.ui = state.preferences.data.ui || {};
    const serialized = Array.from(nextSet);
    state.preferences.data.ui.categories_collapsed_groups = serialized;
    state.preferences.data.ui.categories_collapsed_group_keys = serialized;
  }

  function persistCollapsedCategoryGroups(nextSet) {
    writeCollapsedCategoryGroups(nextSet);
    if (window.App.actions?.savePreferences) {
      window.App.actions.savePreferences().catch(() => {});
    }
  }

  function updateCategoriesBulkUi() {
    // Categories table no longer supports bulk selection; keep hook for callers.
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
    return state.categoryTableItems
      .filter((item) => item.group_id === groupId && !item.is_system)
      .map((item) => item.id);
  }

  function getCategoriesDisplayGroups(queryRaw, queryLower) {
    const filteredRows = state.categoryTableItems.filter((item) => {
      if (!queryLower) {
        return true;
      }
      const groupName = String(item.group_name || "").toLowerCase();
      return (
        String(item.name || "").toLowerCase().includes(queryLower)
        || core.kindLabel(item.kind).toLowerCase().includes(queryLower)
        || groupName.includes(queryLower)
      );
    });

    const groups = [];
    const ungroupedChildren = filteredRows
      .filter((item) => !item.group_id)
      .sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""), "ru"));
    if (ungroupedChildren.length) {
      groups.push({
        key: CATEGORY_UNGROUPED_KEY,
        id: null,
        isUngrouped: true,
        name: "Без группы",
        kind: "",
        accentColor: null,
        children: ungroupedChildren,
      });
    }

    const filteredGroups = state.categoryGroups
      .filter((group) => state.categoryFilterKind === "all" || group.kind === state.categoryFilterKind)
      .sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""), "ru"));

    for (const group of filteredGroups) {
      const groupMatchesQuery = queryLower ? String(group.name || "").toLowerCase().includes(queryLower) : false;
      const childrenSource = groupMatchesQuery ? state.categoryTableItems : filteredRows;
      const children = childrenSource
        .filter((item) => item.group_id === group.id)
        .sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""), "ru"));
      if (!children.length && queryLower && !groupMatchesQuery) {
        continue;
      }
      groups.push({
        key: getCategoryGroupKey(group.id),
        id: group.id,
        isUngrouped: false,
        name: group.name || "Без названия",
        kind: group.kind || "",
        accentColor: group.accent_color || null,
        children,
      });
    }
    return groups;
  }

  function syncCategoryGroupControls(queryActive, groups) {
    const hasToggleGroups = groups.some((group) => !group.isUngrouped);
    if (el.categoriesCollapseAllBtn) {
      el.categoriesCollapseAllBtn.disabled = queryActive || !hasToggleGroups;
    }
    if (el.categoriesExpandAllBtn) {
      el.categoriesExpandAllBtn.disabled = queryActive || !hasToggleGroups;
    }
  }

  function renderCategoryRow(item, queryRaw, options = {}) {
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
    if (options.groupKey) {
      tr.dataset.groupKey = options.groupKey;
    }
    if (options.isCollapsed) {
      tr.classList.add("hidden");
    }
    const accent = resolveGroupAccent(options.groupAccentColor, item.kind);
    tr.style.setProperty("--category-group-accent", accent.accent);
    tr.style.setProperty("--category-group-accent-soft", accent.soft);
    const actionCell = item.is_system
      ? "<span class='muted-small'>Защищено</span>"
      : `<div class='actions row-actions'><button class='btn btn-secondary' data-edit-category-id='${item.id}'>Редактировать</button><button class='btn btn-danger' data-delete-category-id='${item.id}'>Удалить</button></div>`;
    const groupCell = options.groupLabel || "<span class='muted-small'>Без группы</span>";
    const nameCell = core.renderCategoryChip(
      { name: item.name, icon: item.icon || item.group_icon, accent_color: item.group_accent_color || accent.accent },
      queryRaw,
    );
    tr.innerHTML = `
      <td class="category-group-accent-cell" data-label="Группа">${groupCell}</td>
      <td data-label="Название">${nameCell}</td>
      <td data-label="Тип"><span class="kind-pill kind-pill-${kindClass}">${core.highlightText(core.kindLabel(item.kind), queryRaw)}</span></td>
      <td class="mobile-actions-cell" data-label="Действия">${actionCell}</td>
    `;
    return tr;
  }

  function renderGroupHeaderRow(group, queryRaw, isCollapsed, queryActive) {
    const tr = document.createElement("tr");
    tr.className = "category-table-group-row";
    tr.dataset.itemType = "group";
    tr.dataset.groupKey = group.key;
    if (group.id) {
      tr.dataset.groupId = String(group.id);
    }
    const accent = resolveGroupAccent(group.accentColor, group.kind);
    tr.style.setProperty("--category-group-accent", accent.accent);
    tr.style.setProperty("--category-group-accent-soft", accent.soft);
    const chevron = group.isUngrouped ? "•" : (isCollapsed ? "▸" : "▾");
    const groupName = group.isUngrouped
      ? `<span class="muted-small">${core.highlightText(group.name, queryRaw)}</span>`
      : core.renderCategoryChip({ name: group.name, icon: null, accent_color: group.accentColor || accent.accent }, queryRaw);
    const kindMeta = group.kind ? `<span class="item-catalog-group-meta">${core.highlightText(core.kindLabel(group.kind), queryRaw)}</span>` : "";
    const toggleDisabled = queryActive || group.isUngrouped;
    const groupActions = group.id
      ? `<div class="actions row-actions"><button class="btn btn-secondary btn-xs" data-edit-group-id="${group.id}" type="button">Редактировать</button><button class="btn btn-danger btn-xs" data-delete-group-id="${group.id}" type="button">Удалить</button></div>`
      : "";
    tr.innerHTML = `
      <td colspan="4" class="category-table-group-cell category-group-accent-cell">
        <div class="category-table-group-wrap">
          <button type="button" class="item-catalog-group-btn category-table-group-btn" data-category-group-toggle-key="${group.key}" ${toggleDisabled ? "disabled" : ""}>
            <span class="item-catalog-group-chevron">${chevron}</span>
            <span class="item-catalog-group-name">${groupName}</span>
            <span class="item-catalog-group-metas">
              <span class="item-catalog-group-meta">${group.children.length} кат.</span>
              ${kindMeta}
            </span>
          </button>
          ${groupActions}
        </div>
      </td>
    `;
    return tr;
  }

  function renderCategories() {
    const queryRaw = String(el.categorySearchQ.value || "").trim();
    const queryLower = queryRaw.toLowerCase();
    const queryActive = Boolean(queryRaw);
    const groups = getCategoriesDisplayGroups(queryRaw, queryLower);
    syncCategoryGroupControls(queryActive, groups);

    el.categoriesBody.innerHTML = "";
    if (!groups.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="4">Категории не найдены</td>';
      el.categoriesBody.appendChild(row);
      updateCategoriesBulkUi();
      return;
    }

    const collapsedSet = readCollapsedCategoryGroups();
    for (const group of groups) {
      const isCollapsed = !queryActive && !group.isUngrouped && collapsedSet.has(group.key);
      el.categoriesBody.appendChild(renderGroupHeaderRow(group, queryRaw, isCollapsed, queryActive));
      for (const child of group.children) {
        const row = renderCategoryRow(child, queryRaw, {
          groupId: group.id,
          groupKey: group.key,
          isCollapsed,
          groupLabel: group.isUngrouped
            ? "<span class='muted-small'>Без группы</span>"
            : "<span class='muted-small category-tree-mark'>↳</span>",
          groupAccentColor: group.accentColor || null,
        });
        el.categoriesBody.appendChild(row);
      }
    }
    updateCategoriesBulkUi();
  }

  function handleCategoriesGroupToggleClick(event) {
    const btn = event.target.closest("button[data-category-group-toggle-key]");
    if (!btn) {
      return false;
    }
    const queryActive = Boolean(String(el.categorySearchQ.value || "").trim());
    const groupKey = String(btn.dataset.categoryGroupToggleKey || "");
    if (!groupKey || queryActive || groupKey === CATEGORY_UNGROUPED_KEY) {
      return true;
    }
    const collapsedSet = readCollapsedCategoryGroups();
    if (collapsedSet.has(groupKey)) {
      collapsedSet.delete(groupKey);
    } else {
      collapsedSet.add(groupKey);
    }
    persistCollapsedCategoryGroups(collapsedSet);
    renderCategories();
    return true;
  }

  function collapseAllCategoryGroups() {
    const queryActive = Boolean(String(el.categorySearchQ.value || "").trim());
    if (queryActive) {
      return;
    }
    const groups = getCategoriesDisplayGroups("", "");
    const nextSet = new Set(groups.filter((group) => !group.isUngrouped).map((group) => group.key));
    persistCollapsedCategoryGroups(nextSet);
    renderCategories();
  }

  function expandAllCategoryGroups() {
    persistCollapsedCategoryGroups(new Set());
    renderCategories();
  }

  window.App.categoryTableUi = {
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
})();
