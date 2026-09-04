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
      applySavedItemCatalogItem,
      applySavedReceiptTemplateHint,
      invalidateItemCatalogDependentCaches,
      savePreferencesDebounced,
      loadItemSources,
    } = deps;

    function findSourceByName(sourceName) {
      const key = getItemCatalogShopKey(sourceName || "");
      return (state.itemSources || []).find((item) => getItemCatalogShopKey(item?.name || "") === key) || null;
    }

    async function refreshItemBrandsAfterCatalogMutation() {
      invalidateItemCatalogDependentCaches?.();
      await window.App.getRuntimeModule?.("item-brands")?.loadItemBrands?.({ force: true });
    }

    function openSourceGroupModal() {
      if (!el.sourceGroupModal || !el.sourceGroupForm) {
        return;
      }
      state.editItemSourceName = "";
      state.editItemSourceId = null;
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
      window.App.getRuntimeModule?.("catalog-media")?.resetPicker?.("item-source", {
        imageId: null,
        kind: "source",
        label: "Логотип источника",
      });
      updateSourceGroupPreview();
      el.sourceGroupModal.classList.remove("hidden");
      core.bringModalToFront?.(el.sourceGroupModal);
      setTimeout(() => {
        if (el.sourceGroupName) {
          el.sourceGroupName.focus();
        }
      }, 0);
    }

    function closeSourceGroupModal() {
      state.editItemSourceName = "";
      state.editItemSourceId = null;
      el.sourceGroupCreateItemBtn?.classList.add("hidden");
      if (el.sourceGroupCreateItemBtn) {
        el.sourceGroupCreateItemBtn.dataset.createItemTemplateSourceName = "";
      }
      if (el.sourceGroupModal) {
        el.sourceGroupModal.classList.add("hidden");
        core.markModalClosed?.(el.sourceGroupModal);
      }
    }

    function openEditSourceGroupModal(sourceName) {
      const normalized = normalizeItemCatalogShopName(sourceName || "");
      if (!normalized || !el.sourceGroupModal || !el.sourceGroupForm) {
        return;
      }
      state.editItemSourceName = normalized;
      const source = findSourceByName(normalized);
      state.editItemSourceId = Number(source?.id || 0) || null;
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
      window.App.getRuntimeModule?.("catalog-media")?.resetPicker?.("item-source", {
        imageId: source?.image_id,
        kind: "source",
        label: `Логотип ${normalized}`,
      });
      updateSourceGroupPreview();
      el.sourceGroupModal.classList.remove("hidden");
      core.bringModalToFront?.(el.sourceGroupModal);
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
          <td><span class="catalog-source-identity">${window.App.getRuntimeModule?.("catalog-media")?.renderThumb?.(findSourceByName(sourceName)?.image_id, { kind: "source", size: "row", alt: sourceName, fallback: sourceName.slice(0, 1) }) || ""}<span>${escapeHtml(sourceName)}</span></span></td>
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
      const sourceId = Number(state.editItemSourceId || findSourceByName(originalName)?.id || 0);
      const isEdit = sourceId > 0;
      const existing = findSourceByName(sourceName);
      if (!sourceId && existing) {
        closeSourceGroupModal();
        renderItemCatalog(state.itemCatalogItems);
        return;
      }
      if (sourceId && existing && Number(existing.id) !== sourceId) {
        core.setStatus("Источник с таким названием уже существует");
        return;
      }
      let saved = await core.requestJson(
        sourceId ? `/api/v1/operations/item-sources/${sourceId}` : "/api/v1/operations/item-sources",
        {
          method: sourceId ? "PATCH" : "POST",
          headers: core.authHeaders(),
          body: JSON.stringify({ name: sourceName }),
        },
      );
      try {
        saved = await window.App.getRuntimeModule?.("catalog-media")?.commitPicker?.(
          "item-source",
          "source",
          saved?.id || sourceId,
        ) || saved;
      } catch (err) {
        core.showToast?.(`Источник сохранён, но логотип не обновлён: ${String(err?.message || err)}`, { type: "error" });
      }
      invalidateItemCatalogDependentCaches?.();
      state.itemSourcesLoaded = false;
      await loadItemSources?.({ force: true });
      await loadItemCatalog({ force: true });
      if (!isEdit) {
        closeSourceGroupModal();
      } else {
        const refreshed = (state.itemSources || []).find((item) => Number(item?.id || 0) === sourceId) || saved;
        const savedName = normalizeItemCatalogShopName(refreshed?.name || sourceName);
        state.editItemSourceId = Number(refreshed?.id || sourceId);
        state.editItemSourceName = savedName;
        if (el.sourceGroupOriginalName) el.sourceGroupOriginalName.value = savedName;
        if (el.sourceGroupName) el.sourceGroupName.value = savedName;
        window.App.getRuntimeModule?.("catalog-media")?.resetPicker?.("item-source", {
          imageId: refreshed?.image_id,
          kind: "source",
          label: `Логотип ${savedName}`,
        });
        updateSourceGroupPreview();
      }
      core.showToast?.(isEdit ? "Источник обновлён" : "Источник создан", { type: "success" });
    }

    async function deleteItemSourceFlow(sourceName) {
      const normalized = normalizeItemCatalogShopName(sourceName || "");
      if (!normalized) {
        return;
      }
      const linkedCount = matchedSourceItemCount(normalized);
      core.runDestructiveAction({
        confirmMessage: `Удалить источник «${normalized}»? ${linkedCount} поз. останутся в истории.`,
        doDelete: async () => {
          const source = findSourceByName(normalized);
          if (!source?.id) throw new Error("Источник не найден");
          await core.requestJson(`/api/v1/operations/item-sources/${Number(source.id)}`, {
            method: "DELETE",
            headers: core.authHeaders(),
          });
          invalidateItemCatalogDependentCaches?.();
          state.itemSourcesLoaded = false;
        },
        onAfterDelete: async () => {
          await loadItemSources?.({ force: true });
          await refreshItemBrandsAfterCatalogMutation();
          await loadItemCatalog({ force: true });
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
        const image = window.App.getRuntimeModule?.("catalog-media")?.renderThumb?.(item.image_id, { kind: "item", size: "row", alt: item.name || "Позиция" }) || "";
        el.itemTemplateHistoryMeta.innerHTML = `
          ${image}
          <div class="muted-small">Источник</div>
          <div class="operation-receipt-shop">${core.renderCategoryChip({ name: source, icon: null, accent_color: null }, "")}</div>
        `;
      }
      el.itemTemplateHistoryBody.innerHTML = '<tr><td colspan="3">Загрузка...</td></tr>';
      el.itemTemplateHistoryModal.classList.remove("hidden");
      core.bringModalToFront?.(el.itemTemplateHistoryModal);
      const rows = await core.requestJson(`/api/v1/operations/item-templates/${item.id}/prices?limit=200`, {
        headers: core.authHeaders(),
      });
      const list = Array.isArray(rows) ? rows : [];
      if (!list.length) {
        el.itemTemplateHistoryBody.innerHTML = '<tr><td colspan="3">История цен пока пустая</td></tr>';
        return;
      }
      el.itemTemplateHistoryBody.innerHTML = list.map((row) => `
        <tr>
          <td>${core.formatDateRu(row.recorded_at)}</td>
          <td>${core.formatMoney(row.unit_price || 0)}</td>
          <td class="table-actions-cell">
            <button
              class="btn btn-danger btn-xs"
              type="button"
              data-delete-item-template-price-id="${Number(row.id)}"
              data-item-template-id="${Number(item.id)}"
              aria-label="Удалить цену за ${escapeHtml(core.formatDateRu(row.recorded_at))}"
            >Удалить</button>
          </td>
        </tr>
      `).join("");
    }

    async function deleteItemTemplatePriceFlow(templateId, priceId) {
      const normalizedTemplateId = Number(templateId || 0);
      const normalizedPriceId = Number(priceId || 0);
      const item = (state.itemCatalogItems || []).find(
        (row) => Number(row?.id || 0) === normalizedTemplateId,
      );
      if (!item || !normalizedPriceId) {
        return;
      }
      let savedItem = null;
      core.runDestructiveAction({
        confirmTitle: "Удалить цену из истории?",
        confirmMessage: "Запись исчезнет из хронологии цен. Цена в уже сохраненной операции не изменится.",
        confirmLabel: "Удалить цену",
        doDelete: async () => {
          savedItem = await core.requestJson(
            `/api/v1/operations/item-templates/${normalizedTemplateId}/prices/${normalizedPriceId}`,
            {
              method: "DELETE",
              headers: core.authHeaders(),
            },
          );
          core.invalidateUiRequestCache("item-catalog");
          applySavedItemCatalogItem?.(savedItem);
          applySavedReceiptTemplateHint?.(savedItem);
        },
        onAfterDelete: async () => {
          if (Number(state.editItemTemplateId || 0) === normalizedTemplateId) {
            if (el.itemTemplatePrice) {
              el.itemTemplatePrice.value = savedItem?.latest_unit_price ?? "";
              el.itemTemplatePrice.dispatchEvent(new Event("input", { bubbles: true }));
            }
            if (el.itemTemplatePriceDate) {
              core.syncDateFieldValue(
                el.itemTemplatePriceDate,
                savedItem?.latest_price_date || core.getTodayIso(),
              );
            }
          }
          await openItemTemplateHistoryModal(savedItem || item);
          core.setStatus("Цена удалена из истории");
        },
        onDeleteError: "Не удалось удалить цену",
      });
    }

    function closeItemTemplateHistoryModal() {
      if (el.itemTemplateHistoryModal) {
        el.itemTemplateHistoryModal.classList.add("hidden");
        core.markModalClosed?.(el.itemTemplateHistoryModal);
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
      deleteItemTemplatePriceFlow,
    };
  }

  window.App.registerRuntimeModule?.("item-catalog-sources-factory", createItemCatalogSourcesFeature);
})();
