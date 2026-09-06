(() => {
  const { state, el, core } = window.App;

  function reset() {
    state.editDebtMovement = null;
    el.editModal?.classList.remove("editing-debt-movement");
    if (el.editCurrency) el.editCurrency.disabled = false;
  }

  async function open(debtId, flowId) {
    const match = /^debt-(issuance|repayment):(\d+)$/.exec(String(flowId || ""));
    if (!match || !(Number(debtId) > 0)) throw new Error("Не удалось определить движение долга");
    const url = `/api/v1/debts/${Number(debtId)}/movements/${match[1]}/${Number(match[2])}`;
    const item = await core.requestJson(url, { headers: core.authHeaders() });
    const modal = window.App.getRuntimeModule?.("operation-modal");
    modal.closeEditModal();
    state.editDebtMovement = { ...item, url };
    document.getElementById("editTitle").textContent = "Редактировать операцию";
    document.getElementById("editDebtMovementContext").textContent = `${item.title} · ${item.counterparty}`;
    document.getElementById("editAmount").value = item.amount;
    core.syncDateFieldValue(document.getElementById("editDate"), item.event_date);
    document.getElementById("editNote").value = item.note || "";
    el.editKind.value = item.flow_direction === "inflow" ? "income" : "expense";
    if (![...el.editCurrency.options].some((option) => option.value === item.currency)) {
      el.editCurrency.add(new Option(item.currency, item.currency));
    }
    el.editCurrency.value = item.currency;
    el.editCurrency.disabled = true;
    window.App.getRuntimeModule?.("activity")?.configureActivityButton?.(el.editModalActivityBtn, "debt", item.debt_id);
    el.editModal.classList.add("editing-debt-movement");
    el.editModal.classList.remove("hidden");
    core.bringModalToFront?.(el.editModal);
  }

  async function save() {
    const context = state.editDebtMovement;
    if (!context) return;
    const amount = core.resolveMoneyInput(document.getElementById("editAmount").value);
    const eventDate = core.parseDateInputValue(document.getElementById("editDate").value);
    if (!amount.valid || !(amount.value > 0)) throw new Error("Укажите сумму больше нуля");
    if (!eventDate) throw new Error("Проверьте дату операции");
    const saved = await core.requestJson(context.url, {
      method: "PATCH",
      headers: core.authHeaders(),
      body: JSON.stringify({
        amount: amount.value,
        event_date: eventDate,
        note: document.getElementById("editNote").value || null,
      }),
    });
    if (state.editDebtMovement === context) {
      state.editDebtMovement = { ...saved, url: context.url };
      document.getElementById("editAmount").value = saved.amount;
      core.syncDateFieldValue(document.getElementById("editDate"), saved.event_date);
      document.getElementById("editNote").value = saved.note || "";
    }
    for (const prefix of ["operations", "debts", "dashboard", "analytics"]) {
      core.invalidateUiRequestCache?.(prefix);
    }
    window.App.getRuntimeModule?.("dashboard-data")?.invalidateSummaryCache?.();
    state.debtsSectionHydrated = false;
    const operations = window.App.getRuntimeModule?.("operations");
    operations.invalidateAllTimeAnchor();
    await Promise.all([
      operations.loadOperations({ reset: true, force: true }),
      operations.refreshAfterDebtMutation(),
    ]);
  }

  window.App.registerRuntimeModule?.("debt-movement-editor", { open, save, reset });
})();
