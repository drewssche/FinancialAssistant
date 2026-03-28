(() => {
  window.App = window.App || {};

  function toggleDebtMenu({ event, pickerUtils }) {
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
    const ownerCard = trigger.closest(".debt-mobile-entry");
    const ownerRow = trigger.closest("tr");
    const ownerCell = trigger.closest("td");
    const ownerWrap = trigger.closest(".debt-card-children-wrap");
    if (!menu || !pickerUtils?.setPopoverOpen) {
      return true;
    }
    const owners = [trigger, trigger.parentElement].filter(Boolean);
    const clearOpenState = () => {
      ownerCard?.classList.remove("mobile-card-menu-open");
      ownerCell?.classList.remove("mobile-card-menu-open-cell");
      ownerRow?.classList.remove("mobile-card-menu-open-row");
      ownerCell?.classList.remove("table-menu-open-cell");
      ownerRow?.classList.remove("table-menu-open-row");
      ownerWrap?.classList.remove("debt-menu-open-wrap");
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
        node.closest(".debt-menu-open-wrap")?.classList.remove("debt-menu-open-wrap");
      }
    });
    pickerUtils.setPopoverOpen(menu, shouldOpen, { owners, onClose: clearOpenState });
    ownerCard?.classList.toggle("mobile-card-menu-open", shouldOpen);
    ownerCell?.classList.toggle("mobile-card-menu-open-cell", shouldOpen);
    ownerRow?.classList.toggle("mobile-card-menu-open-row", shouldOpen);
    ownerCell?.classList.toggle("table-menu-open-cell", shouldOpen);
    ownerRow?.classList.toggle("table-menu-open-row", shouldOpen);
    ownerWrap?.classList.toggle("debt-menu-open-wrap", shouldOpen);
    if (!shouldOpen) {
      clearOpenState();
      trigger?.blur?.();
    }
    return true;
  }

  function closeDebtActionPopover({ event, pickerUtils }) {
    const menu = event.target.closest(".mobile-card-actions-popover, .table-kebab-popover");
    if (!menu || !pickerUtils?.setPopoverOpen) {
      return;
    }
    const owners = Array.isArray(menu.__appPopoverOwners) ? menu.__appPopoverOwners : [];
    const onClose = typeof menu.__appPopoverOnClose === "function" ? menu.__appPopoverOnClose : null;
    pickerUtils.setPopoverOpen(menu, false, { owners });
    if (onClose) {
      onClose();
    }
    owners.forEach((owner) => owner?.blur?.());
  }

  function handleDebtsCardsClick({
    event,
    pickerUtils,
    openEditDebtModal,
    openDebtHistoryModal,
    openDebtForgivenessModal,
    deleteDebtFlow,
    openDebtRepaymentModal,
  }) {
    if (toggleDebtMenu({ event, pickerUtils })) {
      return true;
    }
    const editBtn = event.target.closest("button[data-edit-debt-id]");
    if (editBtn) {
      closeDebtActionPopover({ event, pickerUtils });
      openEditDebtModal?.(Number(editBtn.dataset.editDebtId || 0));
      return true;
    }

    const historyBtn = event.target.closest("button[data-history-debt-id]");
    if (historyBtn) {
      closeDebtActionPopover({ event, pickerUtils });
      openDebtHistoryModal?.(Number(historyBtn.dataset.historyDebtId || 0));
      return true;
    }

    const deleteBtn = event.target.closest("button[data-delete-debt-id]");
    if (deleteBtn) {
      closeDebtActionPopover({ event, pickerUtils });
      deleteDebtFlow?.(Number(deleteBtn.dataset.deleteDebtId || 0));
      return true;
    }

    const forgiveBtn = event.target.closest("button[data-forgive-debt-id]");
    if (forgiveBtn && !forgiveBtn.disabled) {
      closeDebtActionPopover({ event, pickerUtils });
      openDebtForgivenessModal?.(Number(forgiveBtn.dataset.forgiveDebtId || 0));
      return true;
    }

    const repayBtn = event.target.closest("button[data-repay-debt-id]");
    if (repayBtn && !repayBtn.disabled) {
      closeDebtActionPopover({ event, pickerUtils });
      openDebtRepaymentModal?.(Number(repayBtn.dataset.repayDebtId || 0));
      return true;
    }

    const row = event.target.closest("tr[data-debt-row-id]");
    const mobileRow = event.target.closest(".debt-mobile-entry[data-debt-row-id]");
    const targetRow = row || mobileRow;
    if (!targetRow) {
      return false;
    }
    if (event.target.closest("button, a, input, select, textarea, label, .app-popover")) {
      return true;
    }
    openEditDebtModal?.(Number(targetRow.dataset.debtRowId || 0));
    return true;
  }

  const api = {
    toggleDebtMenu,
    closeDebtActionPopover,
    handleDebtsCardsClick,
  };

  window.App.registerRuntimeModule?.("debts-ui-coordinator", api);
})();
