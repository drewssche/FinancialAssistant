(() => {
  function createOperationModalDebtFeature(deps) {
    const {
      state,
      el,
      core,
      updateCreatePreview,
      setCreateModalActivity,
      openCreateModal,
      selectDebtCounterparty,
      renderDebtCounterpartyPicker,
      closeDebtCounterpartyPopover,
      syncSelectableCurrencyFields,
      applyDebtCurrencyUi,
      updateDebtDueHint,
    } = deps;

    function setDebtDirection(direction) {
      const nextDirection = direction === "borrow" ? "borrow" : "lend";
      if (el.debtDirection) {
        el.debtDirection.value = nextDirection;
      }
      core.syncSegmentedActive(el.createDebtDirectionSwitch, "debt-direction", nextDirection);
      updateCreatePreview();
    }

    function resetCreateDebtFields() {
      closeDebtCounterpartyPopover();
      if (el.debtCounterparty) {
        el.debtCounterparty.value = "";
      }
      if (el.debtPrincipal) {
        el.debtPrincipal.value = "";
      }
      syncSelectableCurrencyFields();
      if (el.debtCurrency) {
        el.debtCurrency.value = core.getCurrencyConfig?.().code || "BYN";
      }
      if (el.debtStartDate) {
        el.debtStartDate.value = "";
      }
      if (el.debtDueDate) {
        el.debtDueDate.value = "";
      }
      if (el.debtNote) {
        el.debtNote.value = "";
      }
      setDebtDirection("lend");
      applyDebtCurrencyUi();
      updateDebtDueHint();
    }

    function prepareDebtEntryMode({ isDebt, submit } = {}) {
      if (el.debtCounterparty) {
        el.debtCounterparty.required = Boolean(isDebt);
      }
      if (el.debtPrincipal) {
        el.debtPrincipal.required = Boolean(isDebt);
      }
      if (el.debtStartDate) {
        el.debtStartDate.required = Boolean(isDebt);
      }
      if (!isDebt) {
        return;
      }
      if (el.debtStartDate && !el.debtStartDate.value) {
        core.syncDateFieldValue(el.debtStartDate, core.getTodayIso());
      }
      renderDebtCounterpartyPicker();
      if (submit) {
        submit.textContent = state.editDebtCreateId ? "Сохранить долг" : "Создать долг";
      }
    }

    async function openCreateModalForDebtEdit(payload) {
      if (!payload?.id) {
        return;
      }
      await openCreateModal({ entryMode: "debt" });
      state.editDebtCreateId = Number(payload.id);
      setCreateModalActivity("debt", payload.id);
      if (el.createEntryModeSwitch) {
        el.createEntryModeSwitch.classList.add("hidden");
      }
      const createTitle = document.getElementById("createTitle");
      if (createTitle) {
        createTitle.textContent = "Редактировать долг";
      }
      const submit = document.getElementById("submitCreateOperationBtn");
      if (submit) {
        submit.textContent = "Сохранить долг";
      }
      selectDebtCounterparty(payload.counterparty || "", { keepOpen: false });
      if (el.debtPrincipal) {
        el.debtPrincipal.value = payload.principal || "";
      }
      syncSelectableCurrencyFields({ debtCurrency: payload.currency || "" });
      if (el.debtCurrency) {
        el.debtCurrency.value = payload.currency || (core.getCurrencyConfig?.().code || "BYN");
      }
      core.syncDateFieldValue(el.debtStartDate, payload.start_date || core.getTodayIso());
      core.syncDateFieldValue(el.debtDueDate, payload.due_date || "");
      if (el.debtNote) {
        el.debtNote.value = payload.note || "";
      }
      setDebtDirection(payload.direction || "lend");
      applyDebtCurrencyUi();
      updateDebtDueHint();
      renderDebtCounterpartyPicker();
      updateCreatePreview();
    }

    return {
      setDebtDirection,
      resetCreateDebtFields,
      prepareDebtEntryMode,
      openCreateModalForDebtEdit,
    };
  }

  window.App.registerRuntimeModule?.("operation-modal-debt-factory", createOperationModalDebtFeature);
})();
