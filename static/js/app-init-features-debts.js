(() => {
  const { state, el, core, actions } = window.App;
  const pickerUtils = window.App.pickerUtils;
  let bound = false;
  let debtsObserver = null;
  let historyObserver = null;

  function toggleDebtMenu(trigger) {
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
      return false;
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

  function bindDebtFeatureHandlers() {
    if (bound) {
      return;
    }
    bound = true;
    let debtSearchDebounceId = null;

    if (el.debtStatusTabs && actions.setDebtStatusFilter) {
      el.debtStatusTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-debt-status]");
        if (!btn) {
          return;
        }
        actions.setDebtStatusFilter(btn.dataset.debtStatus);
      });
    }

    if (el.debtSortTabs && actions.setDebtSortPreset) {
      el.debtSortTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-debt-sort]");
        if (!btn) {
          return;
        }
        actions.setDebtSortPreset(btn.dataset.debtSort);
      });
    }

    if (el.debtSearchQ && actions.applyDebtSearch) {
      el.debtSearchQ.addEventListener("input", () => {
        if (debtSearchDebounceId) {
          clearTimeout(debtSearchDebounceId);
        }
        debtSearchDebounceId = setTimeout(() => {
          actions.applyDebtSearch().catch((err) => core.setStatus(String(err)));
        }, 250);
      });
    }

    if (el.deleteAllDebtsBtn && actions.deleteAllDebtsFlow) {
      el.deleteAllDebtsBtn.addEventListener("click", () => {
        if (el.deleteAllDebtsBtn.disabled) {
          return;
        }
        actions.deleteAllDebtsFlow();
      });
    }

    if (el.debtsCards && actions.openDebtRepaymentModal) {
      el.debtsCards.addEventListener("click", (event) => {
        const menuTrigger = event.target.closest("button[data-mobile-card-menu-trigger], button[data-table-menu-trigger]");
        if (menuTrigger) {
          toggleDebtMenu(menuTrigger);
          return;
        }
        const editBtn = event.target.closest("button[data-edit-debt-id]");
        if (editBtn && actions.openEditDebtModal) {
          actions.openEditDebtModal(Number(editBtn.dataset.editDebtId || 0));
          return;
        }

        const historyBtn = event.target.closest("button[data-history-debt-id]");
        if (historyBtn && actions.openDebtHistoryModal) {
          actions.openDebtHistoryModal(Number(historyBtn.dataset.historyDebtId || 0));
          return;
        }

        const deleteBtn = event.target.closest("button[data-delete-debt-id]");
        if (deleteBtn && actions.deleteDebtFlow) {
          actions.deleteDebtFlow(Number(deleteBtn.dataset.deleteDebtId || 0));
          return;
        }

        const btn = event.target.closest("button[data-repay-debt-id]");
        if (btn && !btn.disabled) {
          actions.openDebtRepaymentModal(Number(btn.dataset.repayDebtId || 0));
          return;
        }

        const row = event.target.closest("tr[data-debt-row-id]");
        const mobileRow = event.target.closest(".debt-mobile-entry[data-debt-row-id]");
        const targetRow = row || mobileRow;
        if (!targetRow) {
          return;
        }
        if (event.target.closest("button, a, input, select, textarea, label, .app-popover")) {
          return;
        }
        if (actions.openEditDebtModal) {
          actions.openEditDebtModal(Number(targetRow.dataset.debtRowId || 0));
        }
      });
    }
    if (actions.openDebtRepaymentModal) {
      document.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-repay-debt-id]");
        if (!btn || btn.disabled) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        actions.openDebtRepaymentModal(Number(btn.dataset.repayDebtId || 0));
      }, true);
      document.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-dashboard-repay-debt-id]");
        if (!btn || btn.disabled) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        actions.openDebtRepaymentModal(Number(btn.dataset.dashboardRepayDebtId || 0));
      }, true);
    }
    if (actions.openDebtHistoryModal) {
      document.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-dashboard-history-debt-id]");
        if (!btn) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        actions.openDebtHistoryModal(Number(btn.dataset.dashboardHistoryDebtId || 0));
      }, true);
    }
    if (actions.openEditDebtModal) {
      document.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-edit-debt-id]");
        if (!btn) {
          return;
        }
        if (!btn.closest("#debtsCards")) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        actions.openEditDebtModal(Number(btn.dataset.editDebtId || 0));
      }, true);
    }
    if (actions.openDebtHistoryModal) {
      document.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-history-debt-id]");
        if (!btn) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        actions.openDebtHistoryModal(Number(btn.dataset.historyDebtId || 0));
      }, true);
    }

    if (el.debtRepaymentForm && actions.submitDebtRepayment) {
      el.debtRepaymentForm.addEventListener("submit", (event) => {
        core.runAction({
          button: event.submitter || el.submitDebtRepaymentBtn,
          pendingText: "Сохранение...",
          successMessage: "Погашение добавлено",
          errorPrefix: "Ошибка добавления погашения",
          action: () => actions.submitDebtRepayment(event),
        });
      });
    }

    if (el.repaymentPresetRow && el.repaymentAmount) {
      el.repaymentPresetRow.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-repayment-preset]");
        if (!btn) {
          return;
        }
        const ratio = Number(btn.dataset.repaymentPreset || 0);
        const debtId = Number(el.repaymentDebtId?.value || 0);
        let outstanding = 0;
        if (debtId > 0) {
          for (const card of window.App.state.debtCardsCache || []) {
            const debt = (card.debts || []).find((item) => Number(item.id || 0) === debtId);
            if (debt) {
              outstanding = Number(debt.outstanding_total || 0);
              break;
            }
          }
        }
        if (!Number.isFinite(ratio) || ratio <= 0 || !Number.isFinite(outstanding) || outstanding <= 0) {
          return;
        }
        el.repaymentAmount.value = (outstanding * ratio).toFixed(2);
        if (actions.updateRepaymentDeltaHint) {
          actions.updateRepaymentDeltaHint();
        }
      });
    }
    if (el.repaymentAmount && actions.updateRepaymentDeltaHint) {
      el.repaymentAmount.addEventListener("input", () => {
        actions.updateRepaymentDeltaHint();
      });
    }

    if (el.debtsInfiniteSentinel && "IntersectionObserver" in window && actions.loadMoreDebtCards) {
      if (debtsObserver) {
        debtsObserver.disconnect();
      }
      debtsObserver = new IntersectionObserver(
        (entries) => {
          const entry = entries[0];
          if (!entry?.isIntersecting) {
            return;
          }
          if (state.activeSection !== "debts") {
            return;
          }
          if (!state.debtCardsHasMore) {
            return;
          }
          actions.loadMoreDebtCards();
        },
        {
          root: null,
          rootMargin: "240px 0px",
          threshold: 0,
        },
      );
      debtsObserver.observe(el.debtsInfiniteSentinel);
    }

    if (el.debtHistoryInfiniteSentinel && "IntersectionObserver" in window && actions.loadMoreDebtHistoryEvents) {
      if (historyObserver) {
        historyObserver.disconnect();
      }
      historyObserver = new IntersectionObserver(
        (entries) => {
          const entry = entries[0];
          if (!entry?.isIntersecting) {
            return;
          }
          if (el.debtHistoryModal?.classList.contains("hidden")) {
            return;
          }
          if (!state.debtHistoryHasMore) {
            return;
          }
          actions.loadMoreDebtHistoryEvents();
        },
        {
          root: el.debtHistoryList || null,
          rootMargin: "180px 0px",
          threshold: 0,
        },
      );
      historyObserver.observe(el.debtHistoryInfiniteSentinel);
    }

  }

  window.App.initFeatureDebts = {
    bindDebtFeatureHandlers,
  };
})();
