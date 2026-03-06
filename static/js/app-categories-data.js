(() => {
  const { state, el, core } = window.App;
  let categoriesRequestController = null;
  let categoriesRequestSeq = 0;
  const CATEGORIES_GROUPS_CACHE_TTL_MS = 60000;
  const CATEGORIES_CATALOG_CACHE_TTL_MS = 60000;
  const CATEGORIES_TABLE_CACHE_TTL_MS = 45000;

  function getCategoriesTableCacheKey(params) {
    return `categories:table:${params.toString()}`;
  }

  function applyCategoriesPageData(data, reset) {
    const pageItems = Array.isArray(data) ? data : (data.items || []);
    state.categoryTotal = Array.isArray(data) ? pageItems.length : Number(data.total || 0);
    if (reset) {
      state.categoryTableItems = pageItems.slice();
    } else {
      const existing = new Set(state.categoryTableItems.map((item) => item.id));
      for (const item of pageItems) {
        if (!existing.has(item.id)) {
          state.categoryTableItems.push(item);
        }
      }
    }
    if (pageItems.length > 0) {
      state.categoryPage += 1;
    }
    state.categoriesHasMore = state.categoryTableItems.length < state.categoryTotal && pageItems.length > 0;
  }

  async function loadCategoryGroups() {
    const categoryUi = window.App.categoryUi;
    const cacheKey = "categories:groups";
    const cached = core.getUiRequestCache(cacheKey, CATEGORIES_GROUPS_CACHE_TTL_MS);
    if (cached) {
      state.categoryGroups = cached;
    } else {
      try {
        state.categoryGroups = await core.requestJson("/api/v1/categories/groups", { headers: core.authHeaders() });
        core.setUiRequestCache(cacheKey, state.categoryGroups);
      } catch {
        state.categoryGroups = [];
      }
    }
    categoryUi.fillGroupSelect(el.categoryGroup, el.categoryKind.value, "Без группы");
    categoryUi.fillGroupSelect(el.bulkCategoryGroup, "", "Группа (не менять)");
  }

  async function loadCategoryCatalog() {
    const cacheKey = "categories:catalog";
    const cached = core.getUiRequestCache(cacheKey, CATEGORIES_CATALOG_CACHE_TTL_MS);
    if (cached) {
      state.categories = cached;
      return;
    }
    state.categories = await core.requestJson("/api/v1/categories", { headers: core.authHeaders() });
    core.setUiRequestCache(cacheKey, state.categories);
  }

  async function loadCategoriesTable(options = {}) {
    const categoryUi = window.App.categoryUi;
    const reset = options.reset !== false;
    const force = options.force === true;
    if (state.categoriesLoading && reset && categoriesRequestController) {
      categoriesRequestController.abort();
    } else if (state.categoriesLoading && !force) {
      return;
    }
    if (!reset && !state.categoriesHasMore) {
      return;
    }

    if (reset) {
      state.categoryPage = 1;
      state.categoryTotal = 0;
      state.categoriesHasMore = true;
      state.categoryTableItems = [];
      state.selectedCategoryIds.clear();
      state.selectedGroupIds.clear();
    }

    const params = new URLSearchParams({
      page: String(state.categoryPage),
      page_size: String(state.categoryPageSize),
    });
    if (state.categoryFilterKind && state.categoryFilterKind !== "all") {
      params.set("kind", state.categoryFilterKind);
    }
    const query = el.categorySearchQ.value.trim();
    if (query) {
      params.set("q", query);
    }

    const cacheKey = getCategoriesTableCacheKey(params);
    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, CATEGORIES_TABLE_CACHE_TTL_MS);
      if (cached) {
        applyCategoriesPageData(cached, reset);
        categoryUi.renderCategories();
        return;
      }
    }

    state.categoriesLoading = true;
    const requestController = new AbortController();
    categoriesRequestController = requestController;
    const requestSeq = ++categoriesRequestSeq;
    try {
      const data = await core.requestJson(`/api/v1/categories?${params.toString()}`, {
        headers: core.authHeaders(),
        signal: requestController.signal,
      });
      if (requestSeq !== categoriesRequestSeq) {
        return;
      }
      core.setUiRequestCache(cacheKey, data);
      applyCategoriesPageData(data, reset);
      categoryUi.renderCategories();
    } catch (err) {
      if (core.isAbortError && core.isAbortError(err)) {
        return;
      }
      throw err;
    } finally {
      if (categoriesRequestController === requestController) {
        categoriesRequestController = null;
        state.categoriesLoading = false;
      }
    }
  }

  async function loadMoreCategoriesTable() {
    await loadCategoriesTable({ reset: false });
  }

  async function loadCategories() {
    const categoryUi = window.App.categoryUi;
    await loadCategoryGroups();
    await loadCategoryCatalog();
    await loadCategoriesTable({ reset: true });

    const liveCategoryIds = new Set(state.categories.map((item) => item.id));
    for (const id of Array.from(state.selectedCategoryIds)) {
      if (!liveCategoryIds.has(id)) {
        state.selectedCategoryIds.delete(id);
      }
    }
    const liveGroupIds = new Set(state.categoryGroups.map((item) => item.id));
    for (const id of Array.from(state.selectedGroupIds)) {
      if (!liveGroupIds.has(id)) {
        state.selectedGroupIds.delete(id);
      }
    }

    categoryUi.fillGroupSelect(el.categoryGroup, el.categoryKind.value, "Без группы");
    categoryUi.fillGroupSelect(el.bulkCategoryGroup, "", "Группа (не менять)");
    categoryUi.populateCategorySelect(el.opCategory, el.opCategory.value, el.opKind.value);
    categoryUi.populateCategorySelect(el.editCategory, el.editCategory.value, el.editKind.value || "expense");

    if (window.App.actions.renderCreateCategoryPicker) {
      window.App.actions.renderCreateCategoryPicker();
    }
    if (window.App.actions.loadDashboardOperations) {
      window.App.actions.loadDashboardOperations().catch(() => {});
    }
    if (window.App.actions.refreshOperationsView) {
      window.App.actions.refreshOperationsView();
    }
  }

  async function createCategory(event) {
    const categoryUi = window.App.categoryUi;
    event.preventDefault();
    const payload = {
      name: el.categoryName.value.trim(),
      kind: el.categoryKind.value,
      group_id: el.categoryGroup.value ? Number(el.categoryGroup.value) : null,
      icon: el.categoryIcon.value || null,
    };

    if (!payload.name) {
      core.setStatus("Введите название категории");
      return;
    }

    const createdCategory = await core.requestJson("/api/v1/categories", {
      method: "POST",
      headers: core.authHeaders(),
      body: JSON.stringify(payload),
    });
    core.invalidateUiRequestCache("categories");
    core.invalidateUiRequestCache("operations");

    el.categoryName.value = "";
    el.categoryGroup.value = "";
    el.categoryIcon.value = "";
    categoryUi.updateIconToggleLabel(el.categoryIconToggle, "");
    categoryUi.closeIconPopovers();
    categoryUi.setCategoryKind("create", "expense");
    categoryUi.closeCreateCategoryModal(false);
    await loadCategories();
    if (window.App.actions.onCategoryCreated) {
      window.App.actions.onCategoryCreated(createdCategory);
    }
  }

  async function updateCategory(event) {
    const categoryUi = window.App.categoryUi;
    event.preventDefault();
    if (!state.editCategoryId) {
      return;
    }
    const payload = {
      name: el.editCategoryName.value.trim(),
      kind: el.editCategoryKind.value,
      group_id: el.editCategoryGroup.value ? Number(el.editCategoryGroup.value) : null,
      icon: el.editCategoryIcon.value || null,
    };
    if (!payload.name) {
      core.setStatus("Введите название категории");
      return;
    }
    await core.requestJson(`/api/v1/categories/${state.editCategoryId}`, {
      method: "PATCH",
      headers: core.authHeaders(),
      body: JSON.stringify(payload),
    });
    core.invalidateUiRequestCache("categories");
    core.invalidateUiRequestCache("operations");
    categoryUi.closeEditCategoryModal();
    await loadCategories();
  }

  async function createGroup(event) {
    event.preventDefault();
    const payload = {
      name: el.groupName.value.trim(),
      kind: el.groupKind.value,
      accent_color: el.groupAccentColor.value || null,
    };
    if (!payload.name) {
      core.setStatus("Введите название группы");
      return;
    }
    await core.requestJson("/api/v1/categories/groups", {
      method: "POST",
      headers: core.authHeaders(),
      body: JSON.stringify(payload),
    });
    core.invalidateUiRequestCache("categories");
    core.invalidateUiRequestCache("operations");
    el.groupName.value = "";
    el.groupAccentColor.value = "#ff8a3d";
    el.groupAccentColorHex.value = "#ff8a3d";
    window.App.actions.closeCreateGroupModal();
    await loadCategories();
  }

  async function updateGroup(event) {
    const categoryUi = window.App.categoryUi;
    event.preventDefault();
    const groupId = Number(el.editGroupId.value || 0);
    const name = el.editGroupName.value.trim();
    const accentColor = el.editGroupAccentColor.value || null;
    if (!groupId) {
      return;
    }
    if (!name) {
      core.setStatus("Введите название группы");
      return;
    }
    await core.requestJson(`/api/v1/categories/groups/${groupId}`, {
      method: "PATCH",
      headers: core.authHeaders(),
      body: JSON.stringify({ name, accent_color: accentColor }),
    });
    core.invalidateUiRequestCache("categories");
    core.invalidateUiRequestCache("operations");
    categoryUi.closeEditGroupModal();
    await loadCategories();
  }

  async function deleteGroupFlow(group) {
    core.runDestructiveAction({
      confirmMessage: `Удалить группу «${group.name}»?`,
      doDelete: async () => {
        await core.requestJson(`/api/v1/categories/groups/${group.id}`, {
          method: "DELETE",
          headers: core.authHeaders(),
        });
        core.invalidateUiRequestCache("categories");
        core.invalidateUiRequestCache("operations");
      },
      onAfterDelete: loadCategories,
      toastMessage: `Группа «${group.name}» удалена`,
      onDeleteError: "Не удалось удалить группу",
    });
  }

  async function deleteCategoryFlow(item) {
    core.runDestructiveAction({
      confirmMessage: `Удалить категорию «${item.name}»?`,
      doDelete: async () => {
        await core.requestJson(`/api/v1/categories/${item.id}`, {
          method: "DELETE",
          headers: core.authHeaders(),
        });
        core.invalidateUiRequestCache("categories");
        core.invalidateUiRequestCache("operations");
      },
      onAfterDelete: loadCategories,
      toastMessage: `Категория «${item.name}» удалена`,
      undoAction: async () => {
        await core.requestJson("/api/v1/categories", {
          method: "POST",
          headers: core.authHeaders(),
          body: JSON.stringify({ name: item.name, kind: item.kind, group_id: item.group_id }),
        });
        core.invalidateUiRequestCache("categories");
        core.invalidateUiRequestCache("operations");
        await loadCategories();
        return "Категория восстановлена";
      },
      onDeleteError: "Не удалось удалить категорию",
    });
  }

  async function bulkDeleteCategories(ids) {
    for (const id of ids) {
      const category = state.categories.find((item) => item.id === id);
      if (!category || category.is_system) {
        continue;
      }
      await core.requestJson(`/api/v1/categories/${id}`, {
        method: "DELETE",
        headers: core.authHeaders(),
      });
    }
    core.invalidateUiRequestCache("categories");
    core.invalidateUiRequestCache("operations");
    state.selectedCategoryIds.clear();
    await loadCategories();
  }

  async function bulkDeleteGroups(ids) {
    for (const id of ids) {
      await core.requestJson(`/api/v1/categories/groups/${id}`, {
        method: "DELETE",
        headers: core.authHeaders(),
      });
    }
    core.invalidateUiRequestCache("categories");
    core.invalidateUiRequestCache("operations");
    state.selectedGroupIds.clear();
    await loadCategories();
  }

  async function bulkUpdateCategories(ids, groupIdValue) {
    const groupId = groupIdValue ? Number(groupIdValue) : null;
    for (const categoryId of ids) {
      const category = state.categories.find((item) => item.id === categoryId);
      if (!category || category.is_system) {
        continue;
      }
      await core.requestJson(`/api/v1/categories/${category.id}`, {
        method: "PATCH",
        headers: core.authHeaders(),
        body: JSON.stringify({ group_id: groupId }),
      });
    }
    core.invalidateUiRequestCache("categories");
    core.invalidateUiRequestCache("operations");
    state.selectedCategoryIds.clear();
    await loadCategories();
  }

  window.App.categoryData = {
    loadCategoryGroups,
    loadCategoryCatalog,
    loadCategoriesTable,
    loadMoreCategoriesTable,
    loadCategories,
    createCategory,
    updateCategory,
    createGroup,
    updateGroup,
    deleteGroupFlow,
    deleteCategoryFlow,
    bulkDeleteCategories,
    bulkDeleteGroups,
    bulkUpdateCategories,
  };
})();
