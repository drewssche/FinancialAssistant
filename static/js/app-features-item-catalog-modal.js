(() => {
  function createItemCatalogModalFeature(deps) {
    const {
      state,
      el,
      core,
      normalizeItemCatalogShopName,
      escapeHtml,
      getItemCatalogShopKey,
      readItemCatalogSourceGroups,
      writeItemCatalogSourceGroups,
      listItemCatalogSourceNames,
      buildItemCatalogGroups,
      renderItemCatalog,
      loadItemCatalog,
      applySavedItemCatalogItem,
      applySavedReceiptTemplateHint,
      invalidateItemCatalogDependentCaches,
      savePreferencesDebounced,
      loadItemSources,
    } = deps;
    const createItemCatalogSourcesFeature = window.App.getRuntimeModule?.("item-catalog-sources-factory");
    const sourcesFeature = createItemCatalogSourcesFeature ? createItemCatalogSourcesFeature(deps) : null;
    const pickerUtils = window.App.getRuntimeModule?.("picker-utils") || {};
    let itemTemplateInitialBrandMeta = null;
    let itemTemplateBrandSelectionTouched = false;
    let itemTemplateInitialImageId = null;

    function getActivityFeature() {
      return window.App.getRuntimeModule?.("activity") || {};
    }

    function getUsageFeature() {
      return window.App.getRuntimeModule?.("usage") || {};
    }

    function getItemTemplateCategoryMeta(categoryId) {
      const normalizedId = Number(categoryId || 0);
      return (state.categories || []).find((item) => Number(item?.id || 0) === normalizedId) || null;
    }

    function getItemTemplateBrandMeta(brandId) {
      const normalizedId = Number(brandId || 0);
      return (state.itemBrands || []).find((item) => Number(item?.id || 0) === normalizedId) || null;
    }

    function getSelectedItemTemplateBrandMeta() {
      const selectedId = Number(el.itemTemplateBrand?.value || 0);
      if (!selectedId) {
        return null;
      }
      return getItemTemplateBrandMeta(selectedId)
        || (Number(itemTemplateInitialBrandMeta?.id || 0) === selectedId ? itemTemplateInitialBrandMeta : null);
    }

    async function refreshItemBrandsAfterCatalogMutation() {
      invalidateItemCatalogDependentCaches?.();
      await window.App.getRuntimeModule?.("item-brands")?.loadItemBrands?.({ force: true });
    }

    function hydrateItemTemplateBrandFields(item) {
      const brandMeta = getItemTemplateBrandMeta(item?.brand_id) || (item?.brand_name ? {
        id: item?.brand_id,
        name: item.brand_name,
        accent_color: item.brand_accent_color,
        image_id: item.brand_image_id,
        is_archived: Boolean(item.brand_is_archived),
      } : null);
      itemTemplateInitialBrandMeta = brandMeta ? { ...brandMeta } : null;
      itemTemplateBrandSelectionTouched = false;
      if (el.itemTemplateBrand) {
        el.itemTemplateBrand.value = brandMeta?.id ? String(brandMeta.id) : "";
      }
      if (el.itemTemplateBrandSearch) {
        el.itemTemplateBrandSearch.value = brandMeta?.name || "";
      }
    }

    function restoreItemTemplateBrandSearchLabel() {
      if (el.itemTemplateBrandSearch) {
        el.itemTemplateBrandSearch.value = getSelectedItemTemplateBrandMeta()?.name || "";
      }
      updateItemTemplatePreview();
    }

    function openItemTemplateModal(item = null) {
      if (!el.itemTemplateModal || !el.itemTemplateForm) {
        return;
      }
      const isEdit = Boolean(item?.id);
      state.editItemTemplateId = isEdit ? Number(item.id) : null;
      getActivityFeature().configureActivityButton?.(el.itemTemplateActivityBtn, isEdit ? "item_template" : null, item?.id);
      getUsageFeature().configureUsageButton?.(el.itemTemplateUsageBtn, isEdit ? "item_template" : null, item?.id, item?.name || "");
      const contextActions = window.App.getRuntimeModule?.("context-actions");
      if (el.itemTemplateHistoryBtn) {
        const showHistory = isEdit && contextActions?.has?.("item_template", "modal", "history");
        el.itemTemplateHistoryBtn.classList.toggle("hidden", !showHistory);
        el.itemTemplateHistoryBtn.dataset.itemTemplateHistoryId = showHistory ? String(item.id) : "";
      }
      if (el.itemTemplateModalTitle) {
        el.itemTemplateModalTitle.textContent = isEdit ? "Редактировать позицию" : "Новая позиция";
      }
      if (el.itemTemplateSource) {
        el.itemTemplateSource.value = normalizeItemCatalogShopName(item?.shop_name || "");
      }
      if (el.itemTemplateSourceSearch) {
        el.itemTemplateSourceSearch.value = normalizeItemCatalogShopName(item?.shop_name || "");
      }
      if (el.itemTemplateSourcePickerBlock) {
        pickerUtils.setPopoverOpen(el.itemTemplateSourcePickerBlock, false, { owners: [el.itemTemplateSourceField] });
      }
      if (el.itemTemplateName) {
        el.itemTemplateName.value = item?.name || "";
      }
      itemTemplateInitialImageId = Number(item?.image_id || 0) || null;
      window.App.getRuntimeModule?.("catalog-media")?.resetPicker?.("item-template", {
        imageId: itemTemplateInitialImageId,
        kind: "item",
        label: item?.name ? `Фото ${item.name}` : "Фото позиции",
      });
      hydrateItemTemplateBrandFields(item);
      if (el.itemTemplateBrandPickerBlock) {
        pickerUtils.setPopoverOpen(el.itemTemplateBrandPickerBlock, false, { owners: [el.itemTemplateBrandField] });
      }
      window.App.getRuntimeModule?.("item-brands")?.ensureItemBrandsLoaded?.().then(() => {
        const loadedBrand = getItemTemplateBrandMeta(el.itemTemplateBrand?.value);
        if (loadedBrand && el.itemTemplateBrandSearch && !el.itemTemplateBrandSearch.value) {
          el.itemTemplateBrandSearch.value = loadedBrand.name || "";
          updateItemTemplatePreview();
        }
      }).catch(() => {});
      const categoryMeta = getItemTemplateCategoryMeta(item?.last_category_id);
      if (el.itemTemplateCategory) {
        el.itemTemplateCategory.value = categoryMeta?.id ? String(categoryMeta.id) : "";
      }
      if (el.itemTemplateCategorySearch) {
        el.itemTemplateCategorySearch.value = categoryMeta?.name || "";
      }
      if (el.itemTemplateCategoryPickerBlock) {
        pickerUtils.setPopoverOpen(el.itemTemplateCategoryPickerBlock, false, { owners: [el.itemTemplateCategoryField] });
      }
      if (el.itemTemplateBrandPickerBlock) {
        pickerUtils.setPopoverOpen(el.itemTemplateBrandPickerBlock, false, { owners: [el.itemTemplateBrandField] });
      }
      if (el.itemTemplatePrice) {
        el.itemTemplatePrice.value = item?.latest_unit_price || "";
      }
      if (el.itemTemplatePriceDate) {
        core.syncDateFieldValue(el.itemTemplatePriceDate, item?.latest_price_date || core.getTodayIso());
      }
      if (el.itemTemplatePreviewBody) {
        updateItemTemplatePreview();
      }
      el.itemTemplateModal.classList.remove("hidden");
      core.bringModalToFront?.(el.itemTemplateModal);
      setTimeout(() => {
        if (!isEdit && !normalizeItemCatalogShopName(item?.shop_name || "") && el.itemTemplateSourceSearch) {
          el.itemTemplateSourceSearch.focus();
          return;
        }
        if (el.itemTemplateName) {
          el.itemTemplateName.focus();
          el.itemTemplateName.select();
        }
      }, 0);
    }

    function closeItemTemplateModal() {
      state.editItemTemplateId = null;
      itemTemplateInitialBrandMeta = null;
      itemTemplateBrandSelectionTouched = false;
      itemTemplateInitialImageId = null;
      getActivityFeature().configureActivityButton?.(el.itemTemplateActivityBtn, null, null);
      getUsageFeature().configureUsageButton?.(el.itemTemplateUsageBtn, null, null);
      if (el.itemTemplateHistoryBtn) {
        el.itemTemplateHistoryBtn.classList.add("hidden");
        el.itemTemplateHistoryBtn.dataset.itemTemplateHistoryId = "";
      }
      if (el.itemTemplateForm) {
        el.itemTemplateForm.reset();
      }
      if (el.itemTemplateModal) {
        el.itemTemplateModal.classList.add("hidden");
        core.markModalClosed?.(el.itemTemplateModal);
      }
      if (el.itemTemplatePreviewBody) {
        el.itemTemplatePreviewBody.innerHTML = "";
      }
      if (el.itemTemplateSourcePickerBlock) {
        pickerUtils.setPopoverOpen(el.itemTemplateSourcePickerBlock, false, { owners: [el.itemTemplateSourceField] });
      }
      if (el.itemTemplateCategoryPickerBlock) {
        pickerUtils.setPopoverOpen(el.itemTemplateCategoryPickerBlock, false, { owners: [el.itemTemplateCategoryField] });
      }
    }

    function closeItemTemplateSourcePicker() {
      pickerUtils.setPopoverOpen(el.itemTemplateSourcePickerBlock, false, { owners: [el.itemTemplateSourceField] });
    }

    function updateItemTemplatePreview() {
      if (!el.itemTemplatePreviewBody) {
        return;
      }
      const source = normalizeItemCatalogShopName(el.itemTemplateSource?.value || el.itemTemplateSourceSearch?.value || "") || "Без источника";
      const name = String(el.itemTemplateName?.value || "").trim() || "—";
      const brandMeta = getSelectedItemTemplateBrandMeta();
      const brandHtml = window.App.getRuntimeModule?.("item-brands")?.renderBrandChip?.(brandMeta) || "<span class='muted-small'>Без бренда</span>";
      const categoryMeta = getItemTemplateCategoryMeta(el.itemTemplateCategory?.value);
      const categoryHtml = categoryMeta?.name
        ? core.renderCategoryChip({
          name: categoryMeta.name,
          icon: categoryMeta.icon || categoryMeta.group_icon || null,
          accent_color: categoryMeta.group_accent_color || null,
        }, "")
        : "<span class='muted-small'>Без категории</span>";
      const parsedPrice = core.resolveMoneyInput(el.itemTemplatePrice?.value || 0);
      const validPrice = !parsedPrice.empty && parsedPrice.previewValue > 0 ? parsedPrice.previewValue : 0;
      const priceDate = core.parseDateInputValue(el.itemTemplatePriceDate?.value || "") || null;
      const itemImage = window.App.getRuntimeModule?.("catalog-media")?.renderThumb?.(itemTemplateInitialImageId, {
        kind: "item",
        size: "row",
        alt: name,
        fallback: name.slice(0, 1),
      }) || "";
      el.itemTemplatePreviewBody.innerHTML = `
        <tr class="preview-row">
          <td>${escapeHtml(source)}</td>
          <td>${brandHtml}</td>
          <td><span class="catalog-item-identity">${itemImage}<span class="catalog-item-identity-main">${escapeHtml(name)}</span></span></td>
          <td>${categoryHtml}</td>
          <td>${core.formatMoney(validPrice)}${priceDate ? `<div class="muted-small">${core.formatDateRu(priceDate)}</div>` : ""}</td>
        </tr>
      `;
    }

    async function submitItemTemplateForm(event) {
      event.preventDefault();
      const sourceName = normalizeItemCatalogShopName(el.itemTemplateSource?.value || el.itemTemplateSourceSearch?.value || "");
      const templateId = Number(state.editItemTemplateId || 0);
      const isEdit = templateId > 0;
      const payload = {
        shop_name: sourceName || null,
        name: String(el.itemTemplateName?.value || "").trim(),
        last_category_id: Number(el.itemTemplateCategory?.value || 0) || null,
      };
      if (!isEdit || itemTemplateBrandSelectionTouched) {
        payload.brand_id = Number(el.itemTemplateBrand?.value || 0) || null;
      }
      const priceRaw = String(el.itemTemplatePrice?.value || "").trim();
      if (priceRaw) {
        const price = core.resolveMoneyInput(priceRaw);
        if (!price.valid || price.value <= 0) {
          core.setStatus("Проверь цену позиции");
          return;
        }
        const priceDate = core.parseDateInputValue(el.itemTemplatePriceDate?.value || "");
        if (!priceDate) {
          core.setStatus("Проверь дату цены");
          return;
        }
        payload.latest_unit_price = price.formatted;
        payload.latest_price_date = priceDate;
      }
      if (!payload.name) {
        core.setStatus("Введите название позиции");
        return;
      }
      const url = isEdit ? `/api/v1/operations/item-templates/${templateId}` : "/api/v1/operations/item-templates";
      const method = isEdit ? "PATCH" : "POST";
      const savedItem = await core.requestJson(url, {
        method,
        headers: core.authHeaders(),
        body: JSON.stringify(payload),
      });
      try {
        const mediaSavedItem = await window.App.getRuntimeModule?.("catalog-media")?.commitPicker?.(
          "item-template",
          "template",
          savedItem?.id || templateId,
        );
        if (mediaSavedItem) Object.assign(savedItem, mediaSavedItem);
      } catch (err) {
        core.showToast?.(`Позиция сохранена, но фото не обновлено: ${String(err?.message || err)}`, { type: "error" });
      }
      itemTemplateInitialImageId = Number(savedItem?.image_id || 0) || null;
      core.invalidateUiRequestCache("item-catalog");
      await refreshItemBrandsAfterCatalogMutation();
      state.itemSourcesLoaded = false;
      await loadItemSources?.({ force: true }).catch(() => []);
      applySavedItemCatalogItem?.(savedItem);
      window.App.getRuntimeModule?.("catalog-products")?.invalidate?.();
      applySavedReceiptTemplateHint(savedItem);
      if (state.itemCatalogView === "products") {
        await window.App.getRuntimeModule?.("catalog-products")?.load?.({ force: true }).catch(() => []);
      }
      window.App.getRuntimeModule?.("operation-modal")?.applySavedTemplateToReceiptDrafts?.(savedItem);
      window.App.getRuntimeModule?.("operations")?.refreshOpenReceiptTemplate?.(savedItem);
      hydrateItemTemplateBrandFields(savedItem);
      if (!isEdit) {
        closeItemTemplateModal();
      } else {
        if (el.itemTemplatePrice) {
          el.itemTemplatePrice.value = savedItem?.latest_unit_price || "";
        }
        if (el.itemTemplatePriceDate) {
          core.syncDateFieldValue(el.itemTemplatePriceDate, savedItem?.latest_price_date || core.getTodayIso());
        }
        updateItemTemplatePreview();
      }
    }

    function renderItemTemplateSourcePicker(query = "") {
      if (!el.itemTemplateSourcePickerBlock || !el.itemTemplateSourceAll) {
        return;
      }
      const normalizedQuery = normalizeItemCatalogShopName(query);
      const normalizedQueryCi = normalizedQuery.toLowerCase();
      const sources = listItemCatalogSourceNames(80);
      const matched = normalizedQuery
        ? sources.filter((name) => name.toLowerCase().includes(normalizedQueryCi))
        : sources.slice(0, 24);
      const exact = Boolean(normalizedQuery) && sources.some((name) => getItemCatalogShopKey(name) === getItemCatalogShopKey(normalizedQuery));
      const chips = matched.map((sourceName) => {
        const sourceMeta = (state.itemSources || []).find((item) => getItemCatalogShopKey(item?.name || "") === getItemCatalogShopKey(sourceName));
        const logo = window.App.getRuntimeModule?.("catalog-media")?.renderThumb?.(sourceMeta?.image_id, {
          kind: "source",
          size: "chip",
          alt: sourceName,
          fallback: sourceName.slice(0, 1),
        }) || "";
        const chip = core.renderCategoryChip({ name: sourceName, icon: null, accent_color: null }, normalizedQuery);
        return `<button type="button" class="chip-btn catalog-source-identity" data-item-template-source-name="${escapeHtml(sourceName)}">${logo}${chip}</button>`;
      }).join("");
      const createChip = normalizedQuery && !exact
        ? `<button type="button" class="chip-btn chip-btn-create" data-item-template-source-create="${escapeHtml(normalizedQuery)}">+ Создать источник «${escapeHtml(normalizedQuery)}»</button>`
        : "";
      el.itemTemplateSourceAll.innerHTML = chips + createChip || "<span class='muted-small'>Нет источников</span>";
      pickerUtils.setPopoverOpen(el.itemTemplateSourcePickerBlock, true, {
        owners: [el.itemTemplateSourceField],
        onClose: closeItemTemplateSourcePicker,
      });
    }

    function selectItemTemplateSource(name, { keepPickerOpen = false } = {}) {
      const normalized = normalizeItemCatalogShopName(name);
      if (el.itemTemplateSource) {
        el.itemTemplateSource.value = normalized;
      }
      if (el.itemTemplateSourceSearch) {
        el.itemTemplateSourceSearch.value = normalized;
      }
      updateItemTemplatePreview();
      if (!keepPickerOpen) {
        closeItemTemplateSourcePicker();
      }
    }

    function handleItemTemplateSourceSearchFocus() {
      renderItemTemplateSourcePicker(el.itemTemplateSourceSearch?.value || "");
    }

    function handleItemTemplateSourceSearchInput() {
      selectItemTemplateSource(el.itemTemplateSourceSearch?.value || "", { keepPickerOpen: true });
      renderItemTemplateSourcePicker(el.itemTemplateSourceSearch?.value || "");
    }

    function handleItemTemplateSourceSearchKeydown(event) {
      if (event.key === "Escape") {
        closeItemTemplateSourcePicker();
        return;
      }
      if (event.key !== "Enter") {
        return;
      }
      event.preventDefault();
      const query = normalizeItemCatalogShopName(el.itemTemplateSourceSearch?.value || "");
      if (!query) {
        return;
      }
      const firstMatch = listItemCatalogSourceNames(80).find((name) => name.toLowerCase().includes(query.toLowerCase()));
      selectItemTemplateSource(firstMatch || query);
    }

    function handleItemTemplateSourcePickerClick(event) {
      const selectBtn = event.target.closest("[data-item-template-source-name]");
      if (selectBtn) {
        selectItemTemplateSource(selectBtn.dataset.itemTemplateSourceName || "");
        return;
      }
      const createBtn = event.target.closest("[data-item-template-source-create]");
      if (createBtn) {
        const createdName = createBtn.dataset.itemTemplateSourceCreate || "";
        selectItemTemplateSource(createdName);
      }
    }

    function handleItemTemplateSourceOutsidePointer(event) {
      pickerUtils.closePopoverOnOutside(event, {
        popover: el.itemTemplateSourcePickerBlock,
        scopes: [el.itemTemplateSourceField],
        onClose: closeItemTemplateSourcePicker,
      });
    }

    function handleItemTemplateSourceSearchFocusOut(event) {
      const next = event.relatedTarget;
      if (next && next.closest && next.closest("#itemTemplateSourceField")) {
        return;
      }
      setTimeout(() => {
        const active = document.activeElement;
        if (active && active.closest && active.closest("#itemTemplateSourceField")) {
          return;
        }
        closeItemTemplateSourcePicker();
      }, 0);
    }

    function closeItemTemplateCategoryPicker() {
      pickerUtils.setPopoverOpen(el.itemTemplateCategoryPickerBlock, false, { owners: [el.itemTemplateCategoryField] });
    }

    function renderItemTemplateCategoryPicker(query = "") {
      if (!el.itemTemplateCategoryPickerBlock || !el.itemTemplateCategoryAll) {
        return;
      }
      const selectedId = Number(el.itemTemplateCategory?.value || 0) || null;
      const selected = getItemTemplateCategoryMeta(selectedId);
      const rawQuery = String(query || "").trim();
      const normalizedQuery = selected && rawQuery.toLowerCase() === String(selected.name || "").toLowerCase()
        ? ""
        : rawQuery;
      const categories = pickerUtils.sortCategoriesByUsage(
        (state.categories || []).filter((item) => item?.kind === "expense"),
        normalizedQuery,
        pickerUtils.DEFAULT_CATEGORY_USAGE_KEY,
      );
      const noCategory = pickerUtils.createMetaChipButton({
        datasetName: "itemTemplateCategoryId",
        datasetValue: "",
        selected: !selectedId,
        label: "Без категории",
        core,
      });
      el.itemTemplateCategoryAll.innerHTML = "";
      el.itemTemplateCategoryAll.appendChild(noCategory);
      for (const category of categories) {
        el.itemTemplateCategoryAll.appendChild(pickerUtils.createChipButton({
          datasetName: "itemTemplateCategoryId",
          datasetValue: category.id,
          selected: Number(category.id) === selectedId,
          html: core.renderCategoryChip({
            name: category.name,
            icon: category.icon || category.group_icon || null,
            accent_color: category.group_accent_color || null,
          }, normalizedQuery),
        }));
      }
      if (!categories.length && normalizedQuery) {
        el.itemTemplateCategoryAll.insertAdjacentHTML("beforeend", "<span class='muted-small'>Ничего не найдено</span>");
      }
      pickerUtils.setPopoverOpen(el.itemTemplateCategoryPickerBlock, true, {
        owners: [el.itemTemplateCategoryField],
        onClose: closeItemTemplateCategoryPicker,
      });
    }

    function selectItemTemplateCategory(categoryId, { keepPickerOpen = false } = {}) {
      const normalizedId = Number(categoryId || 0) || null;
      const categoryMeta = getItemTemplateCategoryMeta(normalizedId);
      if (el.itemTemplateCategory) {
        el.itemTemplateCategory.value = categoryMeta?.id ? String(categoryMeta.id) : "";
      }
      if (el.itemTemplateCategorySearch) {
        el.itemTemplateCategorySearch.value = categoryMeta?.name || "";
      }
      updateItemTemplatePreview();
      if (!keepPickerOpen) {
        closeItemTemplateCategoryPicker();
      }
    }

    function handleItemTemplateCategorySearchFocus() {
      renderItemTemplateCategoryPicker(el.itemTemplateCategorySearch?.value || "");
    }

    function handleItemTemplateCategorySearchInput() {
      if (el.itemTemplateCategory) {
        el.itemTemplateCategory.value = "";
      }
      updateItemTemplatePreview();
      renderItemTemplateCategoryPicker(el.itemTemplateCategorySearch?.value || "");
    }

    function handleItemTemplateCategorySearchKeydown(event) {
      if (event.key === "Escape") {
        closeItemTemplateCategoryPicker();
        return;
      }
      if (event.key !== "Enter") {
        return;
      }
      event.preventDefault();
      const query = String(el.itemTemplateCategorySearch?.value || "").trim();
      const firstMatch = pickerUtils.sortCategoriesByUsage(
        (state.categories || []).filter((item) => item?.kind === "expense"),
        query,
        pickerUtils.DEFAULT_CATEGORY_USAGE_KEY,
      )[0];
      selectItemTemplateCategory(firstMatch?.id || null);
    }

    function handleItemTemplateCategoryPickerClick(event) {
      const button = event.target.closest("button[data-item-template-category-id]");
      if (!button) {
        return;
      }
      selectItemTemplateCategory(button.dataset.itemTemplateCategoryId || null);
    }

    function handleItemTemplateCategorySearchFocusOut(event) {
      const next = event.relatedTarget;
      if (next && next.closest && next.closest("#itemTemplateCategoryField")) {
        return;
      }
      setTimeout(() => {
        const active = document.activeElement;
        if (active && active.closest && active.closest("#itemTemplateCategoryField")) {
          return;
        }
        closeItemTemplateCategoryPicker();
      }, 0);
    }

    function closeItemTemplateBrandPicker() {
      pickerUtils.setPopoverOpen(el.itemTemplateBrandPickerBlock, false, { owners: [el.itemTemplateBrandField] });
    }

    function renderItemTemplateBrandPicker(query = "") {
      if (!el.itemTemplateBrandPickerBlock || !el.itemTemplateBrandAll) {
        return;
      }
      const selectedId = Number(el.itemTemplateBrand?.value || 0) || null;
      const activeSelected = getItemTemplateBrandMeta(selectedId);
      const selected = activeSelected || getSelectedItemTemplateBrandMeta();
      const linkedArchivedBrand = selectedId && selected
        && Boolean(selected.is_archived ?? selected.brand_is_archived ?? false)
        ? selected
        : null;
      const rawQuery = String(query || "").trim();
      const normalizedQuery = selected && rawQuery.toLowerCase() === String(selected.name || "").toLowerCase()
        ? ""
        : rawQuery;
      const brands = (state.itemBrands || [])
        .filter((brand) => !normalizedQuery || String(brand?.name || "").toLowerCase().includes(normalizedQuery.toLowerCase()))
        .sort((a, b) => String(a?.name || "").localeCompare(String(b?.name || ""), "ru"));
      const noBrand = pickerUtils.createMetaChipButton({
        datasetName: "itemTemplateBrandId",
        datasetValue: "",
        selected: !selectedId,
        label: "Без бренда",
        core,
      });
      el.itemTemplateBrandAll.innerHTML = "";
      el.itemTemplateBrandAll.appendChild(noBrand);
      if (linkedArchivedBrand) {
        el.itemTemplateBrandAll.appendChild(pickerUtils.createChipButton({
          datasetName: "itemTemplateBrandId",
          datasetValue: linkedArchivedBrand.id,
          selected: true,
          html: `${window.App.getRuntimeModule?.("item-brands")?.renderBrandChip?.(linkedArchivedBrand, { title: false }) || escapeHtml(linkedArchivedBrand.name || "Бренд")} <span class="muted-small">архив</span>`,
        }));
      }
      for (const brand of brands) {
        el.itemTemplateBrandAll.appendChild(pickerUtils.createChipButton({
          datasetName: "itemTemplateBrandId",
          datasetValue: brand.id,
          selected: Number(brand.id) === selectedId,
          html: window.App.getRuntimeModule?.("item-brands")?.renderBrandChip?.(brand, { title: false }) || escapeHtml(brand.name || "Бренд"),
        }));
      }
      if (!brands.length && normalizedQuery) {
        el.itemTemplateBrandAll.insertAdjacentHTML("beforeend", '<span class="muted-small">Бренд не найден. Создайте его во вкладке «Бренды».</span>');
      }
      pickerUtils.setPopoverOpen(el.itemTemplateBrandPickerBlock, true, {
        owners: [el.itemTemplateBrandField],
        onClose: closeItemTemplateBrandPicker,
      });
    }

    function selectItemTemplateBrand(brandId, { keepPickerOpen = false } = {}) {
      const normalizedId = Number(brandId || 0) || null;
      const brand = getItemTemplateBrandMeta(normalizedId)
        || (Number(itemTemplateInitialBrandMeta?.id || 0) === normalizedId ? itemTemplateInitialBrandMeta : null);
      itemTemplateBrandSelectionTouched = true;
      if (el.itemTemplateBrand) {
        el.itemTemplateBrand.value = brand?.id ? String(brand.id) : "";
      }
      if (el.itemTemplateBrandSearch) {
        el.itemTemplateBrandSearch.value = brand?.name || "";
      }
      updateItemTemplatePreview();
      if (!keepPickerOpen) {
        closeItemTemplateBrandPicker();
      }
    }

    function handleItemTemplateBrandSearchFocus() {
      window.App.getRuntimeModule?.("item-brands")?.ensureItemBrandsLoaded?.().then(() => {
        renderItemTemplateBrandPicker(el.itemTemplateBrandSearch?.value || "");
      }).catch((err) => core.setStatus(`Не удалось загрузить бренды: ${String(err)}`));
    }

    function handleItemTemplateBrandSearchInput() {
      renderItemTemplateBrandPicker(el.itemTemplateBrandSearch?.value || "");
    }

    function handleItemTemplateBrandSearchKeydown(event) {
      if (event.key === "Escape") {
        restoreItemTemplateBrandSearchLabel();
        closeItemTemplateBrandPicker();
        return;
      }
      if (event.key !== "Enter") {
        return;
      }
      event.preventDefault();
      const query = String(el.itemTemplateBrandSearch?.value || "").trim().toLowerCase();
      if (!query) {
        selectItemTemplateBrand(null);
        return;
      }
      const firstMatch = (state.itemBrands || []).find((brand) => String(brand?.name || "").toLowerCase().includes(query));
      if (firstMatch) {
        selectItemTemplateBrand(firstMatch.id);
      } else {
        restoreItemTemplateBrandSearchLabel();
        closeItemTemplateBrandPicker();
      }
    }

    function handleItemTemplateBrandPickerClick(event) {
      const button = event.target.closest("button[data-item-template-brand-id]");
      if (!button) {
        return;
      }
      selectItemTemplateBrand(button.dataset.itemTemplateBrandId || null);
    }

    function handleItemTemplateBrandSearchFocusOut(event) {
      const next = event.relatedTarget;
      if (next && next.closest && next.closest("#itemTemplateBrandField")) {
        return;
      }
      setTimeout(() => {
        const active = document.activeElement;
        if (active && active.closest && active.closest("#itemTemplateBrandField")) {
          return;
        }
        restoreItemTemplateBrandSearchLabel();
        closeItemTemplateBrandPicker();
      }, 0);
    }

    async function deleteItemTemplateFlow(item) {
      core.runDestructiveAction({
        confirmMessage: `Удалить позицию «${item.name || "без названия"}»?`,
        doDelete: async () => {
          await core.requestJson(`/api/v1/operations/item-templates/${item.id}`, {
            method: "DELETE",
            headers: core.authHeaders(),
          });
          state.selectedItemCatalogIds?.delete?.(Number(item.id));
          core.invalidateUiRequestCache("item-catalog");
        },
        onAfterDelete: async () => {
          await refreshItemBrandsAfterCatalogMutation();
          await loadItemCatalog({ force: true });
        },
        toastMessage: "Позиция удалена",
        onDeleteError: "Не удалось удалить позицию",
      });
    }

    async function deleteAllItemTemplatesFlow() {
      core.runDestructiveAction({
        confirmMessage: "Удалить все позиции и очистить список источников?",
        doDelete: async () => {
          await core.requestJson("/api/v1/operations/item-templates", {
            method: "DELETE",
            headers: core.authHeaders(),
          });
          state.selectedItemCatalogIds?.clear?.();
          writeItemCatalogSourceGroups([]);
          core.invalidateUiRequestCache("item-catalog");
        },
        onAfterDelete: async () => {
          await refreshItemBrandsAfterCatalogMutation();
          await loadItemCatalog({ force: true });
          savePreferencesDebounced(450);
        },
        toastMessage: "Каталог позиций и источники очищены",
        onDeleteError: "Не удалось удалить позиции",
      });
    }

    return {
      openItemTemplateModal,
      closeItemTemplateModal,
      submitItemTemplateForm,
      deleteItemTemplateFlow,
      deleteAllItemTemplatesFlow,
      updateItemTemplatePreview,
      handleItemTemplateSourceSearchFocus,
      handleItemTemplateSourceSearchInput,
      handleItemTemplateSourceSearchKeydown,
      handleItemTemplateSourcePickerClick,
      handleItemTemplateSourceOutsidePointer,
      handleItemTemplateSourceSearchFocusOut,
      handleItemTemplateCategorySearchFocus,
      handleItemTemplateCategorySearchInput,
      handleItemTemplateCategorySearchKeydown,
      handleItemTemplateCategoryPickerClick,
      handleItemTemplateCategorySearchFocusOut,
      handleItemTemplateBrandSearchFocus,
      handleItemTemplateBrandSearchInput,
      handleItemTemplateBrandSearchKeydown,
      handleItemTemplateBrandPickerClick,
      handleItemTemplateBrandSearchFocusOut,
      openSourceGroupModal: sourcesFeature?.openSourceGroupModal,
      openEditSourceGroupModal: sourcesFeature?.openEditSourceGroupModal,
      closeSourceGroupModal: sourcesFeature?.closeSourceGroupModal,
      submitSourceGroupForm: sourcesFeature?.submitSourceGroupForm,
      deleteItemSourceFlow: sourcesFeature?.deleteItemSourceFlow,
      updateSourceGroupPreview: sourcesFeature?.updateSourceGroupPreview,
      openItemTemplateHistoryModal: sourcesFeature?.openItemTemplateHistoryModal,
      closeItemTemplateHistoryModal: sourcesFeature?.closeItemTemplateHistoryModal,
      deleteItemTemplatePriceFlow: sourcesFeature?.deleteItemTemplatePriceFlow,
    };
  }

  window.App.registerRuntimeModule?.("item-catalog-modal-factory", createItemCatalogModalFeature);
})();
