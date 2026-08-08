(() => {
  function createItemCatalogSourcesFeature(deps) {
    const {
      state,
      el,
      core,
      normalizeItemCatalogShopName,
      escapeHtml,
      getItemCatalogShopKey,
      readItemCatalogSourceGroups,
      writeItemCatalogSourceGroups,
      buildItemCatalogGroups,
      renderItemCatalog,
      loadItemCatalog,
      savePreferencesDebounced,
    } = deps;

    function openSourceGroupModal() {
      if (!el.sourceGroupModal || !el.sourceGroupForm) {
        return;
      }
      state.editItemSourceName = "";
      el.sourceGroupCreateItemBtn?.classList.add("hidden");
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
      el.sourceGroupCreateItemBtn?.classList.add("hidden");
      if (el.sourceGroupCreateItemBtn) {
        el.sourceGroupCreateItemBtn.dataset.createItemTemplateSourceName = "";
      }
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
      const contextActions = window.App.getRuntimeModule?.("context-actions");
      if (el.sourceGroupCreateItemBtn) {
        const showCreate = contextActions?.has?.("item_source", "modal", "create_child");
        el.sourceGroupCreateItemBtn.classList.toggle("hidden", !showCreate);
        el.sourceGroupCreateItemBtn.dataset.createItemTemplateSourceName = showCreate ? normalized : "";
      }
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
        state.editItemSourceName = sourceName;
        if (el.sourceGroupOriginalName) {
          el.sourceGroupOriginalName.value = sourceName;
        }
        if (el.sourceGroupName) {
          el.sourceGroupName.value = sourceName;
        }
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
        confirmMessage: `Удалить источник «${normalized}» и ${matchedSourceItemCount(normalized)} поз.? История операций сохранится.`,
        doDelete: async () => {
          const matchedItems = (state.itemCatalogItems || []).filter((item) => getItemCatalogShopKey(item.shop_name || "") === getItemCatalogShopKey(normalized));
          for (const item of matchedItems) {
            await core.requestJson(`/api/v1/operations/item-templates/${item.id}`, {
              method: "DELETE",
              headers: core.authHeaders(),
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

    function matchedSourceItemCount(sourceName) {
      const sourceKey = getItemCatalogShopKey(sourceName || "");
      return (state.itemCatalogItems || []).filter((item) => getItemCatalogShopKey(item.shop_name || "") === sourceKey).length;
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
      openSourceGroupModal,
      openEditSourceGroupModal,
      closeSourceGroupModal,
      submitSourceGroupForm,
      deleteItemSourceFlow,
      updateSourceGroupPreview,
      openItemTemplateHistoryModal,
      closeItemTemplateHistoryModal,
    };
  }

  window.App.registerRuntimeModule?.("item-catalog-sources-factory", createItemCatalogSourcesFeature);
})();
