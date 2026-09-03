(() => {
  const { state, el, core } = window.App;
  const escapeHtml = core.escapeHtml || ((value) => String(value ?? ""));
  const DEFAULT_BRAND_COLOR = "#7aa8ff";
  const BRANDS_CACHE_TTL_MS = 20000;

  let requestController = null;
  let activeDetailBrand = null;
  let activeDetailItems = [];
  let brandSearchTimer = null;
  let bound = false;

  function normalizeBrandColor(value) {
    const color = String(value || "").trim().toLowerCase();
    return /^#[0-9a-f]{6}$/.test(color) ? color : DEFAULT_BRAND_COLOR;
  }

  function normalizeBrandName(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function invalidateBrandDependentCaches() {
    const catalog = window.App.getRuntimeModule?.("item-catalog") || {};
    if (catalog.invalidateItemCatalogDependentCaches) {
      catalog.invalidateItemCatalogDependentCaches();
      return;
    }
    for (const prefix of [
      "item-catalog",
      "item-brands",
      "op:receipt:templates",
      "operations",
      "plans",
      "analytics",
      "dashboard:highlights",
    ]) {
      core.invalidateUiRequestCache?.(prefix);
    }
    state.itemBrandsLoaded = false;
  }

  function isBrandArchived(brand) {
    return Boolean(brand?.is_archived ?? brand?.brand_is_archived ?? false);
  }

  function brandFromId(brandId) {
    const id = Number(brandId || 0);
    return (state.itemBrands || []).find((brand) => Number(brand?.id || 0) === id) || null;
  }

  function renderBrandChip(brand, options = {}) {
    const name = normalizeBrandName(brand?.name || brand?.brand_name || "");
    if (!name) {
      return '<span class="item-brand-unassigned">Без бренда</span>';
    }
    const color = normalizeBrandColor(brand?.accent_color || brand?.brand_accent_color);
    const title = options.title === false ? "" : ` title="${escapeHtml(name)}"`;
    return `<span class="item-brand-chip" style="--brand-color:${color}"${title}><span class="item-brand-chip-name">${escapeHtml(name)}</span></span>`;
  }

  function payloadItems(payload) {
    if (Array.isArray(payload)) {
      return payload;
    }
    return Array.isArray(payload?.items) ? payload.items : [];
  }

  async function fetchAllBrands(controller) {
    const pageSize = 100;
    const first = await core.requestJson(`/api/v1/operations/item-brands?page=1&page_size=${pageSize}`, {
      headers: core.authHeaders(),
      signal: controller.signal,
    });
    const items = payloadItems(first).slice();
    const total = Number(first?.total || items.length || 0);
    const pageCount = Math.ceil(total / Number(first?.page_size || pageSize));
    for (let page = 2; page <= pageCount; page += 1) {
      const payload = await core.requestJson(`/api/v1/operations/item-brands?page=${page}&page_size=${pageSize}`, {
        headers: core.authHeaders(),
        signal: controller.signal,
      });
      items.push(...payloadItems(payload));
    }
    return items;
  }

  function relatedCatalogItems(brandId) {
    const id = Number(brandId || 0);
    const catalog = state.itemCatalogAllItems?.length ? state.itemCatalogAllItems : state.itemCatalogItems;
    return (catalog || []).filter((item) => Number(item?.brand_id || 0) === id);
  }

  function brandPurchaseCount(brand) {
    return Number(brand?.purchases_count ?? brand?.purchase_count ?? brand?.operations_count ?? 0);
  }

  function brandSpentTotal(brand) {
    return Number(brand?.spent_total ?? brand?.total_amount ?? 0);
  }

  function syncBrandSelectOptions() {
    const brands = (state.itemBrands || []).slice().sort((a, b) => String(a?.name || "").localeCompare(String(b?.name || ""), "ru"));
    if (el.itemCatalogBrandFilter) {
      const current = String(state.itemCatalogBrandFilter || el.itemCatalogBrandFilter.value || "all");
      el.itemCatalogBrandFilter.innerHTML = `
        <option value="all">Все бренды</option>
        <option value="unassigned">Без бренда</option>
        ${brands.map((brand) => `<option value="${Number(brand.id)}">${escapeHtml(brand.name)}</option>`).join("")}
      `;
      el.itemCatalogBrandFilter.value = Array.from(el.itemCatalogBrandFilter.options).some((option) => option.value === current)
        ? current
        : "all";
      state.itemCatalogBrandFilter = el.itemCatalogBrandFilter.value;
    }
    if (el.itemCatalogBulkBrand) {
      const current = String(el.itemCatalogBulkBrand.value || "");
      el.itemCatalogBulkBrand.innerHTML = `
        <option value="">Без бренда</option>
        ${brands.map((brand) => `<option value="${Number(brand.id)}">${escapeHtml(brand.name)}</option>`).join("")}
      `;
      if (Array.from(el.itemCatalogBulkBrand.options).some((option) => option.value === current)) {
        el.itemCatalogBulkBrand.value = current;
      }
    }
  }

  function getVisibleBrandRows() {
    const query = normalizeBrandName(el.itemBrandsSearchQ?.value || "").toLowerCase();
    if (!query) {
      return (state.itemBrands || []).slice();
    }
    return (state.itemBrands || []).filter((brand) => {
      if (String(brand?.name || "").toLowerCase().includes(query)) {
        return true;
      }
      return relatedCatalogItems(brand?.id).some((item) => (
        String(item?.name || "").toLowerCase().includes(query)
        || String(item?.shop_name || "").toLowerCase().includes(query)
      ));
    });
  }

  function renderBrandKpis() {
    if (!el.itemBrandsKpiGrid) {
      return;
    }
    const brands = state.itemBrands || [];
    const linked = brands.reduce((total, brand) => total + Number(brand?.positions_count || 0), 0);
    const catalog = state.itemCatalogAllItems?.length ? state.itemCatalogAllItems : (state.itemCatalogItems || []);
    const unassigned = catalog.filter((item) => !Number(item?.brand_id || 0)).length;
    el.itemBrandsKpiGrid.innerHTML = `
      <article class="analytics-kpi-card analytics-kpi-neutral"><div class="muted-small">Брендов</div><strong>${brands.length}</strong></article>
      <article class="analytics-kpi-card analytics-kpi-positive"><div class="muted-small">Связанных позиций</div><strong>${linked}</strong></article>
      <article class="analytics-kpi-card ${unassigned ? "analytics-kpi-neutral" : "analytics-kpi-positive"}"><div class="muted-small">Без бренда</div><strong>${unassigned}</strong></article>
    `;
  }

  function renderBrandRow(brand) {
    const id = Number(brand?.id || 0);
    const positionsCount = Number(brand?.positions_count || 0);
    return `
      <tr class="table-record-open-row" data-item-brand-id="${id}">
        <td data-label="Бренд">
          <button class="item-brand-name-button" data-open-item-brand-id="${id}" type="button" aria-label="Открыть бренд ${escapeHtml(brand.name || "")}">
            ${renderBrandChip(brand)}
          </button>
        </td>
        <td data-label="Позиций">${positionsCount}</td>
        <td data-label="Покупок">${brandPurchaseCount(brand)}</td>
        <td data-label="Потрачено"><strong>${core.formatMoney(brandSpentTotal(brand))}</strong></td>
        <td data-label="Последняя покупка">${brand?.last_purchase_date ? core.formatDateRu(brand.last_purchase_date) : "—"}</td>
        <td data-label="Действия"><div class="item-brand-actions">
          <button class="btn btn-secondary btn-xs" data-edit-item-brand-id="${id}" type="button">Изменить</button>
          <button class="btn btn-danger btn-xs" data-delete-item-brand-id="${id}" type="button">Архивировать</button>
        </div></td>
      </tr>
    `;
  }

  function renderItemBrands() {
    syncBrandSelectOptions();
    renderBrandKpis();
    if (!el.itemBrandsBody) {
      return;
    }
    const rows = getVisibleBrandRows().sort((a, b) => {
      const spendDiff = brandSpentTotal(b) - brandSpentTotal(a);
      return spendDiff || String(a?.name || "").localeCompare(String(b?.name || ""), "ru");
    });
    el.itemBrandsBody.innerHTML = rows.length
      ? rows.map(renderBrandRow).join("")
      : '<tr><td colspan="6" class="muted-small">Бренды не найдены</td></tr>';
  }

  async function loadItemBrands(options = {}) {
    const force = options.force === true;
    const cacheKey = "item-brands:active";
    if (!force) {
      const cached = core.getUiRequestCache?.(cacheKey, BRANDS_CACHE_TTL_MS);
      if (cached) {
        state.itemBrands = payloadItems(cached).slice();
        state.itemBrandsLoaded = true;
        renderItemBrands();
        window.App.getRuntimeModule?.("item-catalog")?.refreshItemCatalogView?.();
        return state.itemBrands;
      }
    }
    requestController?.abort();
    const controller = new AbortController();
    requestController = controller;
    el.itemBrandsView?.classList.add("is-loading");
    try {
      const items = await fetchAllBrands(controller);
      if (controller.signal.aborted) {
        return state.itemBrands || [];
      }
      state.itemBrands = items;
      state.itemBrandsLoaded = true;
      core.setUiRequestCache?.(cacheKey, { items });
      renderItemBrands();
      window.App.getRuntimeModule?.("item-catalog")?.refreshItemCatalogView?.();
      return items;
    } catch (err) {
      if (core.isAbortError?.(err)) {
        return state.itemBrands || [];
      }
      throw err;
    } finally {
      if (requestController === controller) {
        requestController = null;
      }
      el.itemBrandsView?.classList.remove("is-loading");
    }
  }

  async function ensureItemBrandsLoaded(options = {}) {
    if (!options.force && state.itemBrandsLoaded) {
      return state.itemBrands || [];
    }
    return loadItemBrands(options);
  }

  function renderBrandPreview() {
    if (!el.itemBrandPreview) {
      return;
    }
    const name = normalizeBrandName(el.itemBrandName?.value || "") || "Название бренда";
    const accentColor = normalizeBrandColor(el.itemBrandAccentColor?.value);
    el.itemBrandPreview.innerHTML = renderBrandChip({ name, accent_color: accentColor }, { title: false });
    el.itemBrandColorPresets?.querySelectorAll("[data-item-brand-color]").forEach((button) => {
      button.classList.toggle("is-active", normalizeBrandColor(button.dataset.itemBrandColor) === accentColor);
    });
  }

  function openItemBrandModal(brand = null) {
    if (!el.itemBrandModal || !el.itemBrandForm) {
      return;
    }
    if (brand?.id && isBrandArchived(brand)) {
      core.showToast?.("Архивный бренд нельзя изменить. Восстановите его повторным созданием.", { type: "info" });
      return;
    }
    const isEdit = Boolean(brand?.id);
    state.editItemBrandId = isEdit ? Number(brand.id) : null;
    if (el.itemBrandModalTitle) {
      el.itemBrandModalTitle.textContent = isEdit ? "Редактировать бренд" : "Новый бренд";
    }
    if (el.submitItemBrandBtn) {
      el.submitItemBrandBtn.textContent = isEdit ? "Сохранить" : "Создать бренд";
    }
    if (el.itemBrandName) {
      el.itemBrandName.value = brand?.name || "";
    }
    if (el.itemBrandAccentColor) {
      el.itemBrandAccentColor.value = normalizeBrandColor(brand?.accent_color);
    }
    renderBrandPreview();
    el.itemBrandModal.classList.remove("hidden");
    setTimeout(() => {
      el.itemBrandName?.focus();
      el.itemBrandName?.select();
    }, 0);
  }

  function closeItemBrandModal() {
    state.editItemBrandId = null;
    el.itemBrandForm?.reset();
    el.itemBrandModal?.classList.add("hidden");
  }

  async function submitItemBrandForm(event) {
    event.preventDefault();
    const name = normalizeBrandName(el.itemBrandName?.value || "");
    if (!name) {
      core.setStatus("Введите название бренда");
      return;
    }
    const id = Number(state.editItemBrandId || 0);
    const saved = await core.requestJson(id ? `/api/v1/operations/item-brands/${id}` : "/api/v1/operations/item-brands", {
      method: id ? "PATCH" : "POST",
      headers: core.authHeaders(),
      body: JSON.stringify({ name, accent_color: normalizeBrandColor(el.itemBrandAccentColor?.value) }),
    });
    invalidateBrandDependentCaches();
    closeItemBrandModal();
    await loadItemBrands({ force: true });
    await window.App.getRuntimeModule?.("item-catalog")?.loadItemCatalog?.({ force: true });
    if (activeDetailBrand && Number(activeDetailBrand.id) === Number(saved?.id || id)) {
      await openItemBrandDetail(saved || brandFromId(id));
    }
    core.showToast?.(id ? "Бренд обновлён" : "Бренд создан", { type: "success" });
  }

  async function deleteItemBrandFlow(brand) {
    const linkedCount = Number(brand?.positions_count || 0);
    const actionLabel = "Архивировать";
    const explanation = linkedCount > 0
      ? `Бренд останется в истории ${linkedCount} связанных позиций, но исчезнет из списка выбора.`
      : "Бренд будет убран из активного справочника и при необходимости его можно будет восстановить повторным созданием.";
    core.showConfirm?.(`${actionLabel} бренд «${brand?.name || "без названия"}»? ${explanation}`, () => {
      core.runAction({
        errorPrefix: `Не удалось ${actionLabel.toLowerCase()} бренд`,
        action: async () => {
          await core.requestJson(`/api/v1/operations/item-brands/${Number(brand.id)}`, {
            method: "DELETE",
            headers: core.authHeaders(),
          });
          invalidateBrandDependentCaches();
          closeItemBrandDetail();
          await loadItemBrands({ force: true });
          await window.App.getRuntimeModule?.("item-catalog")?.loadItemCatalog?.({ force: true });
          core.showToast?.("Бренд архивирован", { type: "success" });
        },
      });
    }, { title: `${actionLabel} бренд`, confirmLabel: actionLabel });
  }

  async function fetchBrandTemplates(brandId) {
    const params = new URLSearchParams({ page: "1", page_size: "100", brand_id: String(brandId) });
    try {
      const first = await core.requestJson(`/api/v1/operations/item-templates?${params.toString()}`, { headers: core.authHeaders() });
      const items = payloadItems(first).slice();
      const total = Number(first?.total || items.length || 0);
      const pageSize = Number(first?.page_size || 100);
      for (let page = 2; page <= Math.ceil(total / pageSize); page += 1) {
        params.set("page", String(page));
        const payload = await core.requestJson(`/api/v1/operations/item-templates?${params.toString()}`, { headers: core.authHeaders() });
        items.push(...payloadItems(payload));
      }
      return items.filter((item) => Number(item?.brand_id || 0) === Number(brandId));
    } catch (err) {
      const local = relatedCatalogItems(brandId);
      if (local.length) {
        return local;
      }
      throw err;
    }
  }

  function renderBrandDetail(brand, items) {
    const archived = isBrandArchived(brand);
    const sortedItems = items.slice().sort((a, b) => {
      const sourceDiff = String(a?.shop_name || "").localeCompare(String(b?.shop_name || ""), "ru");
      return sourceDiff || String(a?.name || "").localeCompare(String(b?.name || ""), "ru");
    });
    if (el.itemBrandDetailTitle) {
      el.itemBrandDetailTitle.innerHTML = `${renderBrandChip(brand, { title: false })}${archived ? '<span class="item-brand-archive-badge">Архивный</span>' : ""}`;
    }
    if (el.itemBrandDetailSubtitle) {
      const statusPrefix = archived ? "Сохранён в истории · " : "";
      el.itemBrandDetailSubtitle.textContent = `${statusPrefix}${items.length} поз. в ${new Set(items.map((item) => String(item?.shop_name || ""))).size} ист.`;
    }
    if (el.editItemBrandFromDetailBtn) {
      el.editItemBrandFromDetailBtn.classList.toggle("hidden", archived);
      el.editItemBrandFromDetailBtn.disabled = archived;
      el.editItemBrandFromDetailBtn.setAttribute("aria-hidden", archived ? "true" : "false");
    }
    if (el.itemBrandDetailKpiGrid) {
      el.itemBrandDetailKpiGrid.innerHTML = `
        <article class="analytics-kpi-card analytics-kpi-neutral"><div class="muted-small">Позиций</div><strong>${Number(brand?.positions_count ?? items.length)}</strong></article>
        <article class="analytics-kpi-card analytics-kpi-positive"><div class="muted-small">Покупок</div><strong>${brandPurchaseCount(brand)}</strong></article>
        <article class="analytics-kpi-card analytics-kpi-neutral"><div class="muted-small">Потрачено</div><strong>${core.formatMoney(brandSpentTotal(brand))}</strong></article>
        <article class="analytics-kpi-card analytics-kpi-neutral"><div class="muted-small">Последняя покупка</div><strong>${brand?.last_purchase_date ? core.formatDateRu(brand.last_purchase_date) : "—"}</strong></article>
      `;
    }
    if (!el.itemBrandDetailBody) {
      return;
    }
    el.itemBrandDetailBody.innerHTML = sortedItems.length ? sortedItems.map((item) => {
      const category = (state.categories || []).find((entry) => Number(entry?.id || 0) === Number(item?.last_category_id || 0));
      const categoryHtml = category?.name
        ? core.renderCategoryChip({
          name: category.name,
          icon: category.icon || category.group_icon || null,
          accent_color: category.group_accent_color || null,
        }, "")
        : '<span class="muted-small">Без категории</span>';
      return `
        <tr class="table-record-open-row" data-item-brand-template-id="${Number(item.id)}">
          <td data-label="Источник" class="item-brand-detail-source">${escapeHtml(item.shop_name || "Без источника")}</td>
          <td data-label="Позиция"><strong>${escapeHtml(item.name || "—")}</strong></td>
          <td data-label="Категория">${categoryHtml}</td>
          <td data-label="Последняя цена">${core.formatMoney(item.latest_unit_price || 0)}</td>
          <td data-label="Действия"><button class="btn btn-secondary btn-xs" data-open-brand-template-id="${Number(item.id)}" type="button">Открыть</button></td>
        </tr>
      `;
    }).join("") : '<tr><td colspan="5" class="muted-small">У бренда пока нет позиций</td></tr>';
  }

  async function openItemBrandDetail(brandOrId) {
    const fallback = typeof brandOrId === "object" ? brandOrId : null;
    const id = Number(fallback?.id || fallback?.brand_id || brandOrId || 0);
    if (!id || !el.itemBrandDetailModal) {
      return;
    }
    const provisionalBrand = brandFromId(id) || {
      ...fallback,
      id,
      name: fallback?.name || fallback?.brand_name || "Бренд",
      accent_color: fallback?.accent_color || fallback?.brand_accent_color,
      is_archived: Boolean(fallback?.is_archived ?? fallback?.brand_is_archived ?? false),
    };
    activeDetailBrand = provisionalBrand;
    activeDetailItems = [];
    el.itemBrandDetailModal.classList.remove("hidden");
    renderBrandDetail(provisionalBrand, []);
    if (el.itemBrandDetailBody) {
      el.itemBrandDetailBody.innerHTML = '<tr><td colspan="5" class="muted-small">Загружаем позиции…</td></tr>';
    }
    const brandPromise = (async () => {
      await ensureItemBrandsLoaded().catch(() => []);
      const activeBrand = brandFromId(id);
      if (activeBrand) {
        return activeBrand;
      }
      try {
        return await core.requestJson(`/api/v1/operations/item-brands/${id}`, { headers: core.authHeaders() });
      } catch (_err) {
        return provisionalBrand;
      }
    })();
    const categoriesPromise = (state.categories || []).length
      ? Promise.resolve()
      : window.App.getRuntimeModule?.("category-actions")?.loadCategories?.();
    const [items, authoritativeBrand] = await Promise.all([
      fetchBrandTemplates(id),
      brandPromise,
      categoriesPromise,
    ]);
    if (!activeDetailBrand || Number(activeDetailBrand.id) !== id) {
      return;
    }
    const resolvedBrand = brandFromId(id) || authoritativeBrand || provisionalBrand;
    activeDetailBrand = resolvedBrand;
    activeDetailItems = items;
    renderBrandDetail(resolvedBrand, items);
  }

  function closeItemBrandDetail() {
    activeDetailBrand = null;
    activeDetailItems = [];
    el.itemBrandDetailModal?.classList.add("hidden");
    if (el.itemBrandDetailBody) {
      el.itemBrandDetailBody.innerHTML = "";
    }
  }

  async function openOperationsForItemBrand(brand = activeDetailBrand) {
    const id = Number(brand?.id || brand?.brand_id || 0);
    if (!id) {
      return;
    }
    const operations = window.App.getRuntimeModule?.("operations") || {};
    if (!operations.openOperationsForBrand) {
      return;
    }
    state.period = "all_time";
    core.syncAllPeriodTabs?.("all_time");
    closeItemBrandDetail();
    await operations.openOperationsForBrand(id, brand?.name || brand?.brand_name || "");
  }

  function visibleCatalogItems() {
    const query = String(el.itemCatalogSearchQ?.value || "").trim().toLowerCase();
    const filter = String(state.itemCatalogBrandFilter || "all");
    return (state.itemCatalogItems || []).filter((item) => {
      if (filter === "unassigned" && Number(item?.brand_id || 0)) {
        return false;
      }
      if (/^\d+$/.test(filter) && Number(item?.brand_id || 0) !== Number(filter)) {
        return false;
      }
      if (!query) {
        return true;
      }
      const brand = brandFromId(item?.brand_id);
      const category = (state.categories || []).find((entry) => Number(entry?.id || 0) === Number(item?.last_category_id || 0));
      return String(item?.name || "").toLowerCase().includes(query)
        || String(item?.shop_name || "").toLowerCase().includes(query)
        || String(item?.brand_name || brand?.name || "").toLowerCase().includes(query)
        || String(category?.name || "").toLowerCase().includes(query);
    });
  }

  function renderCatalogBulkState() {
    const selected = state.selectedItemCatalogIds || new Set();
    const visibleIds = visibleCatalogItems().map((item) => Number(item.id));
    const selectedVisible = visibleIds.filter((id) => selected.has(id)).length;
    el.itemCatalogBulkBar?.classList.toggle("hidden", selected.size === 0);
    if (el.itemCatalogSelectedCount) {
      el.itemCatalogSelectedCount.textContent = `Выбрано: ${selected.size}`;
    }
    if (el.itemCatalogSelectAll) {
      el.itemCatalogSelectAll.checked = visibleIds.length > 0 && selectedVisible === visibleIds.length;
      el.itemCatalogSelectAll.indeterminate = selectedVisible > 0 && selectedVisible < visibleIds.length;
    }
  }

  async function assignSelectedItemBrand() {
    const selectedIds = Array.from(state.selectedItemCatalogIds || []);
    if (!selectedIds.length) {
      return;
    }
    const brandId = Number(el.itemCatalogBulkBrand?.value || 0) || null;
    const result = await core.requestJson("/api/v1/operations/item-templates/bulk-brand", {
      method: "POST",
      headers: core.authHeaders(),
      body: JSON.stringify({ template_ids: selectedIds, brand_id: brandId }),
    });
    state.selectedItemCatalogIds.clear();
    invalidateBrandDependentCaches();
    await loadItemBrands({ force: true });
    await window.App.getRuntimeModule?.("item-catalog")?.loadItemCatalog?.({ force: true });
    renderCatalogBulkState();
    core.showToast?.(`Бренд обновлён у ${Number(result?.updated || 0)} позиций`, { type: "success" });
  }

  function bindCatalogBulkControls() {
    el.itemCatalogBrandFilter?.addEventListener("change", () => {
      state.itemCatalogBrandFilter = el.itemCatalogBrandFilter.value || "all";
      window.App.getRuntimeModule?.("item-catalog")?.refreshItemCatalogView?.();
      renderCatalogBulkState();
    });
    el.itemCatalogSelectAll?.addEventListener("change", () => {
      const selected = state.selectedItemCatalogIds || (state.selectedItemCatalogIds = new Set());
      for (const item of visibleCatalogItems()) {
        const id = Number(item.id);
        if (el.itemCatalogSelectAll.checked) {
          selected.add(id);
        } else {
          selected.delete(id);
        }
      }
      window.App.getRuntimeModule?.("item-catalog")?.refreshItemCatalogView?.();
      renderCatalogBulkState();
    });
    el.itemCatalogBody?.addEventListener("change", (event) => {
      const checkbox = event.target.closest("[data-item-catalog-select-id]");
      if (!checkbox) {
        return;
      }
      const selected = state.selectedItemCatalogIds || (state.selectedItemCatalogIds = new Set());
      const id = Number(checkbox.dataset.itemCatalogSelectId || 0);
      if (checkbox.checked) {
        selected.add(id);
      } else {
        selected.delete(id);
      }
      renderCatalogBulkState();
    });
    el.clearSelectedItemCatalogBtn?.addEventListener("click", () => {
      state.selectedItemCatalogIds?.clear?.();
      window.App.getRuntimeModule?.("item-catalog")?.refreshItemCatalogView?.();
      renderCatalogBulkState();
    });
    el.assignSelectedItemBrandBtn?.addEventListener("click", () => {
      core.runAction({
        button: el.assignSelectedItemBrandBtn,
        pendingText: "Применяем…",
        errorPrefix: "Не удалось назначить бренд",
        action: assignSelectedItemBrand,
      });
    });
  }

  function bind() {
    if (bound) {
      return;
    }
    bound = true;
    el.addItemBrandBtn?.addEventListener("click", () => openItemBrandModal());
    el.refreshItemBrandsBtn?.addEventListener("click", () => {
      core.runAction({ button: el.refreshItemBrandsBtn, pendingText: "Обновляем…", errorPrefix: "Не удалось обновить бренды", action: () => loadItemBrands({ force: true }) });
    });
    el.itemBrandsSearchQ?.addEventListener("input", () => {
      clearTimeout(brandSearchTimer);
      brandSearchTimer = setTimeout(renderItemBrands, 140);
    });
    el.itemBrandsBody?.addEventListener("click", (event) => {
      const editButton = event.target.closest("[data-edit-item-brand-id]");
      if (editButton) {
        openItemBrandModal(brandFromId(editButton.dataset.editItemBrandId));
        return;
      }
      const deleteButton = event.target.closest("[data-delete-item-brand-id]");
      if (deleteButton) {
        deleteItemBrandFlow(brandFromId(deleteButton.dataset.deleteItemBrandId));
        return;
      }
      const openButton = event.target.closest("[data-open-item-brand-id]");
      const row = event.target.closest("tr[data-item-brand-id]");
      if (openButton || (row && !event.target.closest("button, a, input, select, textarea, label"))) {
        openItemBrandDetail(Number(openButton?.dataset.openItemBrandId || row?.dataset.itemBrandId || 0)).catch((err) => core.setStatus(String(err)));
      }
    });
    el.itemBrandForm?.addEventListener("submit", (event) => {
      event.preventDefault();
      core.runAction({ button: el.submitItemBrandBtn, pendingText: "Сохраняем…", errorPrefix: "Не удалось сохранить бренд", action: () => submitItemBrandForm(event) });
    });
    el.itemBrandName?.addEventListener("input", renderBrandPreview);
    el.itemBrandAccentColor?.addEventListener("input", renderBrandPreview);
    el.itemBrandColorPresets?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-item-brand-color]");
      if (!button || !el.itemBrandAccentColor) {
        return;
      }
      el.itemBrandAccentColor.value = normalizeBrandColor(button.dataset.itemBrandColor);
      renderBrandPreview();
    });
    el.closeItemBrandModalBtn?.addEventListener("click", closeItemBrandModal);
    el.itemBrandModal?.addEventListener("click", (event) => {
      if (event.target === el.itemBrandModal) closeItemBrandModal();
    });
    el.closeItemBrandDetailModalBtn?.addEventListener("click", closeItemBrandDetail);
    el.itemBrandDetailModal?.addEventListener("click", (event) => {
      if (event.target === el.itemBrandDetailModal) closeItemBrandDetail();
    });
    el.editItemBrandFromDetailBtn?.addEventListener("click", () => {
      const brand = activeDetailBrand;
      if (isBrandArchived(brand)) {
        return;
      }
      closeItemBrandDetail();
      if (brand) openItemBrandModal(brandFromId(brand.id) || brand);
    });
    el.openItemBrandOperationsBtn?.addEventListener("click", () => {
      openOperationsForItemBrand().catch((err) => core.setStatus(String(err)));
    });
    el.itemBrandDetailBody?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-open-brand-template-id]");
      const row = event.target.closest("tr[data-item-brand-template-id]");
      if (!button && (!row || event.target.closest("button, a, input, select, textarea, label"))) {
        return;
      }
      const id = Number(button?.dataset.openBrandTemplateId || row?.dataset.itemBrandTemplateId || 0);
      const item = activeDetailItems.find((entry) => Number(entry?.id || 0) === id)
        || (state.itemCatalogItems || []).find((entry) => Number(entry?.id || 0) === id);
      if (item) {
        closeItemBrandDetail();
        window.App.getRuntimeModule?.("item-catalog")?.openItemTemplateModal?.(item);
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") {
        return;
      }
      if (!el.itemBrandModal?.classList.contains("hidden")) {
        closeItemBrandModal();
      } else if (!el.itemBrandDetailModal?.classList.contains("hidden")) {
        closeItemBrandDetail();
      }
    });
    bindCatalogBulkControls();
    syncBrandSelectOptions();
    renderCatalogBulkState();
  }

  function cleanupRuntime() {
    requestController?.abort();
    requestController = null;
    clearTimeout(brandSearchTimer);
    brandSearchTimer = null;
    closeItemBrandModal();
    closeItemBrandDetail();
  }

  window.App.registerRuntimeModule?.("item-brands", {
    bind,
    loadItemBrands,
    ensureItemBrandsLoaded,
    renderItemBrands,
    renderBrandChip,
    brandFromId,
    openItemBrandModal,
    closeItemBrandModal,
    openItemBrandDetail,
    closeItemBrandDetail,
    openOperationsForItemBrand,
    renderCatalogBulkState,
    cleanupRuntime,
  });
})();
