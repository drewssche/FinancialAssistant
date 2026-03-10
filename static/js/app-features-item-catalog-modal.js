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
      savePreferencesDebounced,
    } = deps;

    function openItemTemplateModal(item = null) {
      if (!el.itemTemplateModal || !el.itemTemplateForm) {
        return;
      }
      const isEdit = Boolean(item?.id);
      state.editItemTemplateId = isEdit ? Number(item.id) : null;
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
        el.itemTemplateSourcePickerBlock.classList.add("hidden");
      }
      if (el.itemTemplateName) {
        el.itemTemplateName.value = item?.name || "";
      }
      if (el.itemTemplatePrice) {
        el.itemTemplatePrice.value = item?.latest_unit_price || "";
      }
      if (el.itemTemplatePreviewBody) {
        updateItemTemplatePreview();
      }
      el.itemTemplateModal.classList.remove("hidden");
      setTimeout(() => {
        if (!isEdit && el.itemTemplateSourceSearch) {
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
      if (el.itemTemplateForm) {
        el.itemTemplateForm.reset();
      }
      if (el.itemTemplateModal) {
        el.itemTemplateModal.classList.add("hidden");
      }
      if (el.itemTemplatePreviewBody) {
        el.itemTemplatePreviewBody.innerHTML = "";
      }
      if (el.itemTemplateSourcePickerBlock) {
        el.itemTemplateSourcePickerBlock.classList.add("hidden");
      }
    }

    function closeItemTemplateSourcePicker() {
      if (el.itemTemplateSourcePickerBlock) {
        el.itemTemplateSourcePickerBlock.classList.add("hidden");
      }
    }

    function updateItemTemplatePreview() {
      if (!el.itemTemplatePreviewBody) {
        return;
      }
      const source = normalizeItemCatalogShopName(el.itemTemplateSource?.value || el.itemTemplateSourceSearch?.value || "") || "Без источника";
      const name = String(el.itemTemplateName?.value || "").trim() || "—";
      const parsedPrice = core.resolveMoneyInput(el.itemTemplatePrice?.value || 0);
      const validPrice = !parsedPrice.empty && parsedPrice.previewValue > 0 ? parsedPrice.previewValue : 0;
      el.itemTemplatePreviewBody.innerHTML = `
        <tr class="preview-row">
          <td>${escapeHtml(source)}</td>
          <td>${escapeHtml(name)}</td>
          <td>${core.formatMoney(validPrice)}</td>
        </tr>
      `;
    }

    async function submitItemTemplateForm(event) {
      event.preventDefault();
      const sourceName = normalizeItemCatalogShopName(el.itemTemplateSource?.value || el.itemTemplateSourceSearch?.value || "");
      const payload = {
        shop_name: sourceName || null,
        name: String(el.itemTemplateName?.value || "").trim(),
      };
      const priceRaw = String(el.itemTemplatePrice?.value || "").trim();
      if (priceRaw) {
        const price = core.resolveMoneyInput(priceRaw);
        if (!price.valid || price.value <= 0) {
          core.setStatus("Проверь цену позиции");
          return;
        }
        payload.latest_unit_price = price.formatted;
      }
      if (!payload.name) {
        core.setStatus("Введите название позиции");
        return;
      }
      const templateId = Number(state.editItemTemplateId || 0);
      const isEdit = templateId > 0;
      const url = isEdit ? `/api/v1/operations/item-templates/${templateId}` : "/api/v1/operations/item-templates";
      const method = isEdit ? "PATCH" : "POST";
      await core.requestJson(url, {
        method,
        headers: core.authHeaders(),
        body: JSON.stringify(payload),
      });
      if (sourceName) {
        const groups = readItemCatalogSourceGroups();
        if (!groups.some((name) => getItemCatalogShopKey(name) === getItemCatalogShopKey(sourceName))) {
          writeItemCatalogSourceGroups([...groups, sourceName]);
          savePreferencesDebounced(450);
        }
      }
      core.invalidateUiRequestCache("item-catalog");
      closeItemTemplateModal();
      await loadItemCatalog({ force: true });
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
        const chip = core.renderCategoryChip({ name: sourceName, icon: null, accent_color: null }, normalizedQuery);
        return `<button type="button" class="chip-btn" data-item-template-source-name="${escapeHtml(sourceName)}">${chip}</button>`;
      }).join("");
      const createChip = normalizedQuery && !exact
        ? `<button type="button" class="chip-btn chip-btn-create" data-item-template-source-create="${escapeHtml(normalizedQuery)}">+ Создать источник «${escapeHtml(normalizedQuery)}»</button>`
        : "";
      el.itemTemplateSourceAll.innerHTML = chips + createChip || "<span class='muted-small'>Нет источников</span>";
      el.itemTemplateSourcePickerBlock.classList.remove("hidden");
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
        const normalized = normalizeItemCatalogShopName(createdName);
        if (normalized) {
          const groups = readItemCatalogSourceGroups();
          if (!groups.some((name) => getItemCatalogShopKey(name) === getItemCatalogShopKey(normalized))) {
            writeItemCatalogSourceGroups([...groups, normalized]);
            savePreferencesDebounced(450);
          }
        }
      }
    }

    function handleItemTemplateSourceOutsidePointer(event) {
      if (!el.itemTemplateSourcePickerBlock || el.itemTemplateSourcePickerBlock.classList.contains("hidden")) {
        return;
      }
      const path = typeof event.composedPath === "function" ? event.composedPath() : [];
      if (path.some((node) => node?.id === "itemTemplateSourceField")) {
        return;
      }
      closeItemTemplateSourcePicker();
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

    async function deleteItemTemplateFlow(item) {
      core.runDestructiveAction({
        confirmMessage: `Удалить позицию «${item.name || "без названия"}»?`,
        doDelete: async () => {
          await core.requestJson(`/api/v1/operations/item-templates/${item.id}`, {
            method: "DELETE",
            headers: core.authHeaders(),
          });
          core.invalidateUiRequestCache("item-catalog");
        },
        onAfterDelete: async () => {
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
          writeItemCatalogSourceGroups([]);
          core.invalidateUiRequestCache("item-catalog");
        },
        onAfterDelete: async () => {
          await loadItemCatalog({ force: true });
          savePreferencesDebounced(450);
        },
        toastMessage: "Каталог позиций и источники очищены",
        onDeleteError: "Не удалось удалить позиции",
      });
    }

    function openSourceGroupModal() {
      if (!el.sourceGroupModal || !el.sourceGroupForm) {
        return;
      }
      state.editItemSourceName = "";
      el.sourceGroupForm.reset();
      if (el.sourceGroupOriginalName) {
        el.sourceGroupOriginalName.value = "";
      }
      if (el.sourceGroupTitle) {
        el.sourceGroupTitle.textContent = "Новый источник";
      }
      if (el.submitSourceGroupBtn) {
        el.submitSourceGroupBtn.textContent = "Создать источник";
      }
      updateSourceGroupPreview();
      el.sourceGroupModal.classList.remove("hidden");
      setTimeout(() => {
        if (el.sourceGroupName) {
          el.sourceGroupName.focus();
        }
      }, 0);
    }

    function closeSourceGroupModal() {
      state.editItemSourceName = "";
      if (el.sourceGroupModal) {
        el.sourceGroupModal.classList.add("hidden");
      }
    }

    function openEditSourceGroupModal(sourceName) {
      const normalized = normalizeItemCatalogShopName(sourceName || "");
      if (!normalized || !el.sourceGroupModal || !el.sourceGroupForm) {
        return;
      }
      state.editItemSourceName = normalized;
      el.sourceGroupForm.reset();
      if (el.sourceGroupOriginalName) {
        el.sourceGroupOriginalName.value = normalized;
      }
      if (el.sourceGroupName) {
        el.sourceGroupName.value = normalized;
      }
      if (el.sourceGroupTitle) {
        el.sourceGroupTitle.textContent = "Редактировать источник";
      }
      if (el.submitSourceGroupBtn) {
        el.submitSourceGroupBtn.textContent = "Сохранить источник";
      }
      updateSourceGroupPreview();
      el.sourceGroupModal.classList.remove("hidden");
      setTimeout(() => {
        if (el.sourceGroupName) {
          el.sourceGroupName.focus();
          el.sourceGroupName.select();
        }
      }, 0);
    }

    function updateSourceGroupPreview() {
      if (!el.sourceGroupPreviewBody) {
        return;
      }
      const sourceName = normalizeItemCatalogShopName(el.sourceGroupName?.value || "") || "—";
      if (sourceName === "—") {
        el.sourceGroupPreviewBody.innerHTML = "";
        return;
      }
      const sourceKey = getItemCatalogShopKey(sourceName);
      const existingGroup = buildItemCatalogGroups(state.itemCatalogItems || []).find((group) => group.shopKey === sourceKey);
      const positions = existingGroup?.items?.length || 0;
      const usage = existingGroup?.useCountTotal || 0;
      const avg = existingGroup?.avgPrice !== null && existingGroup?.avgPrice !== undefined
        ? core.formatMoney(existingGroup.avgPrice, { withCurrency: false })
        : "—";
      el.sourceGroupPreviewBody.innerHTML = `
        <tr class="preview-row">
          <td>${escapeHtml(sourceName)}</td>
          <td>${positions}</td>
          <td>${usage}</td>
          <td>${avg}</td>
        </tr>
      `;
    }

    async function submitSourceGroupForm(event) {
      event.preventDefault();
      const sourceName = normalizeItemCatalogShopName(el.sourceGroupName?.value || "");
      if (!sourceName) {
        core.setStatus("Введите название источника");
        return;
      }
      const originalName = normalizeItemCatalogShopName(state.editItemSourceName || el.sourceGroupOriginalName?.value || "");
      const groups = readItemCatalogSourceGroups();
      const exists = groups.some((name) => getItemCatalogShopKey(name) === getItemCatalogShopKey(sourceName));
      if (!originalName && exists) {
        closeSourceGroupModal();
        renderItemCatalog(state.itemCatalogItems);
        return;
      }
      if (originalName) {
        if (getItemCatalogShopKey(originalName) === getItemCatalogShopKey(sourceName)) {
          closeSourceGroupModal();
          renderItemCatalog(state.itemCatalogItems);
          return;
        }
        if (getItemCatalogShopKey(originalName) !== getItemCatalogShopKey(sourceName) && exists) {
          core.setStatus("Источник с таким названием уже существует");
          return;
        }
        const matchedItems = (state.itemCatalogItems || []).filter((item) => getItemCatalogShopKey(item.shop_name || "") === getItemCatalogShopKey(originalName));
        for (const item of matchedItems) {
          await core.requestJson(`/api/v1/operations/item-templates/${item.id}`, {
            method: "PATCH",
            headers: core.authHeaders(),
            body: JSON.stringify({ shop_name: sourceName || null }),
          });
        }
        writeItemCatalogSourceGroups(
          groups
            .map((name) => (getItemCatalogShopKey(name) === getItemCatalogShopKey(originalName) ? sourceName : name))
            .filter((name, idx, arr) => name && arr.findIndex((item) => getItemCatalogShopKey(item) === getItemCatalogShopKey(name)) === idx),
        );
        core.invalidateUiRequestCache("item-catalog");
        closeSourceGroupModal();
        await loadItemCatalog({ force: true });
        savePreferencesDebounced(450);
        return;
      }
      writeItemCatalogSourceGroups([...groups, sourceName]);
      closeSourceGroupModal();
      renderItemCatalog(state.itemCatalogItems);
      savePreferencesDebounced(450);
    }

    async function deleteItemSourceFlow(sourceName) {
      const normalized = normalizeItemCatalogShopName(sourceName || "");
      if (!normalized) {
        return;
      }
      core.runDestructiveAction({
        confirmMessage: `Удалить источник «${normalized}»? Позиции останутся, но перейдут в «Без источника».`,
        doDelete: async () => {
          const matchedItems = (state.itemCatalogItems || []).filter((item) => getItemCatalogShopKey(item.shop_name || "") === getItemCatalogShopKey(normalized));
          for (const item of matchedItems) {
            await core.requestJson(`/api/v1/operations/item-templates/${item.id}`, {
              method: "PATCH",
              headers: core.authHeaders(),
              body: JSON.stringify({ shop_name: null }),
            });
          }
          writeItemCatalogSourceGroups(
            readItemCatalogSourceGroups().filter((name) => getItemCatalogShopKey(name) !== getItemCatalogShopKey(normalized)),
          );
          core.invalidateUiRequestCache("item-catalog");
        },
        onAfterDelete: async () => {
          await loadItemCatalog({ force: true });
          savePreferencesDebounced(450);
        },
        toastMessage: "Источник удален",
        onDeleteError: "Не удалось удалить источник",
      });
    }

    async function openItemTemplateHistoryModal(item) {
      if (!item?.id || !el.itemTemplateHistoryModal || !el.itemTemplateHistoryBody) {
        return;
      }
      if (el.itemTemplateHistoryTitle) {
        el.itemTemplateHistoryTitle.textContent = `История цен: ${item.name || "Позиция"}`;
      }
      if (el.itemTemplateHistoryMeta) {
        const source = normalizeItemCatalogShopName(item.shop_name || "") || "Без источника";
        el.itemTemplateHistoryMeta.innerHTML = `
          <div class="muted-small">Источник</div>
          <div class="operation-receipt-shop">${core.renderCategoryChip({ name: source, icon: null, accent_color: null }, "")}</div>
        `;
      }
      el.itemTemplateHistoryBody.innerHTML = '<tr><td colspan="2">Загрузка...</td></tr>';
      el.itemTemplateHistoryModal.classList.remove("hidden");
      const rows = await core.requestJson(`/api/v1/operations/item-templates/${item.id}/prices?limit=200`, {
        headers: core.authHeaders(),
      });
      const list = Array.isArray(rows) ? rows : [];
      if (!list.length) {
        el.itemTemplateHistoryBody.innerHTML = '<tr><td colspan="2">История цен пока пустая</td></tr>';
        return;
      }
      el.itemTemplateHistoryBody.innerHTML = list.map((row) => `
        <tr>
          <td>${core.formatDateRu(row.recorded_at)}</td>
          <td>${core.formatMoney(row.unit_price || 0)}</td>
        </tr>
      `).join("");
    }

    function closeItemTemplateHistoryModal() {
      if (el.itemTemplateHistoryModal) {
        el.itemTemplateHistoryModal.classList.add("hidden");
      }
    }

    return {
      openItemTemplateModal,
      closeItemTemplateModal,
      submitItemTemplateForm,
      deleteItemTemplateFlow,
      deleteAllItemTemplatesFlow,
      openSourceGroupModal,
      openEditSourceGroupModal,
      closeSourceGroupModal,
      submitSourceGroupForm,
      deleteItemSourceFlow,
      updateSourceGroupPreview,
      updateItemTemplatePreview,
      handleItemTemplateSourceSearchFocus,
      handleItemTemplateSourceSearchInput,
      handleItemTemplateSourceSearchKeydown,
      handleItemTemplateSourcePickerClick,
      handleItemTemplateSourceOutsidePointer,
      handleItemTemplateSourceSearchFocusOut,
      openItemTemplateHistoryModal,
      closeItemTemplateHistoryModal,
    };
  }

  window.App = window.App || {};
  window.App.createItemCatalogModalFeature = createItemCatalogModalFeature;
})();
