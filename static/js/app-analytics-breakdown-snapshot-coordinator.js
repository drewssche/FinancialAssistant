(() => {
  function buildCategoryBreakdownSnapshot({
    data,
    state,
    hiddenBreakdownKeys,
    breakdownItemKey,
    formatDateRu,
  }) {
    const items = Array.isArray(data.category_breakdown) ? data.category_breakdown : [];
    const selectedKind = data.category_breakdown_kind || state.analyticsCategoryKind || "expense";
    const selectedLevel = data.category_breakdown_level || state.analyticsBreakdownLevel || "category";
    const hiddenKeys = hiddenBreakdownKeys(selectedLevel, selectedKind);
    let chartIndex = 0;
    const listItems = items.map((item, idx) => {
      const key = breakdownItemKey(selectedLevel, item);
      const isVisible = !hiddenKeys.has(key);
      return {
        ...item,
        palette_index: idx,
        breakdown_key: key,
        is_visible_in_chart: isVisible,
        chart_index: isVisible ? chartIndex++ : null,
      };
    });
    const visibleItems = listItems.filter((item) => item.is_visible_in_chart);
    const chartTotal = visibleItems.reduce((acc, item) => acc + Number(item.total_amount || 0), 0);
    const totalOps = visibleItems.reduce((acc, item) => acc + Number(item.operations_count || 0), 0);
    const incomeTotal = Number(data.income_total || 0);
    const expenseTotal = Number(data.expense_total || 0);
    return {
      payload: data,
      items: visibleItems,
      listItems,
      kind: selectedKind,
      level: selectedLevel,
      total: chartTotal,
      totalOps,
      periodLabel: `${formatDateRu(data.date_from)} - ${formatDateRu(data.date_to)}`,
      defaultTitle: selectedKind === "all" ? "Доходы + расходы" : "Итог периода",
      defaultIncomeTotal: incomeTotal,
      defaultExpenseTotal: expenseTotal,
      defaultIndex: null,
      hoveredIndex: null,
    };
  }

  function buildDashboardBreakdownSnapshot({ data, state, formatDateRu }) {
    const items = Array.isArray(data.category_breakdown) ? data.category_breakdown : [];
    const total = items.reduce((acc, item) => acc + Number(item.total_amount || 0), 0);
    const totalOps = items.reduce((acc, item) => acc + Number(item.operations_count || 0), 0);
    const selectedKind = data.category_breakdown_kind || state.dashboardCategoryKind || "expense";
    const selectedLevel = data.category_breakdown_level || state.dashboardBreakdownLevel || "category";
    const incomeTotal = Number(data.income_total || 0);
    const expenseTotal = Number(data.expense_total || 0);
    return {
      items,
      kind: selectedKind,
      level: selectedLevel,
      total,
      totalOps,
      periodLabel: `${formatDateRu(data.date_from)} - ${formatDateRu(data.date_to)}`,
      defaultTitle: selectedKind === "all" ? "Доходы + расходы" : "Итог периода",
      defaultIncomeTotal: incomeTotal,
      defaultExpenseTotal: expenseTotal,
      defaultIndex: null,
      hoveredIndex: null,
    };
  }

  const api = {
    buildCategoryBreakdownSnapshot,
    buildDashboardBreakdownSnapshot,
  };

  window.App.registerRuntimeModule?.("analytics-breakdown-snapshot-coordinator", api);
})();
