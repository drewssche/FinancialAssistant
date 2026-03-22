(() => {
  function toggleItemCatalogCardMenu({ trigger, pickerUtils }) {
    if (!trigger) {
      return false;
    }
    const mobileMenuId = String(trigger.dataset.mobileCardMenuTrigger || "");
    const tableMenuId = String(trigger.dataset.tableMenuTrigger || "");
    const menu = mobileMenuId
      ? document.querySelector(`.mobile-card-actions-popover[data-mobile-card-menu="${CSS.escape(mobileMenuId)}"]`)
      : tableMenuId
        ? document.querySelector(`.table-kebab-popover[data-table-menu="${CSS.escape(tableMenuId)}"]`)
        : null;
    if (!menu || !pickerUtils?.setPopoverOpen) {
      return false;
    }
    const ownerCard = trigger.closest(".item-catalog-mobile-item-card, .item-catalog-mobile-group-card");
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

  function parseRowItem(row) {
    if (!row) {
      return null;
    }
    try {
      return JSON.parse(row.dataset.itemTemplate || "{}");
    } catch {
      return null;
    }
  }

  function handleItemCatalogBodyClick({
    event,
    pickerUtils,
    handleItemCatalogBodyClickAction,
    deleteItemSourceFlow,
    openEditSourceGroupModalAction,
    deleteItemTemplateFlow,
    openItemTemplateModalAction,
    openItemTemplateHistoryModalAction,
    setStatus,
  }) {
    const menuTrigger = event.target.closest("button[data-mobile-card-menu-trigger], button[data-table-menu-trigger]");
    if (menuTrigger) {
      toggleItemCatalogCardMenu({ trigger: menuTrigger, pickerUtils });
      return true;
    }
    const deleteSourceBtn = event.target.closest("button[data-delete-item-source-name]");
    if (deleteSourceBtn) {
      deleteItemSourceFlow?.(deleteSourceBtn.dataset.deleteItemSourceName || "").catch((err) => setStatus?.(String(err)));
      return true;
    }
    const editSourceBtn = event.target.closest("button[data-edit-item-source-name]");
    if (editSourceBtn) {
      openEditSourceGroupModalAction?.(editSourceBtn.dataset.editItemSourceName || "");
      return true;
    }
    const deleteBtn = event.target.closest("button[data-delete-item-template-id]");
    if (deleteBtn) {
      const item = parseRowItem(deleteBtn.closest("tr"));
      if (item?.id) {
        deleteItemTemplateFlow?.(item).catch((err) => setStatus?.(String(err)));
      }
      return true;
    }
    const editBtn = event.target.closest("button[data-edit-item-template-id]");
    if (editBtn) {
      const item = parseRowItem(editBtn.closest("tr"));
      if (item?.id) {
        openItemTemplateModalAction?.(item);
      }
      return true;
    }
    const historyBtn = event.target.closest("button[data-item-template-history-id]");
    if (historyBtn) {
      const item = parseRowItem(historyBtn.closest("tr"));
      if (item?.id) {
        openItemTemplateHistoryModalAction?.(item).catch((err) => setStatus?.(String(err)));
      }
      return true;
    }
    const itemRow = event.target.closest("tr[data-item-template-open-id]");
    if (itemRow && !event.target.closest("button, a, input, select, textarea, label, .app-popover")) {
      const item = parseRowItem(itemRow);
      if (item?.id) {
        openItemTemplateModalAction?.(item);
      }
      return true;
    }
    handleItemCatalogBodyClickAction?.(event);
    return true;
  }

  const api = {
    toggleItemCatalogCardMenu,
    handleItemCatalogBodyClick,
  };

  window.App.registerRuntimeModule?.("item-catalog-ui-coordinator", api);
})();
