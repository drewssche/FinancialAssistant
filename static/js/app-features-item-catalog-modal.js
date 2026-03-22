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
    const createItemCatalogSourcesFeature = window.App.getRuntimeModule?.("item-catalog-sources-factory");
    const sourcesFeature = createItemCatalogSourcesFeature ? createItemCatalogSourcesFeature(deps) : null;
    const pickerUtils = window.App.getRuntimeModule?.("picker-utils") || {};

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
        pickerUtils.setPopoverOpen(el.itemTemplateSourcePickerBlock, false, { owners: [el.itemTemplateSourceField] });
      }
      if (el.itemTemplateName) {
        el.itemTemplateName.value = item?.name || "";
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
        pickerUtils.setPopoverOpen(el.itemTemplateSourcePickerBlock, false, { owners: [el.itemTemplateSourceField] });
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
      const parsedPrice = core.resolveMoneyInput(el.itemTemplatePrice?.value || 0);
      const validPrice = !parsedPrice.empty && parsedPrice.previewValue > 0 ? parsedPrice.previewValue : 0;
      const priceDate = core.parseDateInputValue(el.itemTemplatePriceDate?.value || "") || null;
      el.itemTemplatePreviewBody.innerHTML = `
        <tr class="preview-row">
          <td>${escapeHtml(source)}</td>
          <td>${escapeHtml(name)}</td>
          <td>${core.formatMoney(validPrice)}${priceDate ? `<div class="muted-small">${core.formatDateRu(priceDate)}</div>` : ""}</td>
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
      openSourceGroupModal: sourcesFeature?.openSourceGroupModal,
      openEditSourceGroupModal: sourcesFeature?.openEditSourceGroupModal,
      closeSourceGroupModal: sourcesFeature?.closeSourceGroupModal,
      submitSourceGroupForm: sourcesFeature?.submitSourceGroupForm,
      deleteItemSourceFlow: sourcesFeature?.deleteItemSourceFlow,
      updateSourceGroupPreview: sourcesFeature?.updateSourceGroupPreview,
      openItemTemplateHistoryModal: sourcesFeature?.openItemTemplateHistoryModal,
      closeItemTemplateHistoryModal: sourcesFeature?.closeItemTemplateHistoryModal,
    };
  }

  window.App.registerRuntimeModule?.("item-catalog-modal-factory", createItemCatalogModalFeature);
})();
