(() => {
  const { state, el, core } = window.App;
  const operationModal = window.App.operationModal;
  const getCategoryMetaById = operationModal.getCategoryMetaById;

  async function loadDashboard() {
    const { dateFrom, dateTo } = core.getPeriodBounds(state.period);
    const params = new URLSearchParams();
    params.set("period", state.period);
    params.set("date_from", dateFrom);
    params.set("date_to", dateTo);

    const data = await core.requestJson(`/api/v1/dashboard/summary?${params.toString()}`, {
      headers: core.authHeaders(),
    });

    el.incomeTotal.textContent = data.income_total;
    el.expenseTotal.textContent = data.expense_total;
    el.balanceTotal.textContent = data.balance;
  }

  async function loadDashboardOperations() {
    const { dateFrom, dateTo } = core.getPeriodBounds(state.period);
    el.dashboardPeriodLabel.textContent = core.formatPeriodLabel(dateFrom, dateTo);
    const params = new URLSearchParams({
      page: "1",
      page_size: "8",
      sort_by: "operation_date",
      sort_dir: "desc",
      date_from: dateFrom,
      date_to: dateTo,
    });

    const data = await core.requestJson(`/api/v1/operations?${params.toString()}`, { headers: core.authHeaders() });
    el.dashboardOperationsBody.innerHTML = "";

    if (!data.items.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="5">Нет операций за выбранный период</td>';
      el.dashboardOperationsBody.appendChild(row);
      return;
    }

    for (const item of data.items) {
      el.dashboardOperationsBody.appendChild(
        core.createOperationRow(item, {
          compact: true,
          selectable: false,
          category: getCategoryMetaById(item.category_id),
        }),
      );
    }
  }

  window.App.featureDashboard = {
    loadDashboard,
    loadDashboardOperations,
  };
})();
