(() => {
  const { state, el, core, actions } = window.App;
  let bound = false;
  let debtsObserver = null;
  let historyObserver = null;

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

    if (el.debtsCards && actions.openDebtRepaymentModal) {
      el.debtsCards.addEventListener("click", (event) => {
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
        if (!btn || btn.disabled) {
          return;
        }
        actions.openDebtRepaymentModal(Number(btn.dataset.repayDebtId || 0));
      });
    }
    if (actions.openDebtRepaymentModal) {
      document.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-repay-debt-id]");
        if (!btn || btn.disabled) {
          return;
        }
        if (!btn.closest("#debtsCards") && !btn.closest("#dashboardDebtsList")) {
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
