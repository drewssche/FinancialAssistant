(() => {
  const { state, el, core, actions } = window.App;
  const pickerUtils = window.App.getRuntimeModule?.("picker-utils");

    function toggleTableMenu(trigger) {
    const menuId = String(trigger?.dataset.tableMenuTrigger || "");
    const menu = menuId ? document.querySelector(`.table-kebab-popover[data-table-menu="${CSS.escape(menuId)}"]`) : null;
    const ownerRow = trigger.closest("tr");
    const ownerCell = trigger.closest("td");
    if (!menu || !pickerUtils?.setPopoverOpen) {
      return false;
    }
      const owners = [trigger, trigger.parentElement].filter(Boolean);
      const clearOpenState = () => {
        ownerCell?.classList.remove("table-menu-open-cell");
        ownerRow?.classList.remove("table-menu-open-row");
      };
      const shouldOpen = menu.classList.contains("hidden");
    document.querySelectorAll(".table-kebab-popover:not(.hidden)").forEach((node) => {
      if (node !== menu) {
        pickerUtils.setPopoverOpen(node, false, {
          owners: Array.isArray(node.__appPopoverOwners) ? node.__appPopoverOwners : [],
        });
        (Array.isArray(node.__appPopoverOwners) ? node.__appPopoverOwners : []).forEach((owner) => owner?.blur?.());
        node.closest(".table-menu-open-cell")?.classList.remove("table-menu-open-cell");
        node.closest(".table-menu-open-row")?.classList.remove("table-menu-open-row");
      }
    });
      pickerUtils.setPopoverOpen(menu, shouldOpen, { owners, onClose: clearOpenState });
      ownerCell?.classList.toggle("table-menu-open-cell", shouldOpen);
      ownerRow?.classList.toggle("table-menu-open-row", shouldOpen);
      if (!shouldOpen) {
        clearOpenState();
        trigger?.blur?.();
      }
      return true;
  }

  function bindOperationsFeatureHandlers(getOperationsObserver, setOperationsObserver) {
    let filterDebounceId = null;

    el.kindFilters.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-kind]");
      if (!btn) {
        return;
      }
      state.filterKind = btn.dataset.kind;
      core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
      core.runAction({
        errorPrefix: "Ошибка применения фильтра",
        action: () => actions.applyFilters(),
      });
    });

    if (el.clearOperationsCategoryFilterBtn && actions.clearOperationsCategoryFilter) {
      el.clearOperationsCategoryFilterBtn.addEventListener("click", () => {
        core.runAction({
          errorPrefix: "Ошибка сброса фильтра категории",
          action: () => actions.clearOperationsCategoryFilter(),
        });
      });
    }
    if (el.resetOperationsFiltersBtn && actions.resetOperationsFilters) {
      el.resetOperationsFiltersBtn.addEventListener("click", () => {
        core.runAction({
          errorPrefix: "Ошибка сброса фильтров",
          action: () => actions.resetOperationsFilters(),
        });
      });
    }
    if (el.operationsQuickViewTabs && actions.setOperationsQuickView) {
      el.operationsQuickViewTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-operations-quick-view]");
        if (!btn) {
          return;
        }
        if (state.operationsQuickView === btn.dataset.operationsQuickView) {
          return;
        }
        core.runAction({
          errorPrefix: "Ошибка применения быстрого среза",
          action: () => actions.setOperationsQuickView(btn.dataset.operationsQuickView),
        });
      });
    }
    if (el.selectVisibleOperationsBtn && actions.selectVisibleOperations) {
      el.selectVisibleOperationsBtn.addEventListener("click", () => {
        actions.selectVisibleOperations();
      });
    }
    if (el.clearVisibleOperationsSelectionBtn && actions.clearVisibleOperationsSelection) {
      el.clearVisibleOperationsSelectionBtn.addEventListener("click", () => {
        actions.clearVisibleOperationsSelection();
      });
    }
    if (el.quickFilterExpenseBtn && actions.setOperationsKindFilter) {
      el.quickFilterExpenseBtn.addEventListener("click", () => {
        core.runAction({
          errorPrefix: "Ошибка применения фильтра расходов",
          action: () => actions.setOperationsKindFilter("expense"),
        });
      });
    }
    if (el.quickFilterIncomeBtn && actions.setOperationsKindFilter) {
      el.quickFilterIncomeBtn.addEventListener("click", () => {
        core.runAction({
          errorPrefix: "Ошибка применения фильтра доходов",
          action: () => actions.setOperationsKindFilter("income"),
        });
      });
    }
    if (el.quickCustomRangeBtn && actions.openPeriodCustomModal) {
      el.quickCustomRangeBtn.addEventListener("click", () => {
        actions.openPeriodCustomModal();
      });
    }

    el.filterQ.addEventListener("input", () => {
      if (filterDebounceId) {
        clearTimeout(filterDebounceId);
      }
      filterDebounceId = setTimeout(() => {
        core.runAction({
          errorPrefix: "Ошибка поиска",
          action: () => actions.applyRealtimeSearch(),
        });
      }, 300);
    });

    el.createKindSwitch.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-kind]");
      if (!btn) {
        return;
      }
      actions.setOperationKind("create", btn.dataset.kind);
    });

    if (el.createEntryModeSwitch) {
      el.createEntryModeSwitch.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-entry-mode]");
        if (!btn || !actions.setCreateEntryMode) {
          return;
        }
        actions.setCreateEntryMode(btn.dataset.entryMode);
      });
    }

    if (el.createOperationModeSwitch) {
      el.createOperationModeSwitch.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-operation-mode]");
        if (!btn || !actions.setCreateOperationMode) {
          return;
        }
        actions.setCreateOperationMode(btn.dataset.operationMode);
      });
    }

    if (el.createDebtDirectionSwitch) {
      el.createDebtDirectionSwitch.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-debt-direction]");
        if (!btn || !actions.setDebtDirection) {
          return;
        }
        actions.setDebtDirection(btn.dataset.debtDirection);
      });
    }

    el.editKindSwitch.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-kind]");
      if (!btn) {
        return;
      }
      actions.setOperationKind("edit", btn.dataset.kind);
    });

    if (el.editOperationModeSwitch) {
      el.editOperationModeSwitch.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-operation-mode]");
        if (!btn || !actions.setEditOperationMode) {
          return;
        }
        actions.setEditOperationMode(btn.dataset.operationMode);
      });
    }

    el.operationsBody.addEventListener("click", (event) => {
      const menuTrigger = event.target.closest("button[data-table-menu-trigger]");
      if (menuTrigger) {
        toggleTableMenu(menuTrigger);
        return;
      }
      const receiptBtn = event.target.closest("button[data-receipt-view-id]");
      if (receiptBtn) {
        const row = receiptBtn.closest("tr");
        const item = row ? JSON.parse(row.dataset.item || "{}") : null;
        if (item?.id && actions.openOperationReceiptModal) {
          actions.openOperationReceiptModal(item);
        }
        return;
      }
      const deleteBtn = event.target.closest("button[data-delete-id]");
      if (deleteBtn) {
        const row = deleteBtn.closest("tr");
        const item = row ? JSON.parse(row.dataset.item || "{}") : null;
        if (item?.id) {
          actions.deleteOperationFlow(item).catch((err) => core.setStatus(String(err)));
        }
        return;
      }

      const editBtn = event.target.closest("button[data-edit-id]");
      if (editBtn) {
        const row = editBtn.closest("tr");
        const item = row ? JSON.parse(row.dataset.item || "{}") : null;
        if (item?.id) {
          actions.openEditModal(item);
        }
        return;
      }

      const row = event.target.closest("tr[data-operation-row-id]");
      if (!row) {
        return;
      }
      if (event.target.closest("button, a, input, select, textarea, label, .app-popover")) {
        return;
      }
      const item = JSON.parse(row.dataset.item || "{}");
      if (item?.id) {
        actions.openEditModal(item);
      }
    });

    if (el.operationsInfiniteSentinel && "IntersectionObserver" in window) {
      const existingObserver = getOperationsObserver();
      if (existingObserver) {
        existingObserver.disconnect();
      }
      const observer = new IntersectionObserver(
        (entries) => {
          const entry = entries[0];
          if (!entry?.isIntersecting) {
            return;
          }
          if (state.activeSection !== "operations") {
            return;
          }
          if (!state.operationsHasMore || state.operationsLoading) {
            return;
          }
          actions.loadMoreOperations().catch((err) => core.setStatus(String(err)));
        },
        {
          root: null,
          rootMargin: "240px 0px",
          threshold: 0,
        },
      );
      observer.observe(el.operationsInfiniteSentinel);
      setOperationsObserver(observer);
    }
  }

  const api = {
    bindOperationsFeatureHandlers,
  };

  window.App.initFeatureOperations = api;
  window.App.registerFeatureInitModule?.("operations", api);
})();
