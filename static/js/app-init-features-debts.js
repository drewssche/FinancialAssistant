(() => {
  const { state, el, core, actions } = window.App;
  const pickerUtils = window.App.getRuntimeModule?.("picker-utils");
  const debtsUiCoordinator = window.App.getRuntimeModule?.("debts-ui-coordinator");
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
        const debtFeature = window.App.getRuntimeModule?.("debts") || {};
        const closedRowsToggle = event.target.closest("button[data-debt-closed-toggle-counterparty-id]");
        if (closedRowsToggle) {
          debtFeature.toggleDebtClosedRows?.(Number(closedRowsToggle.dataset.debtClosedToggleCounterpartyId || 0));
          return;
        }
        const retryButton = event.target.closest("button[data-debts-retry]");
        if (retryButton) {
          core.runAction({
            button: retryButton,
            pendingText: "Загрузка…",
            errorPrefix: "Не удалось загрузить долги",
            action: () => debtFeature.loadDebtsCards?.({ force: true }),
          });
          return;
        }
        debtsUiCoordinator?.handleDebtsCardsClick?.({
          event,
          pickerUtils,
          openEditDebtModal: actions.openEditDebtModal,
          openDebtHistoryModal: actions.openDebtHistoryModal,
          openDebtForgivenessModal: debtFeature.openDebtForgivenessModal,
          deleteDebtFlow: actions.deleteDebtFlow,
          openDebtRepaymentModal: actions.openDebtRepaymentModal,
          openDebtIssuanceModal: actions.openDebtIssuanceModal,
        });
      });
    }
    if (actions.openDebtIssuanceModal) {
      document.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-add-debt-issuance-id]");
        if (!btn || btn.disabled) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        debtsUiCoordinator?.closeDebtActionPopover?.({ event, pickerUtils });
        actions.openDebtIssuanceModal(Number(btn.dataset.addDebtIssuanceId || 0));
      }, true);
    }
    if (actions.openDebtRepaymentModal) {
      document.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-repay-debt-id]");
        if (!btn || btn.disabled) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        debtsUiCoordinator?.closeDebtActionPopover?.({ event, pickerUtils });
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
        debtsUiCoordinator?.closeDebtActionPopover?.({ event, pickerUtils });
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
        debtsUiCoordinator?.closeDebtActionPopover?.({ event, pickerUtils });
        actions.openDebtHistoryModal(Number(btn.dataset.historyDebtId || 0));
      }, true);
    }
    {
      document.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-forgive-debt-id]");
        const debtFeature = window.App.getRuntimeModule?.("debts") || {};
        if (!debtFeature.openDebtForgivenessModal) {
          return;
        }
        if (!btn || btn.disabled) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        debtsUiCoordinator?.closeDebtActionPopover?.({ event, pickerUtils });
        debtFeature.openDebtForgivenessModal(Number(btn.dataset.forgiveDebtId || 0));
      }, true);
      document.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-dashboard-forgive-debt-id]");
        const debtFeature = window.App.getRuntimeModule?.("debts") || {};
        if (!debtFeature.openDebtForgivenessModal) {
          return;
        }
        if (!btn || btn.disabled) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        debtFeature.openDebtForgivenessModal(Number(btn.dataset.dashboardForgiveDebtId || 0));
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
    if (el.debtIssuanceForm && actions.submitDebtIssuance) {
      el.debtIssuanceForm.addEventListener("submit", (event) => {
        core.runAction({
          button: event.submitter || el.submitDebtIssuanceBtn,
          pendingText: "Добавление...",
          successMessage: "Сумма добавлена",
          errorPrefix: "Ошибка добавления суммы",
          action: () => actions.submitDebtIssuance(event),
        });
      });
    }
    if (el.forgiveDebtFromRepaymentBtn) {
      el.forgiveDebtFromRepaymentBtn.addEventListener("click", () => {
        const debtFeature = window.App.getRuntimeModule?.("debts") || {};
        debtFeature.forgiveDebtFromRepaymentFlow?.().catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.debtForgivenessForm) {
      el.debtForgivenessForm.addEventListener("submit", (event) => {
        const debtFeature = window.App.getRuntimeModule?.("debts") || {};
        core.runAction({
          button: event.submitter || el.submitDebtForgivenessBtn,
          pendingText: "Списание...",
          successMessage: "Долг обновлен",
          errorPrefix: "Ошибка прощения долга",
          action: () => debtFeature.submitDebtForgiveness?.(event),
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
    if (el.issuanceAmount && actions.updateIssuanceDeltaHint) {
      el.issuanceAmount.addEventListener("input", () => {
        actions.updateIssuanceDeltaHint();
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

  const api = {
    bindDebtFeatureHandlers,
  };

  window.App.initFeatureDebts = api;
  window.App.registerFeatureInitModule?.("debts", api);
})();
